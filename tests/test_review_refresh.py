"""Review and source refresh share the same compatible publication and recovery lifecycle."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from llama_index.core.embeddings import MockEmbedding
from test_refresh import prefect_backend as prefect_backend
from test_refresh import source_batch as source_batch

from ask_phil.claims import ClaimEvidence
from ask_phil.classified_facts import ContextClaim
from ask_phil.event_graph import EventGraph, EventQuery
from ask_phil.ingestion import build_snapshot, source_input_fingerprint
from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest
from ask_phil.publications import PublicationStore, RefreshRun
from ask_phil.refresh import SourceRefresh
from ask_phil.retrieval import IndexNotReady
from ask_phil.source_records import SourceBatch
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventReview

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("prefect_backend")]


def test_unchanged_source_refresh_preserves_review_and_rollback_restores_all_artifacts(
    database_url: str, source_batch: SourceBatch
) -> None:
    snapshot = build_snapshot(source_batch, "synthetic-review-import")
    EvidenceStore(database_url).load(snapshot)
    passage = snapshot.passages[0]
    fact = ContextClaim(
        claim_id="workshop",
        kind="unclassified",
        character_ids=("sharon-watts",),
        theme=None,
        classification_gap="A synthetic workshop fact outside the event taxonomy.",
        evidence=(
            ClaimEvidence(
                evidence_id=passage.evidence_id, start=0, end=len(passage.text), quote=passage.text
            ),
        ),
    )
    batch = EventBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=source_batch.catalogue,
        extractor="synthetic-reviewed-fixture",
        claims=(),
        context_claims=(fact,),
    )
    review = EventReview(
        claim_id=fact.claim_id,
        claim_sha256=fact.fingerprint,
        verdict="supported",
        reviewer="synthetic-regression",
        note="The source describes the workshop.",
    )
    EventGraph(database_url).install(batch, (review,))
    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    publications = PublicationStore(database_url)
    index = refresh.retriever.prepare(snapshot.snapshot_id)
    run = RefreshRun(
        run_id=uuid4(),
        flow_run_id=uuid4(),
        started_at=datetime.now(UTC),
        status="running",
        input_sha256=source_input_fingerprint(source_batch),
    )
    with publications.writer() as conn:
        publications.publish(snapshot, index, run, conn)
    baseline = publications.active()
    reviewer = KnowledgeReview(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    inspected = reviewer.inspect(snapshot.snapshot_id)
    reviewer.apply(
        ReviewRequest(
            snapshot_id=snapshot.snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            graphs=inspected.graphs,
            event_reviews=(
                review.model_copy(
                    update={
                        "verdict": "disputed",
                        "note": "Unresolved synthetic classification dispute.",
                    }
                ),
            ),
        )
    )
    reviewed = publications.active()

    unchanged = refresh.run(source_batch)

    assert unchanged.status == "skipped"
    assert publications.active() == reviewed
    assert refresh.rollback().status == "rolled_back"
    restored = publications.active()
    assert restored.compatibility_id == baseline.compatibility_id
    assert reviewer.retriever.pin().publication == restored
    query = EventQuery(kind="life_events", character_id="sharon-watts")
    with pytest.raises(IndexNotReady, match="withdrawn"):
        EventGraph(database_url).query(reviewed.manifest.snapshot_id, query)
    in_flight = EventGraph(database_url).query(
        reviewed.manifest.snapshot_id, query, publication=reviewed
    )
    assert reviewed.manifest.graphs is not None
    assert in_flight.graph_sha256 == reviewed.manifest.graphs.event
    assert EventGraph(database_url).text_context(
        restored.manifest.snapshot_id, (passage.evidence_id,)
    ) == (fact,)
