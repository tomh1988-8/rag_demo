"""Immutable source/index manifests and the atomic active-publication pointer."""

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, Field

from ask_phil.claim_projections import GraphVersions, graph_versions
from ask_phil.evidence import Fingerprint, Identifier, PublicationRef, Record, SourceSnapshot
from ask_phil.execution import read_options
from ask_phil.retrieval import IndexNotReady, TextIndex
from ask_phil.source_records import CapturedSource, ImportIssue, SourceSummary


class PublicationNotFound(LookupError):
    pass


class RefreshBusy(ValueError):
    pass


class SnapshotManifest(Record):
    format_version: Literal["source-text-publication-v1"] = "source-text-publication-v1"
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    input_sha256: Fingerprint
    sources: tuple[SourceSummary, ...]
    index: TextIndex
    graphs: GraphVersions | None = Field(default=None, exclude_if=lambda v: v is None)
    review_sha256: Fingerprint | None = Field(default=None, exclude_if=lambda v: v is None)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class ActivePublication(Record):
    compatibility_id: Fingerprint
    manifest: SnapshotManifest
    generation: int
    published_at: AwareDatetime

    @property
    def reference(self) -> PublicationRef:
        return PublicationRef(
            compatibility_id=self.compatibility_id,
            index_sha256=self.manifest.index.fingerprint,
            generation=self.generation,
        )


class SourceResult(Record):
    source_id: str
    outcome: Literal["new", "changed", "unchanged", "failed", "skipped"]
    capture_sha256: Fingerprint | None = None
    checked_at: AwareDatetime | None = None
    detail: str | None = None


class RefreshRun(Record):
    run_id: UUID
    flow_run_id: UUID
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    status: Literal[
        "running", "published", "skipped", "partial", "failed", "interrupted", "rolled_back"
    ]
    action: Literal["refresh", "rollback", "review"] = "refresh"
    input_sha256: Fingerprint | None = None
    snapshot_id: Identifier | None = None
    compatibility_id: Fingerprint | None = None
    sources: tuple[SourceResult, ...] = ()
    issues: tuple[ImportIssue, ...] = ()
    phase: Literal[
        "capturing", "validating", "indexing", "publishing", "recovering", "complete"
    ] = "validating"
    error: str | None = None


class PublicationStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _initialize(self, conn: psycopg.Connection[tuple[object, ...]]) -> None:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshot_publications (
                compatibility_id text PRIMARY KEY,
                snapshot_id text NOT NULL,
                input_sha256 text NOT NULL,
                manifest jsonb NOT NULL,
                published_at timestamptz NOT NULL,
                withdrawn boolean NOT NULL DEFAULT false
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS active_publication (
                singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
                compatibility_id text NOT NULL REFERENCES snapshot_publications,
                previous_id text REFERENCES snapshot_publications,
                generation bigint NOT NULL CHECK (generation > 0)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS refresh_runs (
                run_id uuid PRIMARY KEY,
                document jsonb NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS refresh_captures (
                run_id uuid REFERENCES refresh_runs,
                ordinal integer NOT NULL,
                document jsonb NOT NULL,
                PRIMARY KEY (run_id, ordinal)
            )
        """)

    @contextmanager
    def writer(self) -> Iterator[psycopg.Connection[tuple[object, ...]]]:
        """Serialize maintainer work; queries continue using the old committed pointer."""
        with psycopg.connect(self.database_url, connect_timeout=5, autocommit=True) as conn:
            if conn.execute("SELECT pg_try_advisory_lock(728194)").fetchone() != (True,):
                raise RefreshBusy("Another refresh or recovery is still running.")
            with conn.transaction():
                self._initialize(conn)
                # Owning the session lock proves no prior maintainer still owns these runs.
                abandoned = conn.execute(
                    "SELECT document FROM refresh_runs WHERE document->>'status' = 'running'"
                ).fetchall()
                for row in abandoned:
                    previous = RefreshRun.model_validate(row[0])
                    self.save_run(
                        previous.model_copy(
                            update={
                                "status": "interrupted",
                                "finished_at": datetime.now(UTC),
                                "error": "Prior maintainer stopped before completing this run.",
                            }
                        ),
                        conn,
                    )
            yield conn

    def save_run(self, run: RefreshRun, conn: psycopg.Connection[tuple[object, ...]]) -> None:
        conn.execute(
            "INSERT INTO refresh_runs VALUES (%s, %s) "
            "ON CONFLICT (run_id) DO UPDATE SET document = EXCLUDED.document",
            (run.run_id, Jsonb(run.model_dump(mode="json"))),
        )

    def save_capture(
        self,
        run_id: UUID,
        ordinal: int,
        capture: CapturedSource,
        conn: psycopg.Connection[tuple[object, ...]],
    ) -> None:
        conn.execute(
            "INSERT INTO refresh_captures VALUES (%s, %s, %s)",
            (run_id, ordinal, Jsonb(capture.model_dump(mode="json"))),
        )

    def captures(self, run_id: UUID) -> tuple[CapturedSource, ...]:
        self.run(run_id)
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            rows = conn.execute(
                "SELECT document FROM refresh_captures WHERE run_id = %s ORDER BY ordinal",
                (run_id,),
            ).fetchall()
        return tuple(CapturedSource.model_validate(row[0]) for row in rows)

    def publish(
        self,
        snapshot: SourceSnapshot,
        index: TextIndex,
        run: RefreshRun,
        conn: psycopg.Connection[tuple[object, ...]],
    ) -> RefreshRun:
        if (snapshot.imported is None and run.action != "review") or run.input_sha256 is None:
            raise ValueError(
                "Publication requires a reviewed source import and its input identity."
            )
        if index.snapshot_sha256 != snapshot.fingerprint:
            raise ValueError("Source and index must describe the same snapshot.")
        from ask_phil.knowledge_review import review_revision

        revision = review_revision(self.database_url, snapshot.snapshot_id)
        manifest = SnapshotManifest(
            snapshot_id=snapshot.snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            input_sha256=run.input_sha256,
            sources=snapshot.imported.report().sources if snapshot.imported else (),
            index=index,
            review_sha256=revision.request.fingerprint if revision else None,
        )
        now = datetime.now(UTC)
        result = run.model_copy(
            update={
                "status": "published",
                "phase": "complete",
                "finished_at": now,
                "snapshot_id": snapshot.snapshot_id,
            }
        )
        with conn.transaction():
            # These locks are shared with graph installation. The publication seals
            # membership, including absent projections, before any installer can race it.
            for lock in (728196, 728197, 728198):
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (lock,))
            manifest = manifest.model_copy(
                update={"graphs": graph_versions(conn, snapshot.snapshot_id)}
            )
            result = result.model_copy(update={"compatibility_id": manifest.fingerprint})
            withdrawn = conn.execute(
                "SELECT withdrawn FROM snapshot_publications WHERE compatibility_id = %s",
                (manifest.fingerprint,),
            ).fetchone()
            if withdrawn and withdrawn[0]:
                raise IndexNotReady("This publication was withdrawn; review a corrected input.")
            conn.execute(
                "INSERT INTO snapshot_publications VALUES (%s, %s, %s, %s, %s, false) "
                "ON CONFLICT DO NOTHING",
                (
                    manifest.fingerprint,
                    snapshot.snapshot_id,
                    manifest.input_sha256,
                    Jsonb(manifest.model_dump(mode="json")),
                    now,
                ),
            )
            active = conn.execute(
                "SELECT compatibility_id FROM active_publication FOR UPDATE"
            ).fetchone()
            if active and active[0] == manifest.fingerprint:
                result = result.model_copy(update={"status": "skipped"})
            else:
                conn.execute(
                    """INSERT INTO active_publication VALUES (true, %s, NULL, 1)
                       ON CONFLICT (singleton) DO UPDATE SET
                           previous_id = active_publication.compatibility_id,
                           compatibility_id = EXCLUDED.compatibility_id,
                           generation = active_publication.generation + 1""",
                    (manifest.fingerprint,),
                )
            self.save_run(result, conn)
        return result

    def run(self, run_id: UUID) -> RefreshRun:
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            if conn.execute("SELECT to_regclass('refresh_runs')").fetchone() == (None,):
                raise PublicationNotFound("Refresh run not found.")
            row = conn.execute(
                "SELECT document FROM refresh_runs WHERE run_id = %s", (run_id,)
            ).fetchone()
        if row is None:
            raise PublicationNotFound("Refresh run not found.")
        return RefreshRun.model_validate(row[0])

    def runs(self, limit: int = 20) -> tuple[RefreshRun, ...]:
        if not 1 <= limit <= 100:
            raise ValueError("Inspect between 1 and 100 refresh runs.")
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            if conn.execute("SELECT to_regclass('refresh_runs')").fetchone() == (None,):
                return ()
            rows = conn.execute(
                "SELECT document FROM refresh_runs ORDER BY document->>'started_at' DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return tuple(RefreshRun.model_validate(row[0]) for row in rows)

    def active(self) -> ActivePublication:
        from ask_phil.execution import read_options

        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            if conn.execute("SELECT to_regclass('active_publication')").fetchone() == (None,):
                raise PublicationNotFound("No usable snapshot has been published.")
            row = conn.execute("""
                SELECT p.compatibility_id, p.manifest, a.generation, p.published_at
                FROM active_publication a JOIN snapshot_publications p
                    ON p.compatibility_id = a.compatibility_id
                WHERE NOT p.withdrawn
            """).fetchone()
        if row is None:
            raise PublicationNotFound("No usable snapshot has been published.")
        return ActivePublication(
            compatibility_id=row[0],
            manifest=SnapshotManifest.model_validate(row[1]),
            generation=row[2],
            published_at=row[3],
        )

    def previous(self) -> ActivePublication:
        self.active()
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            row = conn.execute("""
                SELECT p.compatibility_id, p.manifest, a.generation, p.published_at
                FROM active_publication a JOIN snapshot_publications p
                    ON p.compatibility_id = a.previous_id
                WHERE NOT p.withdrawn
            """).fetchone()
        if row is None:
            raise PublicationNotFound("No prior usable publication is available for recovery.")
        return ActivePublication(
            compatibility_id=row[0],
            manifest=SnapshotManifest.model_validate(row[1]),
            generation=row[2],
            published_at=row[3],
        )

    def restore(
        self,
        previous: ActivePublication,
        run: RefreshRun,
        conn: psycopg.Connection[tuple[object, ...]],
    ) -> RefreshRun:
        result = run.model_copy(
            update={
                "status": "rolled_back",
                "phase": "complete",
                "finished_at": datetime.now(UTC),
                "snapshot_id": previous.manifest.snapshot_id,
                "compatibility_id": previous.compatibility_id,
            }
        )
        with conn.transaction():
            current = conn.execute(
                "SELECT compatibility_id, previous_id FROM active_publication FOR UPDATE"
            ).fetchone()
            if current is None or current[1] != previous.compatibility_id:
                raise IndexNotReady("The prior publication changed before recovery.")
            conn.execute(
                "UPDATE snapshot_publications SET withdrawn = true WHERE compatibility_id = %s",
                (current[0],),
            )
            conn.execute(
                """UPDATE active_publication SET compatibility_id = %s,
                   previous_id = NULL, generation = generation + 1""",
                (previous.compatibility_id,),
            )
            self.save_run(result, conn)
        return result

    def is_current(self, compatibility_id: str, generation: int) -> bool:
        """Future reuse must match both the compatible artifacts and their active generation."""
        try:
            current = self.active()
        except PublicationNotFound:
            return False
        return current.compatibility_id == compatibility_id and current.generation == generation

    def pin(
        self, snapshot_id: str | None = None, *, pinned: ActivePublication | None = None
    ) -> ActivePublication | None:
        """Pin a publication once; explicit legacy snapshots remain supported separately."""
        if pinned is not None:
            if snapshot_id is not None and snapshot_id != pinned.manifest.snapshot_id:
                raise IndexNotReady("The requested source differs from the pinned publication.")
            self.verify(pinned)
            return pinned
        if snapshot_id is None:
            current = self.active()
            self.verify(current)
            return current
        from ask_phil.execution import read_options

        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            if conn.execute("SELECT to_regclass('snapshot_publications')").fetchone() == (None,):
                return None
            row = conn.execute(
                """SELECT p.compatibility_id, p.manifest, a.generation, p.published_at, p.withdrawn
                   FROM snapshot_publications p LEFT JOIN active_publication a ON true
                   WHERE p.snapshot_id = %s
                   ORDER BY (p.compatibility_id = a.compatibility_id) DESC,
                       p.withdrawn, p.published_at DESC LIMIT 1""",
                (snapshot_id,),
            ).fetchone()
            if row is None:
                if conn.execute(
                    "SELECT 1 FROM refresh_runs WHERE document->>'snapshot_id' = %s LIMIT 1",
                    (snapshot_id,),
                ).fetchone():
                    raise IndexNotReady("This refresh candidate has not been published.")
                return None
        if row[4]:
            raise IndexNotReady("This publication was withdrawn; its evidence remains inspectable.")
        publication = ActivePublication(
            compatibility_id=row[0],
            manifest=SnapshotManifest.model_validate(row[1]),
            generation=row[2],
            published_at=row[3],
        )
        self.verify(publication)
        return publication

    def verify(self, publication: ActivePublication) -> None:
        """Verify the pinned claim/graph and review identities without reselecting current."""
        from ask_phil.knowledge_review import review_revision

        manifest = publication.manifest
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            if (
                manifest.graphs is not None
                and graph_versions(conn, manifest.snapshot_id) != manifest.graphs
            ):
                raise IndexNotReady("Claim/graph artifacts differ from the pinned publication.")
        revision = review_revision(self.database_url, manifest.snapshot_id)
        if (revision.request.fingerprint if revision else None) != manifest.review_sha256:
            raise IndexNotReady("Review history differs from the pinned publication.")
