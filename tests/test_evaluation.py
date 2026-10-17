import pytest

from ask_phil.evaluation import FactLabel, RetrievalReference, score_retrieval


def test_reviewed_answer_scores_keep_correctness_support_completeness_and_outcome_separate() -> (
    None
):
    from ask_phil.evaluation import QualityReview, score_answer_review

    review = QualityReview.model_validate(
        {
            "case_id": "worked-quality-example",
            "response_sha256": "a" * 64,
            "reference_sha256": "b" * 64,
            "reviewer": "Independent worked arithmetic",
            "rationale": "Three claims, one unassessed for support; three required facts.",
            "claims": [
                {
                    "claim": "Correct and grounded, wrong citation",
                    "correct": True,
                    "grounded": True,
                    "citation_supported": False,
                },
                {
                    "claim": "Correct by reference but unsupported",
                    "correct": True,
                    "grounded": False,
                    "citation_supported": False,
                },
                {
                    "claim": "Wrong; support unassessed",
                    "correct": False,
                    "grounded": None,
                    "citation_supported": None,
                },
            ],
            "required_facts": [
                {"fact": "Covered fact", "covered": True},
                {"fact": "Missing fact", "covered": False},
                {"fact": "Another missing fact", "covered": False},
            ],
            "answerability": False,
            "critical_failures": ["false_citation"],
        }
    )
    scores = score_answer_review(review)
    assert scores.correctness.value == pytest.approx(2 / 3)
    assert scores.groundedness.value == 0.5
    assert scores.groundedness.assessed == 2
    assert scores.groundedness.unassessed == 1
    assert scores.completeness.value == pytest.approx(1 / 3)
    assert scores.citation_support.value == 0
    assert scores.answerability.value == 0
    assert scores.critical_failures == ("false_citation",)


def test_no_factual_claims_or_unassessed_labels_do_not_manufacture_quality_passes() -> None:
    from ask_phil.evaluation import QualityReview, score_answer_review

    review = QualityReview.model_validate(
        {
            "case_id": "abstained",
            "response_sha256": "a" * 64,
            "reference_sha256": "b" * 64,
            "reviewer": "Worked null-denominator example",
            "rationale": "No claims; review pending.",
            "claims": [],
            "required_facts": [{"fact": "Coverage qualification", "covered": None}],
            "answerability": None,
        }
    )
    scores = score_answer_review(review)
    assert (
        scores.correctness.value
        is scores.groundedness.value
        is scores.citation_support.value
        is None
    )
    assert scores.correctness.assessed == scores.correctness.unassessed == 0
    assert scores.completeness.value is None
    assert scores.completeness.unassessed == 1
    assert scores.answerability.value is None


def test_relevance_remains_separate_from_a_correct_but_off_topic_answer() -> None:
    from ask_phil.evaluation import ClaimReview, QualityReview, score_answer_review

    review = QualityReview(
        case_id="off-topic",
        response_sha256="a" * 64,
        reference_sha256="b" * 64,
        reviewer="Independently authored scorer counterexample",
        rationale="The question asks about arrival; the answer only describes a marriage.",
        claims=(
            ClaimReview(
                claim="A source-supported marriage fact",
                correct=True,
                grounded=True,
                citation_supported=True,
            ),
        ),
        required_facts=(),
        answerability=None,
        relevance=False,
    )
    scores = score_answer_review(review)
    assert scores.correctness.value == 1
    assert scores.relevance.value == 0
    assert scores.completeness.value is None


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


@pytest.mark.parametrize("change", ["response", "reference", "required_facts"])
def test_frozen_response_scores_reject_changed_outputs_references_or_reviewed_fact_lists(
    change: str,
) -> None:
    from ask_phil.evaluation import FactReview, QualityReview, score_captured_answer

    review = QualityReview(
        case_id="frozen-example",
        response_sha256="20caabb4ef274d20d2ba249cfba6797fa70f7457bc377254c15548a285e93da6",
        reference_sha256="dcd551b4bd4644479116f7d938f764e046234aee969c5a04d9c06a0540d38040",
        reviewer="Independently specified canonical JSON example",
        rationale="The assessment belongs only to the original output and complete fact list.",
        claims=(),
        required_facts=(FactReview(fact="Expected fact", covered=True),),
        answerability=True,
    )
    response = {"answer": "changed" if change == "response" else "captured"}
    reference = {"fact": "changed" if change == "reference" else "expected"}
    facts = ("Changed fact",) if change == "required_facts" else ("Expected fact",)
    with pytest.raises(ValueError, match="Stale|fact"):
        score_captured_answer(review, response, reference, facts)
