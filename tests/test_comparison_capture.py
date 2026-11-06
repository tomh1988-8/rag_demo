"""A comparison is complete only when its full frozen plan is represented."""

import gzip
import json
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path

import pytest

from ask_phil.comparison_capture import ComparisonPlan
from ask_phil.evaluation import CapturedAnswers, EvaluationRun


def test_routing_score_rejects_an_empty_experiment(tmp_path: Path) -> None:
    captures = tmp_path / "captures"
    reviews = tmp_path / "reviews"
    captures.mkdir()
    reviews.mkdir()
    output = tmp_path / "comparison.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.evaluate_routing",
            "score",
            "--captures",
            str(captures),
            "--reviews",
            str(reviews),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "incomplete" in result.stderr

    assert not output.exists()


def test_stopped_comparison_retains_the_full_plan_and_pending_work(tmp_path: Path) -> None:
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [{"case_id": "one"}, {"case_id": "two"}]}))
    plan = ComparisonPlan(references, {"baseline": ("one", "two"), "candidate": ("one", "two")})
    directory = tmp_path / "first"

    with pytest.raises(TimeoutError):
        with plan.record(directory):
            with EvaluationRun(directory / "baseline.json", references, ("one", "two")) as run:
                run.capture("one", lambda: {"response": {"answer": "One."}})
                run.capture("two", lambda: {"response": {"answer": "Two."}})
            raise TimeoutError("The experiment cannot admit another request.")

    frozen = json.loads((directory / "comparison-plan.json").read_bytes())
    progress = json.loads((directory / "comparison-progress.json").read_bytes())
    assert frozen["arms"] == {"baseline": ["one", "two"], "candidate": ["one", "two"]}
    assert progress["state"] == "incomplete"
    assert [
        (r["arm"], r["case_id"]) for r in progress["observations"] if r["state"] == "pending"
    ] == [
        ("candidate", "one"),
        ("candidate", "two"),
    ]
    with pytest.raises(ValueError, match="incomplete"):
        plan.captures(directory)


def test_continuation_completes_only_missing_observations_without_replacing_prior_work(
    tmp_path: Path,
) -> None:
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [{"case_id": "one"}, {"case_id": "two"}]}))
    plan = ComparisonPlan(references, {"baseline": ("one", "two"), "candidate": ("one", "two")})
    first = tmp_path / "first"
    second = tmp_path / "continuation"
    with plan.record(first):
        with EvaluationRun(first / "baseline.json", references, ("one", "two")) as run:
            run.capture("one", lambda: {"response": {"answer": "Baseline one."}})
            run.capture("two", lambda: {"response": {"answer": "Baseline two."}})
        with EvaluationRun(first / "candidate.json", references, ("one",)) as run:
            run.capture("one", lambda: {"response": {"answer": "Candidate one."}})
    original = (first / "candidate.json").read_bytes()
    assert plan.pending(second, first) == {"candidate": ("two",)}

    with plan.record(second, prior=(first,)):
        with EvaluationRun(second / "candidate.json", references, ("two",)) as run:
            run.capture("two", lambda: {"response": {"answer": "Candidate two."}})

    progress = json.loads((second / "comparison-progress.json").read_bytes())
    captures = plan.captures(second)
    assert plan.pending(tmp_path / "third", second) == {}
    assert progress["state"] == "complete"
    assert len(progress["observations"]) == 4
    assert [row["response"]["answer"] for row in captures["candidate"].cases.values()] == [
        "Candidate one.",
        "Candidate two.",
    ]
    assert (first / "candidate.json").read_bytes() == original


def test_losslessly_archived_captures_keep_their_plan_and_original_response(tmp_path: Path) -> None:
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [{"case_id": "one"}]}))
    plan = ComparisonPlan(references, {"baseline": ("one",)})
    directory = tmp_path / "capture"
    with plan.record(directory):
        with EvaluationRun(directory / "baseline.json", references, ("one",)) as run:
            run.capture("one", lambda: {"response": {"answer": "Original retained answer."}})
    original = directory / "baseline.json"
    original.with_suffix(".json.gz").write_bytes(gzip.compress(original.read_bytes(), mtime=0))
    original.unlink()

    capture = plan.captures(directory)["baseline"]
    assert capture.cases["one"]["response"]["answer"] == "Original retained answer."
    assert plan.inspect(directory)["state"] == "complete"


@pytest.mark.parametrize("problem", ["duplicate", "extra_arm", "changed_plan"])
def test_comparison_rejects_work_outside_the_frozen_plan(tmp_path: Path, problem: str) -> None:
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [{"case_id": "one"}]}))
    plan = ComparisonPlan(references, {"baseline": ("one",)})
    first = tmp_path / "first"
    with plan.record(first):
        with EvaluationRun(first / "baseline.json", references, ("one",)) as run:
            run.capture("one", lambda: {"response": {"answer": "Original."}})
    if problem == "duplicate":
        other = tmp_path / "duplicate"
        other.mkdir()
        (other / "baseline.json").write_bytes((first / "baseline.json").read_bytes())
        with pytest.raises(ValueError, match="Duplicate"):
            plan.captures(first, other)
    elif problem == "extra_arm":
        (first / "unplanned.json").write_bytes((first / "baseline.json").read_bytes())
        with pytest.raises(ValueError, match="Unplanned"):
            plan.captures(first)
    else:
        document = json.loads((first / "comparison-plan.json").read_bytes())
        document["arms"]["baseline"].append("two")
        (first / "comparison-plan.json").write_text(json.dumps(document))
        with pytest.raises(ValueError, match="plan differs"):
            plan.captures(first)


def test_failed_verification_retains_evidence_and_requires_recovery_before_continuing(
    tmp_path: Path,
) -> None:
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [{"case_id": "one"}]}))
    plan = ComparisonPlan(references, {"baseline": ("one",)})
    directory = tmp_path / "failed"

    def unavailable(row: object) -> dict[str, object]:
        raise TimeoutError("External trace readback is unavailable.")

    with pytest.raises(TimeoutError):
        with plan.record(directory):
            with EvaluationRun(directory / "baseline.json", references, ("one",)) as run:
                run.capture(
                    "one", lambda: {"response": {"answer": "Retained."}}, verify=unavailable
                )

    progress = json.loads((directory / "comparison-progress.json").read_bytes())
    assert progress["state"] == "incomplete"
    assert progress["observations"][0]["state"] == "failed"
    captured = json.loads((directory / "baseline.json").read_bytes())
    assert captured["cases"][0]["response"] == {"answer": "Retained."}
    with pytest.raises(ValueError, match="Recover"):
        plan.pending(tmp_path / "continuation", directory)
    with pytest.raises(ValueError, match="incomplete"):
        plan.captures(directory)


@pytest.mark.parametrize("change", ["rewrite", "append", "empty_prior"])
def test_continuation_rejects_later_changes_to_its_frozen_prior_inputs(
    tmp_path: Path, change: str
) -> None:
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [{"case_id": "one"}]}))
    plan = ComparisonPlan(references, {"baseline": ("one",), "candidate": ("one",)})
    first, second = tmp_path / "first", tmp_path / "second"
    with plan.record(first):
        if change != "empty_prior":
            with EvaluationRun(first / "baseline.json", references, ("one",)) as run:
                run.capture("one", lambda: {"response": {"answer": "Original."}})
    with plan.record(second, prior=(first,)):
        pass
    if change == "rewrite":
        original = first / "baseline.json"
        original.write_bytes(original.read_bytes() + b"\n")
    else:
        with EvaluationRun(first / "candidate.json", references, ("one",)) as run:
            run.capture("one", lambda: {"response": {"answer": "Added after freezing."}})
    with pytest.raises(ValueError, match="Prior comparison"):
        plan.captures(second)


def test_budget_stop_between_requests_keeps_verified_work_available_to_continuation(
    tmp_path: Path,
) -> None:
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [{"case_id": "one"}, {"case_id": "two"}]}))
    plan = ComparisonPlan(references, {"baseline": ("one", "two")})
    first, second = tmp_path / "first", tmp_path / "second"
    response = {"answer": "Previously served and verified."}
    with pytest.raises(ValueError, match="budget"):
        with plan.record(first):
            with EvaluationRun(first / "baseline.json", references, ("one", "two")) as run:
                run.capture(
                    "one",
                    lambda: {"response": response},
                    verify=lambda row: {"cli_response": response, "trace_response": response},
                )
                raise ValueError("The budget cannot admit the next request.")
    assert plan.pending(second, first) == {"baseline": ("two",)}
    original = (first / "baseline.json").read_bytes()
    with plan.record(second, prior=(first,)):
        with EvaluationRun(second / "baseline.json", references, ("two",)) as run:
            run.capture("two", lambda: {"response": {"answer": "Newly served."}})
    assert plan.inspect(second)["state"] == "complete"
    assert plan.captures(second)["baseline"].cases["one"]["response"] == response
    assert json.loads(original)["state"] == "failed"
    assert (first / "baseline.json").read_bytes() == original
    with pytest.raises(ValueError, match="complete"):
        CapturedAnswers(first / "baseline.json", references)


@pytest.mark.parametrize("stage", ["between_arms", "before_request", "between_requests"])
def test_continuation_cannot_overlap_an_active_capture_phase(tmp_path: Path, stage: str) -> None:
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [{"case_id": "one"}, {"case_id": "two"}]}))
    plan = ComparisonPlan(references, {"baseline": ("one", "two")})
    first, second = tmp_path / "first", tmp_path / "second"
    with pytest.raises(TimeoutError), plan.record(first), ExitStack() as stack:
        if stage != "between_arms":
            run = stack.enter_context(
                EvaluationRun(first / "baseline.json", references, ("one", "two"))
            )
            if stage == "between_requests":
                response = {"answer": "Verified, but the phase is still active."}
                run.capture(
                    "one",
                    lambda: {"response": response},
                    verify=lambda row: {
                        "cli_response": response,
                        "trace_response": response,
                    },
                )
        with pytest.raises(ValueError, match="Recover"):
            plan.pending(second, first)
        with pytest.raises(ValueError, match="Recover"):
            with plan.record(second, prior=(first,)):
                pytest.fail("A continuation started while its prior phase was active.")
        with pytest.raises(ValueError, match="Recover"):
            plan.pending(tmp_path / "third", second)
        raise TimeoutError("Stop the original phase without another request.")
