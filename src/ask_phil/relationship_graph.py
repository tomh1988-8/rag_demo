"""Immutable admitted relationship assertions behind a bounded read-only SQL query."""

import hashlib
from typing import Literal, Self

import psycopg
from psycopg.types.json import Jsonb
from pydantic import Field, model_validator

from ask_phil.evidence import Fingerprint, Identifier, Record
from ask_phil.execution import current_execution, database_options, read_options
from ask_phil.parentage import ClaimReview
from ask_phil.relationships import (
    HISTORY_LIMITATION,
    RelationshipAdmission,
    RelationshipBatch,
    RelationshipClaim,
    admit_relationships,
)
from ask_phil.security import require_credential_free
from ask_phil.storage import EvidenceStore, SnapshotConflict


class RelationshipQuery(Record):
    kind: Literal["relationship_history"]
    character_id: Identifier
    partner_id: Identifier | None = None
    max_events: int = Field(default=20, ge=1, le=50)

    @model_validator(mode="after")
    def distinct_participants(self) -> Self:
        if self.partner_id == self.character_id:
            raise ValueError("Relationship history requires distinct participants.")
        return self


class RelationshipResult(Record):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    graph_sha256: Fingerprint | None = None
    query: RelationshipQuery
    status: Literal["found", "empty", "truncated", "unavailable", "unknown_character"]
    claims: tuple[RelationshipClaim, ...] = ()
    names: dict[str, str] = Field(default_factory=dict)
    limitation: str = HISTORY_LIMITATION


class RelationshipAudit(Record):
    batch: RelationshipBatch
    reviews: tuple[ClaimReview, ...]
    admission: RelationshipAdmission
    graph_sha256: Fingerprint


class RelationshipGraph:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def install(
        self, batch: RelationshipBatch, reviews: tuple[ClaimReview, ...]
    ) -> RelationshipAudit:
        """Maintainer-only installation. Preserve candidates and review outcomes atomically."""
        snapshot = EvidenceStore(self.database_url).snapshot(batch.snapshot_id)
        report = admit_relationships(snapshot, batch, reviews)
        derivation = (
            batch.model_dump_json()
            + report.model_dump_json()
            + "".join(r.model_dump_json() for r in sorted(reviews, key=lambda r: r.claim_id))
        )
        audit = RelationshipAudit(
            batch=batch,
            reviews=reviews,
            admission=report,
            graph_sha256=hashlib.sha256(
                ("relationship-history-sql-v1:" + derivation).encode()
            ).hexdigest(),
        )
        require_credential_free(audit.model_dump_json())
        with psycopg.connect(
            self.database_url, connect_timeout=5, options=database_options()
        ) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728197)")
            conn.execute("""CREATE TABLE IF NOT EXISTS relationship_projections (
                snapshot_id text PRIMARY KEY REFERENCES source_snapshots(snapshot_id),
                graph_sha256 text NOT NULL UNIQUE, document jsonb NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS relationship_assertions (
                graph_sha256 text REFERENCES relationship_projections(graph_sha256),
                claim_id text NOT NULL, subject_id text NOT NULL, object_id text NOT NULL,
                document jsonb NOT NULL, PRIMARY KEY(graph_sha256, claim_id))""")
            conn.execute("""CREATE INDEX IF NOT EXISTS relationship_subjects
                ON relationship_assertions(graph_sha256, subject_id)""")
            conn.execute("""CREATE INDEX IF NOT EXISTS relationship_objects
                ON relationship_assertions(graph_sha256, object_id)""")
            existing = conn.execute(
                "SELECT document FROM relationship_projections WHERE snapshot_id=%s",
                (batch.snapshot_id,),
            ).fetchone()
            if existing:
                previous = RelationshipAudit.model_validate(existing[0])
                if previous.graph_sha256 != audit.graph_sha256:
                    raise SnapshotConflict(
                        "Snapshot already has a different immutable relationship graph."
                    )
                return previous
            conn.execute(
                "INSERT INTO relationship_projections VALUES (%s,%s,%s)",
                (batch.snapshot_id, audit.graph_sha256, Jsonb(audit.model_dump(mode="json"))),
            )
            admitted = {d.claim_id for d in report.decisions if d.status == "admitted"}
            for claim in batch.claims:
                if claim.claim_id in admitted:
                    conn.execute(
                        "INSERT INTO relationship_assertions VALUES (%s,%s,%s,%s,%s)",
                        (
                            audit.graph_sha256,
                            claim.claim_id,
                            claim.subject_id,
                            claim.object_id,
                            Jsonb(claim.model_dump(mode="json")),
                        ),
                    )
        return audit

    @staticmethod
    def _audit(
        conn: psycopg.Connection[tuple[object, ...]], snapshot_id: str
    ) -> RelationshipAudit | None:
        if conn.execute("SELECT to_regclass('relationship_projections')").fetchone() == (None,):
            return None
        row = conn.execute(
            "SELECT document FROM relationship_projections WHERE snapshot_id=%s", (snapshot_id,)
        ).fetchone()
        return RelationshipAudit.model_validate(row[0]) if row else None

    def audit(self, snapshot_id: str) -> RelationshipAudit | None:
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            return self._audit(conn, snapshot_id)

    def query(self, snapshot_id: str, query: RelationshipQuery) -> RelationshipResult:
        snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
        budget = current_execution.get()
        if budget:
            budget.tool_call("family_graph")
        result = RelationshipResult(
            snapshot_id=snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            query=query,
            status="unavailable",
        )
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            audit = self._audit(conn, snapshot_id)
            if audit is None:
                return result
            if audit.batch.snapshot_sha256 != snapshot.fingerprint:
                raise ValueError("Graph source fingerprint differs from the requested snapshot.")
            names = {c.character_id: c.name for c in audit.batch.catalogue.characters}
            result = result.model_copy(update={"graph_sha256": audit.graph_sha256, "names": names})
            if query.character_id not in names or (
                query.partner_id and query.partner_id not in names
            ):
                return result.model_copy(update={"status": "unknown_character"})
            rows = conn.execute(
                """
                SELECT document FROM relationship_assertions WHERE graph_sha256=%s
                  AND (subject_id=%s OR object_id=%s)
                  AND (%s::text IS NULL OR subject_id=%s OR object_id=%s)
                ORDER BY claim_id LIMIT %s
                """,
                (
                    audit.graph_sha256,
                    query.character_id,
                    query.character_id,
                    query.partner_id,
                    query.partner_id,
                    query.partner_id,
                    query.max_events + 1,
                ),
            ).fetchall()
        if budget:
            budget.check()
        claims = tuple(RelationshipClaim.model_validate(row[0]) for row in rows[: query.max_events])
        return result.model_copy(
            update={
                "claims": claims,
                "status": "truncated"
                if len(rows) > query.max_events
                else ("found" if claims else "empty"),
            }
        )
