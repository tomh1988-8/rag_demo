from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

from starlette.types import ASGIApp
from test_event_claims import reference_batch

from ask_phil.event_graph import EventGraph, EventQuery
from ask_phil.storage import EvidenceStore


def test_shared_incident_returns_other_participants_without_transferring_guilt(
    database_url: str,
) -> None:
    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    graph = EventGraph(database_url)
    audit = graph.install(batch, reviews)
    result = graph.query(
        snapshot.snapshot_id,
        EventQuery(kind="crime_history", character_id="max-branning", participant_id="bobby-beale"),
    )
    assert result.status == "found"
    assert {c.event_id for c in result.claims} == {"lucy-murder"}
    assert {
        (p.character_id, p.role)
        for c in result.claims
        if c.event_type == "commission"
        for p in c.participants
    } == {("bobby-beale", "perpetrator"), ("lucy-beale", "victim")}
    assert any(c.event_type == "conviction" for c in result.claims)
    assert graph.audit(snapshot.snapshot_id) == audit


def test_final_answers_preserve_false_accounts_roles_and_citations(
    database_url: str, tmp_path: Path
) -> None:
    from fastapi.testclient import TestClient

    from ask_phil.api import create_app

    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    EventGraph(database_url).install(batch, reviews)
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/events.db")
    ) as client:
        query = {
            "kind": "crime_history",
            "character_id": "max-branning",
            "participant_id": "bobby-beale",
        }
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Did Max murder Lucy because he was convicted?",
                "route": "graph",
                "graph": query,
            },
        )
        assert response.status_code == 200, response.text
        receipt = response.json()
        answer = receipt["response"]
        assert answer["status"] == "partial"
        assert "Bobby Beale committed the act" in answer["answer"]
        assert "Max Branning was convicted" in answer["answer"]
        assert "neither commission nor innocence" in answer["answer"]
        assert "Max Branning committed" not in answer["answer"]
        assert answer["execution"]["model_calls"] == 0 and answer["execution"]["tool_calls"] == 1
        assert len(answer["citations"]) == 3
        for citation in answer["citations"]:
            assert client.get(citation["resolve_path"]).status_code == 200
        typed = client.post(f"/v1/snapshots/{snapshot.snapshot_id}/events", json=query)
        assert typed.json() == answer["graph"]
        audit = client.get(f"/v1/snapshots/{snapshot.snapshot_id}/event-claims")
        assert len(audit.json()["batch"]["claims"]) == 17
        saved = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert saved.json() == answer
        stella = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Did Phil kill Stella?",
                "route": "graph",
                "graph": {"kind": "crime_history", "character_id": "phil-mitchell"},
            },
        ).json()["response"]
        assert "I confessed" in stella["answer"]
        assert "confession as false" in stella["answer"]
        assert "I committed" not in stella["answer"]


def test_cli_exposes_shared_event_roles_through_the_api(
    database_url: str,
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    import json
    import os
    import subprocess
    import sys

    from ask_phil.api import create_app

    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    EventGraph(database_url).install(batch, reviews)
    with http_server(create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/cli.db")) as url:
        cli = subprocess.run(
            [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "--api-url",
                url,
                "ask",
                "Was Max guilty of the crash?",
                "--snapshot",
                snapshot.snapshot_id,
                "--route",
                "graph",
                "--crime-history",
                "--event",
                "carl-crash",
                "--character",
                "max-branning",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "NO_PROXY": "127.0.0.1"},
        )
    assert cli.returncode == 0, cli.stderr
    answer = json.loads(cli.stdout)["response"]
    assert "graph" in answer, answer
    assert answer["graph"]["query"]["kind"] == "crime_history"
    assert "accusation as false" in answer["answer"]
    assert "confession as false" in answer["answer"]
    assert "Max Branning was acquitted" in answer["answer"]
    assert "Max Branning committed" not in answer["answer"]


def test_bounded_queries_and_empty_history_remain_qualified(
    database_url: str, tmp_path: Path
) -> None:
    import pytest
    from fastapi.testclient import TestClient
    from pydantic import ValidationError

    from ask_phil.api import create_app
    from ask_phil.execution import ExecutionLimits
    from ask_phil.storage import SnapshotConflict

    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    graph = EventGraph(database_url)
    query = EventQuery(kind="crime_history", character_id="max-branning", max_events=1)
    assert graph.query(snapshot.snapshot_id, query).status == "unavailable"
    audit = graph.install(batch, reviews)
    assert graph.install(batch, tuple(reversed(reviews))) == audit
    with pytest.raises(SnapshotConflict):
        graph.install(batch.model_copy(update={"extractor": "changed"}), reviews)
    bounded = graph.query(snapshot.snapshot_id, query)
    assert bounded.status == "truncated"
    assert {c.event_id for c in bounded.claims} == {"carl-crash"}
    assert len(bounded.claims) == 7
    unknown = graph.query(
        snapshot.snapshot_id, query.model_copy(update={"character_id": "steve-mcfadden"})
    )
    assert unknown.status == "unknown_character" and not unknown.claims
    with pytest.raises(ValidationError):
        EventQuery(kind="crime_history", character_id="max-branning", participant_id="max-branning")
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/empty.db")
    ) as client:
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Grant has never committed a crime, right?",
                "route": "graph",
                "graph": {"kind": "crime_history", "character_id": "grant-mitchell"},
            },
        ).json()["response"]
        assert result["status"] == "insufficient_evidence" and not result["citations"]
        assert "does not prove" in result["answer"]
        assert result["graph"]["status"] == "empty"
        invalid = client.post(
            f"/v1/snapshots/{snapshot.snapshot_id}/events",
            json={
                "kind": "crime_history",
                "character_id": "phil-mitchell",
                "direction": "ancestors",
            },
        )
        assert invalid.status_code == 422
    with TestClient(
        create_app(
            database_url,
            tracking_uri=f"sqlite:///{tmp_path}/stop.db",
            execution_limits=ExecutionLimits(tool_calls=0),
        )
    ) as client:
        stopped = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Who was involved?",
                "route": "graph",
                "graph": {"kind": "crime_history", "character_id": "phil-mitchell"},
            },
        ).json()["response"]
        assert stopped["status"] == "insufficient_evidence"
        assert not stopped["citations"] and "graph" not in stopped
        assert stopped["execution"]["stop_reason"] == "tool_call_limit"


def test_family_only_policy_does_not_authorize_the_new_event_tool(
    database_url: str, tmp_path: Path
) -> None:
    from fastapi.testclient import TestClient

    from ask_phil.api import create_app
    from ask_phil.execution import ExecutionLimits

    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    EventGraph(database_url).install(batch, reviews)
    with TestClient(
        create_app(
            database_url,
            tracking_uri=f"sqlite:///{tmp_path}/denied.db",
            execution_limits=ExecutionLimits(capabilities=("family_graph",)),
        )
    ) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Who was involved?",
                "route": "graph",
                "graph": {"kind": "crime_history", "character_id": "phil-mitchell"},
            },
        ).json()["response"]
        assert response["status"] == "insufficient_evidence"
        assert response["execution"]["stop_reason"] == "capability_denied"
        assert not response["citations"] and "graph" not in response
