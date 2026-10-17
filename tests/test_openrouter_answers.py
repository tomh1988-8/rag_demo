"""Real PostgreSQL and MLflow; replace only external model HTTP calls."""

import hashlib
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from ollama import Client

from ask_phil.answering import AnswerService
from ask_phil.answers import AskRequest
from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.models import LocalEmbedding, Models, OpenRouterSettings
from ask_phil.openrouter import Budget, OpenRouterChat
from ask_phil.storage import EvidenceStore


@pytest.mark.integration
@pytest.mark.parametrize(
    "failure", ["none", "http", "truncated", "invalid_json", "missing_usage", "empty_context"]
)
def test_cloud_answer_retains_usage_and_receipt_without_credentials(
    database_url: str,
    seed: SourceSnapshot,
    tmp_path: Path,
    failure: str,
) -> None:
    settings = OpenRouterSettings.model_validate_json(
        Path("config/openrouter-qwen.json").read_text()
    )
    settings = settings.model_copy(update={"embedding_dimensions": 3})
    inference_allowed = True

    def provider(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {
                            "model": settings.embedding_model,
                            "digest": settings.embedding_digest,
                        }
                    ]
                },
            )
        if path == "/api/embed":
            return httpx.Response(
                200, json={"embeddings": [[1.0, 0.0, 0.0]], "prompt_eval_count": 10}
            )
        assert inference_allowed, "Empty context must skip the answer provider."
        if path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 5,
                        "limit_reset": None,
                        "limit_remaining": 5,
                        "include_byok_in_limit": False,
                    }
                },
            )
        if path.endswith("/endpoints"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "endpoints": [
                            {
                                "tag": settings.provider,
                                "name": "Alibaba | " + settings.canonical_slug,
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
        assert path == "/api/v1/chat/completions"
        body = json.loads(request.content)
        assert "oneOf" not in json.dumps(body["response_format"])
        assert "anyOf" in json.dumps(body["response_format"])
        if failure == "http":
            return httpx.Response(503, json={"error": "private-test-key"})
        draft = {
            "answer": "Right, listen. I arrived in February 1990.",
            "status": "answered",
            "evidence_ids": ["phil-arrival-001"],
            "qualifications": [],
            "unanswered": [],
        }
        return httpx.Response(
            200,
            json={
                "id": "cloud-request",
                "provider": "Alibaba",
                "model": settings.canonical_slug,
                "choices": [
                    {
                        "finish_reason": "length" if failure == "truncated" else "stop",
                        "message": {
                            "content": (
                                "not JSON" if failure == "invalid_json" else json.dumps(draft)
                            )
                        },
                    }
                ],
                "usage": {}
                if failure == "missing_usage"
                else {
                    "prompt_tokens": 20,
                    "completion_tokens": 50,
                    "cost": 0.0001,
                    "completion_tokens_details": {"reasoning_tokens": 30},
                },
            },
        )

    transport = httpx.MockTransport(provider)
    models = Models(
        settings,
        LocalEmbedding(
            settings.embedding_model, Client(host="http://local.invalid", transport=transport)
        ),
        OpenRouterChat(
            settings,
            "private-test-key",
            Budget(tmp_path / "budget.sqlite"),
            httpx.Client(transport=transport),
        ),
    )
    service = AnswerService(database_url, models, f"sqlite:///{tmp_path}/mlflow.db")
    if failure == "empty_context":
        EvidenceStore(database_url).load(seed)
        service.prepare(seed.snapshot_id)
        previous = service.ask(
            AskRequest(snapshot_id=seed.snapshot_id, question="When did Phil arrive?")
        )
        assert previous.response.status == "answered"
        assert previous.response.provider_usage is not None
        inference_allowed = False
        text = "Retained captured context. " * 55
        passage = seed.passages[0].model_copy(
            update={
                "text": text,
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
                "end": len(text),
            }
        )
        seed = seed.model_copy(
            update={"snapshot_id": "cloud-empty-context", "passages": (passage,)}
        )
    EvidenceStore(database_url).load(seed)
    service.prepare(seed.snapshot_id)
    receipt = service.ask(
        AskRequest(snapshot_id=seed.snapshot_id, question="When did Phil arrive?")
    )
    response = receipt.response
    if failure == "empty_context":
        assert response.status == "insufficient_evidence"
        assert response.estimated_api_cost_usd == 0
        assert response.provider_usage is None
        assert response.usage.input_tokens == 0
        assert response.usage.output_tokens == 0
    else:
        assert response.status == ("answered" if failure in {"none", "missing_usage"} else "failed")
        unknown_usage = failure in {"http", "missing_usage"}
        assert response.estimated_api_cost_usd == (None if unknown_usage else 0.0001)
        assert response.provider_usage is not None
        assert response.provider_usage.reserved_usd > 0
        assert response.provider_usage.reasoning_tokens == (None if unknown_usage else 30)
        assert response.usage.input_tokens == (None if unknown_usage else 20)
        assert response.usage.output_tokens == (None if unknown_usage else 50)
    assert response.usage.embedding_tokens == 10
    assert service.ledger.get(response.response_id, receipt.read_token) == response
    trace = service.tracking.get_trace(response.trace_id, flush=True)
    assert "private-test-key" not in json.dumps(trace.to_dict())
    assert "private-test-key" not in receipt.model_dump_json()
    assert "Local Ollama API only" not in response.cost_scope
    if failure == "missing_usage":
        from ask_phil.quality_workflow import capture_quality

        reference = json.loads(Path("data/references/quality-comparison-v1.json").read_bytes())
        reference["cases"] = [reference["cases"][0]]
        reference["cases"][0].update(
            snapshot_id=seed.snapshot_id,
            required_facts=[
                {
                    "fact": "Phil arrives in February 1990.",
                    "sufficient_sets": [["phil-arrival-001"]],
                }
            ],
            evidence=[
                {
                    "evidence_id": "phil-arrival-001",
                    "text": seed.passages[0].text,
                    "source_revision": seed.source.revision_id,
                    "sha256": seed.passages[0].sha256,
                }
            ],
        )
        reference_path = tmp_path / "capture-references.json"
        reference_path.write_text(json.dumps(reference))
        output = tmp_path / "capture.json"
        with TestClient(
            create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
        ) as api:
            with pytest.raises(ValueError, match="Unknown serving cost"):
                capture_quality(
                    reference_path,
                    output,
                    api,
                    repeats=1,
                    namespace="unknown-cost-development",
                    private_directory=tmp_path / "private-capture",
                    max_cost_usd=1,
                    profile=settings,
                )
        failed = json.loads(output.read_bytes())
        assert failed["state"] == "failed"
        assert failed["cost_usd"] is None
        assert failed["known_cost_usd"] == "0"
        assert failed["failed_call_usage"]["cost_usd"] is None
        assert failed["failed_call_usage"]["reserved_usd"] > 0
