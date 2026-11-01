"""Response-bound human feedback, durable revisions and explicit collection policy."""

import hashlib
import json
import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self
from uuid import UUID, uuid4, uuid5

import psycopg
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, Field, StringConstraints, field_validator, model_validator

from ask_phil.answers import AnswerRecord
from ask_phil.evidence import Record
from ask_phil.responses import ResponseLedger
from ask_phil.security import redact_text
from ask_phil.sessions import ConversationSessions

if TYPE_CHECKING:
    from ask_phil.feedback_reporting import FeedbackCohort, FeedbackSummary

Rating = Literal["helpful", "not_helpful", "skip"]
Category = Literal[
    "facts", "missing_outdated", "evidence", "harm", "clarity", "persona_tone", "other"
]
FeedbackText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
_ASSESSMENT_NAMESPACE = UUID("580c1c4b-e58c-49cf-81c4-af465a225f9d")


class FeedbackPolicy(Record):
    version: Literal["feedback-v1"] = "feedback-v1"
    enabled: bool = True
    retention_days: int = Field(default=30, ge=1, le=30)
    submissions_per_minute: int = Field(default=10, ge=1, le=10)
    auto_deliver: bool = True
    delivery_batch_size: int = Field(default=20, ge=1, le=100)
    delivery_interval_seconds: float = Field(default=5, ge=0.1, le=60)
    use_notice: str = (
        "Optional feedback helps evaluate this delivered response and prioritize review. "
        "It is not checked factual truth, training data or conversation memory. "
        "Do not include personal information or secrets. Redacted comments and proposed "
        "corrections stay in local PostgreSQL; only the rating, categories and opaque "
        "feedback identity go to the configured local MLflow service. Feedback expires "
        "within the configured retention period. External deletion failures retain only "
        "minimal cleanup identifiers until delivery recovers."
    )

    @classmethod
    def from_environment(cls) -> Self:
        return cls(
            enabled=os.environ.get("ASK_PHIL_FEEDBACK_ENABLED", "true").lower() == "true",
            retention_days=int(os.environ.get("ASK_PHIL_FEEDBACK_RETENTION_DAYS", "30")),
        )


class FeedbackInput(Record):
    submission_id: UUID
    policy_version: Literal["feedback-v1"]
    rating: Rating
    categories: tuple[Category, ...] = Field(default=(), max_length=7)
    comment: FeedbackText = ""
    proposed_correction: FeedbackText = ""

    @model_validator(mode="after")
    def bounded_input(self) -> Self:
        if len(set(self.categories)) != len(self.categories):
            raise ValueError("Duplicate feedback category.")
        if len((self.comment + self.proposed_correction).encode()) > 1000:
            raise ValueError("Feedback exceeds the shared 1000-byte text budget.")
        return self

    @field_validator("comment", "proposed_correction")
    @classmethod
    def redact_credentials(cls, value: str) -> str:
        return redact_text(value)


class FeedbackReceipt(Record):
    feedback_id: UUID
    response_id: UUID
    submission_id: UUID
    revision: int
    accepted_at: AwareDatetime
    expires_at: AwareDatetime
    delivery_state: Literal["pending", "delivered"]


class FeedbackRevision(FeedbackReceipt):
    submission: FeedbackInput
    attempts: int
    last_failure: str | None
    assessment_id: str


class FeedbackInspection(Record):
    response: AnswerRecord
    served_at: AwareDatetime
    expires_at: AwareDatetime
    revisions: tuple[FeedbackRevision, ...]


class FeedbackUnavailable(LookupError):
    pass


class FeedbackConflict(ValueError):
    pass


class FeedbackRateLimited(ValueError):
    pass


class FeedbackStore:
    """Own authorization, response binding and acceptance before any external delivery."""

    def __init__(
        self,
        database_url: str,
        *,
        policy: FeedbackPolicy | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        tracking_uri: str | None = None,
    ) -> None:
        self.database_url = database_url
        self.policy = policy or FeedbackPolicy.from_environment()
        self.clock = clock
        self.tracking_sha256 = hashlib.sha256(
            (
                tracking_uri
                or os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db")
            ).encode()
        ).hexdigest()

    def connect(self) -> psycopg.Connection[tuple[Any, ...]]:
        return psycopg.connect(
            self.database_url,
            connect_timeout=5,
            options="-c statement_timeout=3000 -c lock_timeout=3000",
        )

    def ensure_schema(self) -> None:
        with self.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728201)")
            conn.execute("""CREATE TABLE IF NOT EXISTS feedback_interactions (
                response_id uuid PRIMARY KEY,
                feedback_id uuid NOT NULL UNIQUE,
                context_id uuid NOT NULL,
                served_at timestamptz NOT NULL,
                expires_at timestamptz NOT NULL,
                tracking_sha256 text NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS feedback_revisions (
                response_id uuid NOT NULL REFERENCES feedback_interactions ON DELETE CASCADE,
                revision integer NOT NULL,
                submission_id uuid NOT NULL,
                accepted_at timestamptz NOT NULL,
                submission jsonb NOT NULL,
                delivery_state text NOT NULL DEFAULT 'pending',
                attempts integer NOT NULL DEFAULT 0,
                last_failure text,
                assessment_id text NOT NULL UNIQUE,
                next_attempt_at timestamptz NOT NULL DEFAULT '-infinity',
                PRIMARY KEY (response_id, revision),
                UNIQUE (response_id, submission_id)
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS feedback_cleanup (
                trace_id text NOT NULL,
                assessment_id text PRIMARY KEY,
                tracking_sha256 text NOT NULL,
                attempts integer NOT NULL DEFAULT 0,
                last_failure text
            )""")

    def record_delivery(self, response: AnswerRecord) -> None:
        """Register a committed API result offered for delivery, never an answer cache value."""
        if not self.policy.enabled:
            return
        self.ensure_schema()
        now = self.clock()
        context_id = (
            response.conversation.session_id if response.conversation else response.response_id
        )
        with self.connect() as conn:
            expires_at = now + timedelta(days=self.policy.retention_days)
            if response.conversation:
                context = conn.execute(
                    "SELECT expires_at FROM conversation_feedback_contexts WHERE session_id = %s",
                    (context_id,),
                ).fetchone()
                expires_at = min(expires_at, context[0]) if context else now
            conn.execute(
                "INSERT INTO feedback_interactions "
                "(response_id, feedback_id, context_id, served_at, expires_at, tracking_sha256) "
                "VALUES (%s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (response_id) DO NOTHING",
                (
                    response.response_id,
                    uuid4(),
                    context_id,
                    now,
                    expires_at,
                    self.tracking_sha256,
                ),
            )

    def _authorize(self, response_id: UUID, token: str, session_id: UUID | None) -> AnswerRecord:
        if not self.policy.enabled:
            raise FeedbackUnavailable("Feedback is disabled.")
        if session_id is not None:
            context = ConversationSessions(self.database_url, clock=self.clock).feedback_context(
                session_id, token
            )
            if context is None:
                raise FeedbackUnavailable("Feedback response not found or expired.")
            with self.connect() as conn:
                if conn.execute("SELECT to_regclass('answer_responses')").fetchone() == (None,):
                    raise FeedbackUnavailable("Feedback response not found or expired.")
                row = conn.execute(
                    "SELECT document FROM answer_responses WHERE response_id = %s",
                    (response_id,),
                ).fetchone()
            response = AnswerRecord.model_validate(row[0]) if row else None
            if (
                response is None
                or response.conversation is None
                or (response.conversation.session_id != session_id)
            ):
                raise FeedbackUnavailable("Feedback response not found or expired.")
        else:
            response = ResponseLedger(self.database_url).get(response_id, token)
            if response is None or response.conversation is not None:
                raise FeedbackUnavailable("Feedback response not found or expired.")
        return response

    def inspect(
        self, response_id: UUID, token: str, session_id: UUID | None = None
    ) -> FeedbackInspection:
        self.ensure_schema()
        response = self._authorize(response_id, token, session_id)
        with self.connect() as conn:
            row = conn.execute(
                "SELECT feedback_id, served_at, expires_at FROM feedback_interactions "
                "WHERE response_id = %s AND expires_at > %s",
                (response_id, self.clock()),
            ).fetchone()
            if not row:
                raise FeedbackUnavailable("Feedback response not found or expired.")
            events = conn.execute(
                "SELECT revision, submission_id, accepted_at, submission, delivery_state, "
                "attempts, last_failure, assessment_id FROM feedback_revisions "
                "WHERE response_id = %s ORDER BY revision",
                (response_id,),
            ).fetchall()
        return FeedbackInspection(
            response=response,
            served_at=row[1],
            expires_at=row[2],
            revisions=tuple(
                FeedbackRevision(
                    feedback_id=row[0],
                    response_id=response_id,
                    revision=e[0],
                    submission_id=e[1],
                    accepted_at=e[2],
                    expires_at=row[2],
                    submission=FeedbackInput.model_validate(e[3]),
                    delivery_state=e[4],
                    attempts=e[5],
                    last_failure=e[6],
                    assessment_id=e[7],
                )
                for e in events
            ),
        )

    def accept(
        self,
        response_id: UUID,
        token: str,
        submission: FeedbackInput,
        session_id: UUID | None = None,
    ) -> FeedbackReceipt:
        self.ensure_schema()
        self._authorize(response_id, token, session_id)
        submission = FeedbackInput.model_validate(
            {
                **submission.model_dump(),
                "comment": redact_text(submission.comment, (token,)),
                "proposed_correction": redact_text(submission.proposed_correction, (token,)),
            }
        )
        now = self.clock()
        with self.connect() as conn:
            interaction = conn.execute(
                "SELECT feedback_id, context_id, expires_at FROM feedback_interactions "
                "WHERE response_id = %s AND expires_at > %s",
                (response_id, now),
            ).fetchone()
            if not interaction:
                raise FeedbackUnavailable("Feedback response not found or expired.")
            conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 728202))",
                (str(interaction[1]),),
            )
            previous = conn.execute(
                "SELECT revision, accepted_at, submission, delivery_state "
                "FROM feedback_revisions WHERE response_id = %s AND submission_id = %s",
                (response_id, submission.submission_id),
            ).fetchone()
            if previous:
                if previous[2] != submission.model_dump(mode="json"):
                    raise FeedbackConflict("Submission identity already has different feedback.")
                receipt = FeedbackReceipt(
                    feedback_id=interaction[0],
                    response_id=response_id,
                    submission_id=submission.submission_id,
                    revision=previous[0],
                    accepted_at=previous[1],
                    expires_at=interaction[2],
                    delivery_state=previous[3],
                )
            else:
                count = conn.execute(
                    "SELECT count(*) FROM feedback_revisions r JOIN feedback_interactions i "
                    "USING (response_id) WHERE i.context_id = %s AND r.accepted_at > %s",
                    (interaction[1], now - timedelta(minutes=1)),
                ).fetchone()
                if count and count[0] >= self.policy.submissions_per_minute:
                    raise FeedbackRateLimited("Feedback submission rate exceeded.")
                latest = conn.execute(
                    "SELECT coalesce(max(revision), 0) + 1 FROM feedback_revisions "
                    "WHERE response_id = %s",
                    (response_id,),
                ).fetchone()
                assert latest is not None
                revision = latest[0]
                assessment_id = (
                    "a-" + uuid5(_ASSESSMENT_NAMESPACE, f"{interaction[0]}:{revision}").hex
                )
                conn.execute(
                    "INSERT INTO feedback_revisions "
                    "(response_id, revision, submission_id, accepted_at, submission, "
                    "assessment_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        response_id,
                        revision,
                        submission.submission_id,
                        now,
                        Jsonb(submission.model_dump(mode="json")),
                        assessment_id,
                    ),
                )
                receipt = FeedbackReceipt(
                    feedback_id=interaction[0],
                    response_id=response_id,
                    submission_id=submission.submission_id,
                    revision=revision,
                    accepted_at=now,
                    expires_at=interaction[2],
                    delivery_state="pending",
                )
        return receipt

    def report(
        self, cohort: "FeedbackCohort", *, offset: int = 0, limit: int = 100
    ) -> "FeedbackSummary":
        """Maintainer-only local inspection; never expose the full cohort to anonymous users."""
        from ask_phil.feedback_reporting import FeedbackSignal, ServedFeedback, summarize_feedback

        now = self.clock()
        if cohort.feedback_as_of > now:
            raise ValueError("The feedback cutoff cannot be in the future.")
        if cohort.served_from < now - timedelta(days=30):
            raise ValueError("The cohort starts outside the maximum retained feedback window.")
        self.ensure_schema()
        interactions = []
        with self.connect() as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            if conn.execute("SELECT to_regclass('answer_responses')").fetchone() != (None,):
                rows = conn.execute(
                    "SELECT i.response_id, i.feedback_id, i.served_at, a.document "
                    "FROM feedback_interactions i JOIN answer_responses a USING (response_id) "
                    "WHERE i.served_at >= %s AND i.served_at < %s AND i.expires_at > %s "
                    "ORDER BY i.served_at, i.response_id",
                    (cohort.served_from, cohort.served_until, now),
                ).fetchall()
                for row in rows:
                    revisions = conn.execute(
                        "SELECT revision, accepted_at, submission, delivery_state "
                        "FROM feedback_revisions WHERE response_id = %s ORDER BY revision",
                        (row[0],),
                    ).fetchall()
                    response = AnswerRecord.model_validate(row[3])
                    interactions.append(
                        ServedFeedback(
                            response_id=row[0],
                            served_at=row[2],
                            route=response.route,
                            outcome=response.status,
                            snapshot_id=response.snapshot_id,
                            application_sha256=response.application_sha256,
                            prompt_sha256=response.prompt_sha256,
                            model_id=hashlib.sha256(
                                json.dumps(row[3]["model_settings"], sort_keys=True).encode()
                            ).hexdigest(),
                            feedback=tuple(
                                FeedbackSignal(
                                    feedback_id=row[1],
                                    revision=r[0],
                                    accepted_at=r[1],
                                    rating=r[2]["rating"],
                                    categories=r[2]["categories"],
                                    comment=r[2]["comment"],
                                    proposed_correction=r[2]["proposed_correction"],
                                    delivery_state=r[3],
                                )
                                for r in revisions
                            ),
                        )
                    )
        return summarize_feedback(interactions, cohort, offset=offset, limit=limit)
