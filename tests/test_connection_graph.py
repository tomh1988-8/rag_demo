import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import pytest
from starlette.types import ASGIApp

from ask_phil.claims import ClaimReview
from ask_phil.classified_facts import ContextClaim
from ask_phil.connection_graph import ConnectionGraph, ConnectionQuery
from ask_phil.event_graph import EventGraph
from ask_phil.evidence import SourceSnapshot
from ask_phil.family_graph import FamilyGraph
from ask_phil.parentage import ClaimBatch, ParentageClaim
from ask_phil.relationship_graph import RelationshipGraph
from ask_phil.relationships import RelationshipBatch, RelationshipClaim
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventClaim, EventReview

REFERENCE = json.loads(Path("data/references/connections-v1.json").read_bytes())


@pytest.fixture
def connection_snapshot(database_url: str) -> SourceSnapshot:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/connections-pilot-v1.json").read_bytes()
    )
    reference = json.loads(Path("data/references/connections-v1.json").read_bytes())
    EvidenceStore(database_url).load(snapshot)
    common = dict(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=reference["catalogue"],
        extractor="retained-reviewed-reference-composition",
    )
    family = ClaimBatch(**common, claims=reference["family_claims"])
    relationships = RelationshipBatch(**common, claims=reference["relationship_claims"])
    events = EventBatch(
        **common,
        claims=reference["event_claims"],
        context_claims=reference["context_claims"],
    )

    def supported(claims: Sequence[ParentageClaim | RelationshipClaim]) -> tuple[ClaimReview, ...]:
        return tuple(
            ClaimReview(
                claim_id=c.claim_id,
                claim_sha256=c.fingerprint,
                verdict="supported",
                reviewer="retained-source-reference",
                note="Exact assertion and source span retained from the reviewed reference.",
            )
            for c in claims
        )

    FamilyGraph(database_url).install(family, supported(family.claims))
    RelationshipGraph(database_url).install(relationships, supported(relationships.claims))
    event_claims: tuple[EventClaim | ContextClaim, ...] = (*events.claims, *events.context_claims)
    EventGraph(database_url).install(
        events,
        tuple(
            EventReview(
                claim_id=c.claim_id,
                claim_sha256=c.fingerprint,
                verdict="supported",
                reviewer="retained-source-reference",
                note="Exact assertion and source span retained from the reviewed reference.",
                narrative_commission=getattr(c, "event_type", None) == "commission",
            )
            for c in event_claims
        ),
    )
    return snapshot


def test_biological_connection_derives_grandparent_from_directed_steps(
    database_url: str, connection_snapshot: SourceSnapshot
) -> None:
    result = ConnectionGraph(database_url).query(
        connection_snapshot.snapshot_id,
        ConnectionQuery(
            kind="connection",
            character_id="peggy-mitchell",
            target_id="ben-mitchell",
            max_depth=2,
        ),
    )
    assert result.status == "found"
    assert {p.characters for p in result.paths} == {
        ("peggy-mitchell", "phil-mitchell", "ben-mitchell")
    }
    path = result.paths[0]
    assert path.meaning == "biological_grandparent"
    assert [s.direction for s in path.steps] == ["parent_to_child", "parent_to_child"]
    assert {e.evidence_id for s in path.steps for e in s.evidence} == {
        "family-peggy-phil",
        "family-ben-birth",
    }
    assert result.snapshot_sha256 == connection_snapshot.fingerprint


def test_social_connection_keeps_adoption_and_historical_direction(
    database_url: str, connection_snapshot: SourceSnapshot
) -> None:
    result = ConnectionGraph(database_url).query(
        connection_snapshot.snapshot_id,
        ConnectionQuery(
            kind="connection", character_id="sharon-watts", target_id="den-watts", max_depth=1
        ),
    )
    assert result.status == "found"
    assert len(result.paths) == 1
    path = result.paths[0]
    assert path.meaning == "connection"
    step = path.steps[0].model_dump()
    assert step["direction"] == "object_to_subject"
    assert step["claim"]["relation"] == "adoptive_parent"
    assert step["claim"]["subject_id"] == "den-watts"
    assert step["claim"]["status"] == "unknown"
    assert step["claim"]["evidence"][0]["evidence_id"] == "history-den-adoption"


def test_shared_incident_preserves_conviction_and_commission_as_distinct_roles(
    database_url: str, connection_snapshot: SourceSnapshot
) -> None:
    result = ConnectionGraph(database_url).query(
        connection_snapshot.snapshot_id,
        ConnectionQuery(
            kind="connection", character_id="max-branning", target_id="bobby-beale", max_depth=1
        ),
    )
    assert result.status == "found"
    assert len(result.paths) == 1
    path = result.paths[0]
    assert path.meaning == "connection"
    step = path.steps[0].model_dump()
    assert step["kind"] == "shared_event" and step["event_id"] == "lucy-murder"
    assert {
        (c["event_type"], p["character_id"], p["role"])
        for c in step["claims"]
        for p in c["participants"]
        if c["event_type"] in {"commission", "conviction"}
    } == {
        ("commission", "bobby-beale", "perpetrator"),
        ("commission", "lucy-beale", "victim"),
        ("conviction", "max-branning", "convicted"),
    }


@pytest.mark.parametrize("case", REFERENCE["cases"], ids=lambda c: c["case_id"])
def test_reviewed_connection_cases_allow_supported_alternatives(
    database_url: str, connection_snapshot: SourceSnapshot, case: dict[str, Any]
) -> None:
    query = ConnectionQuery.model_validate(
        {"kind": "connection", **{k: case[k] for k in ("character_id", "target_id", "max_depth")}}
    )
    result = ConnectionGraph(database_url).query(connection_snapshot.snapshot_id, query)
    assert result.status == case["status"]
    actual = {p.characters for p in result.paths}
    allowed = {tuple(p) for p in case["acceptable_paths"]}
    assert actual <= allowed
    if case["status"] == "found":
        assert actual
    if case.get("require_all_alternatives"):
        assert actual == allowed
    for path in result.paths:
        assert len(set(path.characters)) == len(path.characters)
        assert all(e.quote for s in path.steps for e in s.evidence)


def test_expansion_and_result_limits_are_visible(
    database_url: str, connection_snapshot: SourceSnapshot
) -> None:
    graph = ConnectionGraph(database_url)
    query = ConnectionQuery(
        kind="connection", character_id="ben-mitchell", target_id="kathy-beale", max_depth=2
    )
    limited = graph.query(
        connection_snapshot.snapshot_id, query.model_copy(update={"max_paths": 1})
    )
    assert limited.status == "truncated" and len(limited.paths) == 1
    stopped = graph.query(
        connection_snapshot.snapshot_id, query.model_copy(update={"max_expansions": 1})
    )
    assert stopped.status == "truncated"
    assert stopped.expansion_limit_reached is True and stopped.examined_paths == 1


def test_connection_answer_exposes_typed_path_citations_and_actual_trace(
    database_url: str, connection_snapshot: SourceSnapshot, tmp_path: Path
) -> None:
    from fastapi.testclient import TestClient
    from mlflow import MlflowClient

    from ask_phil.api import create_app

    tracking_uri = f"sqlite:///{tmp_path}/connections.db"
    query = dict(kind="connection", character_id="sharon-watts", target_id="den-watts", max_depth=1)
    with TestClient(create_app(database_url, tracking_uri=tracking_uri)) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": connection_snapshot.snapshot_id,
                "question": "How are Sharon Watts and Den Watts connected?",
                "route": "graph",
                "graph": query,
            },
        )
        assert response.status_code == 200, response.text
        receipt = response.json()
        answer = receipt["response"]
        assert answer["route_override"] is True and answer["status"] == "partial"
        assert "adoptive parent" in answer["answer"]
        assert "status unknown" in answer["answer"]
        assert answer["graph"]["paths"][0]["meaning"] == "connection"
        assert answer["snapshot_sha256"] == connection_snapshot.fingerprint
        assert answer["execution"]["model_calls"] == 0 and answer["execution"]["tool_calls"] == 1
        assert {c["evidence_id"] for c in answer["citations"]} == {"history-den-adoption"}
        for citation in answer["citations"]:
            assert (
                client.get(citation["resolve_path"]).json()["matches"][0]["text"]
                == citation["text"]
            )
        typed = client.post(
            f"/v1/snapshots/{connection_snapshot.snapshot_id}/connections", json=query
        )
        assert typed.status_code == 200 and typed.json() == answer["graph"]
        trace = MlflowClient(tracking_uri=tracking_uri).get_trace(answer["trace_id"], flush=True)
        assert trace is not None
        assert next(s.outputs for s in trace.data.spans if s.name == "graph") == answer
        assert (
            next(s.outputs for s in trace.data.spans if s.name == "connection_graph")
            == answer["graph"]
        )
        assert (
            client.get(
                f"/v1/responses/{answer['response_id']}",
                headers={"Authorization": f"Bearer {receipt['read_token']}"},
            ).json()
            == answer
        )


def test_connection_cli_returns_supported_steps_and_explicit_query(
    database_url: str,
    connection_snapshot: SourceSnapshot,
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    from ask_phil.api import create_app

    with http_server(create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/cli.db")) as url:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "--api-url",
                url,
                "ask",
                "How are Peggy and Ben connected?",
                "--snapshot",
                connection_snapshot.snapshot_id,
                "--route",
                "graph",
                "--character",
                "peggy-mitchell",
                "--connect-to",
                "ben-mitchell",
                "--depth",
                "2",
                "--max-paths",
                "2",
                "--max-expansions",
                "50",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "NO_PROXY": "127.0.0.1"},
        )
    assert completed.returncode == 0, completed.stderr
    answer = json.loads(completed.stdout)["response"]
    assert answer["graph"]["query"]["max_expansions"] == 50
    assert answer["graph"]["paths"][0]["meaning"] == "biological_grandparent"
    assert "biological grandparent" in answer["answer"]
    assert {c["evidence_id"] for c in answer["citations"]} == {
        "family-ben-birth",
        "family-peggy-phil",
    }


def test_connection_without_family_projection_uses_only_available_reviewed_incidents(
    database_url: str,
) -> None:
    from test_event_claims import reference_batch

    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    EventGraph(database_url).install(batch, reviews)
    result = ConnectionGraph(database_url).query(
        snapshot.snapshot_id,
        ConnectionQuery(
            kind="connection", character_id="max-branning", target_id="bobby-beale", max_depth=1
        ),
    )
    assert result.status == "found" and len(result.paths) == 1
    assert result.graphs.family is None and result.graphs.relationship is None


def test_connection_scorer_separates_result_set_role_meaning_and_source_resolution(
    database_url: str, connection_snapshot: SourceSnapshot
) -> None:
    from ask_phil.connection_evaluation import ConnectionReference, score_connection
    from ask_phil.connection_graph import SharedEventStep
    from ask_phil.story_events import EventParticipant

    reference = ConnectionReference.model_validate(REFERENCE)
    case = next(c for c in reference.cases if c.case_id == "misleading-conviction")
    result = ConnectionGraph(database_url).query(connection_snapshot.snapshot_id, case.query)
    scores = score_connection(result, case, reference, connection_snapshot)
    assert scores.result_correct and scores.step_meanings_correct and scores.provenance_resolves
    step = result.paths[0].steps[0]
    assert isinstance(step, SharedEventStep)
    wrong_claims = tuple(
        c.model_copy(
            update={
                "participants": (EventParticipant(character_id="max-branning", role="perpetrator"),)
            }
        )
        if c.claim_id == "lucy-max-conviction"
        else c
        for c in step.claims
    )
    wrong_step = step.model_copy(update={"claims": wrong_claims})
    wrong_path = result.paths[0].model_copy(update={"steps": (wrong_step,)})
    wrong_result = result.model_copy(update={"paths": (wrong_path,)})
    wrong = score_connection(wrong_result, case, reference, connection_snapshot)
    assert wrong.result_correct is True
    assert wrong.step_meanings_correct is False
    assert wrong.provenance_resolves is True


def test_unreviewed_relationships_and_text_subjects_cannot_create_connections(
    database_url: str,
) -> None:
    from test_life_events import life_reference

    snapshot, events, reviews = life_reference()
    EvidenceStore(database_url).load(snapshot)
    EventGraph(database_url).install(events, reviews)
    tape = next(c for c in events.context_claims if c.kind == "unclassified")
    unchecked = RelationshipClaim(
        claim_id="unchecked-bridge",
        subject_id="grant-mitchell",
        object_id="kathy-beale",
        relation="marriage",
        episode_id="unsupported-episode",
        status="unknown",
        polarity="affirmed",
        certainty="certain",
        story_time="unknown",
        time_precision="unknown",
        after_claim_id=None,
        evidence=tape.evidence,
    )
    audit = RelationshipGraph(database_url).install(
        RelationshipBatch(
            snapshot_id=snapshot.snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            catalogue=events.catalogue,
            extractor="deliberately-unreviewed-counterexample",
            claims=(unchecked,),
        ),
        (),
    )
    assert audit.admission.decisions[0].status == "held"
    assert EventGraph(database_url).text_context(
        snapshot.snapshot_id,
        tuple(e.evidence_id for c in events.context_claims for e in c.evidence),
    )
    graph = ConnectionGraph(database_url)
    for origin, target in (
        ("grant-mitchell", "kathy-beale"),  # Held claim and text-only co-appearance.
        ("phil-mitchell", "peggy-mitchell"),  # Shared theme and pregnancy do not add parentage.
        ("ian-beale", "lucy-beale"),  # Mention in a death passage is not an event role.
        ("pat-butcher", "peggy-mitchell"),  # A hallucination is not physical presence.
    ):
        result = graph.query(
            snapshot.snapshot_id,
            ConnectionQuery(kind="connection", character_id=origin, target_id=target),
        )
        assert result.status == "empty" and result.paths == ()


def test_connection_limits_abstain_without_truncating_evidence_or_bypassing_authority(
    database_url: str, connection_snapshot: SourceSnapshot, tmp_path: Path
) -> None:
    from fastapi.testclient import TestClient

    from ask_phil.api import create_app
    from ask_phil.execution import ExecutionLimits

    query = dict(kind="connection", character_id="peggy-mitchell", target_id="bobby-beale")
    for name, limits, reason in (
        ("context", ExecutionLimits(context_bytes=2), "context_limit"),
        (
            "authority",
            ExecutionLimits(capabilities=("family_graph", "event_graph")),
            "capability_denied",
        ),
    ):
        with TestClient(
            create_app(
                database_url,
                tracking_uri=f"sqlite:///{tmp_path}/{name}.db",
                execution_limits=limits,
            )
        ) as client:
            response = client.post(
                "/v1/answers",
                json={
                    "snapshot_id": connection_snapshot.snapshot_id,
                    "question": "Trace this connection",
                    "route": "graph",
                    "graph": query,
                },
            )
            assert response.status_code == 200
            answer = response.json()["response"]
            assert answer["status"] == "insufficient_evidence"
            assert answer["execution"]["stop_reason"] == reason
            assert answer["citations"] == [] and "graph" not in answer
            if name == "authority":
                assert (
                    client.post(
                        f"/v1/snapshots/{connection_snapshot.snapshot_id}/connections", json=query
                    ).status_code
                    == 503
                )


def test_connection_uses_published_review_and_explains_held_dispute(
    database_url: str,
    tmp_path: Path,
) -> None:
    from fastapi.testclient import TestClient
    from llama_index.core.embeddings import MockEmbedding
    from test_parentage import reference_batch

    from ask_phil.api import create_app
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest
    from ask_phil.publications import PublicationStore

    snapshot, batch, reviews = reference_batch()
    batch = batch.model_copy(update={"claims": (batch.claims[0],)})
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(batch, (reviews[0],))
    reviewer = KnowledgeReview(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
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
                        "note": "Synthetic unresolved-review regression; not a canon dispute.",
                    }
                ),
            ),
        )
    )
    publication = PublicationStore(database_url).active()
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/review.db")
    ) as client:
        response = client.post(
            "/v1/answers",
            json={
                "question": "How are Phil and Ben connected?",
                "route": "graph",
                "graph": {
                    "kind": "connection",
                    "character_id": "phil-mitchell",
                    "target_id": "ben-mitchell",
                },
            },
        )
        assert response.status_code == 200, response.text
        answer = response.json()["response"]
        assert answer["graph"]["paths"] == []
        assert answer["status"] == "partial"
        assert "Unresolved source disagreement" in answer["answer"]
        assert "no established connection" in answer["answer"]
        assert answer["publication"]["compatibility_id"] == publication.compatibility_id
        assert publication.manifest.graphs is not None
        assert answer["graph"]["graphs"] == publication.manifest.graphs.model_dump()
        assert answer["review_notices"][0]["claim_id"] == "phil-ben"
        assert answer["citations"]
    legacy_manifest = publication.manifest.model_copy(update={"graphs": None})
    legacy = publication.model_copy(
        update={
            "manifest": legacy_manifest,
            "compatibility_id": legacy_manifest.fingerprint,
        }
    )
    result = ConnectionGraph(database_url).query(
        legacy_manifest.snapshot_id,
        ConnectionQuery(kind="connection", character_id="phil-mitchell", target_id="ben-mitchell"),
        publication=legacy,
    )
    assert result.status == "empty"


def test_biological_history_cannot_restore_parentage_held_by_family_admission(
    database_url: str,
) -> None:
    from test_parentage import reference_batch

    snapshot, original, _ = reference_batch()
    # Deliberately unsupported reviewed assertions expose the domain cycle guard;
    # they are admission counterexamples, not new source/canon reference facts.
    first = original.claims[0]
    reverse = first.model_copy(
        update={
            "claim_id": "synthetic-reverse-parent",
            "parent_id": "ben-mitchell",
            "child_id": "phil-mitchell",
        }
    )
    family_batch = original.model_copy(update={"claims": (first, reverse)})
    EvidenceStore(database_url).load(snapshot)
    reviews = tuple(
        ClaimReview(
            claim_id=c.claim_id,
            claim_sha256=c.fingerprint,
            verdict="supported",
            reviewer="synthetic-cycle-counterexample",
            note="Deliberately unsupported cycle regression, not a canon assertion.",
        )
        for c in family_batch.claims
    )
    family = FamilyGraph(database_url).install(family_batch, reviews)
    assert all(d.status == "held" and "cycle" in d.reasons for d in family.admission.decisions)
    history_claims = tuple(
        RelationshipClaim(
            claim_id=c.claim_id,
            subject_id=c.parent_id,
            object_id=c.child_id,
            relation="biological_parent",
            episode_id=c.claim_id,
            status="unknown",
            polarity="affirmed",
            certainty="certain",
            story_time="unknown",
            time_precision="unknown",
            after_claim_id=None,
            evidence=c.evidence,
        )
        for c in family_batch.claims
    )
    history = RelationshipGraph(database_url).install(
        RelationshipBatch(
            snapshot_id=snapshot.snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            catalogue=original.catalogue,
            extractor="synthetic-cycle-counterexample",
            claims=history_claims,
        ),
        tuple(
            r.model_copy(update={"claim_sha256": c.fingerprint})
            for r, c in zip(reviews, history_claims, strict=True)
        ),
    )
    assert all(d.status == "admitted" for d in history.admission.decisions)
    result = ConnectionGraph(database_url).query(
        snapshot.snapshot_id,
        ConnectionQuery(
            kind="connection",
            character_id="phil-mitchell",
            target_id="ben-mitchell",
            max_depth=1,
        ),
    )
    assert result.status == "empty" and result.paths == ()
