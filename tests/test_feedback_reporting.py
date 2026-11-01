from datetime import UTC, datetime, timedelta
from uuid import UUID

from ask_phil.feedback import Rating
from ask_phil.feedback_reporting import (
    FeedbackCohort,
    FeedbackSignal,
    ServedFeedback,
    summarize_feedback,
)

NOW = datetime(2026, 10, 29, 12, tzinfo=UTC)
COHORT = FeedbackCohort(
    served_from=NOW - timedelta(hours=1),
    served_until=NOW + timedelta(hours=1),
    feedback_as_of=NOW + timedelta(minutes=5),
)


def test_skip_and_missing_feedback_never_become_positive_ratings() -> None:
    ratings: tuple[Rating | None, ...] = ("helpful", "not_helpful", "skip", None)
    interactions = tuple(
        ServedFeedback(
            response_id=UUID(int=index),
            served_at=NOW,
            route="text_rag",
            outcome="answered",
            snapshot_id="synthetic-v1",
            application_sha256="a" * 64,
            prompt_sha256="b" * 64,
            model_id="test-model",
            feedback=()
            if rating is None
            else (
                FeedbackSignal(
                    feedback_id=UUID(int=index + 10),
                    revision=1,
                    accepted_at=NOW + timedelta(minutes=1),
                    rating=rating,
                    categories=("facts",) if rating == "not_helpful" else (),
                ),
            ),
        )
        for index, rating in enumerate(ratings, start=1)
    )
    summary = summarize_feedback(interactions, COHORT)
    assert summary.counts.model_dump() == {
        "eligible": 4,
        "submitted": 3,
        "rated": 2,
        "positive": 1,
        "negative": 1,
        "skipped": 1,
        "unrated": 2,
        "no_feedback": 1,
        "feedback_coverage": 0.5,
        "positive_share": 0.5,
        "reported_factual_errors": 1,
        "reported_evidence_errors": 0,
        "pending_delivery": 3,
        "independently_reviewed_correctness": None,
    }
    assert summary.total_review_items == 3
    assert summary.review_priorities[0].response_id == UUID(int=2)


def test_late_revisions_change_one_current_vote_and_respect_the_feedback_cutoff() -> None:
    interaction = ServedFeedback(
        response_id=UUID(int=1),
        served_at=NOW,
        route="graph",
        outcome="partial",
        snapshot_id="synthetic-v1",
        application_sha256="a" * 64,
        prompt_sha256="b" * 64,
        model_id="no-model",
        feedback=(
            FeedbackSignal(
                feedback_id=UUID(int=2),
                revision=1,
                accepted_at=NOW,
                rating="not_helpful",
                categories=("facts",),
            ),
            FeedbackSignal(
                feedback_id=UUID(int=2),
                revision=2,
                accepted_at=NOW + timedelta(minutes=10),
                rating="helpful",
            ),
        ),
    )
    earlier = summarize_feedback([interaction], COHORT)
    later = summarize_feedback(
        [interaction], COHORT.model_copy(update={"feedback_as_of": NOW + timedelta(minutes=15)})
    )
    assert (earlier.counts.rated, earlier.counts.negative, earlier.counts.positive) == (1, 1, 0)
    assert (later.counts.rated, later.counts.negative, later.counts.positive) == (1, 0, 1)
    assert earlier.counts.reported_factual_errors == 1
    assert later.counts.reported_factual_errors == 0
    assert len(later.review_priorities) == 1
    assert later.review_priorities[0].signal.revision == 2


def test_empty_and_unrated_cohorts_have_no_manufactured_positive_score() -> None:
    empty = summarize_feedback([], COHORT)
    assert empty.counts.feedback_coverage is None
    assert empty.counts.positive_share is None
    assert empty.counts.independently_reviewed_correctness is None
    unrated = ServedFeedback(
        response_id=UUID(int=1),
        served_at=NOW,
        route="investigation",
        outcome="clarification",
        snapshot_id="synthetic-v1",
        application_sha256="a" * 64,
        prompt_sha256="b" * 64,
        model_id="test-model",
    )
    summary = summarize_feedback([unrated], COHORT)
    assert summary.counts.eligible == 1
    assert summary.counts.feedback_coverage == 0
    assert summary.counts.positive_share is None
    assert summary.counts.positive == 0


def test_review_pagination_does_not_sample_or_truncate_the_metric_denominators() -> None:
    interactions = [
        ServedFeedback(
            response_id=UUID(int=index),
            served_at=NOW,
            route="text_rag",
            outcome="answered",
            snapshot_id="synthetic-v1",
            application_sha256="a" * 64,
            prompt_sha256="b" * 64,
            model_id="test-model",
            feedback=(
                FeedbackSignal(
                    feedback_id=UUID(int=index + 20),
                    revision=1,
                    accepted_at=NOW,
                    rating="helpful",
                ),
            ),
        )
        for index in range(1, 4)
    ]
    first = summarize_feedback(interactions, COHORT, limit=1)
    second = summarize_feedback(interactions, COHORT, offset=1, limit=1)
    third = summarize_feedback(interactions, COHORT, offset=2, limit=1)
    assert (first.counts.eligible, second.counts.eligible, third.counts.eligible) == (3, 3, 3)
    assert (first.total_review_items, first.next_offset, second.next_offset, third.next_offset) == (
        3,
        1,
        2,
        None,
    )
    assert len({page.review_priorities[0].response_id for page in (first, second, third)}) == 3
