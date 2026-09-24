"""Snapshot-bound exact vector retrieval through LlamaIndex and PostgreSQL."""

import hashlib

import psycopg
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.schema import TextNode
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters, VectorStoreQuery
from llama_index.vector_stores.postgres import PGVectorStore
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool

from ask_phil.evidence import Passage, Record, SourceSnapshot
from ask_phil.storage import EvidenceStore


class IndexNotReady(ValueError):
    pass


class RetrievedPassage(Record):
    passage: Passage
    similarity: float | None


class Retrieval(Record):
    snapshot: SourceSnapshot
    hits: tuple[RetrievedPassage, ...]
    k: int
    embedding_id: str


class TextRetriever:
    def __init__(
        self, database_url: str, embedding: BaseEmbedding, embedding_id: str, dimensions: int
    ) -> None:
        self.database_url = database_url
        self.embedding = embedding
        self.embedding_id = embedding_id
        self.dimensions = dimensions

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
            create_engine_kwargs={"poolclass": NullPool},
        )

    def _filter(self, fingerprint: str) -> MetadataFilters:
        return MetadataFilters(filters=[MetadataFilter(key="snapshot_sha256", value=fingerprint)])

    def prepare(self, snapshot_id: str) -> None:
        """Maintainer operation: publish embeddings only after the complete index is ready."""
        snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
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
            key = (snapshot.fingerprint, self.embedding_id, self.dimensions)
            if conn.execute(
                """SELECT 1 FROM text_indexes WHERE
                   snapshot_sha256 = %s AND embedding_id = %s AND dimensions = %s""",
                key,
            ).fetchone():
                return
            vectors = self._vectors(setup=True)
            # A failed preparation never publishes a manifest; its orphan nodes are
            # replaced on retry while the maintainer lock prevents duplicate writes.
            vectors.delete_nodes(filters=self._filter(snapshot.fingerprint))
            for passage in snapshot.passages:
                vector = self.embedding.get_text_embedding(passage.text)
                vectors.add(
                    [
                        TextNode(
                            id_=f"{snapshot.fingerprint}:{passage.evidence_id}",
                            text=passage.text,
                            embedding=vector,
                            metadata={
                                "snapshot_sha256": snapshot.fingerprint,
                                "evidence_id": passage.evidence_id,
                            },
                        )
                    ]
                )
            conn.execute("INSERT INTO text_indexes VALUES (%s, %s, %s)", key)

    def retrieve(self, snapshot_id: str, query: str, *, k: int = 3) -> Retrieval:
        if not query.strip() or len(query) > 500 or not 1 <= k <= 20:
            raise ValueError("Retrieval requires a question of 1–500 characters and k of 1–20.")
        snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            if conn.execute("SELECT to_regclass('text_indexes')").fetchone() == (None,):
                raise IndexNotReady("Prepare this snapshot's text index before answering.")
            if not conn.execute(
                """SELECT 1 FROM text_indexes WHERE
                   snapshot_sha256 = %s AND embedding_id = %s AND dimensions = %s""",
                (snapshot.fingerprint, self.embedding_id, self.dimensions),
            ).fetchone():
                raise IndexNotReady("Prepare this snapshot with the configured embedding model.")
        result = self._vectors().query(
            VectorStoreQuery(
                query_embedding=self.embedding.get_query_embedding(query),
                similarity_top_k=k,
                filters=self._filter(snapshot.fingerprint),
            )
        )
        passages = {p.evidence_id: p for p in snapshot.passages}
        hits = tuple(
            RetrievedPassage(
                passage=passages[node.metadata["evidence_id"]],
                similarity=result.similarities[i] if result.similarities else None,
            )
            for i, node in enumerate(result.nodes or [])
        )
        return Retrieval(snapshot=snapshot, hits=hits, k=k, embedding_id=self.embedding_id)
