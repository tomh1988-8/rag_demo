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
import psycopg
import pytest
from fastapi.testclient import TestClient
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from mlflow import MlflowClient
from ollama import Client
from starlette.types import ASGIApp

from ask_phil.answering import AnswerService
from ask_phil.answers import AskRequest
from ask_phil.api import create_app
from ask_phil.ingestion import build_snapshot, read_batch
from ask_phil.models import Models, ModelSettings
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration


def test_quality_capture_uses_fresh_api_sessions_and_preserves_each_repeat(
    conversation_client: TestClient, tmp_path: Path
) -> None:
    from ask_phil.evaluation import (
        EvaluationTracking,
        QualityReview,
        document_fingerprint,
        review_capture,
    )
    from ask_phil.quality_comparison import ComparisonDataset
    from ask_phil.quality_workflow import capture_quality, reviewed_comparison_run

    references = json.loads(Path("data/references/quality-comparison-v1.json").read_bytes())
    references["cases"] = [
        case for case in references["cases"] if case["case_id"] in ("phil-intro", "isolated")
    ]
    for case in references["cases"]:
        case["snapshot_id"] = "chat"
    path = tmp_path / "references.json"
    path.write_text(json.dumps(references))
    output = tmp_path / "capture.json"
    tracking = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
    capture_quality(
        path,
        output,
        conversation_client,
        repeats=2,
        namespace="public-test-development",
        private_directory=tmp_path / "private",
        max_cost_usd=0,
        tracking=EvaluationTracking(tracking, "quality-test-captures", {"kind": "software-test"}),
        serving_tracking=tracking,
    )
    captured = json.loads(output.read_bytes())
    responses = [row["response"] for row in captured["cases"]]
    assert captured["state"] == "complete"
    assert len(responses) == 4
    assert len({r["response_id"] for r in responses}) == 4
    assert len({r["conversation"]["session_id"] for r in responses}) == 4
    assert all(r["conversation"]["turn_number"] == 1 for r in responses)
    assert sum("February 1990" in r["answer"] for r in responses) == 2
    assert sum(r["status"] == "clarification" for r in responses) == 2
    assert captured["cost_usd"] == "0.0"
    assert captured["cache_mode"] == "off"
    assert "session_token" not in output.read_text()
    downloaded = tracking.download_artifacts(captured["run_id"], "result/capture.json")
    assert json.loads(Path(downloaded).read_bytes()) == captured
    factual = [r for r in captured["cases"] if r["response"]["status"] == "answered"]
    assert all(r["stage_ms"]["answer_model"] is not None for r in factual)
    annotations = tmp_path / "annotations.json"
    annotations.write_text(
        json.dumps(
            {
                "reviews": [
                    QualityReview.model_validate(
                        {
                            "case_id": row["case_id"],
                            "reviewer": "Independently specified provider fixture",
                            "rationale": "Arrival is February 1990; pronouns need a subject.",
                            "response_sha256": document_fingerprint(row["response"]),
                            "reference_sha256": document_fingerprint(row["reference"]),
                            "claims": [
                                {
                                    "claim": "Phil arrives in February 1990.",
                                    "correct": True,
                                    "grounded": True,
                                    "citation_supported": True,
                                }
                            ]
                            if row["response"]["status"] == "answered"
                            else [],
                            "required_facts": [
                                {"fact": fact["fact"], "covered": True}
                                for fact in row["reference"]["required_facts"]
                            ],
                            "answerability": True,
                            "relevance": True,
                        }
                    ).model_dump(mode="json")
                    for row in captured["cases"]
                ]
            }
        )
    )
    reviewed = tmp_path / "reviewed.json"
    review_capture(output, annotations, output.with_suffix(".references.json"), reviewed)
    scored = reviewed_comparison_run(
        ComparisonDataset.model_validate_json(path.read_bytes()), output, reviewed
    )
    assert len(scored.observations) == 4
    assert all(row.quality.answerability.value == 1 for row in scored.observations)
    assert sum(row.quality.correctness.value == 1 for row in scored.observations) == 2


@pytest.fixture
def session_clock() -> list[datetime]:
    return [datetime(2026, 10, 17, 12, tzinfo=UTC)]


@pytest.fixture
def conversation_models(database_url: str) -> Models:
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
    return models


@pytest.fixture
def conversation_client(
    database_url: str,
    tmp_path: Path,
    session_clock: list[datetime],
    conversation_models: Models,
) -> Iterator[TestClient]:
    with TestClient(
        create_app(
            database_url,
            models=conversation_models,
            tracking_uri=f"sqlite:///{tmp_path}/mlflow.db",
            session_clock=lambda: session_clock[0],
        )
    ) as client:
        yield client


def test_turn_module_advances_and_retains_only_character_references(
    database_url: str,
    tmp_path: Path,
    session_clock: list[datetime],
    conversation_models: Models,
) -> None:
    from ask_phil.sessions import ConversationSessions

    sessions = ConversationSessions(database_url, clock=lambda: session_clock[0])
    answers = AnswerService(database_url, conversation_models, f"sqlite:///{tmp_path}/mlflow.db")
    created = sessions.create()
    first = sessions.ask(
        created.session.session_id,
        created.session_token,
        AskRequest(snapshot_id="chat", question="Tell me about Phil Mitchell."),
        answer=answers.ask,
    )
    followup = sessions.ask(
        created.session.session_id,
        created.session_token,
        AskRequest(snapshot_id="chat", question="When did he arrive?"),
        answer=answers.ask,
    )
    assert "2001" in first.response.answer
    assert "February 1990" in followup.response.answer
    assert followup.response.conversation is not None
    assert followup.response.conversation.turn_number == 2
    state = sessions.get(created.session.session_id, created.session_token)
    assert state.turn_number == 2
    assert [turn.character_ids for turn in state.history] == [
        ("phil-mitchell",),
        ("phil-mitchell",),
    ]
    with TestClient(create_app(database_url)) as reader:
        original = reader.get(
            f"/v1/responses/{first.response.response_id}",
            headers={"Authorization": f"Bearer {first.read_token}"},
        )
    assert original.status_code == 200
    assert original.json() == first.response.model_dump(mode="json")


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


def test_character_relationship_question_requires_an_explicit_name_on_followup(
    conversation_client: TestClient,
) -> None:
    client = conversation_client
    session = client.post("/v1/sessions").json()
    base = f"/v1/sessions/{session['session']['session_id']}"
    headers = {"Authorization": f"Bearer {session['session_token']}"}
    question = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "Who is Phil Mitchell's former wife?"},
    )
    question.raise_for_status()
    # Naming Phil in the question or generated answer does not identify his former wife.
    state = client.get(base, headers=headers).json()
    assert state["history"][-1]["character_ids"] == []
    assert state["history"][-1]["reference_barrier"] is True
    followup = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did she arrive?"},
    )
    followup.raise_for_status()
    assert followup.json()["response"]["status"] == "clarification"


def test_failed_answer_does_not_advance_the_turn_or_extend_reference_memory(
    conversation_client: TestClient,
    session_clock: list[datetime],
) -> None:
    client = conversation_client
    session = client.post("/v1/sessions").json()
    base = f"/v1/sessions/{session['session']['session_id']}"
    headers = {"Authorization": f"Bearer {session['session_token']}"}
    first = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did Phil Mitchell arrive?"},
    )
    first.raise_for_status()
    before = client.get(base, headers=headers).json()
    session_clock[0] += timedelta(minutes=5)
    failed = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "missing-snapshot", "question": "When did Kat Slater arrive?"},
    )
    assert failed.status_code == 404
    assert client.get(base, headers=headers).json() == before
    followup = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did he arrive?"},
    )
    followup.raise_for_status()
    response = followup.json()["response"]
    assert "February 1990" in response["answer"]
    assert response["conversation"]["turn_number"] == 2
    assert (
        response["conversation"]["reference"]["context_turn_id"]
        == first.json()["response"]["conversation"]["turn_id"]
    )


@pytest.mark.parametrize("failure", ["write", "commit"])
def test_failed_turn_persistence_keeps_previous_references_and_allows_recovery(
    conversation_client: TestClient,
    database_url: str,
    failure: str,
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
    before = client.get(base, headers=headers).json()
    # Inject failure in the real disposable database; observe recovery through HTTP.
    with psycopg.connect(database_url) as conn:
        if failure == "write":
            conn.execute("""ALTER TABLE conversation_sessions ADD CONSTRAINT reject_next_turn
                CHECK ((document->>'turn_number')::integer < 2)""")
        else:
            conn.execute("""CREATE FUNCTION reject_next_turn() RETURNS trigger
                LANGUAGE plpgsql AS $$ BEGIN
                    RAISE EXCEPTION 'Test turn commit failure' USING ERRCODE = '23514';
                END $$""")
            conn.execute("""CREATE CONSTRAINT TRIGGER reject_next_turn
                AFTER UPDATE ON conversation_sessions DEFERRABLE INITIALLY DEFERRED
                FOR EACH ROW EXECUTE FUNCTION reject_next_turn()""")
    failed = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did Kat Slater arrive?"},
    )
    assert failed.status_code == 503
    assert failed.json() == {"detail": "Evidence storage is unavailable."}
    assert client.get(base, headers=headers).json() == before
    with psycopg.connect(database_url) as conn:
        if failure == "write":
            conn.execute("ALTER TABLE conversation_sessions DROP CONSTRAINT reject_next_turn")
        else:
            conn.execute("DROP TRIGGER reject_next_turn ON conversation_sessions")
    followup = client.post(
        base + "/turns",
        headers=headers,
        json={"snapshot_id": "chat", "question": "When did he arrive?"},
    )
    followup.raise_for_status()
    response = followup.json()["response"]
    assert response["conversation"]["turn_number"] == 2
    assert "February 1990" in response["answer"]


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

    from ask_phil.sessions import ConversationSessions

    client = conversation_client
    created = client.post("/v1/sessions").json()
    session_id = UUID(created["session"]["session_id"])
    token = created["feedback_token"]
    sessions = ConversationSessions(database_url, clock=lambda: session_clock[0])
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


def test_waiting_turns_serialize_within_their_request_budgets(
    database_url: str,
    tmp_path: Path,
    conversation_models: Models,
) -> None:
    import time
    from dataclasses import replace
    from threading import Event

    from ask_phil.execution import ExecutionLimits

    entered, release = Event(), Event()
    snapshot = EvidenceStore(database_url).snapshot("chat")

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
        if not entered.is_set():
            entered.set()
            assert release.wait(30), "Controlled slow model was not released."
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
                            "answer": "Right, listen. I arrived in February 1990.",
                            "evidence_ids": [snapshot.passages[0].evidence_id],
                            "unanswered": [],
                            "qualifications": [],
                        }
                    ),
                },
            },
        )

    models = replace(
        conversation_models,
        llm=Ollama(
            model="test-answer",
            context_window=4096,
            client=Client(host="http://model.invalid", transport=httpx.MockTransport(provider)),
        ),
    )
    tracking = f"sqlite:///{tmp_path}/queue.db"
    with (
        TestClient(create_app(database_url, models=models, tracking_uri=tracking)) as client,
        TestClient(
            create_app(
                database_url,
                models=models,
                tracking_uri=tracking,
                execution_limits=ExecutionLimits(seconds=0.2),
            )
        ) as limited,
    ):
        created = client.post("/v1/sessions").json()
        base = f"/v1/sessions/{created['session']['session_id']}"
        headers = {"Authorization": f"Bearer {created['session_token']}"}
        request = {"snapshot_id": "chat", "question": "When did Phil Mitchell arrive?"}
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(client.post, base + "/turns", headers=headers, json=request)
            try:
                assert entered.wait(15), "The first model request did not start."
                waiting = executor.submit(
                    client.post, base + "/turns", headers=headers, json=request
                )
                expired = limited.post(base + "/turns", headers=headers, json=request)
                assert expired.status_code == 503
                time.sleep(6)
                assert not waiting.done(), "A valid queued request exhausted a fixed SQL lock wait."
            finally:
                release.set()
            responses = [first.result(timeout=30), waiting.result(timeout=30)]
        assert [r.status_code for r in responses] == [200, 200]
        turns = [r.json()["response"]["conversation"]["turn_number"] for r in responses]
        assert turns == [1, 2]
        assert client.get(base, headers=headers).json()["turn_number"] == 2
