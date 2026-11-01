"""Descriptive feedback arithmetic over retained delivered-response cohorts."""

from collections.abc import Iterable
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from ask_phil.evidence import Fingerprint, Record
from ask_phil.feedback import Category, Rating


class FeedbackCohort(Record):
    served_from: AwareDatetime
    served_until: AwareDatetime
    feedback_as_of: AwareDatetime

    @model_validator(mode="after")
    def ordered_window(self) -> Self:
        if self.served_from >= self.served_until:
            raise ValueError("The served-time cohort must be a nonempty half-open interval.")
        return self


class FeedbackSignal(Record):
    feedback_id: UUID
    revision: int = Field(ge=1)
    accepted_at: AwareDatetime
    rating: Rating
    categories: tuple[Category, ...] = ()
    comment: str = ""
    proposed_correction: str = ""
    delivery_state: Literal["pending", "delivered"] = "pending"


class ServedFeedback(Record):
    response_id: UUID
    served_at: AwareDatetime
    route: str
    outcome: str
    snapshot_id: str
    application_sha256: Fingerprint
    prompt_sha256: Fingerprint
    model_id: str
    feedback: tuple[FeedbackSignal, ...] = ()


class FeedbackCounts(Record):
    eligible: int
    submitted: int
    rated: int
    positive: int
    negative: int
    skipped: int
    unrated: int
    no_feedback: int
    feedback_coverage: float | None
    positive_share: float | None
    reported_factual_errors: int
    reported_evidence_errors: int
    reported_harm_problems: int = 0
    pending_delivery: int
    independently_reviewed_correctness: None = None


class FeedbackSlice(Record):
    dimension: str
    value: str
    counts: FeedbackCounts


class FeedbackPriority(Record):
    response_id: UUID
    served_at: AwareDatetime
    route: str
    outcome: str
    priority: int
    signal: FeedbackSignal


class FeedbackSummary(Record):
    cohort: FeedbackCohort
    counts: FeedbackCounts
    slices: tuple[FeedbackSlice, ...]
    review_priorities: tuple[FeedbackPriority, ...]
    total_review_items: int
    next_offset: int | None
    interpretation: str = (
        "Retained committed API outcomes offered for delivery, including failed and unrated "
        "outcomes; socket receipt and unique people are not measured. The served-time "
        "interval is [from, until); feedback is the latest revision accepted at or before "
        "the cutoff. Coverage is rated/eligible; positive share is helpful/(helpful + "
        "not helpful). Skip and no feedback are not positive. Self-selected helpfulness "
        "and reported problems are not unbiased accuracy, checked correctness or causal proof. "
        "Category slices overlap when an item reports multiple categories. "
        "Delivery state is current processing state, not reconstructed historical state."
    )


def _counts(rows: list[tuple[ServedFeedback, FeedbackSignal | None]]) -> FeedbackCounts:
    signals = [signal for _, signal in rows if signal is not None]
    positive = sum(signal.rating == "helpful" for signal in signals)
    negative = sum(signal.rating == "not_helpful" for signal in signals)
    rated = positive + negative
    return FeedbackCounts(
        eligible=len(rows),
        submitted=len(signals),
        rated=rated,
        positive=positive,
        negative=negative,
        skipped=sum(signal.rating == "skip" for signal in signals),
        unrated=len(rows) - rated,
        no_feedback=len(rows) - len(signals),
        feedback_coverage=rated / len(rows) if rows else None,
        positive_share=positive / rated if rated else None,
        reported_factual_errors=sum(
            bool({"facts", "missing_outdated"}.intersection(signal.categories))
            for signal in signals
        ),
        reported_evidence_errors=sum("evidence" in signal.categories for signal in signals),
        reported_harm_problems=sum("harm" in signal.categories for signal in signals),
        pending_delivery=sum(signal.delivery_state == "pending" for signal in signals),
    )


def summarize_feedback(
    interactions: Iterable[ServedFeedback],
    cohort: FeedbackCohort,
    *,
    offset: int = 0,
    limit: int = 100,
) -> FeedbackSummary:
    """Count every current item once; paginate inspection without sampling the metrics."""
    if offset < 0 or not 1 <= limit <= 100:
        raise ValueError("Review pagination requires a nonnegative offset and 1-100 items.")
    rows: list[tuple[ServedFeedback, FeedbackSignal | None]] = []
    seen: set[UUID] = set()
    for row in interactions:
        if row.response_id in seen:
            raise ValueError("A delivered response must occur exactly once.")
        seen.add(row.response_id)
        if not (
            cohort.served_from <= row.served_at < cohort.served_until
            and row.served_at <= cohort.feedback_as_of
        ):
            continue
        revisions = [s for s in row.feedback if s.accepted_at <= cohort.feedback_as_of]
        if len({s.revision for s in row.feedback}) != len(row.feedback):
            raise ValueError("Feedback revisions must be unique per delivered response.")
        rows.append((row, max(revisions, key=lambda s: s.revision) if revisions else None))
    slices: list[FeedbackSlice] = []
    for dimension in (
        "route",
        "outcome",
        "snapshot_id",
        "application_sha256",
        "prompt_sha256",
        "model_id",
    ):
        groups: dict[str, list[tuple[ServedFeedback, FeedbackSignal | None]]] = {}
        for row, signal in rows:
            groups.setdefault(str(getattr(row, dimension)), []).append((row, signal))
        slices.extend(
            FeedbackSlice(dimension=dimension, value=value, counts=_counts(group))
            for value, group in sorted(groups.items())
        )
    categories: dict[str, list[tuple[ServedFeedback, FeedbackSignal | None]]] = {}
    for row, signal in rows:
        for category in signal.categories if signal and signal.categories else ("none",):
            categories.setdefault(category, []).append((row, signal))
    slices.extend(
        FeedbackSlice(dimension="category", value=value, counts=_counts(group))
        for value, group in sorted(categories.items())
    )
    priorities = []
    for row, signal in rows:
        if signal is None:
            continue
        priority = (
            1
            if {"facts", "missing_outdated"}.intersection(signal.categories)
            else 1
            if "harm" in signal.categories
            else 2
            if "evidence" in signal.categories
            else 3
            if signal.rating == "not_helpful"
            else 4
            if signal.categories or signal.comment or signal.proposed_correction
            else 5
            if signal.rating == "helpful"
            else 6
        )
        priorities.append(
            FeedbackPriority(
                response_id=row.response_id,
                served_at=row.served_at,
                route=row.route,
                outcome=row.outcome,
                priority=priority,
                signal=signal,
            )
        )
    priorities.sort(key=lambda p: (p.priority, p.signal.accepted_at, str(p.response_id)))
    end = offset + limit
    return FeedbackSummary(
        cohort=cohort,
        counts=_counts(rows),
        slices=tuple(slices),
        review_priorities=tuple(priorities[offset:end]),
        total_review_items=len(priorities),
        next_offset=end if end < len(priorities) else None,
    )
