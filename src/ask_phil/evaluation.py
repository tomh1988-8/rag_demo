"""Reference-labelled retrieval and assembled-context scoring, independent of model outputs."""

from pydantic import Field

from ask_phil.evidence import Identifier, Record


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
