import pytest

from ask_phil.evaluation import FactLabel, RetrievalReference, score_retrieval


def test_retrieval_success_does_not_hide_evidence_lost_from_assembled_context() -> None:
    reference = RetrievalReference(
        case_id="worked-two-fact-example",
        question="A synthetic scoring example",
        answerable=True,
        relevant_ids=("p1", "p2", "p3"),
        required_facts=(
            FactLabel(fact="first required fact", sufficient_sets=(("p1",),)),
            FactLabel(fact="second required fact", sufficient_sets=(("p2", "p3"),)),
        ),
    )
    result = score_retrieval(reference, ("irrelevant", "p1", "p2"), ("p1",), k=3)
    assert result.recall_at_k == pytest.approx(2 / 3)
    assert result.hit_at_k == 1
    assert result.mrr_at_k == 0.5
    assert result.relevant_passage_count == 3
    assert result.context_fact_coverage == 0.5
    assert result.required_fact_count == 2
    assert result.context_sufficient is False


def test_absent_evidence_has_no_positive_recall_denominator_or_sufficient_context() -> None:
    reference = RetrievalReference(
        case_id="absent",
        question="Who is Phil's mother?",
        answerable=False,
        relevant_ids=(),
        required_facts=(),
    )
    result = score_retrieval(reference, ("phil-arrival-001",), ("phil-arrival-001",), k=3)
    assert result.recall_at_k is None
    assert result.hit_at_k is None
    assert result.mrr_at_k is None
    assert result.context_fact_coverage is None
    assert result.context_sufficient is False
    assert result.relevant_passage_count == result.required_fact_count == 0
