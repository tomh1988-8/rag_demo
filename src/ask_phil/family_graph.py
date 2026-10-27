"""Immutable reviewed claims and their bounded, read-only PostgreSQL family projection."""

from typing import Literal

import psycopg
from psycopg import sql
from pydantic import Field

from ask_phil.claim_projections import FamilyAudit as FamilyAudit
from ask_phil.claim_projections import FamilyEdge as FamilyEdge
from ask_phil.claim_projections import install_projection
from ask_phil.claims import ClaimReview
from ask_phil.evidence import Fingerprint, Identifier, Record
from ask_phil.execution import current_execution, read_options
from ask_phil.parentage import ClaimBatch
from ask_phil.storage import EvidenceStore

GRAPH_LIMITATION = (
    "Only admitted biological relationships in this reviewed snapshot are traversed. "
    "Missing ancestry does not establish that a relationship does not exist. "
    "Results are incomplete outside the selected material and traversal bounds. "
    "Source-supported does not mean independently cross-checked."
)


class FamilyQuery(Record):
    character_id: Identifier
    direction: Literal["ancestors", "descendants"]
    max_depth: int = Field(default=3, ge=1, le=6)
    max_paths: int = Field(default=20, ge=1, le=50)


class FamilyPath(Record):
    characters: tuple[Identifier, ...] = Field(min_length=2, max_length=7)
    edges: tuple[FamilyEdge, ...] = Field(min_length=1, max_length=6)


class FamilyResult(Record):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    graph_sha256: Fingerprint | None = None
    query: FamilyQuery
    status: Literal["found", "empty", "truncated", "unavailable", "unknown_character"]
    paths: tuple[FamilyPath, ...] = ()
    names: dict[str, str] = Field(default_factory=dict)
    limitation: str = GRAPH_LIMITATION


class FamilyGraph:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def install(self, batch: ClaimBatch, reviews: tuple[ClaimReview, ...]) -> FamilyAudit:
        return install_projection(self.database_url, batch, reviews)

    def audit(self, snapshot_id: str) -> FamilyAudit | None:
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            return self._audit(conn, snapshot_id)

    @staticmethod
    def _audit(
        conn: psycopg.Connection[tuple[object, ...]], snapshot_id: str
    ) -> FamilyAudit | None:
        if conn.execute("SELECT to_regclass('family_projections')").fetchone() == (None,):
            return None
        row = conn.execute(
            "SELECT document FROM family_projections WHERE snapshot_id=%s", (snapshot_id,)
        ).fetchone()
        return FamilyAudit.model_validate(row[0]) if row else None

    def query(self, snapshot_id: str, query: FamilyQuery) -> FamilyResult:
        snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
        budget = current_execution.get()
        if budget:
            budget.tool_call("family_graph")
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            audit = self._audit(conn, snapshot_id)
            result = FamilyResult(
                snapshot_id=snapshot_id,
                snapshot_sha256=snapshot.fingerprint,
                query=query,
                status="unavailable",
            )
            if audit is None:
                return result
            if audit.batch.snapshot_sha256 != snapshot.fingerprint:
                raise ValueError("Graph source fingerprint differs from the requested snapshot.")
            names = {c.character_id: c.name for c in audit.batch.catalogue.characters}
            result = result.model_copy(update={"graph_sha256": audit.graph_sha256, "names": names})
            if query.character_id not in names:
                return result.model_copy(update={"status": "unknown_character"})
            origin, target = (
                ("child_id", "parent_id")
                if query.direction == "ancestors"
                else ("parent_id", "child_id")
            )
            rows = conn.execute(
                sql.SQL("""
                WITH RECURSIVE walk(node, characters, edges, depth) AS (
                    SELECT %s::text, ARRAY[%s]::text[], '[]'::jsonb, 0
                    UNION ALL
                    SELECT e.{target}, w.characters || e.{target},
                           w.edges || jsonb_build_array(e.document), w.depth+1
                    FROM walk w JOIN family_edges e ON e.{origin}=w.node
                    WHERE e.graph_sha256=%s AND w.depth<%s
                      AND NOT e.{target}=ANY(w.characters)
                ) SELECT characters, edges FROM walk WHERE depth>0 LIMIT %s
            """).format(origin=sql.Identifier(origin), target=sql.Identifier(target)),
                (
                    query.character_id,
                    query.character_id,
                    audit.graph_sha256,
                    query.max_depth,
                    query.max_paths + 1,
                ),
            ).fetchall()
        if budget:
            budget.check()
        paths = tuple(
            FamilyPath(characters=row[0], edges=tuple(FamilyEdge.model_validate(e) for e in row[1]))
            for row in rows[: query.max_paths]
        )
        return result.model_copy(
            update={
                "paths": paths,
                "status": "truncated"
                if len(rows) > query.max_paths
                else ("found" if paths else "empty"),
            }
        )
