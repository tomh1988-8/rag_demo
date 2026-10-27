"""Atomic, immutable installation of typed projections from reviewed Claims."""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, cast, overload

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from pydantic import Field

from ask_phil.claims import ClaimEvidence, ClaimReview
from ask_phil.evidence import Fingerprint, Identifier, Record, SourceSnapshot
from ask_phil.execution import database_options
from ask_phil.parentage import AdmissionReport, ClaimBatch, admit_claims
from ask_phil.relationships import RelationshipAdmission, RelationshipBatch, admit_relationships
from ask_phil.security import require_credential_free
from ask_phil.storage import EvidenceStore, SnapshotConflict
from ask_phil.story_events import (
    LIFE_EVENT_TYPES,
    EventAdmission,
    EventBatch,
    EventReview,
    admit_events,
)


class FamilyEdge(Record):
    parent_id: Identifier
    child_id: Identifier
    claim_ids: tuple[Identifier, ...] = Field(min_length=1)
    evidence: tuple[ClaimEvidence, ...] = Field(min_length=1)


class FamilyAudit(Record):
    batch: ClaimBatch
    reviews: tuple[ClaimReview, ...]
    admission: AdmissionReport
    graph_sha256: Fingerprint


class RelationshipAudit(Record):
    batch: RelationshipBatch
    reviews: tuple[ClaimReview, ...]
    admission: RelationshipAdmission
    graph_sha256: Fingerprint


class EventAudit(Record):
    batch: EventBatch
    reviews: tuple[EventReview, ...]
    admission: EventAdmission
    graph_sha256: Fingerprint


type _Audit = FamilyAudit | RelationshipAudit | EventAudit


@dataclass(frozen=True)
class _Write:
    statement: str
    rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True)
class _Projection:
    kind: Literal["family", "relationship", "event"]
    audit: _Audit
    schema: str
    writes: tuple[_Write, ...]


def _fingerprint(
    version: str, batch: Record, report: Record, reviews: Sequence[ClaimReview]
) -> str:
    derivation = (
        batch.model_dump_json()
        + report.model_dump_json()
        + "".join(r.model_dump_json() for r in sorted(reviews, key=lambda r: r.claim_id))
    )
    return hashlib.sha256((version + ":" + derivation).encode()).hexdigest()


@overload
def install_projection(
    database_url: str, batch: ClaimBatch, reviews: tuple[ClaimReview, ...]
) -> FamilyAudit: ...


@overload
def install_projection(
    database_url: str, batch: RelationshipBatch, reviews: tuple[ClaimReview, ...]
) -> RelationshipAudit: ...


@overload
def install_projection(
    database_url: str, batch: EventBatch, reviews: tuple[EventReview, ...]
) -> EventAudit: ...


def install_projection(
    database_url: str,
    batch: ClaimBatch | RelationshipBatch | EventBatch,
    reviews: tuple[ClaimReview, ...],
) -> _Audit:
    """Retain the complete derivation and its projection, or leave neither installed."""
    snapshot = EvidenceStore(database_url).snapshot(batch.snapshot_id)
    if isinstance(batch, ClaimBatch):
        projection = _family(snapshot, batch, reviews)
    elif isinstance(batch, RelationshipBatch):
        projection = _relationships(snapshot, batch, reviews)
    else:
        projection = _events(snapshot, batch, cast(tuple[EventReview, ...], reviews))
    audit = projection.audit
    require_credential_free(audit.model_dump_json())
    lock = {"family": 728196, "relationship": 728197, "event": 728198}[projection.kind]
    with psycopg.connect(database_url, connect_timeout=5, options=database_options()) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (lock,))
        conn.execute(projection.schema)
        existing = conn.execute(
            sql.SQL("SELECT graph_sha256, document FROM {} WHERE snapshot_id=%s").format(
                sql.Identifier(projection.kind + "_projections")
            ),
            (batch.snapshot_id,),
        ).fetchone()
        if existing:
            previous = type(audit).model_validate(existing[1])
            if existing[0] != audit.graph_sha256 or previous.graph_sha256 != audit.graph_sha256:
                raise SnapshotConflict(
                    f"Snapshot already has a different immutable {projection.kind} graph."
                )
            return previous
        for write in projection.writes:
            for row in write.rows:
                conn.execute(write.statement, row)
    return audit


def _family(
    snapshot: SourceSnapshot, batch: ClaimBatch, reviews: tuple[ClaimReview, ...]
) -> _Projection:
    report = admit_claims(snapshot, batch, reviews)
    admitted = {d.claim_id for d in report.decisions if d.status == "admitted"}
    groups: dict[tuple[str, str], list[str]] = {}
    for claim in batch.claims:
        if claim.claim_id in admitted:
            groups.setdefault((claim.parent_id, claim.child_id), []).append(claim.claim_id)
    claims = {c.claim_id: c for c in batch.claims}
    edges = tuple(
        FamilyEdge(
            parent_id=parent,
            child_id=child,
            claim_ids=tuple(sorted(ids)),
            evidence=tuple(e for cid in sorted(ids) for e in claims[cid].evidence),
        )
        for (parent, child), ids in sorted(groups.items())
    )
    audit = FamilyAudit(
        batch=batch,
        reviews=reviews,
        admission=report,
        graph_sha256=_fingerprint("biological-sql-v1", batch, report, reviews),
    )
    return _Projection(
        "family",
        audit,
        """CREATE TABLE IF NOT EXISTS parentage_batches (
            batch_sha256 text PRIMARY KEY,
            snapshot_id text NOT NULL REFERENCES source_snapshots(snapshot_id),
            document jsonb NOT NULL);
        CREATE TABLE IF NOT EXISTS parentage_claims (
            batch_sha256 text REFERENCES parentage_batches(batch_sha256),
            claim_id text NOT NULL, document jsonb NOT NULL,
            PRIMARY KEY(batch_sha256, claim_id));
        CREATE TABLE IF NOT EXISTS family_projections (
            snapshot_id text PRIMARY KEY REFERENCES source_snapshots(snapshot_id),
            graph_sha256 text NOT NULL UNIQUE,
            batch_sha256 text NOT NULL REFERENCES parentage_batches(batch_sha256),
            document jsonb NOT NULL);
        CREATE TABLE IF NOT EXISTS family_edges (
            graph_sha256 text REFERENCES family_projections(graph_sha256),
            parent_id text NOT NULL, child_id text NOT NULL, document jsonb NOT NULL,
            PRIMARY KEY(graph_sha256, parent_id, child_id));
        CREATE INDEX IF NOT EXISTS family_children ON family_edges(graph_sha256, child_id);""",
        (
            _Write(
                "INSERT INTO parentage_batches VALUES (%s,%s,%s)",
                ((batch.fingerprint, batch.snapshot_id, Jsonb(batch.model_dump(mode="json"))),),
            ),
            _Write(
                "INSERT INTO parentage_claims VALUES (%s,%s,%s)",
                tuple(
                    (batch.fingerprint, c.claim_id, Jsonb(c.model_dump(mode="json")))
                    for c in batch.claims
                ),
            ),
            _Write(
                "INSERT INTO family_projections VALUES (%s,%s,%s,%s)",
                (
                    (
                        batch.snapshot_id,
                        audit.graph_sha256,
                        batch.fingerprint,
                        Jsonb(audit.model_dump(mode="json")),
                    ),
                ),
            ),
            _Write(
                "INSERT INTO family_edges VALUES (%s,%s,%s,%s)",
                tuple(
                    (
                        audit.graph_sha256,
                        edge.parent_id,
                        edge.child_id,
                        Jsonb(edge.model_dump(mode="json")),
                    )
                    for edge in edges
                ),
            ),
        ),
    )


def _relationships(
    snapshot: SourceSnapshot, batch: RelationshipBatch, reviews: tuple[ClaimReview, ...]
) -> _Projection:
    report = admit_relationships(snapshot, batch, reviews)
    audit = RelationshipAudit(
        batch=batch,
        reviews=reviews,
        admission=report,
        graph_sha256=_fingerprint("relationship-history-sql-v1", batch, report, reviews),
    )
    admitted = {d.claim_id for d in report.decisions if d.status == "admitted"}
    return _Projection(
        "relationship",
        audit,
        """CREATE TABLE IF NOT EXISTS relationship_projections (
            snapshot_id text PRIMARY KEY REFERENCES source_snapshots(snapshot_id),
            graph_sha256 text NOT NULL UNIQUE, document jsonb NOT NULL);
        CREATE TABLE IF NOT EXISTS relationship_assertions (
            graph_sha256 text REFERENCES relationship_projections(graph_sha256),
            claim_id text NOT NULL, subject_id text NOT NULL, object_id text NOT NULL,
            document jsonb NOT NULL, PRIMARY KEY(graph_sha256, claim_id));
        CREATE INDEX IF NOT EXISTS relationship_subjects
            ON relationship_assertions(graph_sha256, subject_id);
        CREATE INDEX IF NOT EXISTS relationship_objects
            ON relationship_assertions(graph_sha256, object_id);""",
        (
            _Write(
                "INSERT INTO relationship_projections VALUES (%s,%s,%s)",
                ((batch.snapshot_id, audit.graph_sha256, Jsonb(audit.model_dump(mode="json"))),),
            ),
            _Write(
                "INSERT INTO relationship_assertions VALUES (%s,%s,%s,%s,%s)",
                tuple(
                    (
                        audit.graph_sha256,
                        c.claim_id,
                        c.subject_id,
                        c.object_id,
                        Jsonb(c.model_dump(mode="json")),
                    )
                    for c in batch.claims
                    if c.claim_id in admitted
                ),
            ),
        ),
    )


def _events(
    snapshot: SourceSnapshot, batch: EventBatch, reviews: tuple[EventReview, ...]
) -> _Projection:
    report = admit_events(snapshot, batch, reviews)
    version = (
        "story-events-sql-v2"
        if batch.context_claims or any(c.event_type in LIFE_EVENT_TYPES for c in batch.claims)
        else "crime-justice-sql-v1"
    )
    audit = EventAudit(
        batch=batch,
        reviews=reviews,
        admission=report,
        graph_sha256=_fingerprint(version, batch, report, reviews),
    )
    admitted = {d.claim_id for d in report.decisions if d.status == "admitted"}
    return _Projection(
        "event",
        audit,
        """CREATE TABLE IF NOT EXISTS event_projections (
            snapshot_id text PRIMARY KEY REFERENCES source_snapshots(snapshot_id),
            graph_sha256 text NOT NULL UNIQUE, document jsonb NOT NULL);
        CREATE TABLE IF NOT EXISTS event_assertions (
            graph_sha256 text REFERENCES event_projections(graph_sha256),
            claim_id text NOT NULL, event_id text NOT NULL,
            document jsonb NOT NULL, PRIMARY KEY(graph_sha256, claim_id));
        CREATE TABLE IF NOT EXISTS event_participants (
            graph_sha256 text REFERENCES event_projections(graph_sha256),
            event_id text NOT NULL, character_id text NOT NULL,
            PRIMARY KEY(graph_sha256, event_id, character_id));""",
        (
            _Write(
                "INSERT INTO event_projections VALUES (%s,%s,%s)",
                ((batch.snapshot_id, audit.graph_sha256, Jsonb(audit.model_dump(mode="json"))),),
            ),
            _Write(
                "INSERT INTO event_assertions VALUES (%s,%s,%s,%s)",
                tuple(
                    (audit.graph_sha256, c.claim_id, c.event_id, Jsonb(c.model_dump(mode="json")))
                    for c in batch.claims
                    if c.claim_id in admitted
                ),
            ),
            _Write(
                "INSERT INTO event_participants VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                tuple(
                    (audit.graph_sha256, c.event_id, p.character_id)
                    for c in batch.claims
                    if c.claim_id in admitted
                    for p in c.participants
                ),
            ),
        ),
    )
