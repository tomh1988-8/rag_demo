"""Refresh progress, retained captures and terminal outcomes under one writer lock."""

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import httpx
import psycopg

from ask_phil.evidence import SourceSnapshot
from ask_phil.ingestion import build_snapshot, iter_captures, source_input_fingerprint
from ask_phil.publications import (
    ActivePublication,
    PublicationNotFound,
    PublicationStore,
    RefreshRun,
    SourceResult,
)
from ask_phil.retrieval import TextIndex, TextRetriever
from ask_phil.source_records import CapturedSource, CapturePlan, SourceBatch
from ask_phil.storage import EvidenceStore, SnapshotNotFound


class RefreshFailed(ValueError):
    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        super().__init__(f"Refresh {run_id} failed; inspect its recorded outcome.")


class IncompleteImport(ValueError):
    pass


@contextmanager
def refresh_journal(
    publications: PublicationStore,
    flow_run_id: UUID,
    *,
    action: Literal["refresh", "rollback", "review"],
) -> Iterator["RefreshJournal"]:
    """Own the connection and retain ordinary failures and explicit interruptions."""
    with publications.writer() as conn:
        journal = RefreshJournal(publications, conn, flow_run_id, action)
        try:
            yield journal
            if journal._run.status == "running":
                raise ValueError("Refresh ended without a terminal outcome.")
        except BaseException as exc:
            journal._failed(exc)
            if isinstance(exc, Exception):
                raise RefreshFailed(journal._run.run_id) from None
            raise


class RefreshJournal:
    def __init__(
        self,
        publications: PublicationStore,
        conn: psycopg.Connection[tuple[object, ...]],
        flow_run_id: UUID,
        action: Literal["refresh", "rollback", "review"],
    ) -> None:
        self._publications = publications
        self._conn = conn
        self._run = RefreshRun(
            run_id=uuid4(),
            flow_run_id=flow_run_id,
            started_at=datetime.now(UTC),
            status="running",
            action=action,
            phase="capturing"
            if action == "refresh"
            else "recovering"
            if action == "rollback"
            else "validating",
        )
        publications.save_run(self._run, conn)

    def _update(self, **changes: object) -> None:
        updated = self._run.model_copy(update=changes)
        self._publications.save_run(updated, self._conn)
        self._run = updated

    def capture(
        self, source: SourceBatch | CapturePlan, client: httpx.Client | None
    ) -> SourceBatch:
        try:
            before = {s.source_id: s.sha256 for s in self._publications.active().manifest.sources}
        except PublicationNotFound:
            before = {}
        captures: list[CapturedSource] = []
        session = (
            httpx.Client(trust_env=False)
            if isinstance(source, CapturePlan) and client is None
            else nullcontext(client)
        )
        try:
            with session as opened:
                if isinstance(source, CapturePlan):
                    assert opened is not None
                    pending = iter_captures(source.requests, opened)
                else:
                    pending = iter(source.captures)
                for capture in pending:
                    outcome = SourceResult(
                        source_id=capture.source_id,
                        outcome="new"
                        if capture.source_id not in before
                        else (
                            "unchanged"
                            if before[capture.source_id] == capture.sha256
                            else "changed"
                        ),
                        capture_sha256=capture.sha256,
                        checked_at=capture.captured_at,
                    )
                    updated = self._run.model_copy(
                        update={"sources": (*self._run.sources, outcome)}
                    )
                    # A retained capture and its inspectable source outcome commit together.
                    with self._conn.transaction():
                        self._publications.save_capture(
                            self._run.run_id, len(captures), capture, self._conn
                        )
                        self._publications.save_run(updated, self._conn)
                    self._run = updated
                    captures.append(capture)
        except (ValueError, httpx.HTTPError) as exc:
            if isinstance(source, CapturePlan):
                outcomes = tuple(
                    SourceResult(
                        source_id=request.source_id,
                        outcome="failed" if i == 0 else "skipped",
                        detail=str(exc)[:500] if i == 0 else "An earlier source failed.",
                    )
                    for i, request in enumerate(source.requests[len(captures) :])
                )
                self._update(sources=(*self._run.sources, *outcomes))
            raise
        return SourceBatch(
            format_version=1,
            catalogue=source.catalogue,
            policies=source.policies,
            captures=tuple(captures),
        )

    def snapshot(self, batch: SourceBatch) -> SourceSnapshot:
        input_id = source_input_fingerprint(batch)
        self._update(input_sha256=input_id, phase="validating")
        store = EvidenceStore(self._publications.database_url)
        try:
            current = self._publications.active()
        except PublicationNotFound:
            current = None
        if current and current.manifest.input_sha256 == input_id and current.manifest.review_sha256:
            # An unchanged recapture must not undo a subsequent Claim review.
            snapshot = store.snapshot(current.manifest.snapshot_id)
            self._update(snapshot_id=snapshot.snapshot_id)
            return snapshot
        try:
            snapshot = store.snapshot("sources-" + input_id)
        except (SnapshotNotFound, psycopg.errors.UndefinedTable):
            snapshot = build_snapshot(batch, "sources-" + input_id)
        assert snapshot.imported is not None
        self._update(snapshot_id=snapshot.snapshot_id, issues=snapshot.imported.issues)
        if any(i.code in {"missing_record", "missing_section"} for i in self._run.issues):
            raise IncompleteImport("Required source content is missing.")
        store.load(snapshot)
        return snapshot

    def prepare(self, snapshot: SourceSnapshot, retriever: TextRetriever) -> TextIndex:
        self._update(phase="indexing")
        return retriever.prepare(snapshot.snapshot_id)

    def stage_review(self, snapshot: SourceSnapshot, input_sha256: str) -> None:
        self._update(
            snapshot_id=snapshot.snapshot_id, input_sha256=input_sha256, phase="validating"
        )
        EvidenceStore(self._publications.database_url).load(snapshot)

    def publish(self, snapshot: SourceSnapshot, index: TextIndex) -> RefreshRun:
        self._update(phase="publishing")
        self._run = self._publications.publish(snapshot, index, self._run, self._conn)
        return self._run

    def restore(self, previous: ActivePublication) -> RefreshRun:
        self._run = self._publications.restore(previous, self._run, self._conn)
        return self._run

    def _failed(self, exc: BaseException) -> None:
        # An interrupt can arrive immediately after commit, before the in-memory assignment.
        self._run = self._publications.run(self._run.run_id)
        if self._run.status != "running":
            return
        interrupted = not isinstance(exc, Exception)
        partial = isinstance(exc, IncompleteImport) or (
            self._run.phase == "capturing"
            and any(s.capture_sha256 is not None for s in self._run.sources)
        )
        self._update(
            status="interrupted" if interrupted else "partial" if partial else "failed",
            finished_at=datetime.now(UTC),
            error=(
                f"{self._run.phase} interrupted ({type(exc).__name__})."
                if interrupted
                else f"Recovery failed ({type(exc).__name__})."
                if self._run.action == "rollback"
                else f"{self._run.phase} failed ({type(exc).__name__})."
            ),
        )
