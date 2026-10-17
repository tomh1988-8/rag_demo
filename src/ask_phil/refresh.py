"""Manual Prefect source refresh; publication follows complete artifact preparation."""

from contextlib import nullcontext
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import psycopg
from llama_index.core.base.embeddings.base import BaseEmbedding
from prefect import flow
from prefect.runtime import flow_run

from ask_phil.ingestion import (
    SourceBatch,
    build_snapshot,
    iter_captures,
    source_input_fingerprint,
)
from ask_phil.publications import PublicationNotFound, PublicationStore, RefreshRun, SourceResult
from ask_phil.retrieval import IndexNotReady, TextRetriever
from ask_phil.source_records import CapturedSource, CapturePlan
from ask_phil.storage import EvidenceStore, SnapshotNotFound


class RefreshFailed(ValueError):
    def __init__(self, run_id: UUID) -> None:
        self.run_id = run_id
        super().__init__(f"Refresh {run_id} failed; inspect its recorded outcome.")


class IncompleteImport(ValueError):
    pass


class SourceRefresh:
    def __init__(
        self, database_url: str, embedding: BaseEmbedding, embedding_id: str, dimensions: int
    ) -> None:
        self.store = EvidenceStore(database_url)
        self.publications = PublicationStore(database_url)
        self.retriever = TextRetriever(database_url, embedding, embedding_id, dimensions)

    def run(
        self, source: SourceBatch | CapturePlan, *, client: httpx.Client | None = None
    ) -> RefreshRun:
        # The closure keeps database credentials and full captures out of Prefect parameters.
        @flow(
            name="ask-phil-source-refresh",
            version="source-text-v1",
            retries=0,
            persist_result=False,
            timeout_seconds=1200,
            log_prints=False,
        )
        def execute() -> RefreshRun:
            run = RefreshRun(
                run_id=uuid4(),
                flow_run_id=UUID(str(flow_run.id)),
                started_at=datetime.now(UTC),
                status="running",
                phase="capturing",
            )
            with self.publications.writer() as conn:
                self.publications.save_run(run, conn)
                try:
                    batch = self._capture(source, client, run, conn)
                    run = self.publications.run(run.run_id)
                    input_id = source_input_fingerprint(batch)
                    run = run.model_copy(update={"input_sha256": input_id, "phase": "validating"})
                    self.publications.save_run(run, conn)
                    try:
                        snapshot = self.store.snapshot("sources-" + input_id)
                    except (SnapshotNotFound, psycopg.errors.UndefinedTable):
                        snapshot = build_snapshot(batch, "sources-" + input_id)
                    assert snapshot.imported is not None
                    run = run.model_copy(
                        update={
                            "snapshot_id": snapshot.snapshot_id,
                            "issues": snapshot.imported.issues,
                        }
                    )
                    self.publications.save_run(run, conn)
                    if any(i.code in {"missing_record", "missing_section"} for i in run.issues):
                        raise IncompleteImport("Required source content is missing.")
                    self.store.load(snapshot)
                    run = run.model_copy(update={"phase": "indexing"})
                    self.publications.save_run(run, conn)
                    index = self.retriever.prepare(snapshot.snapshot_id)
                    run = run.model_copy(update={"phase": "publishing"})
                    self.publications.save_run(run, conn)
                    return self.publications.publish(snapshot, index, run, conn)
                except Exception as exc:
                    run = self.publications.run(run.run_id)
                    partial = isinstance(exc, IncompleteImport) or (
                        run.phase == "capturing"
                        and any(s.capture_sha256 is not None for s in run.sources)
                    )
                    failed = run.model_copy(
                        update={
                            "status": "partial" if partial else "failed",
                            "finished_at": datetime.now(UTC),
                            "error": f"{run.phase} failed ({type(exc).__name__}).",
                        }
                    )
                    self.publications.save_run(failed, conn)
                    raise RefreshFailed(run.run_id) from None

        return execute()

    def rollback(self) -> RefreshRun:
        @flow(
            name="ask-phil-snapshot-recovery",
            version="source-text-v1",
            retries=0,
            persist_result=False,
            timeout_seconds=120,
            log_prints=False,
        )
        def execute() -> RefreshRun:
            run = RefreshRun(
                run_id=uuid4(),
                flow_run_id=UUID(str(flow_run.id)),
                started_at=datetime.now(UTC),
                status="running",
                action="rollback",
                phase="recovering",
            )
            with self.publications.writer() as conn:
                self.publications.save_run(run, conn)
                try:
                    previous = self.publications.previous()
                    snapshot = self.store.snapshot(previous.manifest.snapshot_id)
                    index = self.retriever.manifest(snapshot.snapshot_id)
                    if (
                        snapshot.fingerprint != previous.manifest.snapshot_sha256
                        or index != previous.manifest.index
                    ):
                        raise IndexNotReady("The prior source/index pair is no longer compatible.")
                    return self.publications.restore(previous, run, conn)
                except Exception as exc:
                    self.publications.save_run(
                        run.model_copy(
                            update={
                                "status": "failed",
                                "finished_at": datetime.now(UTC),
                                "error": f"Recovery failed ({type(exc).__name__}).",
                            }
                        ),
                        conn,
                    )
                    raise RefreshFailed(run.run_id) from None

        return execute()

    def _capture(
        self,
        source: SourceBatch | CapturePlan,
        client: httpx.Client | None,
        run: RefreshRun,
        conn: psycopg.Connection[tuple[object, ...]],
    ) -> SourceBatch:
        try:
            before = {s.source_id: s.sha256 for s in self.publications.active().manifest.sources}
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
                    self.publications.save_capture(run.run_id, len(captures), capture, conn)
                    captures.append(capture)
                    result = SourceResult(
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
                    run = run.model_copy(update={"sources": (*run.sources, result)})
                    self.publications.save_run(run, conn)
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
                self.publications.save_run(
                    run.model_copy(update={"sources": (*run.sources, *outcomes)}), conn
                )
            raise
        return SourceBatch(
            format_version=1,
            catalogue=source.catalogue,
            policies=source.policies,
            captures=tuple(captures),
        )
