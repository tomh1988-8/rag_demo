"""Bounded investigation through the public API, real storage and external providers."""

import hashlib
import json
import subprocess
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from typing import Any
from uuid import uuid4

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient
from llama_index.llms.ollama import Ollama
from mlflow import MlflowClient
from ollama import Client
from starlette.types import ASGIApp

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionLimits
from ask_phil.models import LocalEmbedding, Models, ModelSettings
from ask_phil.parentage import ClaimBatch
from ask_phil.publications import PublicationStore, RefreshRun
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration
pytest_plugins = ("test_family_graph", "test_connection_graph", "test_execution_api")


def decision(tool: str, arguments: dict[str, Any], part: str) -> dict[str, Any]:
    return {
        "coverage": [{"part": part, "evidence_ids": [], "resolved": False}],
        "action": {"kind": "tool", "tool": tool, "arguments": json.dumps(arguments)},
    }


def finish(part: str, evidence_id: str = "phil-arrival-001") -> dict[str, Any]:
    return {
        "coverage": [{"part": part, "evidence_ids": [evidence_id], "resolved": True}],
        "action": {
            "kind": "finish",
            "draft": {
                "answer": "Right, listen. I arrived in February 1990.",
                "status": "answered",
                "evidence_ids": [evidence_id],
                "unanswered": [],
                "qualifications": [],
            },
        },
    }


@pytest.fixture
def investigator_models() -> Callable[[list[dict[str, Any]]], Models]:
    def build(decisions: list[dict[str, Any]]) -> Models:
        outputs = iter(decisions)

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
                return httpx.Response(
                    200, json={"embeddings": [[1.0, 0.0, 0.0]], "prompt_eval_count": 7}
                )
            assert request.url.path == "/api/chat"
            output = dict(next(outputs))
            usage = output.pop("_usage", {"prompt_eval_count": 40, "eval_count": 60})
            hook = output.pop("_hook", None)
            if hook:
                hook()
            return httpx.Response(
                200,
                json={
                    "model": "test-answer",
                    "done": True,
                    **usage,
                    "message": {"role": "assistant", "content": json.dumps(output)},
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
            settings,
            LocalEmbedding(
                "test-embedding", Client(host="http://model.invalid", transport=transport)
            ),
            Ollama(
                model="test-answer",
                context_window=4096,
                additional_kwargs={"num_predict": 256},
                client=Client(host="http://model.invalid", transport=transport),
            ),
        )

    return build


def publish(database_url: str, snapshot: SourceSnapshot, models: Models) -> None:
    EvidenceStore(database_url).load(snapshot)
    index = TextRetriever(database_url, models.embedding, models.settings.embedding_id, 3).prepare(
        snapshot.snapshot_id
    )
    publications = PublicationStore(database_url)
    run = RefreshRun(
        run_id=uuid4(),
        flow_run_id=uuid4(),
        started_at=datetime.now(UTC),
        status="running",
        action="review",
        input_sha256=snapshot.fingerprint,
    )
    with publications.writer() as conn:
        publications.publish(snapshot, index, run, conn)


def test_single_passage_sufficient_investigation_retains_actual_tools_and_usage(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    part = "When did Phil arrive?"
    models = investigator_models(
        [decision("text_search", {"query": part, "k": 1}, part), finish(part)]
    )
    publish(database_url, seed, models)
    uri = f"sqlite:///{tmp_path}/investigation.db"
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=uri,
            execution_limits=ExecutionLimits(model_calls=5, tool_calls=3),
        )
    ) as client:
        result = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert result.status_code == 200, result.text
        receipt = result.json()
        answer = receipt["response"]
        assert answer["status"] == "answered"
        assert answer["route_override"] is True
        assert answer["execution"]["model_calls"] == 3
        assert answer["execution"]["tool_calls"] == 1
        assert answer["usage"] == {"input_tokens": 80, "output_tokens": 120, "embedding_tokens": 7}
        assert [c["evidence_id"] for c in answer["citations"]] == ["phil-arrival-001"]
        investigation = answer["investigation"]
        assert investigation["stop_reason"] == "completed"
        assert investigation["coverage"][0]["resolved"] is True
        assert [s["tool"] for s in investigation["steps"]] == ["text_search"]
        assert investigation["steps"][0]["status"] == "executed"
        trace = MlflowClient(tracking_uri=uri).get_trace(answer["trace_id"], flush=True)
        root = next(s for s in trace.data.spans if s.name == "investigation")
        assert root.outputs == answer
        original = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert original.json() == answer


def test_investigator_uses_reviewed_typed_graph_paths_in_the_same_publication(
    database_url: str,
    family_batch: ClaimBatch,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    from test_family_graph import install_family

    install_family(database_url, family_batch)
    snapshot = EvidenceStore(database_url).snapshot(family_batch.snapshot_id)
    part = "Who are Ben's biological parents?"
    final = finish(part, "family-ben-birth")
    final["action"]["draft"]["answer"] = "Right, listen. Kathy and I are Ben's biological parents."
    models = investigator_models(
        [
            decision(
                "family",
                {"character_id": "ben-mitchell", "direction": "ancestors", "max_depth": 1},
                part,
            ),
            final,
        ]
    )
    publish(database_url, snapshot, models)
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=f"sqlite:///{tmp_path}/family.db",
            execution_limits=ExecutionLimits(model_calls=4, tool_calls=2),
        )
    ) as client:
        response = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["status"] == "answered"
        assert answer["execution"]["model_calls"] == 2
        graph = answer["investigation"]["steps"][0]["result"]
        assert graph["snapshot_sha256"] == answer["snapshot_sha256"]
        assert {tuple(p["characters"]) for p in graph["paths"]} == {
            ("ben-mitchell", "phil-mitchell"),
            ("ben-mitchell", "kathy-beale"),
        }
        assert [p["evidence_id"] for p in answer["context"]] == ["family-ben-birth"]


def test_investigation_cannot_mark_all_parts_answered_after_one_relevant_passage(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    part, missing = "When did Phil arrive?", "Who is Phil's mother?"
    search, final = decision("text_search", {"query": part, "k": 1}, part), finish(part)
    unresolved = {"part": missing, "evidence_ids": [], "resolved": False}
    search["coverage"].append(unresolved)
    final["coverage"].append(unresolved)
    models = investigator_models([search, final])
    publish(database_url, seed, models)
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=f"sqlite:///{tmp_path}/partial.db",
            execution_limits=ExecutionLimits(model_calls=4, tool_calls=2),
        )
    ) as client:
        result = client.post(
            "/v1/answers",
            json={"question": part + " " + missing, "route": "investigation"},
        )
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["status"] == "partial"
        assert answer["unanswered"] == [missing]
        assert "February 1990" in answer["answer"]
        assert missing in answer["answer"]
        assert len(answer["citations"]) == 1


def test_cli_can_explicitly_investigate_in_a_session_with_default_limits(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    part = "When did Phil arrive?"
    models = investigator_models(
        [decision("text_search", {"query": part, "k": 1}, part), finish(part)]
    )
    publish(database_url, seed, models)
    app = create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/cli.db")
    with http_server(app) as url, httpx.Client(base_url=url, trust_env=False) as client:
        session = client.post("/v1/sessions").json()
        path = tmp_path / "session.json"
        path.write_text(json.dumps(session))
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "--api-url",
                url,
                "ask",
                part,
                "--route",
                "investigation",
                "--session",
                str(path),
            ],
            text=True,
            capture_output=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        answer = json.loads(result.stdout)["response"]
        assert answer["status"] == "answered"
        assert answer["conversation"]["turn_number"] == 1
        assert answer["investigation"]["stop_reason"] == "completed"


def test_multiple_requested_facts_acquire_combined_evidence_before_finishing(
    database_url: str,
    family_batch: ClaimBatch,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    from test_family_graph import install_family

    install_family(database_url, family_batch)
    snapshot = EvidenceStore(database_url).snapshot(family_batch.snapshot_id)
    parts = ["Who are Ben's biological parents?", "Who is Phil's biological mother?"]
    initial = decision(
        "family",
        {"character_id": "ben-mitchell", "direction": "ancestors", "max_depth": 1},
        parts[0],
    )
    initial["coverage"].append({"part": parts[1], "evidence_ids": [], "resolved": False})
    second = decision(
        "family",
        {"character_id": "phil-mitchell", "direction": "ancestors", "max_depth": 1},
        parts[0],
    )
    second["coverage"] = [
        {"part": parts[0], "evidence_ids": ["family-ben-birth"], "resolved": True},
        {"part": parts[1], "evidence_ids": [], "resolved": False},
    ]
    final = finish(parts[0], "family-ben-birth")
    final["coverage"].append(
        {"part": parts[1], "evidence_ids": ["family-peggy-phil"], "resolved": True}
    )
    final["action"]["draft"].update(
        answer=(
            "Right, listen. Kathy and I are Ben's biological parents. "
            "Peggy is my biological mother."
        ),
        evidence_ids=["family-ben-birth", "family-peggy-phil"],
    )
    models = investigator_models([initial, second, final])
    publish(database_url, snapshot, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/multi.db")
    ) as client:
        response = client.post(
            "/v1/answers", json={"question": " ".join(parts), "route": "investigation"}
        )
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["status"] == "answered"
        assert {c["evidence_id"] for c in answer["citations"]} == {
            "family-ben-birth",
            "family-peggy-phil",
        }
        assert all(p["resolved"] for p in answer["investigation"]["coverage"])
        assert answer["execution"]["tool_calls"] == 2


def test_malformed_tool_arguments_are_repaired_without_executing_them(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    part = "When did Phil arrive?"
    models = investigator_models(
        [
            decision("text_search", {"query": part, "k": "one", "snapshot_id": "other"}, part),
            decision("text_search", {"query": part, "k": 1}, part),
            finish(part),
        ]
    )
    publish(database_url, seed, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/repair.db")
    ) as client:
        response = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["status"] == "answered"
        assert [s["status"] for s in answer["investigation"]["steps"]] == [
            "invalid_arguments",
            "executed",
        ]
        assert answer["execution"]["model_calls"] == 4
        assert answer["execution"]["tool_calls"] == 1


@pytest.mark.parametrize("tool", ["shell", "sql", "web", "ingest"])
def test_investigator_cannot_expand_its_declared_read_authority(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
    tool: str,
) -> None:
    models = investigator_models(
        [decision(tool, {"instruction": "create new authority"}, "Find evidence")]
    )
    publish(database_url, seed, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/denied.db")
    ) as client:
        response = client.post(
            "/v1/answers", json={"question": "Find newer evidence", "route": "investigation"}
        )
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["execution"]["stop_reason"] == "capability_denied"
        assert answer["execution"]["tool_calls"] == 0
        assert answer["investigation"]["steps"][0]["status"] == "denied_tool"
        assert answer["citations"] == []


def test_repeated_semantically_identical_call_stops_before_another_execution(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    part = "When did Phil arrive?"
    first = decision("text_search", {"query": part}, part)
    second = decision("text_search", {"k": 3, "query": part}, part)
    second["coverage"] = finish(part)["coverage"]
    models = investigator_models([first, second])
    publish(database_url, seed, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/repeat.db")
    ) as client:
        response = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["execution"]["stop_reason"] == "repeated_call"
        assert answer["execution"]["tool_calls"] == 1
        assert answer["status"] == "partial"
        assert "February 1990" in answer["answer"]
        assert answer["investigation"]["steps"][-1]["status"] == "repeated_call"


@pytest.mark.parametrize(
    "limits,reason,tools,models",
    [
        (ExecutionLimits(model_calls=0), "model_call_limit", 0, 0),
        (ExecutionLimits(model_calls=1), "model_call_limit", 1, 1),
        (ExecutionLimits(model_calls=4, tool_calls=0), "tool_call_limit", 0, 1),
        (ExecutionLimits(model_calls=4, context_bytes=100), "context_limit", 1, 2),
    ],
)
def test_investigation_obeys_shared_limits_and_retains_a_stop_receipt(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
    limits: ExecutionLimits,
    reason: str,
    tools: int,
    models: int,
) -> None:
    part = "When did Phil arrive?"
    supplied = investigator_models(
        [decision("text_search", {"query": part, "k": 1}, part), finish(part)]
    )
    publish(database_url, seed, supplied)
    with TestClient(
        create_app(
            database_url,
            models=supplied,
            execution_limits=limits,
            tracking_uri=f"sqlite:///{tmp_path}/limits.db",
        )
    ) as client:
        response = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert response.status_code == 200, response.text
        receipt = response.json()
        answer = receipt["response"]
        assert answer["execution"]["stop_reason"] == reason
        assert answer["execution"]["model_calls"] == models
        assert answer["execution"]["tool_calls"] == tools
        assert answer["status"] == "insufficient_evidence"
        saved = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert saved.json() == answer


def test_unknown_usage_is_reported_and_does_not_remove_the_call_limit(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    part = "When did Phil arrive?"
    search = decision("text_search", {"query": part, "k": 1}, part)
    search["_usage"] = {}
    models = investigator_models([search, finish(part)])
    publish(database_url, seed, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/usage.db")
    ) as client:
        response = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["status"] == "answered"
        assert answer["usage"] == {
            "input_tokens": None,
            "output_tokens": None,
            "embedding_tokens": 7,
        }
        assert answer["execution"]["model_calls"] == 3


def test_active_refresh_cannot_change_the_investigators_pinned_snapshot(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    part = "When did Phil arrive?"
    search = decision("text_search", {"query": part, "k": 1}, part)
    models = investigator_models([search, finish(part)])
    publish(database_url, seed, models)
    original = PublicationStore(database_url).active()
    later = seed.model_copy(update={"snapshot_id": "later-snapshot"})
    search["_hook"] = lambda: publish(database_url, later, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/pin.db")
    ) as client:
        response = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["status"] == "answered"
        assert answer["snapshot_id"] == seed.snapshot_id
        assert answer["publication"]["compatibility_id"] == original.compatibility_id
        assert PublicationStore(database_url).active().manifest.snapshot_id == later.snapshot_id


def test_legacy_snapshot_without_a_compatible_publication_cannot_be_investigated(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    EvidenceStore(database_url).load(seed)
    models = investigator_models([])
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/legacy.db")
    ) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": seed.snapshot_id,
                "question": "When did Phil arrive?",
                "route": "investigation",
            },
        )
        assert response.status_code == 503
        assert "published" in response.json()["detail"]


@pytest.mark.parametrize("disconnect", [False, True])
def test_investigation_network_deadline_and_disconnect_cancel_inflight_work(
    database_url: str,
    seed: SourceSnapshot,
    slow_models: tuple[Models, Event, Event],
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
    disconnect: bool,
) -> None:
    models, entered, closed = slow_models
    publish(database_url, seed, models)
    uri = f"sqlite:///{tmp_path}/network.db"
    app = create_app(
        database_url,
        models=models,
        tracking_uri=uri,
        execution_limits=ExecutionLimits(
            model_calls=4, tool_calls=3, seconds=8 if disconnect else 1.2
        ),
    )
    tracking = MlflowClient(tracking_uri=uri)
    experiment = tracking.create_experiment("ask-phil-serving")
    with http_server(app) as url:
        body = {"question": "When did Phil arrive?", "route": "investigation"}
        if disconnect:
            with pytest.raises(httpx.ReadTimeout):
                httpx.post(url + "/v1/answers", json=body, timeout=0.8)
        else:
            result = httpx.post(url + "/v1/answers", json=body, timeout=10)
            assert result.status_code == 200, result.text
            assert result.json()["response"]["execution"]["stop_reason"] == "timeout"
        assert entered.is_set()
        assert closed.wait(2), "The model connection must close when the investigation stops."
        deadline = time.monotonic() + 3
        traces = tracking.search_traces(locations=[experiment])
        while not traces and time.monotonic() < deadline:
            time.sleep(0.05)
            traces = tracking.search_traces(locations=[experiment])
        assert len(traces) == 1
        trace = tracking.get_trace(traces[0].info.trace_id, flush=True)
        root = next(s for s in trace.data.spans if s.name == "investigation")
        assert root.outputs["execution"]["stop_reason"] == (
            "cancelled" if disconnect else "timeout"
        )
        assert root.outputs["investigation"]["steps"] == []
        assert root.outputs["citations"] == []


@pytest.mark.parametrize(
    "tool,arguments,evidence_id,expected_text",
    [
        (
            "relationships",
            {
                "kind": "relationship_history",
                "character_id": "den-watts",
                "partner_id": "sharon-watts",
            },
            "history-den-adoption",
            "Den adopted Sharon.",
        ),
        (
            "events",
            {
                "kind": "life_events",
                "character_id": "sharon-watts",
                "event_id": "sharon-christmas-pregnancy",
            },
            "sharon-christmas-pregnancy",
            "Sharon discovered she was pregnant on Christmas Day 2005.",
        ),
        (
            "connections",
            {
                "kind": "connection",
                "character_id": "sharon-watts",
                "target_id": "den-watts",
                "max_depth": 1,
            },
            "history-den-adoption",
            "Den is Sharon's adoptive parent, not her biological parent.",
        ),
    ],
)
def test_investigator_can_select_each_declared_graph_family_without_changing_roles(
    database_url: str,
    connection_snapshot: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
    tool: str,
    arguments: dict[str, Any],
    evidence_id: str,
    expected_text: str,
) -> None:
    part = "Explain the captured character fact."
    final = finish(part, evidence_id)
    final["action"]["draft"]["answer"] = "Right, listen. " + expected_text
    models = investigator_models([decision(tool, arguments, part), final])
    publish(database_url, connection_snapshot, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/typed.db")
    ) as client:
        response = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["status"] == "answered"
        step = answer["investigation"]["steps"][0]
        assert step["status"] == "executed"
        assert step["result"]["status"] == "found"
        assert step["result"]["snapshot_sha256"] == answer["snapshot_sha256"]
        assert evidence_id in {c["evidence_id"] for c in answer["citations"]}


def test_ineligible_graph_query_retains_limited_coverage_and_can_abstain(
    database_url: str,
    connection_snapshot: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    part = "How did Phil respond to the manosphere?"
    final = finish(part)
    final["coverage"] = [{"part": part, "evidence_ids": [], "resolved": False}]
    final["action"]["draft"].update(
        status="insufficient_evidence",
        evidence_ids=[],
        answer=(
            "The captured evidence cannot answer this. Missing coverage does not "
            "establish that it never happened."
        ),
        unanswered=[part],
    )
    models = investigator_models(
        [decision("events", {"kind": "theme", "character_id": "phil-mitchell"}, part), final]
    )
    publish(database_url, connection_snapshot, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/empty.db")
    ) as client:
        result = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["status"] == "insufficient_evidence"
        assert answer["citations"] == []
        assert answer["investigation"]["steps"][0]["result"]["status"] == "ineligible"


def test_investigation_cannot_restore_a_disputed_claim_from_its_source_text(
    database_url: str,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    from test_parentage import reference_batch

    from ask_phil.family_graph import FamilyGraph
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest

    snapshot, batch, reviews = reference_batch()
    batch = batch.model_copy(update={"claims": (batch.claims[0],)})
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(batch, (reviews[0],))
    part = "Who is Ben Mitchell's father?"
    final = finish(part, "family-ben-birth")
    final["action"]["draft"]["answer"] = "Right, listen. I am Ben's established biological father."
    models = investigator_models([decision("text_search", {"query": part, "k": 1}, part), final])
    reviewer = KnowledgeReview(database_url, models.embedding, models.settings.embedding_id, 3)
    before = reviewer.inspect(snapshot.snapshot_id)
    reviewer.apply(
        ReviewRequest(
            snapshot_id=snapshot.snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            graphs=before.graphs,
            family_reviews=(
                reviews[0].model_copy(
                    update={
                        "verdict": "disputed",
                        "note": "Synthetic review disagreement; do not assert this link.",
                    }
                ),
            ),
        )
    )
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/dispute.db")
    ) as client:
        result = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["status"] == "partial"
        assert "Unresolved source disagreement" in answer["answer"]
        assert "no established connection" in answer["answer"]
        assert "I am Ben's established" not in answer["answer"]
        assert answer["review_notices"][0]["claim_id"] == "phil-ben"


def test_graph_database_deadline_returns_an_immutable_investigation_stop_receipt(
    database_url: str,
    family_batch: ClaimBatch,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    from test_family_graph import install_family

    install_family(database_url, family_batch)
    snapshot = EvidenceStore(database_url).snapshot(family_batch.snapshot_id)
    part = "Who are Ben's biological parents?"
    models = investigator_models(
        [
            decision(
                "family",
                {"character_id": "ben-mitchell", "direction": "ancestors", "max_depth": 1},
                part,
            )
        ]
    )
    publish(database_url, snapshot, models)
    uri = f"sqlite:///{tmp_path}/sql-timeout.db"
    app = create_app(
        database_url,
        models=models,
        tracking_uri=uri,
        execution_limits=ExecutionLimits(model_calls=4, tool_calls=2, seconds=0.8),
    )
    MlflowClient(tracking_uri=uri).create_experiment("ask-phil-serving")
    with TestClient(app) as client, psycopg.connect(database_url) as lock:
        lock.execute("LOCK TABLE family_edges IN ACCESS EXCLUSIVE MODE")
        with ThreadPoolExecutor(max_workers=1) as workers:
            future = workers.submit(
                client.post, "/v1/answers", json={"question": part, "route": "investigation"}
            )
            try:
                result = future.result(timeout=3)
            finally:
                lock.rollback()
        assert result.status_code == 200, result.text
        receipt = result.json()
        answer = receipt["response"]
        assert answer["execution"]["stop_reason"] == "timeout"
        assert answer["execution"]["tool_calls"] == 1
        assert answer["investigation"]["steps"][0]["status"] == "stopped"
        original = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert original.json() == answer


def test_stop_with_large_retained_passage_preserves_support_without_overflowing_the_reply(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    text = seed.passages[0].text + " Synthetic supporting sentence." * 52
    assert 1600 < len(text) < 1800
    passage = seed.passages[0].model_copy(
        update={"text": text, "end": len(text), "sha256": hashlib.sha256(text.encode()).hexdigest()}
    )
    snapshot = seed.model_copy(
        update={
            "snapshot_id": "large-context-stop",
            "passages": (passage,),
            "source": seed.source.model_copy(update={"support_status": "synthetic_fixture"}),
        }
    )
    part = "When did Phil arrive?"
    first = decision("text_search", {"query": part, "k": 1}, part)
    repeated = decision("text_search", {"query": part, "k": 1}, part)
    repeated["coverage"] = finish(part)["coverage"]
    models = investigator_models([first, repeated])
    publish(database_url, snapshot, models)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/large.db")
    ) as client:
        result = client.post("/v1/answers", json={"question": part, "route": "investigation"})
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["execution"]["stop_reason"] == "repeated_call"
        assert answer["status"] == "partial"
        assert answer["citations"][0]["text"] == text
        assert len(answer["answer"]) < 1600
