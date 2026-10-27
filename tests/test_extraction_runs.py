"""Retained Claim extraction outcomes with real local storage and controlled HTTP."""

import hashlib
import json
import subprocess
import sys
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from mlflow import MlflowClient

from ask_phil.openrouter import Budget, OpenRouterProfile


@pytest.fixture
def extraction_profile() -> OpenRouterProfile:
    return OpenRouterProfile(
        answer_model="test/model",
        canonical_slug="test/model-v1",
        provider="test-provider",
        input_price_per_million=Decimal("0.15"),
        output_price_per_million=Decimal("0.47"),
        output_tokens=4096,
        reasoning_effort="low",
    )


@pytest.fixture
def extraction_tracking(tmp_path: Path) -> MlflowClient:
    tracking = MlflowClient(tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}")
    tracking.create_experiment(
        "ask-phil-offline_evaluation", artifact_location=(tmp_path / "traces").as_uri()
    )
    return tracking


def extraction_transport(
    raw: str, *, fail: bool = False, interrupt: bool = False, finish_reason: str = "stop"
) -> httpx.MockTransport:
    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200, json={"data": {"limit": 5, "limit_reset": None, "limit_remaining": 5}}
            )
        if request.url.path.endswith("/endpoints"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "endpoints": [
                            {
                                "tag": "test-provider",
                                "name": "Test | test/model-v1",
                                "supported_parameters": [
                                    "structured_outputs",
                                    "response_format",
                                    "reasoning",
                                    "max_tokens",
                                ],
                            }
                        ]
                    }
                },
            )
        if interrupt:
            raise KeyboardInterrupt
        if fail:
            return httpx.Response(503, text="synthetic-provider-key")
        return httpx.Response(
            200,
            json={
                "id": "test-extraction",
                "model": "test/model-v1",
                "provider": "Test",
                "choices": [{"finish_reason": finish_reason, "message": {"content": raw}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.00001},
            },
        )

    return httpx.MockTransport(provider)


def test_trace_readback_failure_preserves_claims_raw_output_and_accounting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extraction_profile: OpenRouterProfile,
    extraction_tracking: MlflowClient,
) -> None:
    from ask_phil.claim_extraction import ClaimExtractionRun

    reference = Path("data/references/relationships-v2.json")
    raw = json.dumps({"claims": json.loads(reference.read_bytes())["expected_claims"]})

    def unavailable_trace(*args: object, **kwargs: object) -> None:
        raise OSError("synthetic-provider-key must not appear in retained failure details")

    monkeypatch.setattr(extraction_tracking, "get_trace", unavailable_trace)
    output = tmp_path / "extraction.json"
    with httpx.Client(transport=extraction_transport(raw)) as client:
        result = ClaimExtractionRun(
            extraction_profile,
            "synthetic-provider-key",
            client,
            budget=Budget(tmp_path / "budget.sqlite"),
            tracking=extraction_tracking,
        ).run(Path("data/seed/relationship-pilot-v1.json"), reference, output, relationships=True)

    saved = json.loads(output.read_bytes())
    assert saved == result
    assert saved["raw"] == raw
    assert saved["batch"] is not None and saved["score"]["f1"] == 1
    assert saved["usage"]["cost_usd"] == 0.00001
    assert saved["shared_ledger_usd"] == 0.00001 and saved["unsettled_reservations"] == 0
    assert saved["failure"] == "tracking_failed" and saved["tracking_failure_type"] == "OSError"
    assert saved["state"] == "failed" and saved["execution"]["model_calls"] == 1
    assert "synthetic-provider-key" not in output.read_text()


def test_a_new_run_does_not_reuse_a_previous_runs_charge_when_tracking_setup_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extraction_profile: OpenRouterProfile,
    extraction_tracking: MlflowClient,
) -> None:
    from ask_phil.claim_extraction import ClaimExtractionRun

    snapshot = Path("data/seed/family-pilot-v1.json")
    reference = Path("data/references/parentage-v1.json")
    raw = json.dumps({"claims": json.loads(reference.read_bytes())["expected_claims"]})

    def unavailable_experiment(*args: object, **kwargs: object) -> None:
        raise OSError("Tracking is unavailable before model execution.")

    with httpx.Client(transport=extraction_transport(raw)) as client:
        runner = ClaimExtractionRun(
            extraction_profile,
            "synthetic-provider-key",
            client,
            budget=Budget(tmp_path / "budget.sqlite"),
            tracking=extraction_tracking,
        )
        first = runner.run(snapshot, reference, tmp_path / "first.json")
        assert first["failure"] is None and first["usage"]["cost_usd"] == 0.00001
        monkeypatch.setattr(extraction_tracking, "get_experiment_by_name", unavailable_experiment)
        second = runner.run(snapshot, reference, tmp_path / "second.json")

    assert second["failure"] == "tracking_failed"
    assert second["usage"] is None and second["raw"] is None
    assert second["execution"]["model_calls"] == 0
    assert second["shared_ledger_usd"] == 0.00001


@pytest.mark.parametrize(
    "relationships,events,snapshot_name,reference_name",
    [
        (False, False, "family-pilot-v1.json", "parentage-v1.json"),
        (True, False, "relationship-pilot-v1.json", "relationships-v2.json"),
        (False, True, "crime-pilot-v1.json", "crime-justice-v1.json"),
    ],
)
def test_retained_extraction_matches_its_actual_trace_and_cannot_be_overwritten(
    tmp_path: Path,
    extraction_profile: OpenRouterProfile,
    extraction_tracking: MlflowClient,
    record_property: Callable[[str, object], None],
    relationships: bool,
    events: bool,
    snapshot_name: str,
    reference_name: str,
) -> None:
    from ask_phil.claim_extraction import ClaimExtractionRun

    snapshot = Path("data/seed") / snapshot_name
    reference = Path("data/references") / reference_name
    raw = json.dumps({"claims": json.loads(reference.read_bytes())["expected_claims"]})
    budget = Budget(tmp_path / "budget.sqlite")
    output = tmp_path / "extraction.json"
    with httpx.Client(transport=extraction_transport(raw)) as client:
        runner = ClaimExtractionRun(
            extraction_profile,
            "synthetic-provider-key",
            client,
            budget=budget,
            tracking=extraction_tracking,
        )
        result = runner.run(snapshot, reference, output, relationships=relationships, events=events)
        original = output.read_bytes()
        with pytest.raises(FileExistsError):
            runner.run(snapshot, reference, output, relationships=relationships, events=events)

    assert output.read_bytes() == original
    assert result["state"] == "complete" and result["failure"] is None
    assert result["score"]["f1"] == 1 and budget.summary() == (0.00001, 0)
    trace = extraction_tracking.get_trace(result["trace_id"], flush=True)
    root = next(span for span in trace.data.spans if span.parent_id is None)
    assert root.outputs == json.loads(original)
    assert (
        root.inputs["passages"][0]["text"]
        == json.loads(snapshot.read_bytes())["passages"][0]["text"]
    )
    record_property("trace_id", result["trace_id"])
    record_property("span_count", len(trace.data.spans))


@pytest.mark.parametrize("failure_mode", ["malformed", "provider", "truncated"])
def test_failed_extraction_preserves_observed_usage_and_uncertain_reservations(
    tmp_path: Path,
    extraction_profile: OpenRouterProfile,
    extraction_tracking: MlflowClient,
    failure_mode: str,
) -> None:
    from ask_phil.claim_extraction import ClaimExtractionRun

    output = tmp_path / "failed.json"
    with httpx.Client(
        transport=extraction_transport(
            "not JSON synthetic-provider-key",
            fail=failure_mode == "provider",
            finish_reason="length" if failure_mode == "truncated" else "stop",
        )
    ) as client:
        result = ClaimExtractionRun(
            extraction_profile,
            "synthetic-provider-key",
            client,
            budget=Budget(tmp_path / "budget.sqlite"),
            tracking=extraction_tracking,
        ).run(
            Path("data/seed/relationship-pilot-v1.json"),
            Path("data/references/relationships-v2.json"),
            output,
            relationships=True,
        )

    assert json.loads(output.read_bytes()) == result
    assert result["state"] == "failed" and result["failure"] == "extraction_failed"
    assert result["batch"] is None and result["score"]["schema_valid"] is False
    assert result["execution"]["model_calls"] == 1
    assert "synthetic-provider-key" not in output.read_text()
    if failure_mode in {"malformed", "truncated"}:
        assert result["raw"] == "not JSON [REDACTED]" and result["usage"]["cost_usd"] == 0.00001
        assert result["unsettled_reservations"] == 0
    else:
        assert result["raw"] is None and result["usage"]["cost_usd"] is None
        assert result["shared_ledger_usd"] > 0 and result["unsettled_reservations"] == 1


def test_interruption_retains_an_unsettled_attempt_before_propagating(
    tmp_path: Path,
    extraction_profile: OpenRouterProfile,
    extraction_tracking: MlflowClient,
) -> None:
    from ask_phil.claim_extraction import ClaimExtractionRun

    output = tmp_path / "interrupted.json"
    with httpx.Client(transport=extraction_transport("", interrupt=True)) as client:
        with pytest.raises(KeyboardInterrupt):
            ClaimExtractionRun(
                extraction_profile,
                "synthetic-provider-key",
                client,
                budget=Budget(tmp_path / "budget.sqlite"),
                tracking=extraction_tracking,
            ).run(
                Path("data/seed/relationship-pilot-v1.json"),
                Path("data/references/relationships-v2.json"),
                output,
                relationships=True,
            )

    result = json.loads(output.read_bytes())
    assert result["state"] == "failed" and result["execution"]["model_calls"] == 1
    assert result["usage"]["cost_usd"] is None and result["unsettled_reservations"] == 1


def test_extraction_hashes_the_reference_bytes_it_actually_used(
    tmp_path: Path,
    extraction_profile: OpenRouterProfile,
    extraction_tracking: MlflowClient,
) -> None:
    from ask_phil.claim_extraction import ClaimExtractionRun

    original = Path("data/references/parentage-v1.json").read_bytes()
    reference = tmp_path / "references.json"
    reference.write_bytes(original)
    raw = json.dumps({"claims": json.loads(original)["expected_claims"]})
    transport = extraction_transport(raw)

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/completions"):
            reference.write_text('{"changed": true}')
        return transport.handle_request(request)

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        result = ClaimExtractionRun(
            extraction_profile,
            "synthetic-provider-key",
            client,
            budget=Budget(tmp_path / "budget.sqlite"),
            tracking=extraction_tracking,
        ).run(Path("data/seed/family-pilot-v1.json"), reference, tmp_path / "extraction.json")

    assert result["failure"] is None and result["score"]["f1"] == 1
    assert reference.read_bytes() != original
    assert result["reference_sha256"] == hashlib.sha256(original).hexdigest()


@pytest.mark.parametrize("setup", ["configured", "missing_key", "missing_profile"])
def test_extraction_command_preserves_reference_mismatch_usage_error(
    tmp_path: Path, setup: str
) -> None:
    root = Path(__file__).resolve().parents[1]
    reference = json.loads((root / "data/references/parentage-v1.json").read_bytes())
    reference["snapshot_sha256"] = "f" * 64
    reference_path = tmp_path / "mismatched.json"
    reference_path.write_text(json.dumps(reference))
    key_path = tmp_path / ".secrets/openrouter.key"
    if setup != "missing_key":
        key_path.parent.mkdir(mode=0o700)
        key_path.write_text("synthetic-provider-key")
        key_path.chmod(0o600)
    profile_path = (
        tmp_path / "missing-profile.json"
        if setup == "missing_profile"
        else root / "config/evaluation-sol-low.json"
    )
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/evaluate_parentage.py"),
            "--snapshot",
            str(root / "data/seed/family-pilot-v1.json"),
            "--reference",
            str(reference_path),
            "--profile",
            str(profile_path),
            "--output",
            str(tmp_path / "output.json"),
            "--tracking-uri",
            f"sqlite:///{tmp_path / 'tracking.db'}",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 2
    assert "The frozen reference and source snapshot differ." in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "output.json").exists()
