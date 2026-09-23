"""Immutable captured snapshots and deterministic PostgreSQL text inspection."""

import psycopg
from psycopg.types.json import Jsonb

from ask_phil.evidence import Inspection, Passage, SourceSnapshot


class SnapshotNotFound(LookupError):
    pass


class SnapshotConflict(ValueError):
    pass


class EvidenceStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def load(self, snapshot: SourceSnapshot) -> str:
        """Atomically publish a fixture; an existing identifier cannot change meaning."""
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_snapshots (
                    snapshot_id text PRIMARY KEY,
                    fingerprint text NOT NULL,
                    document jsonb NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS source_passages (
                    snapshot_id text REFERENCES source_snapshots(snapshot_id),
                    evidence_id text NOT NULL,
                    document jsonb NOT NULL,
                    content text NOT NULL,
                    search_vector tsvector GENERATED ALWAYS AS
                        (to_tsvector('english', content)) STORED,
                    PRIMARY KEY (snapshot_id, evidence_id)
                )
            """)
            inserted = conn.execute(
                """INSERT INTO source_snapshots VALUES (%s, %s, %s)
                   ON CONFLICT DO NOTHING RETURNING snapshot_id""",
                (
                    snapshot.snapshot_id,
                    snapshot.fingerprint,
                    Jsonb(snapshot.model_dump(mode="json")),
                ),
            ).fetchone()
            if inserted is None:
                existing = conn.execute(
                    "SELECT fingerprint FROM source_snapshots WHERE snapshot_id = %s",
                    (snapshot.snapshot_id,),
                ).fetchone()
                if existing is None or existing[0] != snapshot.fingerprint:
                    raise SnapshotConflict("Snapshot identifier already names different content.")
                return snapshot.snapshot_id
            for passage in snapshot.passages:
                conn.execute(
                    "INSERT INTO source_passages VALUES (%s, %s, %s, %s)",
                    (
                        snapshot.snapshot_id,
                        passage.evidence_id,
                        Jsonb(passage.model_dump(mode="json")),
                        passage.text,
                    ),
                )
        return snapshot.snapshot_id

    def snapshot(self, snapshot_id: str) -> SourceSnapshot:
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            row = conn.execute(
                "SELECT document FROM source_snapshots WHERE snapshot_id = %s", (snapshot_id,)
            ).fetchone()
        if row is None:
            raise SnapshotNotFound(snapshot_id)
        return SourceSnapshot.model_validate(row[0])

    def inspect(self, snapshot_id: str, query: str, limit: int = 10) -> Inspection:
        snapshot = self.snapshot(snapshot_id)
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            rows = conn.execute(
                """SELECT document FROM source_passages,
                          plainto_tsquery('english', %s) AS query
                   WHERE snapshot_id = %s AND search_vector @@ query
                   ORDER BY ts_rank(search_vector, query) DESC, evidence_id
                   LIMIT %s""",
                (query, snapshot_id, limit),
            ).fetchall()
        return Inspection(
            snapshot_id=snapshot.snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            source=snapshot.source,
            query=query,
            matches=tuple(Passage.model_validate(row[0]) for row in rows),
        )
