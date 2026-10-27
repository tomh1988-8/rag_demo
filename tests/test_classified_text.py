from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_answers_api import models as models
from test_life_events import life_reference

from ask_phil.answers import assemble_context, context_text
from ask_phil.api import create_app
from ask_phil.event_graph import EventGraph, EventQuery
from ask_phil.models import Models
from ask_phil.retrieval import RetrievedPassage, TextRetriever
from ask_phil.storage import EvidenceStore


@pytest.mark.parametrize(
    "models",
    [
        {
            "draft": {
                "answer": (
                    "Right, listen. Grant played Sharon's account of her affair with me "
                    "to a packed pub."
                ),
                "evidence_ids": ["tape-revelation"],
            }
        }
    ],
    indirect=True,
)
def test_unclassified_fact_remains_retrievable_and_answerable_without_a_graph_edge(
    database_url: str, tmp_path: Path, models: Models
) -> None:
    snapshot, batch, reviews = life_reference()
    snapshot = snapshot.model_copy(
        update={
            "snapshot_id": "classified-text-fixture",
            "passages": tuple(p for p in snapshot.passages if p.evidence_id == "tape-revelation"),
        }
    )
    batch = batch.model_copy(
        update={
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "claims": (),
            "context_claims": (batch.context_claims[1],),
        }
    )
    reviews = tuple(r for r in reviews if r.claim_id == "tape-revelation")
    EvidenceStore(database_url).load(snapshot)
    graph = EventGraph(database_url)
    graph.install(batch, reviews)
    retriever = TextRetriever(database_url, models.embedding, models.settings.embedding_id, 3)
    retriever.prepare(snapshot.snapshot_id)
    retrieved = retriever.retrieve(snapshot.snapshot_id, "What did Grant play to the pub?")
    assert retrieved.hits[0].passage.text == snapshot.passages[0].text
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/classified.db")
    ) as client:
        answer = client.post(
            "/v1/answers",
            json={
                "snapshot_id": snapshot.snapshot_id,
                "question": "What did Grant play to the pub?",
            },
        ).json()["response"]
        assert answer["status"] == "answered"
        assert "Grant played Sharon's account" in answer["answer"]
        assert "Classification gap:" in answer["answer"]
        assert "Public revelation of an affair has no checked event category" in answer["answer"]
        assert len(answer["context_claims"]) == 1
        assert client.get(answer["citations"][0]["resolve_path"]).status_code == 200
    result = graph.query(
        snapshot.snapshot_id,
        EventQuery(
            kind="life_events", character_id="grant-mitchell", participant_id="sharon-watts"
        ),
    )
    assert result.status == "empty" and not result.claims


def test_reviewed_classifications_count_toward_the_serialized_context_budget() -> None:
    snapshot, batch, _ = life_reference()
    passage = snapshot.passages[-1]
    hit = RetrievedPassage(passage=passage, similarity=1)
    budget = len(context_text((passage,)).encode())
    assert assemble_context((hit,), budget) == (passage,)
    assert assemble_context((hit,), budget, context_claims=batch.context_claims) == ()
    context = assemble_context((hit,), 1200, context_claims=batch.context_claims)
    assert context == (passage,)
    assert len(context_text(context, batch.context_claims).encode()) <= 1200
