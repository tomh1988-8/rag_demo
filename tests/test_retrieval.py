from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from llama_index.core.embeddings import MockEmbedding
from psycopg import sql

from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionBudget, ExecutionLimits
from ask_phil.publications import PublicationStore, RefreshRun
from ask_phil.retrieval import IndexNotReady, TextRetriever
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration


def test_prepared_index_exposes_reproducible_source_and_artifact_identity(
    database_url: str, seed: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(seed)
    retriever = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)

    manifest = retriever.prepare(seed.snapshot_id)

    assert manifest.snapshot_sha256 == seed.fingerprint
    assert manifest.embedding_id == "test-embedding-v1"
    assert manifest.dimensions == 3
    assert manifest.passages == 1
    restarted = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    assert restarted.manifest(seed.snapshot_id) == manifest
    assert restarted.prepare(seed.snapshot_id) == manifest


def test_vector_retrieval_returns_resolvable_captured_passages_after_restart(
    database_url: str, seed: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(seed)
    retriever = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    retriever.prepare(seed.snapshot_id)
    restarted = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)

    pinned = restarted.pin(seed.snapshot_id)
    result = pinned.retrieve("When did Phil arrive?", k=3)

    assert pinned.snapshot == seed
    assert pinned.publication is None
    assert result.snapshot.fingerprint == seed.fingerprint
    assert [hit.passage.evidence_id for hit in result.hits] == ["phil-arrival-001"]
    assert result.hits[0].passage.text == (
        "Phil Mitchell first arrives in Walford in February 1990 to open an automobile repair "
        "shop, known as The Arches;"
    )
    assert result.hits[0].similarity == pytest.approx(1.0)


def test_index_rejects_passages_too_long_for_the_embedding_input_budget(
    database_url: str, seed: SourceSnapshot
) -> None:
    import hashlib

    text = "Unreviewed lengthy text. " * 100
    long_passage = seed.passages[0].model_copy(
        update={
            "text": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "end": seed.passages[0].start + len(text),
        }
    )
    large = seed.model_copy(update={"snapshot_id": "large-fixture", "passages": (long_passage,)})
    EvidenceStore(database_url).load(large)
    retriever = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)

    with pytest.raises(ValueError, match="embedding input budget"):
        retriever.prepare(large.snapshot_id)
    with pytest.raises(IndexNotReady):
        retriever.retrieve(large.snapshot_id, "What happened?")


def test_reindexing_is_idempotent_and_retrieval_cannot_cross_snapshot_or_model_identity(
    database_url: str, seed: SourceSnapshot
) -> None:
    import hashlib

    text = "A different captured passage."
    other_passage = seed.passages[0].model_copy(
        update={
            "text": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "end": len(text),
        }
    )
    other = seed.model_copy(update={"snapshot_id": "other-snapshot", "passages": (other_passage,)})
    store = EvidenceStore(database_url)
    store.load(seed)
    store.load(other)
    retriever = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    retriever.prepare(seed.snapshot_id)
    retriever.prepare(seed.snapshot_id)
    retriever.prepare(other.snapshot_id)
    original = retriever.retrieve(seed.snapshot_id, "What happened?")
    assert len(original.hits) == 1
    assert original.hits[0].passage == seed.passages[0]
    changed_model = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v2", 3)
    with pytest.raises(IndexNotReady):
        changed_model.retrieve(seed.snapshot_id, "What happened?")


@pytest.mark.parametrize("damage", ["vectors", "publication-index", "publication-source"])
def test_pinned_publication_rejects_incompatible_artifacts_before_model_work(
    database_url: str, damage: str
) -> None:
    source = SourceSnapshot.model_validate_json(
        Path("data/seed/context-fit-legacy-v1.json").read_bytes()
    )
    EvidenceStore(database_url).load(source)
    retriever = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    index = retriever.prepare(source.snapshot_id)
    publications = PublicationStore(database_url)
    with publications.writer() as conn:
        publications.publish(
            source,
            index,
            RefreshRun(
                run_id=uuid4(),
                flow_run_id=uuid4(),
                started_at=datetime.now(UTC),
                status="running",
                input_sha256=source.fingerprint,
            ),
            conn,
        )
    with psycopg.connect(database_url) as conn:
        if damage == "vectors":
            table = conn.execute(
                "SELECT tablename FROM pg_tables WHERE tablename LIKE 'data_passages_%'"
            ).fetchone()
            assert table is not None
            conn.execute(
                sql.SQL("UPDATE {} SET embedding = '[1,0,0]'").format(sql.Identifier(table[0]))
            )
        else:
            location = (
                "{index,artifact_sha256}" if damage == "publication-index" else "{snapshot_sha256}"
            )
            conn.execute(
                "UPDATE snapshot_publications SET manifest = jsonb_set(manifest, %s, %s)",
                (location, '"' + "0" * 64 + '"'),
            )
    pinned = retriever.pin()
    budget = ExecutionBudget(ExecutionLimits())
    with budget.activate(), pytest.raises(IndexNotReady, match="artifacts|publication"):
        pinned.retrieve("What happened?")
    assert budget.record().model_calls == 0
