import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.types import ASGIApp
from test_relationship_claims import reference_batch, support_reviews

from ask_phil.api import create_app
from ask_phil.evidence import Passage
from ask_phil.execution import ExecutionLimits
from ask_phil.family_graph import FamilyGraph, FamilyQuery
from ask_phil.parentage import ClaimBatch, ClaimReview
from ask_phil.relationship_graph import RelationshipGraph, RelationshipQuery
from ask_phil.storage import EvidenceStore


def test_history_keeps_repeated_episodes_and_social_edges_out_of_ancestry(
    database_url: str,
) -> None:
    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    graph = RelationshipGraph(database_url)
    audit = graph.install(batch, reviews)
    result = graph.query(
        snapshot.snapshot_id,
        RelationshipQuery(
            kind="relationship_history", character_id="kat-slater", partner_id="alfie-moon"
        ),
    )
    assert result.status == "found"
    assert {c.relation for c in result.claims} == {"marriage", "remarriage"}
    assert len({c.episode_id for c in result.claims}) == 2
    assert all(c.time_precision == "relative" for c in result.claims)
    assert result.graph_sha256 == audit.graph_sha256
    adoption = graph.query(
        snapshot.snapshot_id,
        RelationshipQuery(
            kind="relationship_history", character_id="sharon-watts", partner_id="den-watts"
        ),
    )
    assert [(c.subject_id, c.object_id, c.relation) for c in adoption.claims] == [
        ("den-watts", "sharon-watts", "adoptive_parent")
    ]
    parentage = ClaimBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=batch.catalogue,
        claims=(),
        extractor="empty-biological-reference",
    )
    FamilyGraph(database_url).install(parentage, tuple[ClaimReview, ...]())
    ancestry = FamilyGraph(database_url).query(
        snapshot.snapshot_id, FamilyQuery(character_id="sharon-watts", direction="ancestors")
    )
    assert ancestry.status == "empty"
    assert ancestry.paths == ()
    assert graph.audit(snapshot.snapshot_id) == audit


pytestmark = pytest.mark.integration


def test_a_self_pair_does_not_widen_into_all_partners() -> None:
    with pytest.raises(ValidationError):
        RelationshipQuery(
            kind="relationship_history", character_id="phil-mitchell", partner_id="phil-mitchell"
        )


def test_history_answers_are_typed_cited_and_saved_without_model_configuration(
    database_url: str, tmp_path: Path
) -> None:
    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    RelationshipGraph(database_url).install(batch, reviews)
    query = {
        "kind": "relationship_history",
        "character_id": "phil-mitchell",
        "partner_id": "kathy-beale",
    }
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/traces.db")
    ) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Explain Phil and Kathy's history",
                "route": "graph",
                "graph": query,
            },
        )
        assert response.status_code == 200, response.text
        receipt = response.json()
        answer = receipt["response"]
        assert answer["status"] == "partial"
        assert {c["relation"] for c in answer["graph"]["claims"]} == {
            "marriage",
            "separation",
            "reconciliation",
        }
        assert "divorced" not in answer["answer"]
        assert "unknown" in answer["answer"]
        assert answer["model_settings"] is None
        assert answer["execution"]["model_calls"] == 0
        assert answer["execution"]["tool_calls"] == 1
        assert len(answer["citations"]) == 4
        assert answer["answer"].count("Phil Mitchell married Kathy Beale") == 1
        for citation in answer["citations"]:
            assert client.get(citation["resolve_path"]).status_code == 200
        saved = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert saved.json() == answer
        typed = client.post(f"/v1/snapshots/{snapshot.snapshot_id}/relationships", json=query)
        assert typed.json() == answer["graph"]
        audit = client.get(f"/v1/snapshots/{snapshot.snapshot_id}/relationship-claims")
        assert len(audit.json()["batch"]["claims"]) == 13


def test_cli_uses_shared_api_for_relationship_histories(
    database_url: str,
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    RelationshipGraph(database_url).install(batch, reviews)
    with http_server(create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/cli.db")) as url:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "--api-url",
                url,
                "ask",
                "Explain Kat and Alfie's marriages",
                "--snapshot",
                snapshot.snapshot_id,
                "--route",
                "graph",
                "--history",
                "--character",
                "kat-slater",
                "--partner",
                "alfie-moon",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "NO_PROXY": "127.0.0.1"},
        )
    assert result.returncode == 0, result.stderr
    answer = json.loads(result.stdout)["response"]
    assert answer["route"] == "graph"
    assert "remarried" in answer["answer"]
    assert {c["relation"] for c in answer["graph"]["claims"]} == {"marriage", "remarriage"}


def test_bounds_and_unknown_characters_are_explicit(database_url: str) -> None:
    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    graph = RelationshipGraph(database_url)
    query = RelationshipQuery(kind="relationship_history", character_id="kat-slater", max_events=1)
    assert graph.query(snapshot.snapshot_id, query).status == "unavailable"
    graph.install(batch, reviews)
    limited = graph.query(snapshot.snapshot_id, query)
    assert limited.status == "truncated" and len(limited.claims) == 1
    unknown = graph.query(
        snapshot.snapshot_id, query.model_copy(update={"partner_id": "shane-richie"})
    )
    assert unknown.status == "unknown_character" and not unknown.claims
    absent = graph.query(snapshot.snapshot_id, query.model_copy(update={"partner_id": "den-watts"}))
    assert absent.status == "empty" and "does not prove" in absent.limitation


def test_synthetic_ward_statuses_and_held_claims_survive_storage(database_url: str) -> None:
    snapshot, original, _ = reference_batch()
    ward = original.claims[8].model_copy(
        update={
            "relation": "ward",
            "status": "current",
            "claim_id": "synthetic-ward",
        }
    )
    former = original.claims[9].model_copy(update={"status": "former"})
    held = original.claims[0].model_copy(update={"certainty": "uncertain"})
    batch = original.model_copy(
        update={"claims": (ward, former, held), "extractor": "synthetic-rules"}
    )
    EvidenceStore(database_url).load(snapshot)
    graph = RelationshipGraph(database_url)
    audit = graph.install(batch, support_reviews(batch))
    result = graph.query(
        snapshot.snapshot_id,
        RelationshipQuery(
            kind="relationship_history", character_id="sharon-watts", partner_id="den-watts"
        ),
    )
    assert [(c.relation, c.subject_id, c.object_id, c.status) for c in result.claims] == [
        ("ward", "den-watts", "sharon-watts", "current")
    ]
    assert len(audit.batch.claims) == 3
    assert [d.claim_id for d in audit.admission.decisions if d.status == "held"] == [held.claim_id]


def test_synthetic_ward_answer_preserves_guardian_role_and_labels_its_source(
    database_url: str, tmp_path: Path
) -> None:
    snapshot, original, _ = reference_batch()
    text = "Synthetic example: Den is Sharon's guardian; Sharon is his ward, not his adopted child."
    source = snapshot.source.model_copy(update={"support_status": "synthetic_fixture"})
    passage = Passage(
        evidence_id="synthetic-ward",
        text=text,
        start=0,
        end=len(text),
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        source=source,
    )
    snapshot = snapshot.model_copy(
        update={"snapshot_id": "synthetic-ward-v1", "source": source, "passages": (passage,)}
    )
    ward = original.claims[8].model_copy(
        update={
            "relation": "ward",
            "claim_id": "synthetic-ward",
            "status": "current",
            "story_time": "unknown",
            "time_precision": "unknown",
            "evidence": (
                original.claims[8]
                .evidence[0]
                .model_copy(
                    update={
                        "evidence_id": passage.evidence_id,
                        "start": 0,
                        "end": len(text),
                        "quote": text,
                    }
                ),
            ),
        }
    )
    batch = original.model_copy(
        update={
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "claims": (ward,),
            "extractor": "synthetic-example",
        }
    )
    EvidenceStore(database_url).load(snapshot)
    RelationshipGraph(database_url).install(batch, support_reviews(batch))
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/ward.db")
    ) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Explain the guardian and ward",
                "route": "graph",
                "graph": {"kind": "relationship_history", "character_id": "sharon-watts"},
            },
        )
    assert response.status_code == 200
    answer = response.json()["response"]["answer"]
    assert "synthetic" in answer.lower()
    assert "guardian of the ward Sharon Watts" in answer
    assert "status current in the captured account" in answer


@pytest.mark.parametrize(
    "limits,reason",
    [
        (ExecutionLimits(capabilities=()), "capability_denied"),
        (ExecutionLimits(tool_calls=0), "tool_call_limit"),
        (ExecutionLimits(context_bytes=2), "context_limit"),
    ],
)
def test_history_stops_are_saved_without_partial_claim_leakage(
    database_url: str, tmp_path: Path, limits: ExecutionLimits, reason: str
) -> None:
    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    RelationshipGraph(database_url).install(batch, reviews)
    with TestClient(
        create_app(
            database_url, tracking_uri=f"sqlite:///{tmp_path}/stops.db", execution_limits=limits
        )
    ) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "Explain the relationship history",
                "route": "graph",
                "graph": {"kind": "relationship_history", "character_id": "phil-mitchell"},
            },
        )
        assert response.status_code == 200
        receipt = response.json()
        answer = receipt["response"]
        assert answer["status"] == "insufficient_evidence" and answer["citations"] == []
        assert answer.get("graph") is None and answer["context"] == []
        assert answer["execution"]["stop_reason"] == reason
        assert answer["execution"]["model_calls"] == 0
        assert (
            client.get(
                f"/v1/responses/{answer['response_id']}",
                headers={
                    "Authorization": f"Bearer {receipt['read_token']}",
                },
            ).json()
            == answer
        )
