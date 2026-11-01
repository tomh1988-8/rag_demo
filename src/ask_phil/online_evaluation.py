"""Versioned online sampling and context-only assessment contracts."""

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, Field

from ask_phil.answers import AnswerRecord
from ask_phil.evaluation import document_fingerprint
from ask_phil.evidence import Fingerprint, Identifier, Record
from ask_phil.execution import ExecutionPolicies, ExecutionRecord
from ask_phil.feedback import Category, Rating
from ask_phil.feedback_reporting import FeedbackSummary
from ask_phil.openrouter import OpenRouterProfile
from ask_phil.semantic_judge import SupportAssessment


class OnlinePolicy(Record):
    version: Literal["online-v1"] = "online-v1"
    enabled: bool = True
    background_rate: float = Field(default=0.1, ge=0, le=1, allow_inf_nan=False)
    feedback_rate: float = Field(default=1, ge=0, le=1, allow_inf_nan=False)
    seed: str = Field(default="ask-phil-online-v1", min_length=1, max_length=100)
    batch_size: int = Field(default=20, ge=1, le=100)
    interval_seconds: float = Field(default=10, ge=0.1, le=300)
    retry_seconds: float = Field(default=10, ge=0.1, le=300)
    max_attempts: int = Field(default=3, ge=1, le=5)
    seconds: float = Field(default=45, ge=1, le=120)
    max_judge_calls: int = Field(default=20, ge=0, le=100)
    max_judge_spend_usd: float = Field(default=0.25, ge=0, le=1, allow_inf_nan=False)
    review_rate: float = Field(default=0.1, gt=0, le=1, allow_inf_nan=False)
    evaluator_revision: Identifier = "support-v1"

    @classmethod
    def from_environment(cls) -> "OnlinePolicy":
        path = os.environ.get("ASK_PHIL_ONLINE_POLICY")
        policy = cls.model_validate_json(Path(path).read_bytes()) if path else cls()
        if os.environ.get("ASK_PHIL_ONLINE_ENABLED", "true").lower() != "true":
            return policy.model_copy(update={"enabled": False})
        return policy

    @property
    def fingerprint(self) -> str:
        return document_fingerprint(self.model_dump(mode="json"))

    def selects(self, response_id: UUID, cohort: str, rate: float) -> bool:
        value = hashlib.sha256(f"{self.seed}:{cohort}:{response_id}".encode()).digest()
        return int.from_bytes(value, "big") < int(rate * 2**256)


class OnlineChecks(Record):
    version: Literal["saved-evidence-checks-v1"] = "saved-evidence-checks-v1"
    citation_integrity: bool | None
    context_available: bool
    reference_correctness: None = None
    reference_recall: None = None
    reference_completeness: None = None
    persona: None = None
    reason: str


class OnlineConfiguration(Record):
    policy: OnlinePolicy
    tracking_sha256: Fingerprint
    calibration_sha256: Fingerprint | None
    scope_sha256: Fingerprint | None
    judge: OpenRouterProfile | None
    execution: ExecutionPolicies | None
    implementation: dict[str, Fingerprint]


def check_saved_answer(response: AnswerRecord) -> OnlineChecks:
    """Check retained citation identity, never infer semantic support or truth."""
    context = {p.evidence_id: p for p in response.context}
    integrity = all(
        c.evidence_id in context
        and c.sha256 == context[c.evidence_id].sha256
        and c.text == context[c.evidence_id].text
        and c.start == context[c.evidence_id].start
        and c.end == context[c.evidence_id].end
        for c in response.citations
    )
    return OnlineChecks(
        citation_integrity=integrity if response.citations else None,
        context_available=bool(response.context),
        reason="Citation identity checks only; support needs a calibrated semantic judge. "
        "Correctness, recall, completeness and persona have no reviewed online expectations.",
    )


JobState = Literal[
    "unselected",
    "pending",
    "running",
    "completed",
    "failed",
    "ineligible",
    "budget_skipped",
    "disabled",
]


class OnlineJob(Record):
    job_id: UUID
    response_id: UUID
    generation_id: UUID
    config_sha256: Fingerprint
    created_at: AwareDatetime
    served_at: AwareDatetime
    updated_at: AwareDatetime
    state: JobState
    selection_reasons: tuple[str, ...] = ()
    selection_priority: int = 3
    background_rate: float
    feedback_rate: float
    feedback_revision: int = 0
    assessment_feedback_revision: int = 0
    attempts: int = 0
    next_attempt_at: AwareDatetime
    failure: str | None = None
    response_sha256: Fingerprint | None = None
    trace_verified: bool = False
    checks: OnlineChecks | None = None
    support_state: str = "disabled"
    support: SupportAssessment | None = None
    support_execution: ExecutionRecord | None = None
    support_result_key: Fingerprint | None = None
    support_origin_job_id: UUID | None = None
    support_reused: bool = False
    judge_calls: int = 0
    judge_reserved_usd: float = 0
    judge_cost_usd: float | None = 0
    completed_at: AwareDatetime | None = None
    exported: bool = False
    prefect_run_id: UUID | None = None


class OnlineInspection(OnlineJob):
    response: AnswerRecord
    configuration: OnlineConfiguration | None = None
    triage: tuple["OnlineTriage", ...] = ()


class OnlineTriage(Record):
    rubric: Literal["feedback-report-triage-v1"] = "feedback-report-triage-v1"
    feedback_revision: int
    feedback_id: UUID
    accepted_at: AwareDatetime
    processed_at: AwareDatetime
    rating: Rating
    categories: tuple[Category, ...]
    priority: Literal["reported_problem", "negative", "remaining"]
    disposition: Literal["unresolved"] = "unresolved"
    interpretation: str = "Feedback-aware triage; a reported issue is not checked correctness."


class OnlineDisagreement(Record):
    response_id: UUID
    feedback_revision: int
    rating: Rating
    supported: bool
    reason: str
    disposition: Literal["unresolved"] = "unresolved"


class ReviewRequirement(Record):
    response_id: UUID
    feedback_revision: int
    reason: str


class OnlineCycle(Record):
    discovered: int = 0
    completed: int = 0
    pending: int = 0
    disabled: bool = False
    busy: bool = False


class OnlineReport(Record):
    report_id: UUID
    created_at: AwareDatetime
    config_sha256: Fingerprint
    configuration: OnlineConfiguration
    feedback: FeedbackSummary
    selected: int
    online_eligible: int
    completed: int
    states: dict[str, int]
    selection_cohorts: dict[str, int]
    sample_coverage: float | None
    score_coverage: float | None
    oldest_pending_seconds: float | None
    pending_triage_revisions: int = 0
    triaged_revisions: int = 0
    oldest_pending_triage_seconds: float | None = None
    maximum_triage_lag_seconds: float | None = None
    assessment_lag_seconds: tuple[float, ...]
    online_judge_cost_usd: float | None
    online_judge_reserved_usd: float
    online_judge_calls: int
    cumulative_online_judge_calls: int = 0
    cumulative_online_judge_cost_usd: float | None = 0
    cumulative_online_judge_allocation_usd: float = 0
    unsettled_online_judge_jobs: int = 0
    scored: int = 0
    support_scored: int = 0
    exported: int = 0
    enabled: bool = True
    serving_cost_usd: float | None
    offline_evaluation_cost_usd: None = None
    jobs: tuple[OnlineJob, ...]
    disagreements: tuple[OnlineDisagreement, ...] = ()
    required_reviews: tuple[ReviewRequirement, ...] = ()
    remaining_rating_review_rate: float = 0.1
    interpretation: str = (
        "Eligible/rated denominators are all retained served interactions; selected/eligible "
        "and scored/selected describe this configuration's sample. Completed includes only "
        "successful jobs; code checks and semantic scores have separate denominators. "
        "Cumulative online expense includes all configuration revisions and retained "
        "uncertain reservations, even after interaction expiry. Feedback is latest "
        "as of the stated cutoff; processing states are current at report creation. "
        "Counts are served deliveries, not independent factual examples. "
        "Background and directed samples may overlap. Ratings are self-selected helpfulness "
        "and reported issues, not unbiased accuracy. Context support is not canon correctness. "
        "Observed trends do not establish causality. Offline expense is unavailable here."
    )


def seconds_since(now: datetime, earlier: datetime) -> float:
    return max(0.0, (now - earlier).total_seconds())
