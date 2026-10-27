"""Immutable admitted event assertions behind a bounded read-only SQL query."""

import hashlib
from typing import Literal, Self

import psycopg
from psycopg.types.json import Jsonb
from pydantic import Field, model_validator

from ask_phil.evidence import Fingerprint, Identifier, Record
from ask_phil.execution import current_execution, database_options, read_options
from ask_phil.security import require_credential_free
from ask_phil.storage import EvidenceStore, SnapshotConflict
from ask_phil.story_events import (
    EVENT_LIMITATION,
    EventAdmission,
    EventBatch,
    EventClaim,
    EventReview,
    admit_events,
)


class EventQuery(Record):
    kind: Literal["crime_history"]
    character_id: Identifier
    participant_id: Identifier | None = None
    event_id: Identifier | None = None
    max_events: int = Field(default=10, ge=1, le=20)

    @model_validator(mode="after")
    def distinct_participants(self) -> Self:
        if self.participant_id == self.character_id:
            raise ValueError("Shared-event queries require distinct participants.")
        return self


class EventResult(Record):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    graph_sha256: Fingerprint | None = None
    query: EventQuery
    status: Literal["found", "empty", "truncated", "unavailable", "unknown_character"]
    claims: tuple[EventClaim, ...] = ()
    names: dict[str, str] = Field(default_factory=dict)
    limitation: str = EVENT_LIMITATION


class EventAudit(Record):
    batch: EventBatch
    reviews: tuple[EventReview, ...]
    admission: EventAdmission
    graph_sha256: Fingerprint


class EventGraph:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def install(self, batch: EventBatch, reviews: tuple[EventReview, ...]) -> EventAudit:
        """Maintainer-only installation. Preserve candidates and review outcomes atomically."""
        snapshot = EvidenceStore(self.database_url).snapshot(batch.snapshot_id)
        report = admit_events(snapshot, batch, reviews)
        derivation = (
            batch.model_dump_json()
            + report.model_dump_json()
            + "".join(r.model_dump_json() for r in sorted(reviews, key=lambda r: r.claim_id))
        )
        audit = EventAudit(
            batch=batch,
            reviews=reviews,
            admission=report,
            graph_sha256=hashlib.sha256(
                ("crime-justice-sql-v1:" + derivation).encode()
            ).hexdigest(),
        )
        require_credential_free(audit.model_dump_json())
        with psycopg.connect(
            self.database_url, connect_timeout=5, options=database_options()
        ) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728198)")
            conn.execute("""CREATE TABLE IF NOT EXISTS event_projections (
                snapshot_id text PRIMARY KEY REFERENCES source_snapshots(snapshot_id),
                graph_sha256 text NOT NULL UNIQUE, document jsonb NOT NULL)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS event_assertions (
                graph_sha256 text REFERENCES event_projections(graph_sha256),
                claim_id text NOT NULL, event_id text NOT NULL,
                document jsonb NOT NULL, PRIMARY KEY(graph_sha256, claim_id))""")
            conn.execute("""CREATE TABLE IF NOT EXISTS event_participants (
                graph_sha256 text REFERENCES event_projections(graph_sha256),
                event_id text NOT NULL, character_id text NOT NULL,
                PRIMARY KEY(graph_sha256, event_id, character_id))""")
            existing = conn.execute(
                "SELECT document FROM event_projections WHERE snapshot_id=%s",
                (batch.snapshot_id,),
            ).fetchone()
            if existing:
                previous = EventAudit.model_validate(existing[0])
                if previous.graph_sha256 != audit.graph_sha256:
                    raise SnapshotConflict(
                        "Snapshot already has a different immutable event graph."
                    )
                return previous
            conn.execute(
                "INSERT INTO event_projections VALUES (%s,%s,%s)",
                (batch.snapshot_id, audit.graph_sha256, Jsonb(audit.model_dump(mode="json"))),
            )
            admitted = {d.claim_id for d in report.decisions if d.status == "admitted"}
            for claim in batch.claims:
                if claim.claim_id in admitted:
                    conn.execute(
                        "INSERT INTO event_assertions VALUES (%s,%s,%s,%s)",
                        (
                            audit.graph_sha256,
                            claim.claim_id,
                            claim.event_id,
                            Jsonb(claim.model_dump(mode="json")),
                        ),
                    )
                    for participant in claim.participants:
                        conn.execute(
                            "INSERT INTO event_participants VALUES (%s,%s,%s) "
                            "ON CONFLICT DO NOTHING",
                            (audit.graph_sha256, claim.event_id, participant.character_id),
                        )
        return audit

    @staticmethod
    def _audit(conn: psycopg.Connection[tuple[object, ...]], snapshot_id: str) -> EventAudit | None:
        if conn.execute("SELECT to_regclass('event_projections')").fetchone() == (None,):
            return None
        row = conn.execute(
            "SELECT document FROM event_projections WHERE snapshot_id=%s", (snapshot_id,)
        ).fetchone()
        return EventAudit.model_validate(row[0]) if row else None

    def audit(self, snapshot_id: str) -> EventAudit | None:
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            return self._audit(conn, snapshot_id)

    def query(self, snapshot_id: str, query: EventQuery) -> EventResult:
        snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
        budget = current_execution.get()
        if budget:
            budget.tool_call("event_graph")
        result = EventResult(
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
                query.participant_id and query.participant_id not in names
            ):
                return result.model_copy(update={"status": "unknown_character"})
            events = conn.execute(
                """SELECT a.event_id FROM event_participants a
                WHERE a.graph_sha256=%s AND a.character_id=%s
                AND (%s::text IS NULL OR a.event_id=%s)
                AND (%s::text IS NULL OR EXISTS (
                    SELECT 1 FROM event_participants b WHERE b.graph_sha256=a.graph_sha256
                    AND b.event_id=a.event_id AND b.character_id=%s))
                ORDER BY a.event_id LIMIT %s""",
                (
                    audit.graph_sha256,
                    query.character_id,
                    query.event_id,
                    query.event_id,
                    query.participant_id,
                    query.participant_id,
                    query.max_events + 1,
                ),
            ).fetchall()
            selected = [str(row[0]) for row in events[: query.max_events]]
            rows = conn.execute(
                """SELECT document FROM event_assertions WHERE graph_sha256=%s
                AND event_id=ANY(%s) ORDER BY event_id, claim_id""",
                (audit.graph_sha256, selected),
            ).fetchall()
        if budget:
            budget.check()
        claims = tuple(EventClaim.model_validate(row[0]) for row in rows)
        return result.model_copy(
            update={
                "claims": claims,
                "status": "truncated"
                if len(events) > query.max_events
                else ("found" if claims else "empty"),
            }
        )
