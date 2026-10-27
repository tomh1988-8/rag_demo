"""Installation invariants observed through each typed graph's existing interface."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Barrier

import psycopg
import pytest
from psycopg import sql
from test_event_claims import reference_batch as event_reference
from test_life_events import life_reference
from test_parentage import reference_batch as family_reference
from test_relationship_claims import reference_batch as relationship_reference

from ask_phil.event_graph import EventAudit, EventGraph, EventQuery
from ask_phil.evidence import SourceSnapshot
from ask_phil.family_graph import FamilyAudit, FamilyGraph, FamilyQuery
from ask_phil.parentage import ClaimBatch, ClaimReview
from ask_phil.relationship_graph import RelationshipAudit, RelationshipGraph, RelationshipQuery
from ask_phil.relationships import RelationshipBatch
from ask_phil.storage import EvidenceStore, SnapshotConflict
from ask_phil.story_events import EventBatch, EventReview

pytestmark = pytest.mark.integration

type Batch = ClaimBatch | RelationshipBatch | EventBatch
type Audit = FamilyAudit | RelationshipAudit | EventAudit


@dataclass(frozen=True)
class ProjectionCase:
    snapshot: SourceSnapshot
    batch: Batch
    reviews: tuple[ClaimReview, ...]
    graph: FamilyGraph | RelationshipGraph | EventGraph
    fault_table: str

    def install(self, batch: Batch, *, reverse_reviews: bool = False) -> Audit:
        reviews = tuple(reversed(self.reviews)) if reverse_reviews else self.reviews
        if isinstance(batch, ClaimBatch):
            assert isinstance(self.graph, FamilyGraph)
            return self.graph.install(batch, reviews)
        if isinstance(batch, RelationshipBatch):
            assert isinstance(self.graph, RelationshipGraph)
            return self.graph.install(batch, reviews)
        assert isinstance(self.graph, EventGraph)
        return self.graph.install(
            batch, tuple(EventReview.model_validate(r.model_dump()) for r in reviews)
        )

    def query_status(self, snapshot_id: str) -> str:
        if isinstance(self.graph, FamilyGraph):
            return self.graph.query(
                snapshot_id, FamilyQuery(character_id="ben-mitchell", direction="ancestors")
            ).status
        if isinstance(self.graph, RelationshipGraph):
            return self.graph.query(
                snapshot_id,
                RelationshipQuery(kind="relationship_history", character_id="kat-slater"),
            ).status
        assert isinstance(self.batch, EventBatch)
        first = self.batch.claims[0]
        return self.graph.query(
            snapshot_id,
            EventQuery(
                kind="life_events" if first.event_type == "pregnancy" else "crime_history",
                character_id=first.participants[0].character_id,
                max_events=20,
            ),
        ).status


@pytest.fixture(params=["family", "relationship", "event", "life"])
def projection_case(request: pytest.FixtureRequest, database_url: str) -> ProjectionCase:
    if request.param == "relationship":
        snapshot, relationships, reviews = relationship_reference()
        case = ProjectionCase(
            snapshot,
            relationships,
            reviews,
            RelationshipGraph(database_url),
            "relationship_assertions",
        )
    elif request.param in {"event", "life"}:
        snapshot, events, event_reviews = (
            event_reference() if request.param == "event" else life_reference()
        )
        case = ProjectionCase(
            snapshot, events, event_reviews, EventGraph(database_url), "event_participants"
        )
    else:
        snapshot, family, reviews = family_reference()
        case = ProjectionCase(snapshot, family, reviews, FamilyGraph(database_url), "family_edges")
    EvidenceStore(database_url).load(case.snapshot)
    return case


def test_concurrent_replay_retains_one_immutable_audit(projection_case: ProjectionCase) -> None:
    case = projection_case
    ready = Barrier(2)

    def install(reverse: bool) -> Audit:
        ready.wait(timeout=10)
        return case.install(case.batch, reverse_reviews=reverse)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = tuple(pool.map(install, (False, True)))
    assert first == second == case.graph.audit(case.snapshot.snapshot_id)
    assert case.query_status(case.snapshot.snapshot_id) == "found"
    with pytest.raises(SnapshotConflict):
        case.install(case.batch.model_copy(update={"extractor": "a-different-extraction"}))
    assert case.graph.audit(case.snapshot.snapshot_id) == first


def test_failed_projection_write_retains_prior_graph_and_can_retry(
    projection_case: ProjectionCase, database_url: str
) -> None:
    case = projection_case
    original = case.install(case.batch)
    candidate = case.snapshot.model_copy(
        update={"snapshot_id": case.snapshot.snapshot_id + "-retry"}
    )
    EvidenceStore(database_url).load(candidate)
    batch = case.batch.model_copy(
        update={"snapshot_id": candidate.snapshot_id, "snapshot_sha256": candidate.fingerprint}
    )
    # The external database rejects a projection row after the audit insert.
    # Observe rollback through the graph interface, without inspecting its SQL state.
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            sql.SQL("ALTER TABLE {} ADD CONSTRAINT reject_new_rows CHECK (false) NOT VALID").format(
                sql.Identifier(case.fault_table)
            )
        )
        try:
            with pytest.raises(psycopg.errors.CheckViolation):
                case.install(batch)
            assert case.graph.audit(candidate.snapshot_id) is None
            assert case.query_status(candidate.snapshot_id) == "unavailable"
            assert case.graph.audit(case.snapshot.snapshot_id) == original
            assert case.query_status(case.snapshot.snapshot_id) == "found"
        finally:
            conn.execute(
                sql.SQL("ALTER TABLE {} DROP CONSTRAINT reject_new_rows").format(
                    sql.Identifier(case.fault_table)
                )
            )
    retried = case.install(batch)
    assert case.graph.audit(candidate.snapshot_id) == retried
    assert case.query_status(candidate.snapshot_id) == "found"
