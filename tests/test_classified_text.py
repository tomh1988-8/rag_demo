from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_answers_api import models as models
from test_investigation_api import decision, finish, publish
from test_investigation_api import investigator_models as investigator_models
from test_life_events import life_reference

from ask_phil.answers import assemble_context, context_text
from ask_phil.api import create_app
from ask_phil.event_graph import EventGraph, EventQuery
from ask_phil.execution import ExecutionLimits
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


@pytest.mark.parametrize("route", ["text_rag", "investigation"])
@pytest.mark.parametrize("gap_length", [1200, 1800])
def test_stopped_reply_fits_with_the_complete_classification_qualification(
    database_url: str,
    tmp_path: Path,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    route: str,
    gap_length: int,
) -> None:
    snapshot, batch, reviews = life_reference()
    snapshot = snapshot.model_copy(
        update={
            "snapshot_id": "qualified-stop-fixture",
            "passages": tuple(p for p in snapshot.passages if p.evidence_id == "tape-revelation"),
        }
    )
    gap = ("The checked event categories do not classify this synthetic source fact. " * 30)[
        :gap_length
    ]
    claim = batch.context_claims[1].model_copy(update={"classification_gap": gap})
    batch = batch.model_copy(
        update={
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "claims": (),
            "context_claims": (claim,),
        }
    )
    review = reviews[-1].model_copy(update={"claim_sha256": claim.fingerprint})
    EvidenceStore(database_url).load(snapshot)
    EventGraph(database_url).install(batch, (review,))
    question = "What did Grant play to the pub?"
    repeated = decision("text_search", {"query": question, "k": 1}, question)
    repeated["coverage"] = finish(question, "tape-revelation")["coverage"]
    models = investigator_models(
        [decision("text_search", {"query": question, "k": 1}, question), repeated]
    )
    publish(database_url, snapshot, models)
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=f"sqlite:///{tmp_path}/qualified-stop.db",
            execution_limits=ExecutionLimits(
                model_calls=1 if route == "text_rag" else 8, tool_calls=4, context_bytes=4000
            ),
        )
    ) as client:
        result = client.post("/v1/answers", json={"question": question, "route": route})
        assert result.status_code == 200, result.text
        receipt = result.json()
        answer = receipt["response"]
        assert len(answer["answer"]) <= 1600
        assert answer["context"][0]["text"] == snapshot.passages[0].text
        if gap_length == 1200:
            assert answer["status"] == "partial"
            assert gap in answer["answer"]
            assert "This fact remains text-only." in answer["answer"]
            assert answer["citations"][0]["text"] == snapshot.passages[0].text
            assert answer["context_claims"][0]["classification_gap"] == gap
        else:
            assert answer["status"] == "insufficient_evidence"
            assert answer["citations"] == []
            assert "qualifications" in answer["answer"]
            assert answer["unanswered"]
        saved = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert saved.json() == answer


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
