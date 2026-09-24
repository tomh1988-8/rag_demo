"""Reference-labelled retrieval and assembled-context scoring, independent of model outputs."""

from typing import Literal

from pydantic import Field, StrictBool

from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record

CriticalFailure = Literal["false_premise", "unsupported_negative", "false_citation"]


class ClaimReview(Record):
    claim: NonEmpty
    correct: StrictBool | None
    grounded: StrictBool | None
    citation_supported: StrictBool | None


class FactReview(Record):
    fact: NonEmpty
    covered: StrictBool | None


class QualityReview(Record):
    """External review annotations, never the answer model's self-reported confidence."""

    case_id: Identifier
    response_sha256: Fingerprint
    reference_sha256: Fingerprint
    reviewer: NonEmpty
    rationale: NonEmpty
    claims: tuple[ClaimReview, ...]
    required_facts: tuple[FactReview, ...]
    answerability: StrictBool | None
    critical_failures: tuple[CriticalFailure, ...] = ()


class ReviewMetric(Record):
    passed: int
    assessed: int
    unassessed: int
    value: float | None


class AnswerQuality(Record):
    correctness: ReviewMetric
    groundedness: ReviewMetric
    completeness: ReviewMetric
    citation_support: ReviewMetric
    answerability: ReviewMetric
    critical_failures: tuple[CriticalFailure, ...]


def score_answer_review(review: QualityReview) -> AnswerQuality:
    """Reviewed binary labels only. Missing assessments never become passes or failures.

    Correctness compares claims with references; groundedness compares with actual
    context; citation support checks the claim's cited passages. Completeness counts
    required facts/qualifications, answerability the appropriateness of the outcome.
    A zero denominator is unavailable. No combined score hides critical failures.
    """

    def metric(labels: tuple[bool | None, ...]) -> ReviewMetric:
        known = [value for value in labels if value is not None]
        passed = sum(known)
        return ReviewMetric(
            passed=passed,
            assessed=len(known),
            unassessed=len(labels) - len(known),
            value=passed / len(known) if known else None,
        )

    return AnswerQuality(
        correctness=metric(tuple(c.correct for c in review.claims)),
        groundedness=metric(tuple(c.grounded for c in review.claims)),
        completeness=metric(tuple(f.covered for f in review.required_facts)),
        citation_support=metric(tuple(c.citation_supported for c in review.claims)),
        answerability=metric((review.answerability,)),
        critical_failures=review.critical_failures,
    )


class FactLabel(Record):
    fact: str
    sufficient_sets: tuple[tuple[Identifier, ...], ...] = Field(min_length=1)


class RetrievalReference(Record):
    case_id: Identifier
    question: str
    answerable: bool
    relevant_ids: tuple[Identifier, ...]
    required_facts: tuple[FactLabel, ...]


class RetrievalScore(Record):
    k: int
    relevant_passage_count: int
    recall_at_k: float | None
    hit_at_k: float | None
    mrr_at_k: float | None
    required_fact_count: int
    context_fact_coverage: float | None
    context_sufficient: bool


def score_retrieval(
    reference: RetrievalReference,
    retrieved_ids: tuple[str, ...],
    context_ids: tuple[str, ...],
    *,
    k: int,
) -> RetrievalScore:
    """Deduplicate before top-k; exact snapshot-local IDs, binary passage relevance.

    Recall/Hit/MRR exclude unanswerable cases with no relevant passages. Context
    coverage uses independently labelled whole-span sufficient sets per required fact.
    No sufficient answer exists for a reference marked unanswerable in this snapshot.
    """
    if k < 1:
        raise ValueError("k must be positive")
    top = tuple(dict.fromkeys(retrieved_ids))[:k]
    relevant = set(reference.relevant_ids)
    ranks = [i for i, identifier in enumerate(top, 1) if identifier in relevant]
    context = set(context_ids)
    covered = sum(
        any(set(sufficient).issubset(context) for sufficient in fact.sufficient_sets)
        for fact in reference.required_facts
    )
    fact_count = len(reference.required_facts)
    return RetrievalScore(
        k=k,
        relevant_passage_count=len(relevant),
        recall_at_k=len(ranks) / len(relevant) if relevant else None,
        hit_at_k=float(bool(ranks)) if relevant else None,
        mrr_at_k=(1 / ranks[0] if ranks else 0.0) if relevant else None,
        required_fact_count=fact_count,
        context_fact_coverage=covered / fact_count if fact_count else None,
        context_sufficient=reference.answerable and fact_count > 0 and covered == fact_count,
    )
