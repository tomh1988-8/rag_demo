"""Manual Prefect source refresh; the journal owns progress and retained outcomes."""

from uuid import UUID

import httpx
from llama_index.core.base.embeddings.base import BaseEmbedding
from prefect import flow
from prefect.runtime import flow_run

from ask_phil.publications import PublicationStore, RefreshRun
from ask_phil.refresh_journal import IncompleteImport as IncompleteImport
from ask_phil.refresh_journal import RefreshFailed as RefreshFailed
from ask_phil.refresh_journal import refresh_journal
from ask_phil.retrieval import TextRetriever
from ask_phil.source_records import CapturePlan, SourceBatch


class SourceRefresh:
    def __init__(
        self, database_url: str, embedding: BaseEmbedding, embedding_id: str, dimensions: int
    ) -> None:
        self.publications = PublicationStore(database_url)
        self.retriever = TextRetriever(database_url, embedding, embedding_id, dimensions)

    def run(
        self, source: SourceBatch | CapturePlan, *, client: httpx.Client | None = None
    ) -> RefreshRun:
        # Keep database credentials and captures out of Prefect parameters.
        @flow(
            name="ask-phil-source-refresh",
            version="source-text-v1",
            retries=0,
            persist_result=False,
            timeout_seconds=1200,
            log_prints=False,
        )
        def execute() -> RefreshRun:
            with refresh_journal(
                self.publications, UUID(str(flow_run.id)), action="refresh"
            ) as journal:
                batch = journal.capture(source, client)
                snapshot = journal.snapshot(batch)
                index = journal.prepare(snapshot, self.retriever)
                return journal.publish(snapshot, index)

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
            with refresh_journal(
                self.publications, UUID(str(flow_run.id)), action="rollback"
            ) as journal:
                return journal.restore(self.retriever.previous())

        return execute()
