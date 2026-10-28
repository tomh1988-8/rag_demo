"""Quality comparisons at the already confirmed evaluation/scorer boundary."""

import hashlib
import json
from pathlib import Path

import pytest

from ask_phil.evaluation import QualityReview, score_answer_review
from ask_phil.quality_comparison import ComparisonDataset, ComparisonRun


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("configuration", "prompt_sha256", "f" * 64),
        ("configuration", "snapshot_sha256", "f" * 64),
        ("configuration", "answer_settings_sha256", "f" * 64),
        ("configuration", "context_bytes", 600),
        ("configuration", "retrieval_k", 2),
        ("configuration", "retrieval_version", "unrecorded-retrieval"),
        ("configuration", "context_version", "unrecorded-context"),
        ("configuration", "cache_mode", "warm"),
        ("capture", "application_sha256", "f" * 64),
        ("capture", "prompt_sha256", "f" * 64),
        ("capture", "cache_namespace", "different-namespace"),
    ],
)
def test_comparison_rejects_declared_controls_that_differ_from_saved_answers(
    tmp_path: Path, section: str, field: str, value: str | int
) -> None:
    from ask_phil.quality_workflow import reviewed_comparison_run

    evidence = Path("docs/implementation/issue-9")
    dataset = ComparisonDataset.model_validate_json(
        Path("data/references/quality-comparison-v1.json").read_bytes()
    )
    capture = json.loads((evidence / "baseline-capture-v2.json").read_bytes())
    review = json.loads((evidence / "baseline-review.json").read_bytes())
    target = capture["configuration"] if section == "configuration" else capture
    target[field] = value
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(json.dumps(capture))
    review["capture_sha256"] = hashlib.sha256(capture_path.read_bytes()).hexdigest()
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(review))

    with pytest.raises(ValueError, match="controls.*saved answer"):
        reviewed_comparison_run(dataset, capture_path, review_path)


def test_comparison_rejects_relabelled_frozen_reference_even_with_fresh_hashes(
    tmp_path: Path,
) -> None:
    from ask_phil.evaluation import document_fingerprint
    from ask_phil.quality_workflow import reviewed_comparison_run

    evidence = Path("docs/implementation/issue-9")
    dataset = ComparisonDataset.model_validate_json(
        Path("data/references/quality-comparison-v1.json").read_bytes()
    )
    capture = json.loads((evidence / "baseline-capture-v2.json").read_bytes())
    review = json.loads((evidence / "baseline-review.json").read_bytes())
    row = capture["cases"][0]
    row["reference"]["category"] = "relabelled-category"
    row["reference_sha256"] = document_fingerprint(row["reference"])
    review["cases"][0]["review"]["reference_sha256"] = row["reference_sha256"]
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(json.dumps(capture))
    review["capture_sha256"] = hashlib.sha256(capture_path.read_bytes()).hexdigest()
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(review))

    with pytest.raises(ValueError, match="reference"):
        reviewed_comparison_run(dataset, capture_path, review_path)


def test_retained_comparison_replays_without_rewriting_historical_answers() -> None:
    from ask_phil.quality_comparison import compare_development
    from ask_phil.quality_workflow import reviewed_comparison_run

    evidence = Path("docs/implementation/issue-9")
    dataset = ComparisonDataset.model_validate_json(
        Path("data/references/quality-comparison-v1.json").read_bytes()
    )
    baseline = reviewed_comparison_run(
        dataset, evidence / "baseline-capture-v2.json", evidence / "baseline-review.json"
    )
    candidate = reviewed_comparison_run(
        dataset, evidence / "candidate-capture.json", evidence / "candidate-review.json"
    )
    report = compare_development(dataset, baseline, candidate, changed_factor="answer_settings")
    assert report["case_count"] == 7
    assert report["paired_observations"] == 14
    assert report["critical_gates"] == {"baseline": "failed", "candidate": "failed"}
    assert (
        report["dimensions"]
        == json.loads((evidence / "comparison.json").read_bytes())["dimensions"]
    )


@pytest.mark.parametrize("missing", ["case_ids", "case_state"])
def test_comparison_requires_declared_observations_and_completed_cases(
    tmp_path: Path, missing: str
) -> None:
    from ask_phil.quality_workflow import reviewed_comparison_run

    evidence = Path("docs/implementation/issue-9")
    dataset = ComparisonDataset.model_validate_json(
        Path("data/references/quality-comparison-v1.json").read_bytes()
    )
    capture = json.loads((evidence / "baseline-capture-v2.json").read_bytes())
    review = json.loads((evidence / "baseline-review.json").read_bytes())
    if missing == "case_ids":
        del capture["case_ids"]
    else:
        del capture["cases"][0]["state"]
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(json.dumps(capture))
    review["capture_sha256"] = hashlib.sha256(capture_path.read_bytes()).hexdigest()
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(review))

    with pytest.raises(ValueError, match="declared|complete"):
        reviewed_comparison_run(dataset, capture_path, review_path)


def test_comparison_rejects_retrieval_scores_that_differ_from_saved_evidence(
    tmp_path: Path,
) -> None:
    from ask_phil.quality_workflow import reviewed_comparison_run

    evidence = Path("docs/implementation/issue-9")
    dataset = ComparisonDataset.model_validate_json(
        Path("data/references/quality-comparison-v1.json").read_bytes()
    )
    capture = json.loads((evidence / "baseline-capture-v2.json").read_bytes())
    review = json.loads((evidence / "baseline-review.json").read_bytes())
    capture["cases"][0]["retrieval_score"]["recall_at_k"] = 0.0
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(json.dumps(capture))
    review["capture_sha256"] = hashlib.sha256(capture_path.read_bytes()).hexdigest()
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(review))

    with pytest.raises(ValueError, match="retrieval scores.*saved answer"):
        reviewed_comparison_run(dataset, capture_path, review_path)


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
