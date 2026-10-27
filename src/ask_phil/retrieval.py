"""Snapshot-bound exact vector retrieval through LlamaIndex and PostgreSQL."""

import hashlib
import json
import math
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import TYPE_CHECKING, Literal

import psycopg
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, VectorStoreQuery
from llama_index.vector_stores.postgres import PGVectorStore
from psycopg.conninfo import conninfo_to_dict
from psycopg.types.json import Jsonb
from pydantic import Field
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from ask_phil.classified_facts import ContextClaim
from ask_phil.event_graph import EventGraph
from ask_phil.evidence import Fingerprint, Passage, Record, SourceSnapshot
from ask_phil.execution import ExecutionStopped, current_execution, read_options
from ask_phil.storage import EvidenceStore

if TYPE_CHECKING:
    from ask_phil.publications import ActivePublication


@contextmanager
def _read_timeout() -> Iterator[None]:
    """Normalize direct and vector-adapter read deadlines at the retrieval seam."""
    try:
        yield
    except (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable):
        raise ExecutionStopped("timeout") from None
    except DBAPIError as exc:
        if isinstance(exc.orig, (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable)):
            raise ExecutionStopped("timeout") from None
        raise


def _validate_query(query: str, k: int) -> None:
    if (
        not isinstance(query, str)
        or not query.strip()
        or len(query) > 500
        or len(query.encode()) > 1000
        or type(k) is not int
        or not 1 <= k <= 20
    ):
        raise ValueError("Retrieval requires a question of 1–500 characters and k of 1–20.")


class IndexNotReady(ValueError):
    pass


class TextIndex(Record):
    format_version: Literal["pgvector-exact-v1"] = "pgvector-exact-v1"
    snapshot_sha256: Fingerprint
    embedding_id: str
    dimensions: int
    passages: int
    artifact_sha256: Fingerprint

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


class RetrievedPassage(Record):
    passage: Passage
    similarity: float | None = Field(ge=-1.000001, le=1.000001, allow_inf_nan=False)


class Retrieval(Record):
    snapshot: SourceSnapshot
    hits: tuple[RetrievedPassage, ...]
    k: int
    embedding_id: str
    context_claims: tuple[ContextClaim, ...] = Field(default=(), exclude_if=lambda v: not v)


class TextRetriever:
    def __init__(
        self, database_url: str, embedding: BaseEmbedding, embedding_id: str, dimensions: int
    ) -> None:
        self.database_url = database_url
        self.embedding = embedding
        self.embedding_id = embedding_id
        self.dimensions = dimensions

    def pin(self, snapshot_id: str | None = None) -> "PinnedText":
        """Retain one source identity for inspection and subsequent retrieval."""
        from ask_phil.publications import PublicationStore

        publication = PublicationStore(self.database_url).pin(snapshot_id)
        selected = publication.manifest.snapshot_id if publication else snapshot_id
        if selected is None:
            raise IndexNotReady("Publish a usable source/index snapshot before answering.")
        snapshot = EvidenceStore(self.database_url).snapshot(selected)
        return PinnedText(self, snapshot, publication)

    def previous(self) -> "ActivePublication":
        """Resolve a usable recovery publication before the active pointer can change."""
        from ask_phil.publications import PublicationStore

        publication = PublicationStore(self.database_url).previous()
        snapshot = EvidenceStore(self.database_url).snapshot(publication.manifest.snapshot_id)
        PinnedText(self, snapshot, publication).verify()
        return publication

    def _vectors(self, *, setup: bool = False) -> PGVectorStore:
        params = {
            k: str(v) for k, v in conninfo_to_dict(self.database_url).items() if v is not None
        }

        def url(driver: str) -> str:
            return URL.create(
                driver,
                username=params.get("user"),
                password=params.get("password"),
                host=params.get("host"),
                port=int(params["port"]) if "port" in params else None,
                database=params.get("dbname"),
            ).render_as_string(hide_password=False)

        identity = f"{self.embedding_id}:{self.dimensions}"
        return PGVectorStore(
            connection_string=url("postgresql+psycopg"),
            async_connection_string=url("postgresql+asyncpg"),
            table_name="passages_" + hashlib.sha256(identity.encode()).hexdigest()[:24],
            embed_dim=self.dimensions,
            perform_setup=setup,
            initialization_fail_on_error=True,
            use_jsonb=True,
            create_engine_kwargs={
                "poolclass": NullPool,
                "connect_args": {
                    "connect_timeout": 5,
                    **({"options": read_options()} if not setup else {}),
                },
            },
        )

    def _filter(self, fingerprint: str) -> MetadataFilters:
        return MetadataFilters(filters=[MetadataFilter(key="snapshot_sha256", value=fingerprint)])

    def prepare(self, snapshot_id: str) -> TextIndex:
        """Maintainer operation: publish embeddings only after the complete index is ready."""
        snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
        fingerprint = snapshot.fingerprint
        if any(len(p.text.encode()) > 1800 for p in snapshot.passages):
            raise ValueError(
                "Passage exceeds the 1800-byte embedding input budget; split it first."
            )
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728193)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS text_indexes (
                    snapshot_sha256 text NOT NULL,
                    embedding_id text NOT NULL,
                    dimensions integer NOT NULL,
                    PRIMARY KEY (snapshot_sha256, embedding_id, dimensions)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS text_index_artifacts (
                    snapshot_sha256 text NOT NULL,
                    embedding_id text NOT NULL,
                    dimensions integer NOT NULL,
                    document jsonb NOT NULL,
                    PRIMARY KEY (snapshot_sha256, embedding_id, dimensions),
                    FOREIGN KEY (snapshot_sha256, embedding_id, dimensions)
                        REFERENCES text_indexes(snapshot_sha256, embedding_id, dimensions)
                )
            """)
            key = (fingerprint, self.embedding_id, self.dimensions)
            if conn.execute(
                """SELECT 1 FROM text_indexes WHERE
                   snapshot_sha256 = %s AND embedding_id = %s AND dimensions = %s""",
                key,
            ).fetchone():
                artifact = self._artifact(snapshot)
                existing = conn.execute(
                    """SELECT document FROM text_index_artifacts WHERE
                       snapshot_sha256 = %s AND embedding_id = %s AND dimensions = %s""",
                    key,
                ).fetchone()
                if existing and TextIndex.model_validate(existing[0]) != artifact:
                    raise IndexNotReady("The saved index manifest no longer matches its artifacts.")
                conn.execute(
                    "INSERT INTO text_index_artifacts VALUES (%s, %s, %s, %s) "
                    "ON CONFLICT DO NOTHING",
                    (*key, Jsonb(artifact.model_dump())),
                )
                return artifact
            vectors = self._vectors(setup=True)
            # A failed preparation never publishes a manifest; its orphan nodes are
            # replaced on retry while the maintainer lock prevents duplicate writes.
            vectors.delete_nodes(filters=self._filter(fingerprint))
            for passage in snapshot.passages:
                vector = self.embedding.get_text_embedding(passage.text)
                vectors.add(
                    [
                        TextNode(
                            id_=f"{fingerprint}:{passage.evidence_id}",
                            text=passage.text,
                            embedding=vector,
                            metadata={
                                "snapshot_sha256": fingerprint,
                                "evidence_id": passage.evidence_id,
                            },
                        )
                    ]
                )
            artifact = self._artifact(snapshot)
            conn.execute("INSERT INTO text_indexes VALUES (%s, %s, %s)", key)
            conn.execute(
                "INSERT INTO text_index_artifacts VALUES (%s, %s, %s, %s)",
                (*key, Jsonb(artifact.model_dump())),
            )
        return artifact

    def _artifact(self, snapshot: SourceSnapshot) -> TextIndex:
        fingerprint = snapshot.fingerprint
        nodes = self._vectors().get_nodes(filters=self._filter(fingerprint))
        expected = {f"{fingerprint}:{p.evidence_id}": p for p in snapshot.passages}
        if len(nodes) != len(expected) or {node.node_id for node in nodes} != set(expected):
            raise IndexNotReady("The text index is incomplete or has duplicate logical passages.")
        records = []
        for node in sorted(nodes, key=lambda n: n.node_id):
            passage = expected[node.node_id]
            vector = [float(value) for value in node.get_embedding()]
            if (
                node.get_content() != passage.text
                or node.metadata.get("evidence_id") != passage.evidence_id
                or len(vector) != self.dimensions
                or not all(math.isfinite(value) for value in vector)
                or not any(value != 0 for value in vector)
            ):
                raise IndexNotReady(
                    "An index artifact does not match its source or vector contract."
                )
            records.append((passage.evidence_id, passage.sha256, vector))
        return TextIndex(
            snapshot_sha256=fingerprint,
            embedding_id=self.embedding_id,
            dimensions=self.dimensions,
            passages=len(nodes),
            artifact_sha256=hashlib.sha256(
                json.dumps(records, separators=(",", ":"), allow_nan=False).encode()
            ).hexdigest(),
        )

    def manifest(self, snapshot_id: str) -> TextIndex:
        """Resolve a complete index and verify its retained artifacts without model calls."""
        with _read_timeout():
            snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
            return self._manifest(snapshot)

    def _manifest(self, snapshot: SourceSnapshot) -> TextIndex:
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            if conn.execute("SELECT to_regclass('text_index_artifacts')").fetchone() == (None,):
                raise IndexNotReady("Prepare the snapshot to establish its index manifest.")
            row = conn.execute(
                """SELECT document FROM text_index_artifacts WHERE
                   snapshot_sha256 = %s AND embedding_id = %s AND dimensions = %s""",
                (snapshot.fingerprint, self.embedding_id, self.dimensions),
            ).fetchone()
        if row is None:
            raise IndexNotReady("No compatible index manifest exists for this snapshot.")
        manifest = TextIndex.model_validate(row[0])
        if manifest != self._artifact(snapshot):
            raise IndexNotReady("The saved index manifest no longer matches its artifacts.")
        return manifest

    def retrieve(self, snapshot_id: str, query: str, *, k: int = 3) -> Retrieval:
        _validate_query(query, k)
        return self.pin(snapshot_id).retrieve(query, k=k)

    def _retrieve(self, snapshot: SourceSnapshot, query: str, *, k: int = 3) -> Retrieval:
        budget = current_execution.get()
        if budget:
            budget.tool_call("text_retrieval")
        with psycopg.connect(self.database_url, connect_timeout=5, options=read_options()) as conn:
            if conn.execute("SELECT to_regclass('text_indexes')").fetchone() == (None,):
                raise IndexNotReady("Prepare this snapshot's text index before answering.")
            if not conn.execute(
                """SELECT 1 FROM text_indexes WHERE
                   snapshot_sha256 = %s AND embedding_id = %s AND dimensions = %s""",
                (snapshot.fingerprint, self.embedding_id, self.dimensions),
            ).fetchone():
                raise IndexNotReady("Prepare this snapshot with the configured embedding model.")
        if budget:
            budget.model_call(Decimal(0))
        try:
            vector = self.embedding.get_query_embedding(query)
            if (
                len(vector) != self.dimensions
                or not all(math.isfinite(value) for value in vector)
                or not any(value != 0 for value in vector)
            ):
                raise ValueError("Invalid embedding.")
        except (ValueError, IndexError, TypeError, KeyError):
            raise ExecutionStopped("malformed_output") from None
        result = self._vectors().query(
            VectorStoreQuery(
                query_embedding=vector,
                similarity_top_k=k,
                filters=self._filter(snapshot.fingerprint),
            )
        )
        if budget:
            budget.check()
        passages = {p.evidence_id: p for p in snapshot.passages}
        try:
            nodes = result.nodes or []
            if len(nodes) > k or (result.similarities and len(result.similarities) != len(nodes)):
                raise ValueError("Invalid retrieval result count.")
            identifiers = [node.metadata["evidence_id"] for node in nodes]
            if len(set(identifiers)) != len(identifiers):
                raise ValueError("Duplicate retrieval evidence.")
            for node in nodes:
                passage = passages[node.metadata["evidence_id"]]
                if (
                    node.node_id != f"{snapshot.fingerprint}:{passage.evidence_id}"
                    or node.get_content() != passage.text
                ):
                    raise ValueError("Retrieved evidence differs from the snapshot.")
            hits = tuple(
                RetrievedPassage(
                    passage=passages[node.metadata["evidence_id"]],
                    similarity=result.similarities[i] if result.similarities else None,
                )
                for i, node in enumerate(nodes)
            )
        except (ValueError, TypeError, KeyError, IndexError):
            raise ExecutionStopped("malformed_output") from None
        annotations = EventGraph(self.database_url).text_context(
            snapshot.snapshot_id, tuple(h.passage.evidence_id for h in hits)
        )
        if budget:
            budget.check()
        return Retrieval(
            snapshot=snapshot,
            hits=hits,
            k=k,
            embedding_id=self.embedding_id,
            context_claims=annotations,
        )


class PinnedText:
    """A captured source retained for one operation, including explicit legacy sources."""

    def __init__(
        self,
        retriever: TextRetriever,
        snapshot: SourceSnapshot,
        publication: "ActivePublication | None",
    ) -> None:
        self._retriever = retriever
        self._snapshot = snapshot
        self._publication = publication
        self._verified = False

    @property
    def snapshot(self) -> SourceSnapshot:
        return self._snapshot

    @property
    def publication(self) -> "ActivePublication | None":
        return self._publication

    def verify(self) -> None:
        """Check a published source/index pair once within this operation's pin.

        Explicit legacy snapshots retain their historical behavior: retrieval
        requires their prepared index, while clarification can inspect only the source.
        Every new pin verifies published artifacts afresh.
        """
        if self._verified:
            return
        with _read_timeout():
            if self.publication:
                expected = self.publication.manifest
                manifest = self._retriever._manifest(self.snapshot)
                if (
                    self.snapshot.fingerprint != expected.snapshot_sha256
                    or manifest != expected.index
                ):
                    raise IndexNotReady(
                        "The configured retrieval index differs from the publication."
                    )
        self._verified = True

    def retrieve(self, query: str, *, k: int = 3) -> Retrieval:
        _validate_query(query, k)
        with _read_timeout():
            self.verify()
            return self._retriever._retrieve(self.snapshot, query, k=k)
