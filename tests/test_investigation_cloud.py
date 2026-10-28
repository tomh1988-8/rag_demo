"""Complete investigator accounting with a controlled external cloud provider."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from ollama import Client
from test_investigation_api import decision, finish, publish

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.models import LocalEmbedding, Models, OpenRouterSettings
from ask_phil.openrouter import Budget, OpenRouterChat

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("missing_usage", [False, True])
def test_all_cloud_decisions_are_accounted_and_unknown_spend_keeps_the_reservation(
    database_url: str, seed: SourceSnapshot, tmp_path: Path, missing_usage: bool
) -> None:
    settings = OpenRouterSettings.model_validate_json(
        Path("config/openrouter-sol.json").read_bytes()
    )
    settings = settings.model_copy(update={"embedding_dimensions": 3})
    part = "When did Phil arrive?"
    outputs = iter([decision("text_search", {"query": part, "k": 1}, part), finish(part)])
    paid: list[dict[str, Any]] = []

    def provider(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"model": settings.embedding_model, "digest": settings.embedding_digest}
                    ]
                },
            )
        if path == "/api/embed":
            return httpx.Response(
                200, json={"embeddings": [[1.0, 0.0, 0.0]], "prompt_eval_count": 7}
            )
        if path.endswith("/key"):
            return httpx.Response(
                200, json={"data": {"limit": 5, "limit_reset": None, "limit_remaining": 5}}
            )
        if path.endswith("/endpoints"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "endpoints": [
                            {
                                "tag": settings.provider,
                                "name": "OpenAI | " + settings.canonical_slug,
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
        paid.append(body)
        assert "oneOf" not in json.dumps(body["response_format"])
        return httpx.Response(
            200,
            json={
                "id": "decision-" + str(len(paid)),
                "provider": "OpenAI",
                "model": settings.canonical_slug,
                "choices": [
                    {"finish_reason": "stop", "message": {"content": json.dumps(next(outputs))}}
                ],
                "usage": {}
                if missing_usage
                else {
                    "prompt_tokens": 20,
                    "completion_tokens": 50,
                    "cost": 0.005 if len(paid) == 1 else 0.007,
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
    publish(database_url, seed, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/cloud.db")
    ) as client:
        result = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        if missing_usage:
            assert len(paid) == 1
            assert answer["execution"]["stop_reason"] == "spend_limit"
            assert float(answer["execution"]["reserved_usd"]) > 0.12
            assert answer["estimated_api_cost_usd"] is None
            assert answer["usage"]["input_tokens"] is None
            assert answer["execution"]["model_calls"] == 2
        else:
            assert answer["status"] == "answered"
            assert len(paid) == 2
            assert answer["estimated_api_cost_usd"] == pytest.approx(0.012)
            assert float(answer["execution"]["reserved_usd"]) == pytest.approx(0.012)
            assert answer["usage"] == {
                "input_tokens": 40,
                "output_tokens": 100,
                "embedding_tokens": 7,
            }
            assert [
                c["provider_usage"]["cost_usd"] for c in answer["investigation"]["model_executions"]
            ] == [0.005, 0.007]
        assert "private-test-key" not in json.dumps(answer)
