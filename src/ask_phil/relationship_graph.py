"""Immutable admitted relationship assertions behind a bounded read-only SQL query."""

from typing import Literal, Self

import psycopg
from pydantic import Field, model_validator

from ask_phil.claim_projections import RelationshipAudit as RelationshipAudit
from ask_phil.claim_projections import install_projection
from ask_phil.claims import ClaimReview
from ask_phil.evidence import Fingerprint, Identifier, Record
from ask_phil.execution import current_execution, read_options
from ask_phil.relationships import (
    HISTORY_LIMITATION,
    RelationshipBatch,
    RelationshipClaim,
)
from ask_phil.storage import EvidenceStore


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


class RelationshipGraph:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def install(
        self, batch: RelationshipBatch, reviews: tuple[ClaimReview, ...]
    ) -> RelationshipAudit:
        return install_projection(self.database_url, batch, reviews)

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
