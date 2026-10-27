"""Versioned review, publication and recovery through public application boundaries."""

from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from llama_index.core.embeddings import MockEmbedding
from test_answers_api import models as models
from test_parentage import reference_batch

from ask_phil.api import create_app
from ask_phil.claims import ClaimReview
from ask_phil.family_graph import FamilyGraph, FamilyQuery
from ask_phil.models import Models
from ask_phil.publications import PublicationStore
from ask_phil.refresh_journal import RefreshFailed
from ask_phil.retrieval import IndexNotReady
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration


def test_review_publishes_corrected_graph_and_preserves_inspectable_history(
    database_url: str, tmp_path: Path
) -> None:
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest

    snapshot, batch, reviews = reference_batch()
    correct = batch.claims[0]
    mistaken = correct.model_copy(update={"claim_id": "mistaken-negation", "polarity": "negated"})
    batch = batch.model_copy(update={"claims": (correct, mistaken)})
    original_reviews = (
        reviews[0],
        reviews[0].model_copy(
            update={
                "claim_id": mistaken.claim_id,
                "claim_sha256": mistaken.fingerprint,
            }
        ),
    )
    store = EvidenceStore(database_url)
    store.load(snapshot)
    graph = FamilyGraph(database_url)
    original = graph.install(batch, original_reviews)
    reviewer = KnowledgeReview(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    before = reviewer.inspect(snapshot.snapshot_id)
    request = ReviewRequest(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        graphs=before.graphs,
        family_reviews=(
            ClaimReview(
                claim_id=mistaken.claim_id,
                claim_sha256=mistaken.fingerprint,
                verdict="superseded",
                superseded_by=(correct.claim_id,),
                reviewer="synthetic-correction-regression",
                note="The birth passage supports the positive assertion, not this negation.",
            ),
        ),
    )
    published = reviewer.apply(request)
    current = PublicationStore(database_url).active()
    assert published.status == "published"
    assert current.manifest.snapshot_id != snapshot.snapshot_id
    result = graph.query(
        current.manifest.snapshot_id,
        FamilyQuery(
            character_id="ben-mitchell",
            direction="ancestors",
        ),
    )
    assert [path.characters for path in result.paths] == [("ben-mitchell", "phil-mitchell")]
    inspected = reviewer.inspect(current.manifest.snapshot_id)
    assert inspected.history[-1].request == request
    assert inspected.family is not None
    assert inspected.family.batch.claims == batch.claims
    assert (
        next(r for r in inspected.family.reviews if r.claim_id == mistaken.claim_id).verdict
        == "superseded"
    )
    assert graph.audit(snapshot.snapshot_id) == original
    assert store.snapshot(current.manifest.snapshot_id).passages == snapshot.passages
    assert current.manifest.graphs == inspected.graphs
    assert reviewer.apply(request).status == "skipped"


@pytest.mark.parametrize("models", [{"forbid_chat": True}], indirect=True)
def test_text_and_graph_answers_explain_the_same_pinned_dispute(
    database_url: str, tmp_path: Path, models: Models
) -> None:
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest

    snapshot, batch, reviews = reference_batch()
    batch = batch.model_copy(update={"claims": (batch.claims[0],)})
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(batch, (reviews[0],))
    reviewer = KnowledgeReview(database_url, models.embedding, models.settings.embedding_id, 3)
    before = reviewer.inspect(snapshot.snapshot_id)
    request = ReviewRequest(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        graphs=before.graphs,
        family_reviews=(
            reviews[0].model_copy(
                update={
                    "verdict": "disputed",
                    "note": "Synthetic review disagreement; do not assert this link.",
                }
            ),
        ),
    )
    reviewer.apply(request)
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/review.db")
    ) as client:
        for route in ("text_rag", "graph"):
            payload: dict[str, object] = {
                "question": "Who is Ben Mitchell's father?",
                "route": route,
            }
            if route == "graph":
                payload["graph"] = {"character_id": "ben-mitchell", "direction": "ancestors"}
            response = client.post("/v1/answers", json=payload)
            assert response.status_code == 200, response.text
            answer = response.json()["response"]
            assert "Unresolved source disagreement" in answer["answer"]
            assert "no established connection" in answer["answer"]
            assert answer["review_notices"][0]["claim_id"] == "phil-ben"
            assert answer["citations"]
            assert (
                answer["publication"]["compatibility_id"]
                == PublicationStore(database_url).active().compatibility_id
            )
            if route == "graph":
                assert answer["graph"]["paths"] == []
            for citation in answer["citations"]:
                assert client.get(citation["resolve_path"]).status_code == 200


def test_failed_projection_preserves_last_usable_publication_and_retry_is_inspectable(
    database_url: str,
) -> None:
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest

    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(batch, reviews)
    reviewer = KnowledgeReview(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    before = reviewer.inspect(snapshot.snapshot_id)
    reviewer.apply(
        ReviewRequest(
            snapshot_id=before.snapshot_id,
            snapshot_sha256=before.snapshot_sha256,
            graphs=before.graphs,
            family_reviews=(reviews[0],),
        )
    )
    active = PublicationStore(database_url).active()
    pinned = reviewer.retriever.pin()
    request = ReviewRequest(
        snapshot_id=active.manifest.snapshot_id,
        snapshot_sha256=active.manifest.snapshot_sha256,
        graphs=reviewer.inspect(active.manifest.snapshot_id).graphs,
        family_reviews=(
            reviews[0].model_copy(
                update={"verdict": "disputed", "note": "Synthetic failure/recovery case."}
            ),
        ),
    )
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(
            "ALTER TABLE family_edges ADD CONSTRAINT reject_review CHECK (false) NOT VALID"
        )
        try:
            with pytest.raises(RefreshFailed) as failure:
                reviewer.apply(request)
            failed = PublicationStore(database_url).run(failure.value.run_id)
            assert failed.status == "failed"
            assert failed.snapshot_id is not None
            assert reviewer.inspect(failed.snapshot_id).history[-1].request == request
            with pytest.raises(IndexNotReady, match="not been published"):
                reviewer.retriever.pin(failed.snapshot_id)
            with pytest.raises(IndexNotReady, match="not been published"):
                FamilyGraph(database_url).query(
                    failed.snapshot_id,
                    FamilyQuery(character_id="ben-mitchell", direction="ancestors"),
                )
            assert PublicationStore(database_url).active() == active
            assert FamilyGraph(database_url).audit(failed.snapshot_id) is None
        finally:
            conn.execute("ALTER TABLE family_edges DROP CONSTRAINT reject_review")
    retried = reviewer.apply(request)
    assert retried.status == "published"
    assert PublicationStore(database_url).active().generation == active.generation + 1
    assert pinned.snapshot.snapshot_id == active.manifest.snapshot_id
    assert pinned.retrieve("Ben's father").snapshot.snapshot_id == active.manifest.snapshot_id


def test_interrupted_indexing_keeps_previous_graph_and_resumes_the_same_review(
    database_url: str,
) -> None:
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest

    class InterruptedEmbedding(MockEmbedding):
        def _get_text_embedding(self, text: str) -> list[float]:
            raise KeyboardInterrupt("External embedding work interrupted.")

    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(batch, reviews)
    reviewer = KnowledgeReview(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    before = reviewer.inspect(snapshot.snapshot_id)
    reviewer.apply(
        ReviewRequest(
            snapshot_id=before.snapshot_id,
            snapshot_sha256=before.snapshot_sha256,
            graphs=before.graphs,
            family_reviews=(reviews[0],),
        )
    )
    active = PublicationStore(database_url).active()
    request = ReviewRequest(
        snapshot_id=active.manifest.snapshot_id,
        snapshot_sha256=active.manifest.snapshot_sha256,
        graphs=reviewer.inspect(active.manifest.snapshot_id).graphs,
        family_reviews=(
            reviews[0].model_copy(
                update={"verdict": "disputed", "note": "Synthetic interrupted review."}
            ),
        ),
    )
    interrupted = KnowledgeReview(
        database_url, InterruptedEmbedding(embed_dim=3), "test-embedding-v1", 3
    )
    with pytest.raises(KeyboardInterrupt):
        interrupted.apply(request)
    run = PublicationStore(database_url).runs()[0]
    assert run.status == "interrupted" and run.phase == "indexing"
    assert PublicationStore(database_url).active() == active
    assert run.snapshot_id is not None
    with pytest.raises(IndexNotReady):
        FamilyGraph(database_url).query(
            run.snapshot_id, FamilyQuery(character_id="ben-mitchell", direction="ancestors")
        )
    assert reviewer.apply(request).status == "published"


@pytest.mark.parametrize("later_outcome", ["superseded", "disputed", "uncertain", "unsupported"])
def test_published_correction_history_survives_later_review_and_explains_current_accounts(
    database_url: str, later_outcome: str
) -> None:
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest

    snapshot, original, reviews = reference_batch()
    current = original.claims[0]
    old = current.model_copy(update={"claim_id": "earlier-negation", "polarity": "negated"})
    raw = original.model_copy(update={"claims": (old, current)})
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(raw, (reviews[0],))
    reviewer = KnowledgeReview(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    before = reviewer.inspect(snapshot.snapshot_id)
    retirement = ClaimReview(
        claim_id=old.claim_id,
        claim_sha256=old.fingerprint,
        verdict="superseded",
        superseded_by=(current.claim_id,),
        reviewer="synthetic-history",
        note="Original negation was wrong; retain this historical correction link.",
    )
    reviewer.apply(
        ReviewRequest(
            snapshot_id=before.snapshot_id,
            snapshot_sha256=before.snapshot_sha256,
            graphs=before.graphs,
            family_reviews=(retirement,),
        )
    )
    first = reviewer.inspect(PublicationStore(database_url).active().manifest.snapshot_id)
    terminal = current.model_copy(update={"claim_id": "latest-parentage", "parent_role": "parent"})
    changed = ClaimReview.model_validate(
        {
            **reviews[0].model_dump(),
            "verdict": later_outcome,
            "superseded_by": (terminal.claim_id,) if later_outcome == "superseded" else (),
            "note": "Later synthetic review changes the current interpretation.",
        }
    )
    changes = (
        (
            changed,
            reviews[0].model_copy(
                update={"claim_id": terminal.claim_id, "claim_sha256": terminal.fingerprint}
            ),
        )
        if later_outcome == "superseded"
        else (changed,)
    )
    result = reviewer.apply(
        ReviewRequest(
            snapshot_id=first.snapshot_id,
            snapshot_sha256=first.snapshot_sha256,
            graphs=first.graphs,
            family_reviews=changes,
            new_family_claims=(terminal,) if later_outcome == "superseded" else (),
        )
    )
    assert result.snapshot_id is not None
    latest = reviewer.inspect(result.snapshot_id)
    assert len(latest.history) == 2
    assert latest.family is not None
    assert next(r for r in latest.family.reviews if r.claim_id == old.claim_id) == retirement
    assert reviewer.inspect(first.snapshot_id) == first
    graph = FamilyGraph(database_url).query(
        result.snapshot_id, FamilyQuery(character_id="ben-mitchell", direction="ancestors")
    )
    notices = reviewer.retriever.pin().retrieve("Ben's father", k=1).review_notices
    predecessor = next(n for n in notices if n.claim_id == old.claim_id)
    if later_outcome == "superseded":
        assert graph.paths[0].edges[0].claim_ids == ("latest-parentage",)
        assert (
            "Current replacement source account: Phil Mitchell as Ben Mitchell's biological parent"
            in predecessor.explanation
        )
    else:
        assert not graph.paths
        assert "Current replacement remains held" in predecessor.explanation
        assert {n.claim_id for n in notices} == {old.claim_id, current.claim_id}


def test_review_inspection_is_read_only_and_exposes_source_spans_and_history(
    database_url: str, tmp_path: Path
) -> None:
    snapshot, batch, reviews = reference_batch()
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(batch, reviews)
    with TestClient(
        create_app(database_url, tracking_uri=f"sqlite:///{tmp_path}/inspection.db")
    ) as client:
        response = client.get(f"/v1/snapshots/{snapshot.snapshot_id}/reviews")
        assert response.status_code == 200
        body = response.json()
        assert body["family"]["batch"]["catalogue"]["characters"]
        assert body["family"]["admission"]["decisions"][-1]["reasons"] == ["non_biological"]
        assert body["evidence"][0]["text"] == snapshot.passages[0].text
        assert body["history"] == []
        assert (
            client.post(f"/v1/snapshots/{snapshot.snapshot_id}/reviews", json={}).status_code == 405
        )


def test_dispute_follows_corrected_child_from_retrieved_predecessor(database_url: str) -> None:
    import hashlib

    from ask_phil.claims import ClaimEvidence
    from ask_phil.evidence import Passage, SourceSnapshot
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest
    from ask_phil.parentage import ClaimBatch

    class PredecessorEmbedding(MockEmbedding):
        def _get_text_embedding(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0] if "earlier account" in text else [0.0, 1.0, 0.0]

        def _get_query_embedding(self, query: str) -> list[float]:
            return [1.0, 0.0, 0.0]

    pilot = Path("docs/implementation/issue-15")
    snapshot = SourceSnapshot.model_validate_json(
        (pilot / "synthetic-dispute-source.json").read_bytes()
    )
    batch = ClaimBatch.model_validate_json((pilot / "synthetic-dispute-claims.json").read_bytes())
    current, competing = batch.claims
    text = (
        "Synthetic earlier account misidentifies Peggy in a claim about "
        "Phil Mitchell being Ben's biological father."
    )
    passage = Passage(
        evidence_id="synthetic-earlier-account",
        text=text,
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        start=0,
        end=len(text),
    )
    snapshot = snapshot.model_copy(
        update={
            "snapshot_id": "synthetic-corrected-child",
            "passages": (*snapshot.passages, passage),
        }
    )
    predecessor = current.model_copy(
        update={
            "claim_id": "mistaken-child",
            "child_id": "peggy-mitchell",
            "evidence": (
                ClaimEvidence(evidence_id=passage.evidence_id, start=0, end=len(text), quote=text),
            ),
        }
    )
    raw = batch.model_copy(
        update={
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "claims": (predecessor, current),
        }
    )
    supported = ClaimReview(
        claim_id=current.claim_id,
        claim_sha256=current.fingerprint,
        verdict="supported",
        reviewer="synthetic-corrected-child",
        note="The source identifies Ben as the child; the earlier Peggy identity was wrong.",
    )
    EvidenceStore(database_url).load(snapshot)
    graph = FamilyGraph(database_url)
    graph.install(raw, (supported,))
    reviewer = KnowledgeReview(
        database_url, PredecessorEmbedding(embed_dim=3), "test-embedding-v1", 3
    )
    before = reviewer.inspect(snapshot.snapshot_id)
    correction = reviewer.apply(
        ReviewRequest(
            snapshot_id=before.snapshot_id,
            snapshot_sha256=before.snapshot_sha256,
            graphs=before.graphs,
            family_reviews=(
                ClaimReview(
                    claim_id=predecessor.claim_id,
                    claim_sha256=predecessor.fingerprint,
                    verdict="superseded",
                    superseded_by=(current.claim_id,),
                    reviewer=supported.reviewer,
                    note=supported.note,
                ),
            ),
        )
    )
    assert correction.snapshot_id is not None
    corrected = reviewer.inspect(correction.snapshot_id)
    disputed = tuple(
        ClaimReview(
            claim_id=claim.claim_id,
            claim_sha256=claim.fingerprint,
            verdict="disputed",
            reviewer="synthetic-corrected-child",
            note="The Phil and Grant accounts conflict; neither establishes Ben's father.",
        )
        for claim in (current, competing)
    )
    outcome = reviewer.apply(
        ReviewRequest(
            snapshot_id=corrected.snapshot_id,
            snapshot_sha256=corrected.snapshot_sha256,
            graphs=corrected.graphs,
            family_reviews=disputed,
            new_family_claims=(competing,),
        )
    )
    assert outcome.snapshot_id is not None
    assert not graph.query(
        outcome.snapshot_id, FamilyQuery(character_id="ben-mitchell", direction="ancestors")
    ).paths
    retrieved = reviewer.retriever.pin().retrieve("The earlier account", k=1)
    assert [hit.passage.evidence_id for hit in retrieved.hits] == [passage.evidence_id]
    assert {notice.claim_id for notice in retrieved.review_notices} == {
        predecessor.claim_id,
        current.claim_id,
        competing.claim_id,
    }
    assert {eid for notice in retrieved.review_notices for eid in notice.evidence_ids} == {
        passage.evidence_id,
        "synthetic-account-1",
        "synthetic-account-2",
    }
    current_notices = [
        notice
        for notice in retrieved.review_notices
        if notice.claim_id in {current.claim_id, competing.claim_id}
    ]
    assert all(
        notice.disputed and "Unresolved source disagreement" in notice.explanation
        for notice in current_notices
    )


@pytest.mark.parametrize("models", [{"forbid_chat": True}], indirect=True)
def test_dispute_keeps_both_source_accounts_or_abstains_at_the_context_limit(
    database_url: str, tmp_path: Path, models: Models
) -> None:
    import json

    from pydantic import TypeAdapter

    from ask_phil.evidence import SourceSnapshot
    from ask_phil.execution import ExecutionLimits
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest
    from ask_phil.parentage import ClaimBatch

    pilot = Path("docs/implementation/issue-15")
    snapshot = SourceSnapshot.model_validate_json(
        (pilot / "synthetic-dispute-source.json").read_bytes()
    )
    batch = ClaimBatch.model_validate_json((pilot / "synthetic-dispute-claims.json").read_bytes())
    reviews = TypeAdapter(tuple[ClaimReview, ...]).validate_json(
        (pilot / "synthetic-dispute-reviews.json").read_bytes()
    )
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(batch, reviews)
    reviewer = KnowledgeReview(database_url, models.embedding, models.settings.embedding_id, 3)
    inspected = reviewer.inspect(snapshot.snapshot_id)
    request = ReviewRequest.model_validate(
        {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "graphs": inspected.graphs.model_dump(),
            **json.loads((pilot / "synthetic-dispute-action.json").read_bytes()),
        }
    )
    reviewer.apply(request)
    one_hit = reviewer.retriever.pin().retrieve("Ben's father", k=1)
    assert len(one_hit.hits) == 1
    assert {n.claim_id for n in one_hit.review_notices} == {
        "synthetic-father-1",
        "synthetic-father-2",
    }
    for limit in (1200, 250):
        with TestClient(
            create_app(
                database_url,
                models=models,
                tracking_uri=f"sqlite:///{tmp_path}/budget.db",
                execution_limits=ExecutionLimits(context_bytes=limit),
            )
        ) as client:
            result = client.post("/v1/answers", json={"question": "Who is Ben Mitchell's father?"})
            assert result.status_code == 200, result.text
            answer = result.json()["response"]
            if limit == 1200:
                assert answer["status"] == "partial"
                assert "Phil Mitchell" in answer["answer"] and "Grant Mitchell" in answer["answer"]
                assert "Synthetic" in answer["answer"]
                assert {c["evidence_id"] for c in answer["citations"]} == {
                    "synthetic-account-1",
                    "synthetic-account-2",
                }
            else:
                assert answer["status"] == "insufficient_evidence"
                assert answer["citations"] == []


def test_maintainer_can_supply_a_new_supported_correction_without_editing_the_raw_claim(
    database_url: str,
) -> None:
    from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest

    snapshot, batch, reviews = reference_batch()
    correct = batch.claims[0]
    mistaken = correct.model_copy(update={"claim_id": "incorrect-parentage", "polarity": "negated"})
    raw = batch.model_copy(update={"claims": (mistaken,)})
    EvidenceStore(database_url).load(snapshot)
    graph = FamilyGraph(database_url)
    original = graph.install(raw, ())
    reviewer = KnowledgeReview(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    before = reviewer.inspect(snapshot.snapshot_id)
    request = ReviewRequest(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        graphs=before.graphs,
        new_family_claims=(correct,),
        family_reviews=(
            reviews[0],
            ClaimReview(
                claim_id=mistaken.claim_id,
                claim_sha256=mistaken.fingerprint,
                verdict="superseded",
                superseded_by=(correct.claim_id,),
                reviewer="synthetic-correction-regression",
                note="The source supports the newly supplied positive assertion.",
            ),
        ),
    )
    outcome = reviewer.apply(request)
    assert outcome.snapshot_id is not None
    corrected = reviewer.inspect(outcome.snapshot_id)
    assert corrected.family is not None
    assert corrected.family.batch.claims == (mistaken, correct)
    assert graph.audit(snapshot.snapshot_id) == original
    assert graph.query(
        outcome.snapshot_id, FamilyQuery(character_id="ben-mitchell", direction="ancestors")
    ).paths[0].characters == ("ben-mitchell", "phil-mitchell")
