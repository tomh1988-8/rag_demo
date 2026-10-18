import json
import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import pytest
from starlette.types import ASGIApp

from ask_phil.evidence import SourceSnapshot
from ask_phil.family_graph import FamilyGraph, FamilyQuery
from ask_phil.parentage import ClaimBatch, ClaimReview
from ask_phil.storage import EvidenceStore, SnapshotConflict

pytestmark = pytest.mark.integration


@pytest.fixture
def family_batch() -> ClaimBatch:
    reference = json.loads(Path("data/references/parentage-v1.json").read_text())
    return ClaimBatch(
        snapshot_id=reference["snapshot_id"],
        snapshot_sha256=reference["snapshot_sha256"],
        catalogue=reference["catalogue"],
        claims=reference["expected_claims"],
        extractor="reviewed-reference-fixture",
    )


def install_family(database_url: str, batch: ClaimBatch) -> FamilyGraph:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    EvidenceStore(database_url).load(snapshot)
    graph = FamilyGraph(database_url)
    reviews = tuple(
        ClaimReview(
            claim_id=c.claim_id,
            claim_sha256=c.fingerprint,
            verdict="supported",
            reviewer="reference-fixture",
            note="Supported by reviewed selected spans.",
        )
        for c in batch.claims
    )
    graph.install(batch, reviews)
    return graph


def test_ancestry_returns_supported_paths_and_keeps_adoption_out(
    database_url: str, family_batch: ClaimBatch
) -> None:
    graph = install_family(database_url, family_batch)
    result = graph.query(
        family_batch.snapshot_id,
        FamilyQuery(character_id="ben-mitchell", direction="ancestors", max_depth=3),
    )
    assert result.status == "found"
    assert {tuple(path.characters) for path in result.paths} == {
        ("ben-mitchell", "phil-mitchell"),
        ("ben-mitchell", "kathy-beale"),
        ("ben-mitchell", "phil-mitchell", "peggy-mitchell"),
    }
    grandparent = next(p for p in result.paths if p.characters[-1] == "peggy-mitchell")
    assert [(e.parent_id, e.child_id) for e in grandparent.edges] == [
        ("phil-mitchell", "ben-mitchell"),
        ("peggy-mitchell", "phil-mitchell"),
    ]
    assert {e.evidence[0].evidence_id for e in grandparent.edges} == {
        "family-ben-birth",
        "family-peggy-phil",
    }
    adoptive = graph.query(
        family_batch.snapshot_id, FamilyQuery(character_id="sharon-watts", direction="ancestors")
    )
    assert adoptive.status == "empty"
    assert "does not establish" in adoptive.limitation
    audit = graph.audit(family_batch.snapshot_id)
    assert audit is not None
    assert len(audit.batch.claims) == 4


def test_graph_answer_is_explicit_cited_saved_and_does_not_require_models(
    database_url: str,
    family_batch: ClaimBatch,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi.testclient import TestClient

    from ask_phil.api import create_app

    install_family(database_url, family_batch)
    monkeypatch.setenv("ASK_PHIL_MODELS", str(tmp_path / "missing-models.json"))
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
    ) as client:
        failed_text = client.post(
            "/v1/answers",
            json={"snapshot_id": family_batch.snapshot_id, "question": "Who is Ben's father?"},
        )
        assert failed_text.status_code == 503
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": family_batch.snapshot_id,
                "question": "Who are Ben's ancestors?",
                "route": "graph",
                "graph": {"character_id": "ben-mitchell", "direction": "ancestors", "max_depth": 3},
            },
        )
        assert result.status_code == 200, result.text
        receipt = result.json()
        response = receipt["response"]
        assert response["route"] == "graph"
        assert response["route_override"] is True
        assert response["graph"]["status"] == "found"
        assert response["status"] == "partial"
        assert "Peggy Mitchell" in response["answer"]
        assert {c["evidence_id"] for c in response["citations"]} == {
            "family-ben-birth",
            "family-peggy-phil",
        }
        for citation in response["citations"]:
            assert client.get(citation["resolve_path"]).status_code == 200
        assert response["usage"] == {"input_tokens": 0, "output_tokens": 0, "embedding_tokens": 0}
        assert response["execution"]["tool_calls"] == 1
        assert response["elapsed_ms"] > 0
        assert response["model_settings"] is None
        saved = client.get(
            f"/v1/responses/{response['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert saved.json() == response


def test_cli_exposes_graph_override_and_typed_traversal(
    database_url: str,
    family_batch: ClaimBatch,
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    from ask_phil.api import create_app

    install_family(database_url, family_batch)
    app = create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
    with http_server(app) as url:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "--api-url",
                url,
                "ask",
                "Show Peggy's descendants",
                "--snapshot",
                family_batch.snapshot_id,
                "--route",
                "graph",
                "--character",
                "peggy-mitchell",
                "--direction",
                "descendants",
                "--depth",
                "2",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "NO_PROXY": "127.0.0.1"},
        )
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)["response"]
    assert response["route"] == "graph"
    assert {tuple(p["characters"]) for p in response["graph"]["paths"]} == {
        ("peggy-mitchell", "phil-mitchell"),
        ("peggy-mitchell", "phil-mitchell", "ben-mitchell"),
    }


def test_query_bounds_missing_projection_and_immutable_reinstallation(
    database_url: str, family_batch: ClaimBatch
) -> None:
    graph = install_family(database_url, family_batch)
    one_level = graph.query(
        family_batch.snapshot_id,
        FamilyQuery(character_id="ben-mitchell", direction="ancestors", max_depth=1),
    )
    assert {p.characters[-1] for p in one_level.paths} == {"phil-mitchell", "kathy-beale"}
    limited = graph.query(
        family_batch.snapshot_id,
        FamilyQuery(character_id="ben-mitchell", direction="ancestors", max_paths=1),
    )
    assert limited.status == "truncated"
    assert len(limited.paths) == 1
    original = graph.audit(family_batch.snapshot_id)
    assert original is not None
    assert graph.install(family_batch, original.reviews) == original
    assert graph.install(family_batch, tuple(reversed(original.reviews))) == original
    with pytest.raises(SnapshotConflict):
        graph.install(
            family_batch.model_copy(update={"extractor": "different-run"}), original.reviews
        )
    assert graph.audit(family_batch.snapshot_id) == original
    unknown = graph.query(
        family_batch.snapshot_id, FamilyQuery(character_id="steve-mcfadden", direction="ancestors")
    )
    assert unknown.status == "unknown_character"
    assert unknown.paths == ()


def test_missing_graph_and_disabled_graph_capability_are_honest_saved_outcomes(
    database_url: str, seed: SourceSnapshot, tmp_path: Path
) -> None:
    from fastapi.testclient import TestClient

    from ask_phil.api import create_app
    from ask_phil.execution import ExecutionLimits

    EvidenceStore(database_url).load(seed)
    request = {
        "snapshot_id": seed.snapshot_id,
        "question": "Who are Phil's parents?",
        "route": "graph",
        "graph": {"character_id": "phil-mitchell", "direction": "ancestors"},
    }
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/tracking.db")
    ) as client:
        response = client.post("/v1/answers", json=request)
        assert response.status_code == 200
        answer = response.json()["response"]
        assert answer["status"] == "insufficient_evidence"
        assert answer["graph"]["status"] == "unavailable"
        assert answer["citations"] == []
        assert (
            client.post(
                f"/v1/snapshots/{seed.snapshot_id}/family",
                json={"character_id": "phil-mitchell", "direction": "ancestors", "max_depth": 7},
            ).status_code
            == 422
        )
    with TestClient(
        create_app(
            database_url,
            tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
            execution_limits=ExecutionLimits(capabilities=("text_retrieval",)),
        )
    ) as client:
        response = client.post("/v1/answers", json=request)
        assert response.status_code == 200
        answer = response.json()["response"]
        assert answer["execution"]["stop_reason"] == "capability_denied"
        assert answer["status"] == "insufficient_evidence"
        assert "graph" not in answer
        assert (
            client.post(
                f"/v1/snapshots/{seed.snapshot_id}/family",
                json={"character_id": "phil-mitchell", "direction": "ancestors"},
            ).status_code
            == 503
        )


def test_graph_session_retains_explicit_anchor_without_inventing_a_relative_reference(
    database_url: str, family_batch: ClaimBatch, tmp_path: Path
) -> None:
    from fastapi.testclient import TestClient

    from ask_phil.api import create_app

    install_family(database_url, family_batch)
    app = create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/traces.db")
    with TestClient(app) as client:
        session = client.post("/v1/sessions").json()
        path = f"/v1/sessions/{session['session']['session_id']}"
        headers = {"Authorization": f"Bearer {session['session_token']}"}
        result = client.post(
            path + "/turns",
            headers=headers,
            json={
                "question": "Show Ben Mitchell's ancestry",
                "snapshot_id": family_batch.snapshot_id,
                "route": "graph",
                "graph": {"character_id": "ben-mitchell", "direction": "ancestors"},
            },
        )
        assert result.status_code == 200, result.text
        response = result.json()["response"]
        reference = response["conversation"]["reference"]
        assert reference["character_ids"] == ["ben-mitchell"]
        assert reference["followup_requires_name"] is True
        history = client.get(path, headers=headers).json()["history"]
        assert history[-1]["character_ids"] == []
        assert history[-1]["reference_barrier"] is True
        assert client.post(path + "/reset", headers=headers).status_code == 200
