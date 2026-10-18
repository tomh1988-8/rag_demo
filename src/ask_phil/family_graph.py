"""Immutable reviewed claims and their bounded, read-only PostgreSQL family projection."""

import hashlib
from typing import Literal

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from pydantic import Field

from ask_phil.evidence import Fingerprint, Identifier, Record
from ask_phil.execution import current_execution, database_options, read_options
from ask_phil.parentage import AdmissionReport, ClaimBatch, ClaimEvidence, ClaimReview, admit_claims
from ask_phil.security import require_credential_free
from ask_phil.storage import EvidenceStore, SnapshotConflict

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


class FamilyEdge(Record):
    parent_id: Identifier
    child_id: Identifier
    claim_ids: tuple[Identifier, ...] = Field(min_length=1)
    evidence: tuple[ClaimEvidence, ...] = Field(min_length=1)


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


class FamilyAudit(Record):
    batch: ClaimBatch
    reviews: tuple[ClaimReview, ...]
    admission: AdmissionReport
    graph_sha256: Fingerprint


class FamilyGraph:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def install(self, batch: ClaimBatch, reviews: tuple[ClaimReview, ...]) -> FamilyAudit:
        """Maintainer-only, atomic derivation. Existing snapshot projections cannot be replaced."""
        snapshot = EvidenceStore(self.database_url).snapshot(batch.snapshot_id)
        report = admit_claims(snapshot, batch, reviews)
        admitted = {d.claim_id for d in report.decisions if d.status == "admitted"}
        groups: dict[tuple[str, str], list[str]] = {}
        for claim in batch.claims:
            if claim.claim_id in admitted:
                groups.setdefault((claim.parent_id, claim.child_id), []).append(claim.claim_id)
        edges = []
        claims = {c.claim_id: c for c in batch.claims}
        for (parent, child), ids in sorted(groups.items()):
            edges.append(
                FamilyEdge(
                    parent_id=parent,
                    child_id=child,
                    claim_ids=tuple(sorted(ids)),
                    evidence=tuple(e for cid in sorted(ids) for e in claims[cid].evidence),
                )
            )
        derivation = (
            batch.model_dump_json()
            + report.model_dump_json()
            + "".join(r.model_dump_json() for r in sorted(reviews, key=lambda r: r.claim_id))
        )
        fingerprint = hashlib.sha256(("biological-sql-v1:" + derivation).encode()).hexdigest()
        audit = FamilyAudit(
            batch=batch, reviews=reviews, admission=report, graph_sha256=fingerprint
        )
        require_credential_free(audit.model_dump_json())
        with psycopg.connect(
            self.database_url, connect_timeout=5, options=database_options()
        ) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728196)")
            conn.execute("""CREATE TABLE IF NOT EXISTS parentage_batches (
                batch_sha256 text PRIMARY KEY,
                snapshot_id text NOT NULL REFERENCES source_snapshots(snapshot_id),
                document jsonb NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS parentage_claims (
                batch_sha256 text REFERENCES parentage_batches(batch_sha256),
                claim_id text NOT NULL, document jsonb NOT NULL,
                PRIMARY KEY(batch_sha256, claim_id))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS family_projections (
                snapshot_id text PRIMARY KEY REFERENCES source_snapshots(snapshot_id),
                graph_sha256 text NOT NULL UNIQUE,
                batch_sha256 text NOT NULL REFERENCES parentage_batches(batch_sha256),
                document jsonb NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS family_edges (
                graph_sha256 text REFERENCES family_projections(graph_sha256),
                parent_id text NOT NULL, child_id text NOT NULL, document jsonb NOT NULL,
                PRIMARY KEY(graph_sha256, parent_id, child_id))""")
            conn.execute("""CREATE INDEX IF NOT EXISTS family_children
                ON family_edges(graph_sha256, child_id)""")
            existing = conn.execute(
                "SELECT graph_sha256, document FROM family_projections WHERE snapshot_id=%s",
                (batch.snapshot_id,),
            ).fetchone()
            if existing:
                if existing[0] != fingerprint:
                    raise SnapshotConflict(
                        "Snapshot already has a different immutable family graph."
                    )
                return FamilyAudit.model_validate(existing[1])
            conn.execute(
                "INSERT INTO parentage_batches VALUES (%s,%s,%s)",
                (
                    batch.fingerprint,
                    batch.snapshot_id,
                    Jsonb(batch.model_dump(mode="json")),
                ),
            )
            for claim in batch.claims:
                conn.execute(
                    "INSERT INTO parentage_claims VALUES (%s,%s,%s)",
                    (
                        batch.fingerprint,
                        claim.claim_id,
                        Jsonb(claim.model_dump(mode="json")),
                    ),
                )
            conn.execute(
                "INSERT INTO family_projections VALUES (%s,%s,%s,%s)",
                (
                    batch.snapshot_id,
                    fingerprint,
                    batch.fingerprint,
                    Jsonb(audit.model_dump(mode="json")),
                ),
            )
            for edge in edges:
                conn.execute(
                    "INSERT INTO family_edges VALUES (%s,%s,%s,%s)",
                    (
                        fingerprint,
                        edge.parent_id,
                        edge.child_id,
                        Jsonb(edge.model_dump(mode="json")),
                    ),
                )
        return audit

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
