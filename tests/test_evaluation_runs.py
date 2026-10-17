"""Recorded evaluations are exercised through their public capture/review interface."""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


def capture_files(tmp_path: Path, kind: str = "policy") -> tuple[Path, Path, Path]:
    reference: dict[str, Any] = {
        "case_id": "arrival",
        "required_facts": ["Phil arrives in February 1990."],
    }
    reference_hash = "e4639f6fdccfa2ecfdceacafa558527724968d1c2b05ae1a4c0f93671264e51b"
    if kind == "corpus":
        reference["required_facts"] = [
            {"fact": "Phil arrives in February 1990.", "sufficient_sets": [["evidence-1"]]}
        ]
        reference_hash = "d102de6d82c7dad13edf14f2e501689d9ae24605ebd01171bf356be5cce7a7a0"
    elif kind == "conversation":
        reference = {
            "case_id": "arrival",
            "operation": "ask",
            "expected_facts": ["Phil arrives in February 1990."],
        }
        reference_hash = "17a439e17c327ddebd5548cee13356aae997c122de48cebc941b9c1a0fc283cb"
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"steps" if kind == "conversation" else "cases": [reference]}))
    capture = tmp_path / "capture.json"
    capture.write_text(
        json.dumps(
            {
                "state": "complete",
                "reference_file_sha256": hashlib.sha256(references.read_bytes()).hexdigest(),
                "cases": [
                    {
                        **(
                            {"reference": reference} if kind == "policy" else {"case_id": "arrival"}
                        ),
                        "response": {"answer": "Right, listen. I arrived in February 1990."},
                    }
                ],
            }
        )
    )
    reviews = tmp_path / "reviews.json"
    review: dict[str, Any] = {
        "case_id": "arrival",
        "response_sha256": "e4234e07acf262353e9851e8ae5fc825b2e7cae065cc33c87e90e39a64243dad",
        "reference_sha256": reference_hash,
        "reviewer": "Synthetic software fixture",
        "rationale": "Independently specified arrival fact and retained answer.",
        "claims": [],
        "required_facts": [{"fact": "Phil arrives in February 1990.", "covered": True}],
        "answerability": True,
    }
    reviews.write_text(json.dumps({"reviews": [review]}))
    return capture, reviews, references


@pytest.mark.parametrize("kind", ["policy", "corpus", "conversation"])
def test_review_rejects_duplicate_captured_cases_before_publishing(
    tmp_path: Path, kind: str
) -> None:
    from ask_phil.evaluation import review_capture

    capture, reviews, references = capture_files(tmp_path, kind)
    document = json.loads(capture.read_text())
    document["cases"] *= 2
    capture.write_text(json.dumps(document))
    output = tmp_path / "scores.json"
    with pytest.raises(ValueError, match="Duplicate captured case"):
        review_capture(capture, reviews, references, output)
    assert not output.exists()


@pytest.mark.parametrize("kind", ["policy", "corpus", "conversation"])
def test_review_scores_retained_capture_formats_without_manufacturing_claim_scores(
    tmp_path: Path, kind: str
) -> None:
    from ask_phil.evaluation import review_capture

    capture, reviews, references = capture_files(tmp_path, kind)
    output = tmp_path / "scores.json"
    review_capture(capture, reviews, references, output)
    result = json.loads(output.read_text())
    assert result["cases"][0]["scores"]["completeness"] == {
        "passed": 1,
        "assessed": 1,
        "unassessed": 0,
        "value": 1.0,
    }
    assert result["cases"][0]["scores"]["correctness"]["value"] is None


@pytest.mark.parametrize(
    ("problem", "message"),
    [
        ("incomplete", "complete"),
        ("missing_review", "exactly once"),
        ("duplicate_review", "exactly once"),
        ("stale_references", "frozen references"),
        ("changed_response", "Stale review"),
        ("missing_response", "response"),
        ("unknown_case", "Unknown captured case"),
        ("missing_declared_case", "declared cases"),
    ],
)
def test_review_refuses_incomplete_or_mismatched_evidence(
    tmp_path: Path, problem: str, message: str
) -> None:
    from ask_phil.evaluation import review_capture

    capture, reviews, references = capture_files(tmp_path)
    document = json.loads(capture.read_text())
    annotations = json.loads(reviews.read_text())
    if problem == "incomplete":
        document["state"] = "failed"
    elif problem == "missing_review":
        annotations["reviews"] = []
    elif problem == "duplicate_review":
        annotations["reviews"] *= 2
    elif problem == "stale_references":
        references.write_text(references.read_text() + "\n")
    elif problem == "changed_response":
        document["cases"][0]["response"]["answer"] = "I arrived in 2001."
    elif problem == "missing_response":
        del document["cases"][0]["response"]
    elif problem == "unknown_case":
        document["cases"][0]["reference"]["case_id"] = "unknown"
    else:
        document["case_ids"] = ["arrival", "not-recorded"]
    capture.write_text(json.dumps(document))
    reviews.write_text(json.dumps(annotations))
    output = tmp_path / "scores.json"
    with pytest.raises(ValueError, match=message):
        review_capture(capture, reviews, references, output)
    assert not output.exists()


@pytest.mark.parametrize("failure", [TimeoutError, KeyboardInterrupt])
def test_interrupted_capture_retains_the_attempt_before_external_execution(
    tmp_path: Path, failure: type[BaseException]
) -> None:
    from ask_phil.evaluation import EvaluationRun

    _, _, references = capture_files(tmp_path)
    output = tmp_path / "new-capture.json"

    def interrupted() -> dict[str, Any]:
        attempted = json.loads(output.read_text())
        assert attempted["state"] == "running"
        assert attempted["cases"][0]["case_id"] == "arrival"
        assert attempted["cases"][0]["state"] == "attempting"
        raise failure("private upstream details must not enter the journal")

    with pytest.raises(failure):
        with EvaluationRun(output, references, ("arrival",)) as run:
            run.capture("arrival", interrupted)
    failed = json.loads(output.read_text())
    assert failed["state"] == "failed"
    assert failed["cases"][0]["state"] == "failed"
    assert failed["failure_type"] == failure.__name__
    assert "private upstream" not in output.read_text()


def test_completed_capture_preserves_frozen_evidence_and_can_be_reviewed(tmp_path: Path) -> None:
    from ask_phil.evaluation import EvaluationRun, review_capture

    _, reviews, references = capture_files(tmp_path)
    output = tmp_path / "new-capture.json"
    with EvaluationRun(output, references, ("arrival",), metadata={"cost_usd": "0"}) as run:
        run.capture(
            "arrival",
            lambda: {"response": {"answer": "Right, listen. I arrived in February 1990."}},
        )
    captured = json.loads(output.read_text())
    assert captured["state"] == "complete"
    assert captured["case_ids"] == ["arrival"]
    assert captured["cases"][0]["response_sha256"] == (
        "e4234e07acf262353e9851e8ae5fc825b2e7cae065cc33c87e90e39a64243dad"
    )
    review_capture(output, reviews, references, tmp_path / "scores.json")
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        with EvaluationRun(output, references, ("arrival",)):
            pytest.fail("An existing capture was overwritten.")
    assert output.read_bytes() == original


@pytest.mark.parametrize("problem", ["missing", "duplicate", "caught_failure"])
def test_run_cannot_complete_with_missing_duplicate_or_failed_cases(
    tmp_path: Path, problem: str
) -> None:
    from ask_phil.evaluation import EvaluationRun

    _, _, references = capture_files(tmp_path)
    output = tmp_path / "new-capture.json"

    def failed() -> dict[str, Any]:
        raise TimeoutError

    with pytest.raises(ValueError):
        with EvaluationRun(output, references, ("arrival",)) as run:
            if problem == "duplicate":
                run.capture("arrival", lambda: {"response": {"answer": "Captured."}})
                run.capture("arrival", lambda: {"response": {"answer": "Duplicate."}})
            elif problem == "caught_failure":
                with pytest.raises(TimeoutError):
                    run.capture("arrival", failed)
    assert json.loads(output.read_text())["state"] == "failed"


@pytest.mark.parametrize("unavailable", [False, True])
def test_tracking_completion_agrees_with_the_saved_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unavailable: bool
) -> None:
    from mlflow import MlflowClient

    from ask_phil.evaluation import EvaluationRun, EvaluationTracking

    monkeypatch.chdir(tmp_path)
    _, _, references = capture_files(tmp_path)
    client = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
    tracking = EvaluationTracking(client, "captured-answer-tests", {"kind": "software-test"})
    output = tmp_path / "new-capture.json"

    def reject_artifact(*args: Any, **kwargs: Any) -> None:
        raise ConnectionError("private tracking details")

    if unavailable:
        monkeypatch.setattr(client, "log_artifact", reject_artifact)

    def record() -> None:
        with EvaluationRun(output, references, ("arrival",), tracking=tracking) as run:
            run.capture("arrival", lambda: {"response": {"answer": "Captured."}})
            run.annotate(cost_usd="0.125", model_calls=1)

    if unavailable:
        with pytest.raises(ConnectionError):
            record()
    else:
        record()
    saved = json.loads(output.read_text())
    actual = client.get_run(saved["run_id"])
    assert saved["state"] == ("failed" if unavailable else "complete")
    assert actual.info.status == ("FAILED" if unavailable else "FINISHED")
    if not unavailable:
        assert actual.data.params["cost_usd"] == "0.125"
        assert (
            json.loads(
                Path(
                    client.download_artifacts(saved["run_id"], saved["result_artifact"])
                ).read_text()
            )
            == saved
        )
    assert "private tracking" not in output.read_text()


@pytest.mark.parametrize("change", ["state", "reference_sha256", "response_sha256", "reference"])
def test_review_checks_the_capture_journal_identity(tmp_path: Path, change: str) -> None:
    from ask_phil.evaluation import review_capture

    capture, reviews, references = capture_files(tmp_path)
    document = json.loads(capture.read_text())
    row = document["cases"][0]
    if change == "state":
        row["state"] = "attempting"
    elif change == "reference":
        row["reference"]["required_facts"] = ["An unsupported replacement fact."]
    else:
        row[change] = "a" * 64
    capture.write_text(json.dumps(document))
    output = tmp_path / "scores.json"
    with pytest.raises(ValueError):
        review_capture(capture, reviews, references, output)
    assert not output.exists()


@pytest.mark.parametrize("change", ["annotation", "execution"])
def test_case_execution_cannot_replace_run_or_reference_identity(
    tmp_path: Path, change: str
) -> None:
    from ask_phil.evaluation import EvaluationRun

    _, _, references = capture_files(tmp_path)
    output = tmp_path / "new-capture.json"
    with pytest.raises(ValueError):
        with EvaluationRun(output, references, ("arrival",)) as run:
            if change == "annotation":
                run.annotate(case_ids=[], cases=[], state="complete")
            else:
                run.capture("arrival", lambda: {"case_id": "replaced", "state": "complete"})
    assert json.loads(output.read_text())["state"] == "failed"


@pytest.mark.parametrize("selection", [(), ("arrival", "arrival"), ("unknown",)])
def test_capture_selection_must_identify_unique_frozen_cases(
    tmp_path: Path, selection: tuple[str, ...]
) -> None:
    from ask_phil.evaluation import EvaluationRun

    _, _, references = capture_files(tmp_path)
    output = tmp_path / "new-capture.json"
    with pytest.raises(ValueError):
        with EvaluationRun(output, references, selection):
            pass
    assert not output.exists()


@pytest.mark.parametrize(
    "script", ["evaluate_answer_policy.py", "evaluate_text_corpus.py", "evaluate_conversation.py"]
)
def test_score_commands_publish_reviewed_results_without_model_configuration(
    tmp_path: Path, script: str
) -> None:
    from mlflow import MlflowClient

    capture, reviews, references = capture_files(tmp_path)
    output = tmp_path / "scores.json"
    tracking_uri = f"sqlite:///{tmp_path}/mlflow.db"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/" + script,
            "score",
            "--capture",
            str(capture),
            "--reviews",
            str(reviews),
            "--references",
            str(references),
            "--output",
            str(output),
        ],
        env={
            **os.environ,
            "MLFLOW_TRACKING_URI": tracking_uri,
            "ASK_PHIL_MODELS": str(tmp_path / "absent-model-settings.json"),
        },
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    saved = json.loads(output.read_text())
    assert saved["model_calls"] == saved["answer_model_calls_in_review"] == 0
    tracked = MlflowClient(tracking_uri=tracking_uri).get_run(saved["run_id"])
    assert tracked.info.status == "FINISHED"
    assert tracked.data.metrics["arrival.completeness.value"] == 1.0


def test_tracking_publication_cannot_expose_a_completed_local_capture_early(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mlflow import MlflowClient

    from ask_phil.evaluation import EvaluationRun, EvaluationTracking

    monkeypatch.chdir(tmp_path)
    _, _, references = capture_files(tmp_path)
    client = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
    output = tmp_path / "new-capture.json"

    def interrupted_upload(*args: Any, **kwargs: Any) -> None:
        assert json.loads(output.read_text())["state"] == "finalizing"
        raise KeyboardInterrupt

    monkeypatch.setattr(client, "log_artifact", interrupted_upload)
    with pytest.raises(KeyboardInterrupt):
        with EvaluationRun(
            output,
            references,
            ("arrival",),
            tracking=EvaluationTracking(client, "interrupted-publication", {}),
        ) as run:
            run.capture("arrival", lambda: {"response": {"answer": "Captured."}})
    assert json.loads(output.read_text())["state"] == "failed"


def test_tracking_retains_distinct_inputs_and_result_with_identical_filenames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mlflow import MlflowClient

    from ask_phil.evaluation import EvaluationTracking, review_capture

    monkeypatch.chdir(tmp_path)
    capture, reviews, references = capture_files(tmp_path)
    colliding = []
    for role, source in [("capture", capture), ("reviews", reviews), ("references", references)]:
        directory = tmp_path / role
        directory.mkdir()
        copied = directory / "data.json"
        copied.write_bytes(source.read_bytes())
        colliding.append(copied)
    client = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
    output = tmp_path / "output" / "data.json"
    result = review_capture(
        colliding[0],
        colliding[1],
        colliding[2],
        output,
        tracking=EvaluationTracking(client, "colliding-inputs", {}),
    )
    downloaded = Path(client.download_artifacts(result["run_id"], ""))
    retained = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in downloaded.rglob("*")
        if path.is_file()
    }
    assert {
        hashlib.sha256(path.read_bytes()).hexdigest() for path in [*colliding, output]
    } <= retained


@pytest.mark.parametrize("phase", ["termination", "completion_upload"])
def test_downloaded_capture_is_not_reviewable_after_incomplete_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    from mlflow import MlflowClient

    from ask_phil.evaluation import EvaluationRun, EvaluationTracking, review_capture

    monkeypatch.chdir(tmp_path)
    _, reviews, references = capture_files(tmp_path)
    client = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
    output = tmp_path / "new-capture.json"
    terminate = client.set_terminated
    upload = client.log_artifact

    def fail_termination(run_id: str, status: str | None = None, **kwargs: Any) -> None:
        if status in {None, "FINISHED"}:
            raise ConnectionError("tracking termination unavailable")
        terminate(run_id, status=status, **kwargs)

    def fail_completion_upload(
        run_id: str, local_path: str, artifact_path: str | None = None
    ) -> None:
        if client.get_run(run_id).info.status == "FINISHED":
            raise ConnectionError("completion upload unavailable")
        upload(run_id, local_path, artifact_path=artifact_path)

    if phase == "termination":
        monkeypatch.setattr(client, "set_terminated", fail_termination)
    else:
        monkeypatch.setattr(client, "log_artifact", fail_completion_upload)
    with pytest.raises(ConnectionError):
        with EvaluationRun(
            output,
            references,
            ("arrival",),
            tracking=EvaluationTracking(client, "incomplete-publication", {}),
        ) as run:
            run.capture(
                "arrival",
                lambda: {"response": {"answer": "Right, listen. I arrived in February 1990."}},
            )
    saved = json.loads(output.read_text())
    retained = Path(client.download_artifacts(saved["run_id"], saved["result_artifact"]))
    assert json.loads(retained.read_text())["state"] != "complete"
    with pytest.raises(ValueError, match="complete"):
        review_capture(retained, reviews, references, tmp_path / "scores.json")


@pytest.mark.parametrize(
    ("response", "fingerprint"),
    [
        (None, "74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b"),
        ({}, "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"),
        ({"answer": ""}, "3bdf68cc1aec55545f98aa543b2f023f23ac6ec1293c4b67bc998cc1e33b3c60"),
        ({"answer": "   "}, "a54372398ebe0bb935ebfe4247b2cc68f318fc37c2c4f8997029c7621ffb9ddc"),
        ({"answer": 42}, "ecf59a2696ca44a417e20e2a7eabb1b26e82c779f8546bea354a2cc80e8e1eed"),
    ],
)
def test_hash_bound_annotations_cannot_replace_a_missing_served_answer(
    tmp_path: Path, response: object, fingerprint: str
) -> None:
    from ask_phil.evaluation import review_capture

    capture, reviews, references = capture_files(tmp_path)
    document = json.loads(capture.read_text())
    document["cases"][0]["response"] = response
    capture.write_text(json.dumps(document))
    annotations = json.loads(reviews.read_text())
    annotations["reviews"][0]["response_sha256"] = fingerprint
    reviews.write_text(json.dumps(annotations))
    output = tmp_path / "scores.json"
    with pytest.raises(ValueError, match="response"):
        review_capture(capture, reviews, references, output)
    assert not output.exists()


def test_later_edits_to_execution_values_do_not_rewrite_frozen_capture(tmp_path: Path) -> None:
    from ask_phil.evaluation import EvaluationRun, review_capture

    _, reviews, references = capture_files(tmp_path)
    output = tmp_path / "new-capture.json"
    payload = {"response": {"answer": "Right, listen. I arrived in February 1990."}}
    with EvaluationRun(output, references, ("arrival",)) as run:
        returned = run.capture("arrival", lambda: payload)
        payload["response"]["answer"] = "Changed provider object."
        returned["response"]["answer"] = "Changed returned value."
        returned["reference"]["required_facts"] = ["Changed expected fact."]
    reviewed = review_capture(output, reviews, references, tmp_path / "scores.json")
    assert reviewed["cases"][0]["scores"]["completeness"]["value"] == 1.0
