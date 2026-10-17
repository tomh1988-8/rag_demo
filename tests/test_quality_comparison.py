"""Quality comparisons at the already confirmed evaluation/scorer boundary."""

from pathlib import Path

import pytest

from ask_phil.evaluation import QualityReview, score_answer_review
from ask_phil.quality_comparison import ComparisonDataset, ComparisonRun


def test_comparison_rejects_scores_that_do_not_match_the_frozen_review(tmp_path: Path) -> None:
    import hashlib
    import json

    from ask_phil.evaluation import FactReview, document_fingerprint
    from ask_phil.quality_comparison import ComparisonDataset
    from ask_phil.quality_workflow import reviewed_comparison_run

    dataset = ComparisonDataset.model_validate_json(
        Path("data/references/quality-comparison-v1.json").read_bytes()
    )
    case = dataset.cases[0]
    reference = {
        **case.model_dump(mode="json"),
        "case_id": "phil-intro-r0",
        "comparison_case_id": case.case_id,
        "repeat": 0,
    }
    response = {"answer": "An unrelated answer.", "estimated_api_cost_usd": 0.0, "elapsed_ms": 1}
    annotation = QualityReview(
        case_id="phil-intro-r0",
        response_sha256=document_fingerprint(response),
        reference_sha256=document_fingerprint(reference),
        reviewer="Independent counterexample",
        rationale="The answer omits the arrival fact.",
        claims=(),
        required_facts=(FactReview(fact=case.required_facts[0].fact, covered=False),),
        answerability=False,
        relevance=False,
    )
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(
        json.dumps(
            {
                "state": "complete",
                "case_ids": ["phil-intro-r0"],
                "dataset_sha256": dataset.fingerprint,
                "code_revision": "test-revision",
                "configuration": {
                    "configuration_id": "single-query-v1",
                    "retrieval_version": "original-query-v1",
                    "context_version": "whole-v2",
                    "context_bytes": 1200,
                    "retrieval_k": 3,
                    "answer_settings_sha256": "a" * 64,
                    "prompt_sha256": "b" * 64,
                    "snapshot_sha256": "c" * 64,
                    "cache_mode": "off",
                    "cache_namespace": "independent-test-namespace",
                },
                "cases": [
                    {
                        "case_id": "phil-intro-r0",
                        "reference": reference,
                        "response": response,
                        "response_sha256": document_fingerprint(response),
                        "reference_sha256": document_fingerprint(reference),
                        "state": "complete",
                        "retrieval_score": None,
                        "stage_ms": {},
                    }
                ],
            }
        )
    )
    scores = score_answer_review(annotation).model_dump(mode="json")
    scores["completeness"].update(passed=1, value=1.0)
    review_path = tmp_path / "review.json"
    review_path.write_text(
        json.dumps(
            {
                "state": "complete",
                "capture_sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest(),
                "cases": [
                    {
                        "case_id": "phil-intro-r0",
                        "review": annotation.model_dump(mode="json"),
                        "scores": scores,
                    }
                ],
            }
        )
    )
    with pytest.raises(ValueError, match="scores.*review"):
        reviewed_comparison_run(dataset, capture_path, review_path)


@pytest.fixture
def worked_comparison() -> tuple[ComparisonDataset, ComparisonRun, ComparisonRun]:
    dataset = ComparisonDataset.model_validate_json(
        Path("data/references/quality-comparison-v1.json").read_bytes()
    )
    case = next(c for c in dataset.cases if c.split == "development")
    review = QualityReview(
        case_id=case.case_id,
        response_sha256="a" * 64,
        reference_sha256="b" * 64,
        reviewer="Independent worked comparison",
        rationale="The candidate misses relevance on the second repeat.",
        claims=(),
        required_facts=(),
        answerability=True,
        relevance=True,
    )
    config = {
        "configuration_id": "single-query-v1",
        "retrieval_version": "original-query-v1",
        "context_version": "whole-passages-v2",
        "context_bytes": 1200,
        "retrieval_k": 3,
        "answer_settings_sha256": "a" * 64,
        "prompt_sha256": "b" * 64,
        "snapshot_sha256": "c" * 64,
        "cache_mode": "off",
        "cache_namespace": "baseline-development-unique",
    }
    rows = [
        {
            "case_id": case.case_id,
            "repeat": repeat,
            "response_sha256": "d" * 64,
            "quality": score_answer_review(review).model_dump(),
            "serving_cost_usd": 0.01,
            "elapsed_ms": 100,
            "stage_ms": {"retrieval": None, "context": None, "generation": None},
        }
        for repeat in (0, 1)
    ]
    common = {
        "dataset_sha256": dataset.fingerprint,
        "code_revision": "worked-revision",
        "application_sha256": "e" * 64,
    }
    baseline = ComparisonRun.model_validate(
        {**common, "configuration": config, "observations": rows}
    )
    candidate_rows = [dict(row) for row in rows]
    candidate_rows[1] = {
        **candidate_rows[1],
        "quality": score_answer_review(review.model_copy(update={"relevance": False})).model_dump(),
    }
    candidate = ComparisonRun.model_validate(
        {
            **common,
            "configuration": {**config, "cache_namespace": "candidate-development-unique"},
            "observations": candidate_rows,
        }
    )
    return dataset, baseline, candidate


def test_paired_comparison_reports_repeats_failures_and_unknowns_separately(
    worked_comparison: tuple[ComparisonDataset, ComparisonRun, ComparisonRun],
) -> None:
    from ask_phil.quality_comparison import compare_development

    dataset, baseline, candidate = worked_comparison
    case = dataset.cases[0]
    report = compare_development(dataset, baseline, candidate, changed_factor="repeat_control")
    assert report["independent_groups"] == 1
    assert report["case_count"] == 1
    assert report["paired_observations"] == 2
    assert report["dimensions"]["relevance"]["candidate_mean"] == 0.5
    assert report["dimensions"]["relevance"]["paired_delta"] == -0.5
    assert report["dimensions"]["correctness"]["paired_delta"] is None
    assert report["failures"][0]["case_id"] == case.case_id
    assert report["failures"][0]["dimension"] == "relevance"
    assert report["serving_cost_usd"] == {"baseline": 0.02, "candidate": 0.02}
    assert report["offline_evaluation_cost_usd"] == {"baseline": 0.0, "candidate": 0.0}


@pytest.mark.parametrize(
    "problem",
    ["model", "cache", "namespace", "pairs", "duplicates", "holdout", "code", "application"],
)
def test_comparison_rejects_uncontrolled_or_contaminated_pairs(
    worked_comparison: tuple[ComparisonDataset, ComparisonRun, ComparisonRun], problem: str
) -> None:
    from ask_phil.quality_comparison import compare_development

    dataset, baseline, candidate = worked_comparison
    if problem == "model":
        candidate = candidate.model_copy(
            update={
                "configuration": candidate.configuration.model_copy(
                    update={"answer_settings_sha256": "f" * 64}
                )
            }
        )
    elif problem == "cache":
        candidate = candidate.model_copy(
            update={
                "configuration": candidate.configuration.model_copy(update={"cache_mode": "warm"})
            }
        )
    elif problem == "namespace":
        candidate = candidate.model_copy(update={"configuration": baseline.configuration})
    elif problem == "pairs":
        candidate = candidate.model_copy(update={"observations": candidate.observations[:1]})
    elif problem == "duplicates":
        candidate = candidate.model_copy(
            update={"observations": (*candidate.observations, candidate.observations[0])}
        )
    elif problem == "code":
        candidate = candidate.model_copy(update={"code_revision": "different-source-revision"})
    elif problem == "application":
        candidate = candidate.model_copy(update={"application_sha256": "f" * 64})
    else:
        dataset = dataset.model_copy(
            update={
                "cases": (
                    dataset.cases[0].model_copy(update={"split": "held_out"}),
                    *dataset.cases[1:],
                )
            }
        )
        baseline = baseline.model_copy(update={"dataset_sha256": dataset.fingerprint})
        candidate = candidate.model_copy(update={"dataset_sha256": dataset.fingerprint})
    with pytest.raises(ValueError):
        compare_development(dataset, baseline, candidate, changed_factor="repeat_control")


def test_related_events_cannot_cross_evaluation_partitions() -> None:
    from ask_phil.quality_comparison import ComparisonCase, ComparisonDataset

    baseline = ComparisonCase(
        case_id="arrival",
        group_ids=("arrival-event",),
        split="development",
        category="supported",
        question="When did Phil arrive?",
        snapshot_id="source-v1",
        expected_status="answered",
        required_facts=(),
        allowed_alternatives=(),
        forbidden_assertions=(),
        evidence=(),
        review_note="Synthetic split-control example; no factual reference annotations.",
        synthetic_provenance="Authored software fixture, not canon.",
    )
    with pytest.raises(ValueError, match="group.*split"):
        ComparisonDataset(
            dataset_id="worked-splits-v1",
            cases=(
                baseline,
                baseline.model_copy(update={"case_id": "paraphrase", "split": "held_out"}),
            ),
        )


def test_reusing_the_same_evidence_cannot_hide_a_cross_split_derivative() -> None:
    from ask_phil.quality_comparison import ComparisonDataset

    dataset = ComparisonDataset.model_validate_json(
        Path("data/references/quality-comparison-v1.json").read_bytes()
    )
    original = dataset.cases[0]
    derivative = original.model_copy(
        update={
            "case_id": "hidden-derivative",
            "split": "held_out",
            "group_ids": ("misleading-new-group",),
            "session": None,
            "question": "In which year and month did Phil appear?",
        }
    )
    with pytest.raises(ValueError, match="evidence.*split"):
        ComparisonDataset(dataset_id="evidence-overlap-v1", cases=(original, derivative))
