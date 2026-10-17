import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from mlflow import MlflowClient
from ollama import Client
from starlette.types import ASGIApp

from ask_phil.api import create_app
from ask_phil.ingestion import build_snapshot, read_batch
from ask_phil.models import Models, ModelSettings
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration


@pytest.fixture
def session_clock() -> list[datetime]:
    return [datetime(2026, 10, 17, 12, tzinfo=UTC)]


@pytest.fixture
def conversation_client(
    database_url: str, tmp_path: Path, session_clock: list[datetime]
) -> Iterator[TestClient]:
    # Real retained source and identity catalogue, narrowed to one sufficient span.
    snapshot = build_snapshot(read_batch(Path("data/sources/core-profiles-v2.json.gz")), "chat")
    passage = next(
        p
        for p in snapshot.passages
        if p.location
        and p.location.source_id == "phil-mitchell-wiki"
        and "first arrives in Walford" in p.text
    )
    snapshot = snapshot.model_copy(update={"passages": (passage,)})
    EvidenceStore(database_url).load(snapshot)

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
        if request.url.path == "/api/embed":
            return httpx.Response(200, json={"embeddings": [[1.0, 0.0, 0.0]]})
        body = json.loads(request.content)
        prompt = body["messages"][-1]["content"]
        assert "Question: When did he" not in prompt
        assert "2001" not in prompt, "Misleading earlier generated answer became prompt history."
        wrong = "Tell me about" in prompt
        return httpx.Response(
            200,
            json={
                "model": "test-answer",
                "done": True,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "status": "answered",
                            "answer": "Right, listen. I arrived in "
                            + ("2001." if wrong else "February 1990."),
                            "evidence_ids": [passage.evidence_id],
                            "unanswered": [],
                            "qualifications": [],
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
    models = Models(
        settings=settings,
        embedding=OllamaEmbedding(
            model_name="test-embedding", client_kwargs={"transport": transport}
        ),
        llm=Ollama(
            model="test-answer",
            context_window=4096,
            client=Client(host="http://model.invalid", transport=transport),
        ),
    )
    TextRetriever(database_url, models.embedding, settings.embedding_id, 3).prepare("chat")
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=f"sqlite:///{tmp_path}/mlflow.db",
            session_clock=lambda: session_clock[0],
        )
    ) as client:
        yield client


def test_followup_retrieves_again_without_using_misleading_generated_history(
    conversation_client: TestClient,
    tmp_path: Path,
) -> None:
    client = conversation_client
    created = client.post("/v1/sessions")
    assert created.status_code == 201, created.text
    session = created.json()
    session_id = session["session"]["session_id"]
    headers = {"Authorization": f"Bearer {session['session_token']}"}
    path = f"/v1/sessions/{session_id}/turns"
    first = client.post(
        path,
        headers=headers,
        json={"snapshot_id": "chat", "question": "Tell me about Phil Mitchell."},
    )
    assert first.status_code == 200, first.text
    assert "2001" in first.json()["response"]["answer"]  # Deliberately incorrect provider fixture.
    followup = client.post(
        path,
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did he first arrive in Walford?"},
    )
    assert followup.status_code == 200, followup.text
    response = followup.json()["response"]
    assert "February 1990" in response["answer"]
    assert response["question"] == "When did he first arrive in Walford?"
    assert response["conversation"]["reference"]["question"] == (
        "When did Phil Mitchell first arrive in Walford?"
    )
    assert response["conversation"]["session_id"] == session_id
    assert response["conversation"]["turn_number"] == 2
    assert response["response_id"] != first.json()["response"]["response_id"]
    assert response["trace_id"] != first.json()["response"]["trace_id"]
    assert response["retrieved"] and response["context"] and response["citations"]
    assert "February 1990" in response["citations"][0]["text"]
    trace = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/mlflow.db").get_trace(
        response["trace_id"], flush=True
    )
    assert {s.name for s in trace.data.spans} >= {
        "text_retrieval",
        "assembled_context",
        "answer_model",
    }
    assert "2001" not in json.dumps([s.inputs for s in trace.data.spans])


def test_unresolved_and_ambiguous_followups_do_not_ask_model_to_guess(
    conversation_client: TestClient,
) -> None:
    client = conversation_client
    session = client.post("/v1/sessions").json()
    path = f"/v1/sessions/{session['session']['session_id']}/turns"
    headers = {"Authorization": f"Bearer {session['session_token']}"}
    missing = client.post(
        path, headers=headers, json={"snapshot_id": "chat", "question": "When did he arrive?"}
    )
    assert missing.status_code == 200, missing.text
    assert missing.json()["response"]["status"] == "clarification"
    client.post(
        path,
        headers=headers,
        json={"snapshot_id": "chat", "question": "Compare Phil Mitchell and Grant Mitchell."},
    ).raise_for_status()
    ambiguous = client.post(
        path, headers=headers, json={"snapshot_id": "chat", "question": "When did he arrive?"}
    )
    assert ambiguous.status_code == 200, ambiguous.text
    response = ambiguous.json()["response"]
    assert response["status"] == "clarification"
    assert "Phil Mitchell" in response["answer"] and "Grant Mitchell" in response["answer"]
    assert response["citations"] == response["retrieved"] == response["context"] == []
    assert response["retrieval_k"] == 0
    assert response["usage"] == {"input_tokens": 0, "output_tokens": 0, "embedding_tokens": 0}
    selected = client.post(
        path, headers=headers, json={"snapshot_id": "chat", "question": "Phil Mitchell"}
    ).json()["response"]
    assert selected["status"] == "answered"
    assert selected["conversation"]["reference"]["question"] == "When did Phil Mitchell arrive?"


def test_reset_clears_references_and_preserves_original_response_identity(
    conversation_client: TestClient,
) -> None:
    client = conversation_client
    session = client.post("/v1/sessions").json()
    base = f"/v1/sessions/{session['session']['session_id']}"
    headers = {"Authorization": f"Bearer {session['session_token']}"}
    original = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did Phil Mitchell first arrive?"},
    ).json()
    reset = client.post(base + "/reset", headers=headers)
    assert reset.status_code == 200, reset.text
    assert reset.json()["generation"] == 1
    assert reset.json()["history"] == []
    followup = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did he arrive?"},
    ).json()["response"]
    assert followup["status"] == "clarification"
    assert followup["conversation"]["generation"] == 1
    assert followup["conversation"]["turn_number"] == 2
    saved = client.get(
        f"/v1/responses/{original['response']['response_id']}",
        headers={"Authorization": f"Bearer {original['read_token']}"},
    )
    assert saved.json() == original["response"]


def test_idle_and_absolute_lifetimes_remove_context_without_reviving_old_responses(
    conversation_client: TestClient,
    session_clock: list[datetime],
) -> None:
    client = conversation_client
    session = client.post("/v1/sessions").json()
    base = f"/v1/sessions/{session['session']['session_id']}"
    headers = {"Authorization": f"Bearer {session['session_token']}"}
    client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did Phil Mitchell arrive?"},
    ).raise_for_status()
    session_clock[0] += timedelta(minutes=30)
    state = client.get(base, headers=headers)
    assert state.status_code == 200, state.text
    assert state.json()["history"] == []
    followup = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did he arrive?"},
    )
    assert followup.json()["response"]["status"] == "clarification"
    session_clock[0] += timedelta(minutes=90)
    assert client.get(base, headers=headers).status_code == 404
    assert client.post(base + "/reset", headers=headers).status_code == 404


def test_feedback_context_outlives_reset_and_session_without_becoming_memory(
    conversation_client: TestClient,
    database_url: str,
    session_clock: list[datetime],
) -> None:
    from uuid import UUID

    from ask_phil.sessions import SessionStore

    client = conversation_client
    created = client.post("/v1/sessions").json()
    session_id = UUID(created["session"]["session_id"])
    token = created["feedback_token"]
    sessions = SessionStore(database_url, clock=lambda: session_clock[0])
    assert sessions.feedback_context(session_id, token) is not None
    assert sessions.feedback_context(session_id, created["session_token"]) is None
    headers = {"Authorization": f"Bearer {created['session_token']}"}
    assert client.post(f"/v1/sessions/{session_id}/reset", headers=headers).status_code == 200
    session_clock[0] += timedelta(hours=2)
    assert sessions.feedback_context(session_id, token) is not None
    assert client.get(f"/v1/sessions/{session_id}", headers=headers).status_code == 404
    session_clock[0] += timedelta(days=30)
    assert sessions.feedback_context(session_id, token) is None


def test_cli_creates_private_session_asks_followup_and_resets_over_http(
    conversation_client: TestClient,
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    with http_server(conversation_client.app) as url:
        command = [sys.executable, "-m", "ask_phil.cli", "--api-url", url]
        private_file = tmp_path / "session.json"
        env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}

        def run(*args: str) -> dict[str, object]:
            result = subprocess.run(
                [*command, *args], env=env, capture_output=True, text=True, timeout=40
            )
            assert result.returncode == 0, result.stderr
            return dict(json.loads(result.stdout))

        run("start-session", str(private_file))
        assert private_file.stat().st_mode & 0o777 == 0o600
        run(
            "ask",
            "When did Phil Mitchell arrive?",
            "--session",
            str(private_file),
            "--snapshot",
            "chat",
        )
        followup = run(
            "ask", "When did he arrive?", "--session", str(private_file), "--snapshot", "chat"
        )
        assert isinstance(followup["response"], dict)
        assert "February 1990" in followup["response"]["answer"]
        run("reset", str(private_file))
        after_reset = run(
            "ask", "When did he arrive?", "--session", str(private_file), "--snapshot", "chat"
        )
        assert isinstance(after_reset["response"], dict)
        assert after_reset["response"]["status"] == "clarification"


def test_sessions_are_isolated_and_reference_state_survives_application_restart(
    conversation_client: TestClient,
    database_url: str,
    session_clock: list[datetime],
) -> None:
    client = conversation_client
    first = client.post("/v1/sessions").json()
    second = client.post("/v1/sessions").json()
    base = f"/v1/sessions/{first['session']['session_id']}"
    first_headers = {"Authorization": f"Bearer {first['session_token']}"}
    other_headers = {"Authorization": f"Bearer {second['session_token']}"}
    question = {"snapshot_id": "chat", "question": "When did Phil Mitchell arrive?"}
    assert client.post(base + "/turns", headers=first_headers, json=question).status_code == 200
    assert client.post(base + "/reset", headers=other_headers).status_code == 404
    assert client.post(base + "/turns", headers=other_headers, json=question).status_code == 404
    assert client.get(base).status_code == 404
    isolated = client.post(
        f"/v1/sessions/{second['session']['session_id']}/turns",
        headers=other_headers,
        json={"snapshot_id": "chat", "question": "When did he arrive?"},
    )
    assert isolated.json()["response"]["status"] == "clarification"
    # A new application process reads only the bounded state from PostgreSQL.
    with TestClient(create_app(database_url, session_clock=lambda: session_clock[0])) as restarted:
        retained = restarted.get(base, headers=first_headers)
        assert retained.status_code == 200
        assert retained.json()["history"][-1]["character_ids"] == ["phil-mitchell"]


def test_concurrent_turns_have_distinct_monotonic_identity_and_bounded_context(
    conversation_client: TestClient,
) -> None:
    client = conversation_client
    created = client.post("/v1/sessions").json()
    base = f"/v1/sessions/{created['session']['session_id']}"
    headers = {"Authorization": f"Bearer {created['session_token']}"}

    def ask() -> dict[str, object]:
        result = client.post(
            base + "/turns",
            headers=headers,
            json={"snapshot_id": "chat", "question": "When did Phil Mitchell arrive?"},
        )
        assert result.status_code == 200, result.text
        return dict(result.json()["response"]["conversation"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        turns = list(executor.map(lambda _: ask(), range(2)))
    assert {t["turn_number"] for t in turns} == {1, 2}
    assert len({t["turn_id"] for t in turns}) == 2
    for _ in range(8):
        client.post(
            base + "/turns",
            headers=headers,
            json={"snapshot_id": "chat", "question": "What is recorded?"},
        ).raise_for_status()
    state = client.get(base, headers=headers).json()
    assert len(state["history"]) == 8
    assert all(not turn["character_ids"] for turn in state["history"])
    response = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did he arrive?"},
    ).json()["response"]
    assert response["status"] == "clarification"


def test_interactive_cli_conversation_supports_followups_and_reset(
    conversation_client: TestClient,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    with http_server(conversation_client.app) as url:
        result = subprocess.run(
            [sys.executable, "-m", "ask_phil.cli", "--api-url", url, "chat", "--snapshot", "chat"],
            input=(
                "When did Phil Mitchell arrive?\nWhen did he arrive?\n/reset\n"
                "When did he arrive?\n/quit\n"
            ),
            text=True,
            capture_output=True,
            timeout=60,
        )
    assert result.returncode == 0, result.stderr
    assert result.stdout.count("February 1990") >= 2
    assert "Which character do you mean?" in result.stdout
    assert '"generation": 1' in result.stdout
