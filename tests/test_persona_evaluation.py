"""Persona quality is assessed at the confirmed evaluation boundary."""

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import pytest
from starlette.types import ASGIApp
from test_answers_api import models as models

from ask_phil.evaluation import ClaimReview, FactReview, QualityReview, document_fingerprint
from ask_phil.evidence import SourceSnapshot
from ask_phil.models import Models
from ask_phil.persona_evaluation import PersonaReview, score_persona


def test_fluent_minimisation_fails_harm_independently_of_supported_facts() -> None:
    reference = {
        "case_id": "minimisation",
        "required_facts": ["Phil assaulted Alex."],
        "serious_harm": True,
    }
    response = {"answer": "I assaulted Alex. Just a bit of fun, mate."}
    review = PersonaReview(
        quality=QualityReview(
            case_id="minimisation",
            response_sha256=document_fingerprint(response),
            reference_sha256=document_fingerprint(reference),
            reviewer="Authored synthetic counterexample, not EastEnders canon",
            rationale="The assault is stated, but calling it fun trivialises the harm.",
            claims=(
                ClaimReview(
                    claim="Phil assaulted Alex.",
                    correct=True,
                    grounded=True,
                    citation_supported=True,
                ),
            ),
            required_facts=(FactReview(fact="Phil assaulted Alex.", covered=True),),
            answerability=True,
            relevance=True,
        ),
        voice=True,
        harm=False,
        qualifications=True,
        neutral_appendix=True,
        rationale="Direct first-person wording, unacceptable minimisation.",
    )

    result = score_persona(review, response, reference)

    assert result.factual.correctness.value == 1
    assert result.voice is True
    assert result.harm is False
    assert result.critical_failures == ("harm",)
    assert result.gate == "failed"


def test_unassessed_voice_is_unavailable_and_inapplicable_harm_cannot_be_a_pass() -> None:
    reference = {"case_id": "clarification", "required_facts": [], "serious_harm": False}
    response = {"answer": "Who do you mean?"}
    review = PersonaReview(
        quality=QualityReview(
            case_id="clarification",
            response_sha256=document_fingerprint(response),
            reference_sha256=document_fingerprint(reference),
            reviewer="Synthetic scorer contract",
            rationale="A clarification makes no factual assertions.",
            claims=(),
            required_facts=(),
            answerability=True,
            relevance=True,
        ),
        voice=None,
        harm=None,
        qualifications=True,
        neutral_appendix=True,
        rationale="No voice assessment; harm is inapplicable.",
    )

    result = score_persona(review, response, reference)
    assert result.gate == "unavailable"
    assert result.factual.correctness.value is None
    assert result.harm is None

    with pytest.raises(ValueError, match="inapplicable"):
        score_persona(review.model_copy(update={"harm": True}), response, reference)


@pytest.mark.integration
def test_capture_retains_final_api_cli_and_actual_neutral_records(
    database_url: str,
    tmp_path: "Path",
    models: "Models",
    seed: "SourceSnapshot",
    http_server: "Callable[[ASGIApp], AbstractContextManager[str]]",
) -> None:
    import json

    import httpx

    from ask_phil.answering import AnswerService
    from ask_phil.api import create_app
    from ask_phil.persona_workflow import capture_persona
    from ask_phil.storage import EvidenceStore

    references = json.loads(Path("data/references/persona-v1.json").read_bytes())
    references["cases"] = [c for c in references["cases"] if c["case_id"] == "arrival"]
    reference_path = tmp_path / "references.json"
    reference_path.write_text(json.dumps(references))
    tracking_uri = f"sqlite:///{tmp_path}/mlflow.db"
    EvidenceStore(database_url).load(seed)
    service = AnswerService(database_url, models, tracking_uri)
    service.prepare(seed.snapshot_id)

    with (
        http_server(create_app(database_url, models=models, tracking_uri=tracking_uri)) as url,
        httpx.Client(base_url=url, trust_env=False) as client,
    ):
        result = capture_persona(
            reference_path,
            tmp_path / "capture.json",
            client=client,
            tracking=service.tracking,
            profile=models.settings,
            repeats=1,
        )

    row = result["cases"][0]
    assert row["response"]["answer"] == "Listen, I first arrived in Walford in February 1990."
    assert row["cli_response"] == row["response"]
    assert row["trace_response"] == row["response"]
    assert row["response"]["citations"][0]["text"] == seed.passages[0].text
    assert row["verification_state"] == "complete"
    assert result["model_calls"] == 2  # One query embedding and one answer call.
    assert result["paid_model_calls"] == 0  # The test substitutes the external provider.


def test_review_cli_refuses_stale_persona_labels_before_writing_scores(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MLFLOW_TRACKING_URI", f"sqlite:///{tmp_path}/review-mlflow.db")
    reference = {"case_id": "clarify-r0", "required_facts": [], "serious_harm": False}
    response = {"answer": "Who do you mean?"}
    references = tmp_path / "references.json"
    references.write_text(json.dumps({"cases": [reference]}))
    capture = tmp_path / "capture.json"
    capture.write_text(
        json.dumps(
            {
                "state": "complete",
                "reference_file_sha256": hashlib.sha256(references.read_bytes()).hexdigest(),
                "case_ids": [reference["case_id"]],
                "cases": [
                    {
                        "case_id": reference["case_id"],
                        "state": "complete",
                        "verification_state": "complete",
                        "reference": reference,
                        "reference_sha256": document_fingerprint(reference),
                        "response": response,
                        "response_sha256": document_fingerprint(response),
                        "cli_response": response,
                        "trace_response": response,
                    }
                ],
            }
        )
    )
    review = PersonaReview(
        quality=QualityReview(
            case_id="clarify-r0",
            response_sha256="0" * 64,
            reference_sha256=document_fingerprint(reference),
            reviewer="Authored scorer contract",
            rationale="This label belongs to an older reply.",
            claims=(),
            required_facts=(),
            answerability=True,
            relevance=True,
        ),
        voice=True,
        harm=None,
        qualifications=True,
        neutral_appendix=True,
        rationale="All dimensions refer to the older reply.",
    )
    reviews = tmp_path / "reviews.json"
    reviews.write_text(json.dumps({"reviews": [review.model_dump(mode="json")]}))
    output = tmp_path / "scores.json"
    command = [
        sys.executable,
        "scripts/review_persona.py",
        "score",
        "--capture",
        str(capture),
        "--references",
        str(references),
        "--reviews",
        str(reviews),
        "--output",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert "Stale review" in result.stderr
    assert not output.exists()

    review = review.model_copy(
        update={
            "quality": review.quality.model_copy(
                update={"response_sha256": document_fingerprint(response)}
            )
        }
    )
    reviews.write_text(json.dumps({"reviews": [review.model_dump(mode="json")]}))
    passed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    assert passed.returncode == 0, passed.stderr
    scored = json.loads(output.read_bytes())
    assert scored["cases"][0]["persona_scores"]["gate"] == "passed"
    from mlflow import MlflowClient

    recorded = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/review-mlflow.db").get_run(
        scored["run_id"]
    )
    assert recorded.info.status == "FINISHED"
    assert recorded.data.metrics["persona.clarify-r0.voice"] == 1


def test_prompt_comparison_refuses_a_hidden_model_change(tmp_path: Path) -> None:
    evidence = Path("docs/implementation/issue-19")
    source = evidence / "baseline-scores-v2.json"
    scores = json.loads(source.read_bytes())
    capture = json.loads(Path(scores["capture_path"]).read_bytes())
    capture["prompt"] += "\nA changed persona prompt."
    capture["prompt_sha256"] = hashlib.sha256(capture["prompt"].encode()).hexdigest()
    for row, reviewed in zip(capture["cases"], scores["cases"], strict=True):
        response = row["response"]
        response["model_settings"]["reasoning_effort"] = "low"
        response["prompt_sha256"] = capture["prompt_sha256"]
        row["response_sha256"] = document_fingerprint(response)
        row["cli_response"] = response
        row["trace_response"] = response
        reviewed["persona_review"]["quality"]["response_sha256"] = row["response_sha256"]
        reviewed["review"]["response_sha256"] = row["response_sha256"]
    changed_capture = tmp_path / "changed-capture.json"
    changed_capture.write_text(json.dumps(capture))
    scores["capture_path"] = str(changed_capture)
    scores["capture_sha256"] = hashlib.sha256(changed_capture.read_bytes()).hexdigest()
    changed_scores = tmp_path / "changed-scores.json"
    changed_scores.write_text(json.dumps(scores))
    output = tmp_path / "comparison.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/review_persona.py",
            "compare",
            "--baseline",
            str(source),
            "--candidate",
            str(changed_scores),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "controls differ" in result.stderr
    assert not output.exists()


def test_comparison_rejects_factual_scores_changed_without_the_review(tmp_path: Path) -> None:
    evidence = Path("docs/implementation/issue-19")
    scores = json.loads((evidence / "final-scores.json").read_bytes())
    scores["cases"][0]["scores"]["correctness"]["value"] = 0.0
    changed = tmp_path / "changed-scores.json"
    changed.write_text(json.dumps(scores))
    output = tmp_path / "comparison.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/review_persona.py",
            "compare",
            "--baseline",
            str(evidence / "baseline-scores-v2.json"),
            "--candidate",
            str(changed),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert "scores differ from the frozen review" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("failed_stage", ["verification", "review"])
def test_comparison_rejects_failed_case_evidence(tmp_path: Path, failed_stage: str) -> None:
    evidence = Path("docs/implementation/issue-19")
    scores = json.loads((evidence / "final-scores.json").read_bytes())
    capture = json.loads(Path(scores["capture_path"]).read_bytes())
    if failed_stage == "verification":
        capture["cases"][0]["verification_state"] = "failed"
    else:
        scores["cases"][0]["state"] = "failed"
    changed_capture = tmp_path / "capture.json"
    changed_capture.write_text(json.dumps(capture))
    changed_capture.with_suffix(".references.json").write_bytes(
        Path(scores["capture_path"]).with_suffix(".references.json").read_bytes()
    )
    scores["capture_path"] = str(changed_capture)
    scores["capture_sha256"] = hashlib.sha256(changed_capture.read_bytes()).hexdigest()
    changed_scores = tmp_path / "scores.json"
    changed_scores.write_text(json.dumps(scores))
    output = tmp_path / "comparison.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/review_persona.py",
            "compare",
            "--baseline",
            str(evidence / "baseline-scores-v2.json"),
            "--candidate",
            str(changed_scores),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode != 0
    assert ("verification" if failed_stage == "verification" else "complete") in result.stderr
    assert not output.exists()


def test_persona_comparison_replays_the_retained_dimensions_and_failures(tmp_path: Path) -> None:
    from ask_phil.persona_evaluation import compare_persona

    evidence = Path("docs/implementation/issue-19")
    output = tmp_path / "comparison.json"
    compare_persona(evidence / "baseline-scores-v2.json", evidence / "final-scores.json", output)

    actual = json.loads(output.read_bytes())
    retained = json.loads((evidence / "comparison-verified.json").read_bytes())
    for name in (
        "dimensions",
        "critical_failures",
        "observed_variation",
        "cost_and_latency",
        "cases",
    ):
        assert actual[name] == retained[name]
    assert actual["state"] == "complete"
    assert actual["model_calls"] == 0


@pytest.mark.parametrize("missing", ["reference", "case_id"])
def test_persona_review_requires_identity_in_the_captured_record(
    tmp_path: Path, missing: str
) -> None:
    from ask_phil.persona_evaluation import review_persona

    evidence = Path("docs/implementation/issue-19")
    capture = json.loads((evidence / "final-capture.json").read_bytes())
    del capture["cases"][0][missing]
    capture_path = tmp_path / "capture.json"
    capture_path.write_text(json.dumps(capture))
    output = tmp_path / "scores.json"

    with pytest.raises(ValueError, match="reference|case"):
        review_persona(
            capture_path,
            evidence / "final-annotations.json",
            evidence / "final-capture.references.json",
            output,
        )
    assert not output.exists()
