"""Durable online assessments orchestrated by Prefect, independent of serving."""

import hashlib
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from mlflow.entities import AssessmentSource, AssessmentSourceType, Feedback
from mlflow.exceptions import MlflowException
from prefect import flow
from prefect.runtime import flow_run
from psycopg.types.json import Jsonb

from ask_phil.answers import AnswerRecord
from ask_phil.evaluation import document_fingerprint
from ask_phil.feedback import FeedbackStore
from ask_phil.feedback_delivery import _tracking
from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.online_evaluation import (
    OnlineCycle,
    OnlineDisagreement,
    OnlineInspection,
    OnlineJob,
    OnlinePolicy,
    OnlineReport,
    OnlineTriage,
    ReviewRequirement,
    check_saved_answer,
    seconds_since,
)
from ask_phil.online_judging import checked_calibration
from ask_phil.openrouter import maximum_call_cost
from ask_phil.semantic_judge import SupportInput, SupportJudge, SupportPassage


class OnlineEvaluation:
    def __init__(
        self,
        database_url: str,
        tracking_uri: str,
        *,
        policy: OnlinePolicy | None = None,
        judge: SupportJudge | None = None,
        calibration: Path | None = None,
        cancellation: Event | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.feedback = FeedbackStore(database_url, tracking_uri=tracking_uri, clock=clock)
        self.tracking_uri = tracking_uri
        self.policy = policy or OnlinePolicy.from_environment()
        self.cancellation = cancellation or Event()
        self.judge = judge
        self.calibration_sha256 = (
            checked_calibration(judge, calibration) if judge and calibration else None
        )
        self.config_sha256 = document_fingerprint(
            {
                "policy": self.policy.model_dump(mode="json"),
                "tracking_sha256": self.feedback.tracking_sha256,
                "calibration_sha256": self.calibration_sha256,
                "judge": judge.chat.profile.model_dump(mode="json") if judge else None,
                "execution": judge.policies.model_dump(mode="json") if judge else None,
                "implementation": {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (
                        Path(__file__),
                        Path(__file__).with_name("online_evaluation.py"),
                        Path(__file__).with_name("online_judging.py"),
                        Path(__file__).with_name("semantic_judge.py"),
                    )
                },
            }
        )

    def ensure_schema(self) -> None:
        self.feedback.ensure_schema()
        with self.feedback.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728202)")
            conn.execute("""CREATE TABLE IF NOT EXISTS online_jobs (
                job_id uuid PRIMARY KEY,
                response_id uuid NOT NULL REFERENCES feedback_interactions ON DELETE CASCADE,
                config_sha256 text NOT NULL,
                document jsonb NOT NULL,
                UNIQUE (response_id, config_sha256)
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS online_reports (
                report_id uuid PRIMARY KEY, document jsonb NOT NULL, expires_at timestamptz NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS online_triage (
                job_id uuid NOT NULL REFERENCES online_jobs ON DELETE CASCADE,
                revision integer NOT NULL, document jsonb NOT NULL,
                PRIMARY KEY (job_id, revision)
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS online_expense (
                job_id uuid PRIMARY KEY, calls integer NOT NULL,
                reserved_usd numeric NOT NULL, cost_usd numeric, usage jsonb
            )""")
            conn.execute(
                "DELETE FROM online_reports WHERE expires_at <= %s", (self.feedback.clock(),)
            )
            conn.execute(
                "DELETE FROM online_jobs WHERE response_id IN "
                "(SELECT response_id FROM feedback_interactions WHERE expires_at <= %s)",
                (self.feedback.clock(),),
            )

    def process(self) -> OnlineCycle:
        @flow(
            name="ask-phil-online-evaluation",
            version="online-v1",
            retries=0,
            persist_result=False,
            log_prints=False,
            timeout_seconds=self.policy.seconds + 15,
        )
        def execute() -> OnlineCycle:
            return self._process(UUID(str(flow_run.id)))

        return execute()

    def _save(self, job: OnlineJob) -> None:
        with self.feedback.connect() as conn:
            conn.execute(
                "INSERT INTO online_jobs VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (job_id) DO UPDATE SET document = excluded.document",
                (
                    job.job_id,
                    job.response_id,
                    job.config_sha256,
                    Jsonb(job.model_dump(mode="json")),
                ),
            )

    def _process(self, run_id: UUID) -> OnlineCycle:
        self.ensure_schema()
        if not self.policy.enabled:
            return OnlineCycle(disabled=True)
        with self.feedback.connect() as conn:
            if conn.execute("SELECT to_regclass('answer_responses')").fetchone() == (None,):
                return OnlineCycle()
        now = self.feedback.clock()
        deadline = time.monotonic() + self.policy.seconds
        discovered = completed = 0
        with self.feedback.connect() as lock:
            acquired = lock.execute("SELECT pg_try_advisory_lock(728203)").fetchone()
            if not acquired or not acquired[0]:
                return OnlineCycle(busy=True)
            try:
                interrupted = lock.execute(
                    "SELECT document FROM online_jobs WHERE config_sha256=%s "
                    "AND document->>'state'='running'",
                    (self.config_sha256,),
                ).fetchall()
                for (document,) in interrupted:
                    interrupted_job = OnlineJob.model_validate(document)
                    self._save(
                        interrupted_job.model_copy(
                            update={
                                "state": "failed",
                                "support_state": "uncertain_interrupted",
                                "failure": "InterruptedJudge",
                                "updated_at": now,
                            }
                        )
                    )
                rows = lock.execute(
                    "SELECT i.response_id, i.served_at, j.document, "
                    "coalesce(r.revision, 0), r.submission, a.document->>'generation_id' "
                    "FROM feedback_interactions i JOIN answer_responses a USING (response_id) "
                    "LEFT JOIN online_jobs j ON j.response_id = i.response_id "
                    "AND j.config_sha256 = %s LEFT JOIN LATERAL "
                    "(SELECT revision, submission FROM feedback_revisions "
                    "WHERE response_id = i.response_id ORDER BY revision DESC LIMIT 1) r ON true "
                    "WHERE i.expires_at > %s AND i.tracking_sha256 = %s "
                    "AND (j.job_id IS NULL OR coalesce(r.revision, 0) > "
                    "(j.document->>'feedback_revision')::integer) "
                    "ORDER BY CASE WHEN r.submission->'categories' ?| "
                    "array['facts','evidence','harm','missing_outdated'] THEN 0 "
                    "WHEN r.submission->>'rating' = 'not_helpful' THEN 1 ELSE 2 END, "
                    "i.served_at, i.response_id LIMIT %s",
                    (
                        self.config_sha256,
                        now,
                        self.feedback.tracking_sha256,
                        self.policy.batch_size,
                    ),
                ).fetchall()
                for response_id, served_at, previous, revision, submission, generation_id in rows:
                    selected = self.policy.selects(
                        response_id, "background", self.policy.background_rate
                    )
                    job = (
                        OnlineJob(
                            job_id=uuid5(
                                NAMESPACE_URL, f"ask-phil-online:{response_id}:{self.config_sha256}"
                            ),
                            response_id=response_id,
                            generation_id=UUID(generation_id) if generation_id else response_id,
                            config_sha256=self.config_sha256,
                            created_at=now,
                            served_at=served_at,
                            updated_at=now,
                            state="pending" if selected else "unselected",
                            selection_reasons=("random_background",) if selected else (),
                            background_rate=self.policy.background_rate,
                            feedback_rate=self.policy.feedback_rate,
                            next_attempt_at=now,
                            prefect_run_id=run_id,
                        )
                        if previous is None
                        else OnlineJob.model_validate(previous)
                    )
                    reasons = list(job.selection_reasons)
                    if (
                        submission
                        and self.policy.selects(response_id, "feedback", self.policy.feedback_rate)
                        and "feedback_directed" not in reasons
                    ):
                        reasons.append("feedback_directed")
                    job = job.model_copy(
                        update={
                            "selection_reasons": tuple(reasons),
                            "feedback_revision": revision,
                            "state": "pending"
                            if reasons and job.state == "unselected"
                            else job.state,
                            "updated_at": now,
                        }
                    )
                    self._save(job)
                    if revision:
                        with self.feedback.connect() as conn:
                            revisions = conn.execute(
                                "SELECT r.revision, r.submission, r.accepted_at, i.feedback_id "
                                "FROM feedback_revisions r JOIN feedback_interactions i "
                                "USING (response_id) WHERE response_id = %s "
                                "AND revision <= %s ORDER BY revision",
                                (response_id, revision),
                            ).fetchall()
                            for rev, item, accepted_at, feedback_id in revisions:
                                triage = OnlineTriage(
                                    feedback_revision=rev,
                                    feedback_id=feedback_id,
                                    accepted_at=accepted_at,
                                    processed_at=now,
                                    rating=item["rating"],
                                    categories=item["categories"],
                                    priority="reported_problem"
                                    if {
                                        "facts",
                                        "evidence",
                                        "harm",
                                        "missing_outdated",
                                    }.intersection(item["categories"])
                                    else "negative"
                                    if item["rating"] == "not_helpful"
                                    else "remaining",
                                )
                                conn.execute(
                                    "INSERT INTO online_triage VALUES (%s,%s,%s) "
                                    "ON CONFLICT DO NOTHING",
                                    (job.job_id, rev, Jsonb(triage.model_dump(mode="json"))),
                                )
                    discovered += 1
                documents = lock.execute(
                    "SELECT document FROM online_jobs WHERE config_sha256 = %s "
                    "AND (document->>'state' = 'pending' OR "
                    "(document->>'state' = 'completed' AND document->>'exported' = 'false')) "
                    "AND (document->>'next_attempt_at')::timestamptz <= %s "
                    "ORDER BY CASE WHEN document->'selection_reasons' ? 'feedback_directed' "
                    "THEN 0 ELSE 1 END, document->>'created_at' LIMIT %s",
                    (self.config_sha256, now, self.policy.batch_size),
                ).fetchall()
                for (document,) in documents:
                    if self.cancellation.is_set() or time.monotonic() >= deadline:
                        break
                    job = OnlineJob.model_validate(document)
                    job = job.model_copy(
                        update={"attempts": job.attempts + 1, "prefect_run_id": run_id}
                    )
                    try:
                        response = self.inspect(job.job_id).response
                        if job.checks is None:
                            trace = _tracking(self.tracking_uri).get_trace(response.trace_id)
                            roots = [s for s in trace.data.spans if s.parent_id is None]
                            if len(roots) != 1 or roots[0].outputs != response.model_dump(
                                mode="json"
                            ):
                                raise ValueError("Original trace differs from saved response.")
                            job = self._judge(job, response, deadline)
                            job = job.model_copy(
                                update={
                                    "state": job.state
                                    if job.state in {"failed", "budget_skipped"}
                                    else "completed",
                                    "checks": check_saved_answer(response),
                                    "assessment_feedback_revision": job.feedback_revision,
                                    "trace_verified": True,
                                    "response_sha256": document_fingerprint(
                                        response.model_dump(mode="json")
                                    ),
                                    "completed_at": datetime.now(UTC),
                                }
                            )
                            # Commit before export; a lost acknowledgement never repeats scoring.
                            self._save(job)
                        self._export(job, response, deadline)
                        job = job.model_copy(
                            update={
                                "exported": True,
                                "failure": job.failure
                                if job.state in {"failed", "budget_skipped"}
                                else None,
                            }
                        )
                        completed += 1
                    except ValueError as exc:
                        job = job.model_copy(
                            update={"state": "ineligible", "failure": type(exc).__name__}
                        )
                    except Exception as exc:
                        job = job.model_copy(
                            update={
                                "state": "failed"
                                if job.attempts >= self.policy.max_attempts
                                else job.state,
                                "failure": type(exc).__name__,
                                "next_attempt_at": datetime.now(UTC)
                                + timedelta(seconds=self.policy.retry_seconds),
                            }
                        )
                    self._save(job.model_copy(update={"updated_at": datetime.now(UTC)}))
                remaining = lock.execute(
                    "SELECT count(*) FROM online_jobs WHERE config_sha256 = %s "
                    "AND (document->>'state' = 'pending' OR "
                    "(document->>'state' = 'completed' AND document->>'exported' = 'false'))",
                    (self.config_sha256,),
                ).fetchone()
            finally:
                lock.execute("SELECT pg_advisory_unlock(728203)")
        return OnlineCycle(
            discovered=discovered, completed=completed, pending=remaining[0] if remaining else 0
        )

    def _export(self, job: OnlineJob, response: AnswerRecord, deadline: float) -> None:
        def check() -> None:
            if self.cancellation.is_set() or time.monotonic() >= deadline:
                raise TimeoutError("Online export deferred.")

        check()
        tracking = _tracking(self.tracking_uri)
        identifier = "a-" + uuid5(job.job_id, "checks").hex
        value = job.checks.model_dump(mode="json") if job.checks else {}
        try:
            existing = tracking.get_assessment(response.trace_id, identifier)
        except MlflowException as exc:
            if exc.error_code != "RESOURCE_DOES_NOT_EXIST":
                raise
            assessment = Feedback(
                name="online_evidence_checks",
                value=value,
                source=AssessmentSource(
                    source_type=AssessmentSourceType.CODE, source_id=job.config_sha256
                ),
                metadata={"response_id": str(job.response_id), "job_id": str(job.job_id)},
            )
            assessment.assessment_id = identifier
            check()
            tracking.log_assessment(response.trace_id, assessment)
            check()
            existing = tracking.get_assessment(response.trace_id, identifier)
        if existing.feedback is None or existing.feedback.value != value:
            raise ValueError("Online assessment readback differs.")
        if job.support is not None:
            check()
            support_id = "a-" + uuid5(job.job_id, "support").hex
            support_value = job.support.model_dump(mode="json")
            try:
                result = tracking.get_assessment(response.trace_id, support_id)
            except MlflowException as exc:
                if exc.error_code != "RESOURCE_DOES_NOT_EXIST":
                    raise
                assessment = Feedback(
                    name="online_context_support",
                    value=support_value,
                    source=AssessmentSource(
                        source_type=AssessmentSourceType.LLM_JUDGE, source_id=job.config_sha256
                    ),
                    metadata={
                        "response_id": str(job.response_id),
                        "calibration_sha256": self.calibration_sha256 or "",
                    },
                )
                assessment.assessment_id = support_id
                check()
                tracking.log_assessment(response.trace_id, assessment)
                check()
                result = tracking.get_assessment(response.trace_id, support_id)
            if result.feedback is None or result.feedback.value != support_value:
                raise ValueError("Online semantic assessment readback differs.")

    def _judge(self, job: OnlineJob, response: AnswerRecord, deadline: float) -> OnlineJob:
        judge = self.judge
        if judge is None or not judge.policies.online_enabled:
            return job.model_copy(update={"support_state": "disabled"})
        if self.calibration_sha256 is None:
            return job.model_copy(update={"support_state": "uncalibrated"})
        if not response.context or response.status not in {"answered", "partial"}:
            return job.model_copy(update={"support_state": "ineligible_missing_context_or_outcome"})
        try:
            supplied = SupportInput(
                answer=response.answer,
                context=tuple(
                    SupportPassage(evidence_id=p.evidence_id, text=p.text) for p in response.context
                ),
            )
        except ValueError:
            return job.model_copy(update={"support_state": "ineligible_input_budget"})
        maximum = float(maximum_call_cost(judge.chat.profile))
        with self.feedback.connect() as conn:
            spent = conn.execute(
                "SELECT coalesce(sum(calls),0), "
                "coalesce(sum(coalesce(cost_usd,reserved_usd)),0) "
                "FROM online_expense"
            ).fetchone()
            previous = conn.execute(
                "SELECT 1 FROM online_expense WHERE job_id = %s", (job.job_id,)
            ).fetchone()
            if previous:
                return job.model_copy(
                    update={
                        "state": "failed",
                        "support_state": "uncertain_interrupted",
                        "judge_calls": 1,
                        "judge_cost_usd": None,
                        "judge_reserved_usd": maximum,
                    }
                )
            if spent and (
                spent[0] >= self.policy.max_judge_calls
                or float(spent[1]) + maximum > self.policy.max_judge_spend_usd
            ):
                return job.model_copy(
                    update={"state": "budget_skipped", "support_state": "budget_skipped"}
                )
            conn.execute(
                "INSERT INTO online_expense VALUES (%s,1,%s,NULL,NULL)", (job.job_id, maximum)
            )
        # The reservation commits before inference; a crash leaves uncertain work, never a retry.
        job = job.model_copy(
            update={
                "state": "running",
                "judge_calls": 1,
                "judge_cost_usd": None,
                "judge_reserved_usd": maximum,
            }
        )
        self._save(job)
        result = judge.assess_online(
            supplied, cancellation=self.cancellation, seconds=deadline - time.monotonic()
        )
        usage = judge.chat.last_call
        cost = usage.cost_usd if usage else (0 if result.execution.model_calls == 0 else None)
        with self.feedback.connect() as conn:
            conn.execute(
                "UPDATE online_expense SET calls=%s, cost_usd=%s, usage=%s WHERE job_id=%s",
                (
                    result.execution.model_calls,
                    cost,
                    Jsonb(usage.model_dump(mode="json")) if usage else None,
                    job.job_id,
                ),
            )
        return job.model_copy(
            update={
                "state": "failed"
                if result.status == "failed"
                else "budget_skipped"
                if result.status == "skipped"
                else "pending",
                "support_state": result.status,
                "support": result.assessment,
                "support_execution": result.execution,
                "judge_calls": result.execution.model_calls,
                "judge_cost_usd": cost,
                "failure": result.execution.stop_reason,
            }
        )

    def inspect(self, job_id: UUID) -> OnlineInspection:
        self.ensure_schema()
        with self.feedback.connect() as conn:
            row = conn.execute(
                "SELECT j.document, a.document FROM online_jobs j JOIN answer_responses a "
                "USING (response_id) WHERE j.job_id = %s",
                (job_id,),
            ).fetchone()
            triage = conn.execute(
                "SELECT document FROM online_triage WHERE job_id = %s ORDER BY revision",
                (job_id,),
            ).fetchall()
        if row is None:
            raise LookupError("Online assessment not found.")
        return OnlineInspection(
            **row[0],
            response=AnswerRecord.model_validate(row[1]),
            triage=tuple(OnlineTriage.model_validate(r[0]) for r in triage),
        )

    def report(self, cohort: FeedbackCohort) -> OnlineReport:
        self.ensure_schema()
        feedback = self.feedback.report(cohort)
        priorities = list(feedback.review_priorities)
        offset = feedback.next_offset
        while offset is not None:
            page = self.feedback.report(cohort, offset=offset)
            priorities.extend(page.review_priorities)
            offset = page.next_offset
        feedback = feedback.model_copy(
            update={"review_priorities": tuple(priorities), "next_offset": None}
        )
        with self.feedback.connect() as conn:
            rows = (
                conn.execute(
                    "SELECT j.document, a.document FROM online_jobs j "
                    "JOIN feedback_interactions i USING (response_id) "
                    "JOIN answer_responses a USING (response_id) WHERE j.config_sha256 = %s "
                    "AND i.served_at >= %s AND i.served_at < %s AND i.served_at <= %s "
                    "AND i.expires_at > %s ORDER BY i.served_at, i.response_id",
                    (
                        self.config_sha256,
                        cohort.served_from,
                        cohort.served_until,
                        cohort.feedback_as_of,
                        self.feedback.clock(),
                    ),
                ).fetchall()
                if feedback.counts.eligible
                else []
            )
        jobs = tuple(OnlineJob.model_validate(row[0]) for row in rows)
        disagreements = []
        for priority in feedback.review_priorities:
            job = next((j for j in jobs if j.response_id == priority.response_id), None)
            signal = priority.signal
            if (
                job
                and job.support
                and job.support.supported is not None
                and (
                    (signal.rating == "not_helpful" and job.support.supported)
                    or (signal.rating == "helpful" and not job.support.supported)
                )
            ):
                disagreements.append(
                    OnlineDisagreement(
                        response_id=job.response_id,
                        feedback_revision=signal.revision,
                        rating=signal.rating,
                        supported=job.support.supported,
                        reason="Helpfulness/report and context support measure different things; "
                        "inspect evidence.",
                    )
                )
        now = self.feedback.clock()
        selected = sum(bool(j.selection_reasons) for j in jobs)
        completed = sum(j.state == "completed" for j in jobs)
        pending = [seconds_since(now, j.created_at) for j in jobs if j.state == "pending"]
        with self.feedback.connect() as conn:
            undiscovered = (
                conn.execute(
                    "SELECT min(i.served_at) FILTER (WHERE i.tracking_sha256=%s), "
                    "sum((a.document->>'estimated_api_cost_usd')::numeric), "
                    "count(*) FILTER (WHERE a.document->>'estimated_api_cost_usd' IS NULL), "
                    "count(*) FILTER (WHERE i.tracking_sha256<>%s) "
                    "FROM feedback_interactions i JOIN answer_responses a USING (response_id) "
                    "WHERE i.served_at >= %s AND i.served_at < %s AND i.served_at <= %s "
                    "AND i.expires_at > %s AND NOT EXISTS (SELECT 1 FROM online_jobs j "
                    "WHERE j.response_id=i.response_id AND j.config_sha256=%s)",
                    (
                        self.feedback.tracking_sha256,
                        self.feedback.tracking_sha256,
                        cohort.served_from,
                        cohort.served_until,
                        cohort.feedback_as_of,
                        now,
                        self.config_sha256,
                    ),
                ).fetchone()
                if feedback.counts.eligible
                else None
            )
        foreign = undiscovered[3] if undiscovered else 0
        online_eligible = feedback.counts.eligible - foreign
        missing_jobs = max(0, online_eligible - len(jobs))
        states: dict[str, int] = dict(Counter(j.state for j in jobs))
        if missing_jobs:
            states["undiscovered"] = missing_jobs
            if undiscovered and undiscovered[0]:
                pending.append(seconds_since(now, undiscovered[0]))
        if foreign:
            states["ineligible_backend"] = foreign
        costs = [j.judge_cost_usd for j in jobs]
        with self.feedback.connect() as conn:
            expense = conn.execute(
                "SELECT coalesce(sum(calls),0), coalesce(sum(cost_usd),0), "
                "coalesce(sum(coalesce(cost_usd,reserved_usd)),0), "
                "count(*) FILTER (WHERE cost_usd IS NULL) FROM online_expense"
            ).fetchone()
        serving = [row[1]["estimated_api_cost_usd"] for row in rows]
        requirements = []
        remaining = []
        for item in feedback.review_priorities:
            signal = item.signal
            if signal.categories or signal.comment or signal.proposed_correction:
                reason = "category_or_comment"
            elif any(d.response_id == item.response_id for d in disagreements):
                reason = "judge_disagreement"
            elif signal.rating != "skip":
                remaining.append(item)
                if not self.policy.selects(item.response_id, "review", self.policy.review_rate):
                    continue
                reason = "remaining_rating_sample"
            else:
                continue
            requirements.append(
                ReviewRequirement(
                    response_id=item.response_id, feedback_revision=signal.revision, reason=reason
                )
            )
        if remaining and not any(r.reason == "remaining_rating_sample" for r in requirements):
            item = min(
                remaining,
                key=lambda p: hashlib.sha256(
                    f"{self.policy.seed}:review:{p.response_id}".encode()
                ).hexdigest(),
            )
            requirements.append(
                ReviewRequirement(
                    response_id=item.response_id,
                    feedback_revision=item.signal.revision,
                    reason="remaining_rating_sample_minimum_one",
                )
            )
        report = OnlineReport(
            report_id=uuid4(),
            created_at=now,
            config_sha256=self.config_sha256,
            feedback=feedback,
            selected=selected,
            online_eligible=online_eligible,
            completed=completed,
            states=states,
            selection_cohorts=dict(Counter(r for j in jobs for r in j.selection_reasons)),
            sample_coverage=selected / online_eligible if online_eligible else None,
            score_coverage=sum(j.checks is not None for j in jobs) / selected if selected else None,
            oldest_pending_seconds=max(pending) if pending else None,
            assessment_lag_seconds=tuple(
                seconds_since(j.completed_at, j.served_at) for j in jobs if j.completed_at
            ),
            online_judge_cost_usd=sum(c for c in costs if c is not None)
            if None not in costs
            else None,
            online_judge_reserved_usd=sum(j.judge_reserved_usd for j in jobs),
            online_judge_calls=sum(j.judge_calls for j in jobs),
            cumulative_online_judge_calls=expense[0] if expense else 0,
            cumulative_online_judge_cost_usd=float(expense[1])
            if expense and not expense[3]
            else None,
            cumulative_online_judge_allocation_usd=float(expense[2]) if expense else 0,
            unsettled_online_judge_jobs=expense[3] if expense else 0,
            scored=sum(j.checks is not None for j in jobs),
            support_scored=sum(
                j.support is not None and j.support.supported is not None for j in jobs
            ),
            exported=sum(j.exported for j in jobs),
            enabled=self.policy.enabled,
            serving_cost_usd=sum(c for c in serving if c is not None)
            + (float(undiscovered[1] or 0) if undiscovered else 0)
            if None not in serving and (not undiscovered or not undiscovered[2])
            else None,
            jobs=jobs,
            disagreements=tuple(disagreements),
            required_reviews=tuple(requirements),
            remaining_rating_review_rate=self.policy.review_rate,
        )
        with self.feedback.connect() as conn:
            expiry = conn.execute(
                "SELECT min(expires_at) FROM feedback_interactions "
                "WHERE served_at >= %s AND served_at < %s AND expires_at > %s",
                (cohort.served_from, cohort.served_until, now),
            ).fetchone()
            conn.execute(
                "INSERT INTO online_reports VALUES (%s, %s, %s)",
                (
                    report.report_id,
                    Jsonb(report.model_dump(mode="json")),
                    expiry[0] if expiry and expiry[0] else now + timedelta(days=30),
                ),
            )
        return report
