import json
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from mlflow import MlflowClient
from ollama import Client

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.models import Models, ModelSettings
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def tracking_uri(tmp_path_factory: pytest.TempPathFactory) -> str:
    path: Path = tmp_path_factory.mktemp("mlflow")
    return f"sqlite:///{path}/tracking.db"


@pytest.fixture
def models(request: pytest.FixtureRequest) -> Models:
    reported_usage = getattr(request, "param", {})

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"model": "test-answer", "digest": "a" * 64},
                        {"model": "test-embedding", "digest": "b" * 64},
                    ]
                },
            )
        body = json.loads(request.content)
        if request.url.path == "/api/embed":
            return httpx.Response(200, json={"embeddings": [[1.0, 0.0, 0.0]]})
        assert request.url.path == "/api/chat"
        assert body["stream"] is False
        assert body["options"]["num_predict"] == 256
        assert body["options"]["num_ctx"] == 4096
        return httpx.Response(
            200,
            json={
                "model": "test-answer",
                "done": True,
                **reported_usage,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "answer": "Listen, I first arrived in Walford in February 1990.",
                            "evidence_ids": ["phil-arrival-001"],
                            "status": "answered",
                        }
                    ),
                },
            },
        )

    transport = httpx.MockTransport(provider)
    settings = ModelSettings(
        answer_model="test-answer",
        answer_digest="a" * 64,
        embedding_model="test-embedding",
        embedding_digest="b" * 64,
        embedding_dimensions=3,
    )
    return Models(
        settings=settings,
        embedding=OllamaEmbedding(
            model_name="test-embedding",
            client_kwargs={"transport": transport},
        ),
        llm=Ollama(
            model="test-answer",
            context_window=4096,
            additional_kwargs={"num_predict": 256},
            client=Client(host="http://model.invalid", transport=transport),
        ),
    )


def test_answer_has_resolvable_citations_real_trace_and_durable_private_receipt(
    database_url: str, seed: SourceSnapshot, models: Models, tracking_uri: str
) -> None:
    EvidenceStore(database_url).load(seed)
    TextRetriever(database_url, models.embedding, models.settings.embedding_id, 3).prepare(
        seed.snapshot_id
    )
    app = create_app(database_url, models=models, tracking_uri=tracking_uri)
    with TestClient(app) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": seed.snapshot_id,
                "question": "When does Phil Mitchell first arrive in Walford?",
            },
        )
        assert response.status_code == 200, response.text
        receipt = response.json()
        answer = receipt["response"]
        assert answer["status"] == "answered"
        assert "February 1990" in answer["answer"]
        assert answer["source"]["support_status"] == "source_supported"
        assert answer["route"] == "text_rag"
        assert answer["elapsed_ms"] > 0
        assert answer["usage"]["input_tokens"] is None
        citation = answer["citations"][0]
        assert client.get(citation["resolve_path"]).json()["matches"][0]["text"] == citation["text"]
    with TestClient(
        create_app(database_url, models=models, tracking_uri=tracking_uri)
    ) as restarted:
        path = f"/v1/responses/{answer['response_id']}"
        assert restarted.get(path).status_code == 404
        original = restarted.get(path, headers={"Authorization": f"Bearer {receipt['read_token']}"})
        assert original.status_code == 200
        assert original.json() == answer
    trace = MlflowClient(tracking_uri=tracking_uri).get_trace(answer["trace_id"], flush=True)
    assert trace.info.trace_id == answer["trace_id"]
    assert {span.name for span in trace.data.spans} >= {
        "text_retrieval",
        "assembled_context",
        "answer_model",
    }
    assert receipt["read_token"] not in trace.to_json()


def test_invalid_model_citation_becomes_a_traced_failure_with_a_response_identifier(
    database_url: str, seed: SourceSnapshot, models: Models, tracking_uri: str
) -> None:
    def bad_provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"model": "test-answer", "digest": "a" * 64},
                        {"model": "test-embedding", "digest": "b" * 64},
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "model": "test-answer",
                "done": True,
                "prompt_eval_count": 123,
                "eval_count": 25,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "answer": "An unsupported claim.",
                            "evidence_ids": ["invented-001"],
                        }
                    ),
                },
            },
        )

    models = replace(
        models,
        llm=Ollama(
            model="test-answer",
            context_window=4096,
            client=Client(host="http://model.invalid", transport=httpx.MockTransport(bad_provider)),
        ),
    )
    EvidenceStore(database_url).load(seed)
    TextRetriever(database_url, models.embedding, models.settings.embedding_id, 3).prepare(
        seed.snapshot_id
    )
    with TestClient(create_app(database_url, models=models, tracking_uri=tracking_uri)) as client:
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": seed.snapshot_id,
                "question": "When did Phil arrive?",
            },
        )
        assert result.status_code == 200, result.text
        receipt = result.json()
        answer = receipt["response"]
        assert answer["status"] == "failed"
        assert "unsupported claim" not in answer["answer"].lower()
        assert answer["citations"] == []
        assert answer["usage"]["input_tokens"] == 123
        assert answer["usage"]["output_tokens"] == 25
        saved = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert saved.json() == answer
        trace = MlflowClient(tracking_uri=tracking_uri).get_trace(answer["trace_id"], flush=True)
        assert trace.info.state.value == "ERROR"


def test_cli_asks_and_resolves_the_original_response_over_http(
    database_url: str, seed: SourceSnapshot, models: Models, tracking_uri: str, tmp_path: Path
) -> None:
    EvidenceStore(database_url).load(seed)
    TextRetriever(database_url, models.embedding, models.settings.embedding_id, 3).prepare(
        seed.snapshot_id
    )
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(database_url, models=models, tracking_uri=tracking_uri),
                log_level="error",
            )
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            command = [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "--api-url",
                f"http://127.0.0.1:{listener.getsockname()[1]}",
            ]
            env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
            asked = subprocess.run(
                [*command, "ask", "When did Phil arrive?", "--snapshot", seed.snapshot_id],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            assert asked.returncode == 0, asked.stderr
            receipt_file = tmp_path / "receipt.json"
            receipt_file.write_text(asked.stdout)
            original = subprocess.run(
                [*command, "response", str(receipt_file)],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )
            assert original.returncode == 0, original.stderr
            assert json.loads(original.stdout) == json.loads(asked.stdout)["response"]
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_changed_model_digest_requires_an_explicit_configuration_and_baseline_update(
    database_url: str, seed: SourceSnapshot, models: Models, tracking_uri: str
) -> None:
    EvidenceStore(database_url).load(seed)
    TextRetriever(database_url, models.embedding, models.settings.embedding_id, 3).prepare(
        seed.snapshot_id
    )
    changed = replace(
        models, settings=models.settings.model_copy(update={"answer_digest": "c" * 64})
    )
    with TestClient(create_app(database_url, models=changed, tracking_uri=tracking_uri)) as client:
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": seed.snapshot_id,
                "question": "When did Phil arrive?",
            },
        )
        assert result.status_code == 503
        assert "model" in result.json()["detail"].lower()


@pytest.mark.parametrize(("snapshot_id", "status"), [("missing", 404), ("phil-arrival-v1", 503)])
def test_unknown_or_unindexed_snapshot_returns_an_explicit_api_error(
    database_url: str,
    seed: SourceSnapshot,
    models: Models,
    tracking_uri: str,
    snapshot_id: str,
    status: int,
) -> None:
    EvidenceStore(database_url).load(seed)
    with TestClient(create_app(database_url, models=models, tracking_uri=tracking_uri)) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot_id,
                "question": "When did Phil arrive?",
            },
        )
        assert response.status_code == status


@pytest.mark.parametrize(
    "models,expected_input,expected_output",
    [({}, None, None), ({"prompt_eval_count": 40, "eval_count": 5}, 40, 5)],
    indirect=["models"],
)
def test_embedding_usage_is_reported_separately_from_answer_tokens(
    database_url: str,
    seed: SourceSnapshot,
    models: Models,
    tracking_uri: str,
    expected_input: int | None,
    expected_output: int | None,
) -> None:
    from ask_phil.models import LocalEmbedding

    def embedding_provider(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["truncate"] is False
        count = 12 if body["input"].startswith("task: search result | query:") else 34
        return httpx.Response(
            200,
            json={
                "embeddings": [[1.0, 0.0, 0.0]],
                "prompt_eval_count": count,
            },
        )

    models = replace(
        models,
        embedding=LocalEmbedding(
            model_name="test-embedding",
            client=Client(
                host="http://model.invalid", transport=httpx.MockTransport(embedding_provider)
            ),
        ),
    )
    EvidenceStore(database_url).load(seed)
    TextRetriever(database_url, models.embedding, models.settings.embedding_id, 3).prepare(
        seed.snapshot_id
    )
    with TestClient(create_app(database_url, models=models, tracking_uri=tracking_uri)) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": seed.snapshot_id,
                "question": "When did Phil arrive?",
            },
        ).json()["response"]
        assert response["usage"] == {
            "input_tokens": expected_input,
            "output_tokens": expected_output,
            "embedding_tokens": 12,
        }
        trace = MlflowClient(tracking_uri=tracking_uri).get_trace(response["trace_id"], flush=True)
        embedding_span = next(span for span in trace.data.spans if span.name == "query_embedding")
        assert embedding_span.outputs["input_tokens"] == 12
        if expected_input is not None:
            assert trace.info.token_usage == {
                "input_tokens": 52,
                "output_tokens": 5,
                "total_tokens": 57,
            }
        root = next(span for span in trace.data.spans if span.name == "text_rag")
        assert root.attributes["usage_complete"] is (expected_input is not None)
