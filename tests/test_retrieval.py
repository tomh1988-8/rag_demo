import pytest
from llama_index.core.embeddings import MockEmbedding

from ask_phil.evidence import SourceSnapshot
from ask_phil.retrieval import IndexNotReady, TextRetriever
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration


def test_vector_retrieval_returns_resolvable_captured_passages_after_restart(
    database_url: str, seed: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(seed)
    retriever = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    retriever.prepare(seed.snapshot_id)
    restarted = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)

    result = restarted.retrieve(seed.snapshot_id, "When did Phil arrive?", k=3)

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
