"""Feedback and assessment reports from one retained, consistent PostgreSQL read."""

import hashlib
import json
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from ask_phil.answers import AnswerRecord
from ask_phil.evaluation import document_fingerprint
from ask_phil.feedback import FeedbackStore
from ask_phil.feedback_reporting import (
    FeedbackCohort,
    FeedbackSignal,
    FeedbackSummary,
    ServedFeedback,
    summarize_feedback,
)
from ask_phil.online_evaluation import (
    OnlineConfiguration,
    OnlineDisagreement,
    OnlineJob,
    OnlineReport,
    OnlineTriage,
    ReviewRequirement,
    seconds_since,
)


@dataclass(frozen=True)
class _Interaction:
    response: AnswerRecord
    serving_cost_usd: float | None
    expires_at: datetime
    tracking_sha256: str
    feedback: ServedFeedback


class RetainedReports:
    """Own retained membership, revision loading and complete report assembly."""

    def __init__(self, store: FeedbackStore) -> None:
        self.store = store

    def _validate(self, cohort: FeedbackCohort, now: datetime) -> None:
        if cohort.feedback_as_of > now:
            raise ValueError("The feedback cutoff cannot be in the future.")
        if cohort.served_from < now - timedelta(days=30):
            raise ValueError("The cohort starts outside the maximum retained feedback window.")

    def _load(
        self,
        conn: psycopg.Connection[tuple[Any, ...]],
        cohort: FeedbackCohort,
        now: datetime,
    ) -> tuple[_Interaction, ...]:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        if conn.execute("SELECT to_regclass('answer_responses')").fetchone() == (None,):
            return ()
        rows = conn.execute(
            "SELECT i.response_id, i.feedback_id, i.served_at, i.expires_at, "
            "i.tracking_sha256, a.document FROM feedback_interactions i "
            "JOIN answer_responses a USING (response_id) "
            "WHERE i.served_at >= %s AND i.served_at < %s AND i.served_at <= %s "
            "AND i.expires_at > %s ORDER BY i.served_at, i.response_id",
            (cohort.served_from, cohort.served_until, cohort.feedback_as_of, now),
        ).fetchall()
        signals: dict[UUID, list[FeedbackSignal]] = {}
        revisions = conn.execute(
            "SELECT r.response_id, i.feedback_id, r.revision, r.accepted_at, "
            "r.submission, r.delivery_state FROM feedback_revisions r "
            "JOIN feedback_interactions i USING (response_id) "
            "WHERE r.response_id=ANY(%s) AND r.accepted_at <= %s "
            "ORDER BY r.response_id, r.revision",
            ([row[0] for row in rows], cohort.feedback_as_of),
        ).fetchall()
        for response_id, feedback_id, revision, accepted_at, submission, delivery in revisions:
            signals.setdefault(response_id, []).append(
                FeedbackSignal(
                    feedback_id=feedback_id,
                    revision=revision,
                    accepted_at=accepted_at,
                    rating=submission["rating"],
                    categories=submission["categories"],
                    comment=submission["comment"],
                    proposed_correction=submission["proposed_correction"],
                    delivery_state=delivery,
                )
            )
        interactions = []
        for response_id, _, served_at, expires_at, tracking, document in rows:
            response = AnswerRecord.model_validate(document)
            interactions.append(
                _Interaction(
                    response=response,
                    serving_cost_usd=response.estimated_api_cost_usd
                    if document.get("estimated_api_cost_usd") is not None
                    else None,
                    expires_at=expires_at,
                    tracking_sha256=tracking,
                    feedback=ServedFeedback(
                        response_id=response_id,
                        served_at=served_at,
                        route=response.route,
                        outcome=response.status,
                        snapshot_id=response.snapshot_id,
                        application_sha256=response.application_sha256,
                        prompt_sha256=response.prompt_sha256,
                        model_id=hashlib.sha256(
                            json.dumps(document["model_settings"], sort_keys=True).encode()
                        ).hexdigest(),
                        feedback=tuple(signals.get(response_id, ())),
                    ),
                )
            )
        return tuple(interactions)

    def feedback(
        self, cohort: FeedbackCohort, *, offset: int = 0, limit: int = 100
    ) -> FeedbackSummary:
        now = self.store.clock()
        self._validate(cohort, now)
        if offset < 0 or not 1 <= limit <= 100:
            raise ValueError("Review pagination requires a nonnegative offset and 1-100 items.")
        self.store.ensure_schema()
        with self.store.connect() as conn:
            interactions = self._load(conn, cohort, now)
        return summarize_feedback(
            (i.feedback for i in interactions), cohort, offset=offset, limit=limit
        )

    def online(self, cohort: FeedbackCohort, configuration: OnlineConfiguration) -> OnlineReport:
        now = self.store.clock()
        self._validate(cohort, now)
        policy = configuration.policy
        config_sha256 = document_fingerprint(configuration.model_dump(mode="json"))
        with self.store.connect() as conn:
            interactions = self._load(conn, cohort, now)
            identifiers = [i.response.response_id for i in interactions]
            jobs = tuple(
                OnlineJob.model_validate(row[0])
                for row in conn.execute(
                    "SELECT j.document FROM online_jobs j "
                    "JOIN feedback_interactions i USING (response_id) "
                    "WHERE j.config_sha256=%s AND j.response_id=ANY(%s) "
                    "ORDER BY i.served_at, i.response_id",
                    (config_sha256, identifiers),
                ).fetchall()
            )
            triage = {
                (job_id, revision): OnlineTriage.model_validate(document)
                for job_id, revision, document in conn.execute(
                    "SELECT t.job_id, t.revision, t.document FROM online_triage t "
                    "JOIN online_jobs j USING (job_id) "
                    "WHERE j.config_sha256=%s AND j.response_id=ANY(%s)",
                    (config_sha256, identifiers),
                ).fetchall()
            }
            expense = conn.execute(
                "SELECT coalesce(sum(calls),0), coalesce(sum(cost_usd),0), "
                "coalesce(sum(coalesce(cost_usd,reserved_usd)),0), "
                "count(*) FILTER (WHERE cost_usd IS NULL) FROM online_expense"
            ).fetchone()

        feedback = summarize_feedback((i.feedback for i in interactions), cohort, limit=None)
        jobs_by_response = {j.response_id: j for j in jobs}
        disagreements = []
        for priority in feedback.review_priorities:
            job = jobs_by_response.get(priority.response_id)
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
        local = [i for i in interactions if i.tracking_sha256 == self.store.tracking_sha256]
        undiscovered = [i for i in local if i.response.response_id not in jobs_by_response]
        foreign = len(interactions) - len(local)
        selected = sum(bool(j.selection_reasons) for j in jobs)
        pending = [
            seconds_since(now, j.created_at)
            for j in jobs
            if j.state == "pending"
            or (
                j.state in {"completed", "failed", "budget_skipped"}
                and j.checks is not None
                and not j.exported
                and j.attempts < policy.max_attempts
            )
        ]
        missed_revisions = []
        triaged = []
        for interaction in local:
            job = jobs_by_response.get(interaction.response.response_id)
            for revision in interaction.feedback.feedback:
                recorded = triage.get((job.job_id, revision.revision)) if job else None
                if recorded is None:
                    missed_revisions.append(revision.accepted_at)
                else:
                    triaged.append(seconds_since(recorded.processed_at, revision.accepted_at))
        triage_age = seconds_since(now, min(missed_revisions)) if missed_revisions else None
        if triage_age is not None:
            pending.append(triage_age)
        states: dict[str, int] = dict(Counter(j.state for j in jobs))
        if undiscovered:
            states["undiscovered"] = len(undiscovered)
            pending.append(seconds_since(now, min(i.feedback.served_at for i in undiscovered)))
        if foreign:
            states["ineligible_backend"] = foreign
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
                if not policy.selects(item.response_id, "review", policy.review_rate):
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
                    f"{policy.seed}:review:{p.response_id}".encode()
                ).hexdigest(),
            )
            requirements.append(
                ReviewRequirement(
                    response_id=item.response_id,
                    feedback_revision=item.signal.revision,
                    reason="remaining_rating_sample_minimum_one",
                )
            )
        costs = [j.judge_cost_usd for j in jobs]
        serving = [i.serving_cost_usd for i in interactions]
        report = OnlineReport(
            report_id=uuid4(),
            created_at=now,
            config_sha256=config_sha256,
            configuration=configuration,
            feedback=feedback,
            selected=selected,
            online_eligible=len(local),
            completed=sum(j.state == "completed" for j in jobs),
            states=states,
            selection_cohorts=dict(Counter(r for j in jobs for r in j.selection_reasons)),
            sample_coverage=selected / len(local) if local else None,
            score_coverage=sum(j.checks is not None for j in jobs) / selected if selected else None,
            oldest_pending_seconds=max(pending) if pending else None,
            pending_triage_revisions=len(missed_revisions),
            triaged_revisions=len(triaged),
            oldest_pending_triage_seconds=triage_age,
            maximum_triage_lag_seconds=max(triaged) if triaged else None,
            assessment_lag_seconds=tuple(
                seconds_since(j.completed_at, j.served_at) for j in jobs if j.completed_at
            ),
            online_judge_cost_usd=sum(c for c in costs if c is not None)
            if None not in costs
            else None,
            online_judge_reserved_usd=sum(
                j.judge_reserved_usd for j in jobs if j.judge_cost_usd is None
            ),
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
            enabled=policy.enabled
            and os.environ.get("ASK_PHIL_ONLINE_ENABLED", "true").lower() == "true",
            serving_cost_usd=sum(c for c in serving if c is not None)
            if None not in serving
            else None,
            jobs=jobs,
            disagreements=tuple(disagreements),
            required_reviews=tuple(requirements),
            remaining_rating_review_rate=policy.review_rate,
        )
        expiry = min((i.expires_at for i in interactions), default=now + timedelta(days=30))
        with self.store.connect() as conn:
            conn.execute(
                "INSERT INTO online_reports VALUES (%s,%s,%s)",
                (report.report_id, Jsonb(report.model_dump(mode="json")), expiry),
            )
        return report
