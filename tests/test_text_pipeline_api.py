import json
import subprocess
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.testclient import TestClient
from llama_index.llms.ollama import Ollama
from ollama import Client
from starlette.types import ASGIApp
from test_answers_api import models as models
from test_source_windows import window_source as window_source

from ask_phil.api import create_app
from ask_phil.claims import ClaimEvidence
from ask_phil.classified_facts import ContextClaim
from ask_phil.event_graph import EventGraph
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionLimits
from ask_phil.model_transport import local_transport
from ask_phil.models import LocalEmbedding, Models, ModelSettings
from ask_phil.retrieval import RetrievedPassage, TextRetriever
from ask_phil.source_windows import expand_context
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventReview
from ask_phil.text_retrieval import TextPolicy

pytestmark = pytest.mark.integration


def test_expanded_citation_resolves_to_the_exact_saved_revision_after_restart(
    database_url: str, window_source: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(window_source)
    context = expand_context(
        window_source,
        (RetrievedPassage(passage=window_source.passages[0], similarity=1),),
        byte_budget=1200,
    ).context
    qualification = context[1]
    another = window_source.model_copy(update={"snapshot_id": "another-window-revision"})
    EvidenceStore(database_url).load(another)

    with TestClient(create_app(database_url)) as client:
        response = client.get(
            f"/v1/snapshots/{window_source.snapshot_id}/evidence/{qualification.evidence_id}"
        )
        assert (
            client.get(
                f"/v1/snapshots/{another.snapshot_id}/evidence/{qualification.evidence_id}"
            ).status_code
            == 404
        )
    assert response.status_code == 200
    assert response.json()["matches"] == [qualification.model_dump(mode="json")]


@pytest.fixture
def pipeline_models(request: pytest.FixtureRequest) -> Models:
    options = dict(getattr(request, "param", {}))

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"model": "test-answer", "digest": "a" * 64},
                        {"model": "test-embedding", "digest": "b" * 64},
                    ]
                },
            )
        body = json.loads(request.content)
        if request.url.path == "/api/embed":
            content = str(body["input"])
            if options.get("variant_embedding_failure") and "EastEnders:" in content:
                return httpx.Response(503, json={"error": "Controlled embedding failure."})
            variant_or_qualifier = "not convicted" in content or "EastEnders:" in content
            return httpx.Response(
                200,
                json={
                    "embeddings": [[0, 1, 0] if variant_or_qualifier else [1, 0, 0]],
                    "prompt_eval_count": 3,
                },
            )
        assert request.url.path == "/api/chat"
        output: dict[str, object]
        if "variants" in body["format"]["properties"]:
            output = {
                "variants": [
                    options.get(
                        "variant", "EastEnders: Was Phil convicted of that fictional robbery?"
                    ),
                    options.get(
                        "variant", "EastEnders: Was Phil convicted of that fictional robbery?"
                    ),
                ]
            }
        else:
            evidence = json.loads(body["messages"][-1]["content"].split("Captured evidence: ")[1])
            output = {
                "answer": options.get(
                    "answer",
                    (
                        "Synthetic example: I was accused but not convicted "
                        "of that fictional robbery."
                    ),
                ),
                "status": "answered",
                "evidence_ids": [p["evidence_id"] for p in evidence],
                "qualifications": [],
                "unanswered": [],
            }
        return httpx.Response(
            200,
            json={
                "model": "test-answer",
                "done": True,
                "prompt_eval_count": 7,
                "eval_count": 5,
                "message": {"role": "assistant", "content": json.dumps(output)},
            },
        )

    transport = httpx.MockTransport(provider)
    settings = ModelSettings(
        answer_model="test-answer",
        answer_digest="a" * 64,
        embedding_model="test-embedding",
        embedding_digest="b" * 64,
        embedding_dimensions=3,
    )
    return Models(
        settings=settings,
        embedding=LocalEmbedding(
            "test-embedding", Client(host="http://model.invalid", transport=transport)
        ),
        llm=Ollama(
            model="test-answer",
            context_window=4096,
            additional_kwargs={"num_predict": 256},
            client=Client(host="http://model.invalid", transport=transport),
        ),
    )


def test_combined_pipeline_answers_original_question_with_fused_expanded_evidence(
    database_url: str, window_source: SourceSnapshot, pipeline_models: Models, tmp_path: Path
) -> None:
    EvidenceStore(database_url).load(window_source)
    TextRetriever(
        database_url, pipeline_models.embedding, pipeline_models.settings.embedding_id, 3
    ).prepare(window_source.snapshot_id)
    with TestClient(
        create_app(
            database_url,
            models=pipeline_models,
            tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
            text_policy=TextPolicy(mode="combined", per_query_k=1, selected_hits=2),
            execution_limits=ExecutionLimits(model_calls=5, tool_calls=3),
        )
    ) as client:
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": window_source.snapshot_id,
                "question": "Was Phil convicted of that fictional robbery?",
            },
        )
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["status"] == "answered"
        assert "not convicted" in answer["answer"]
        record = answer["text_pipeline"]
        assert record["resolved_question"] == "Was Phil convicted of that fictional robbery?"
        assert record["variants"]["queries"] == [
            "Was Phil convicted of that fictional robbery?",
            "EastEnders: Was Phil convicted of that fictional robbery?",
        ]
        assert len(record["rankings"]) == 2
        assert len(record["expansion"]["windows"]) == 1
        assert answer["execution"]["model_calls"] == 4
        assert answer["usage"] == {"input_tokens": 14, "output_tokens": 10, "embedding_tokens": 6}
        assert len(record["model_executions"]) == 2
        assert answer["route"] == "text_rag"
        for citation in answer["citations"]:
            resolved = client.get(citation["resolve_path"])
            assert resolved.status_code == 200
            assert resolved.json()["matches"][0]["text"] == citation["text"]


def test_small_request_budget_preserves_original_query_and_answer_capacity(
    database_url: str, window_source: SourceSnapshot, pipeline_models: Models, tmp_path: Path
) -> None:
    EvidenceStore(database_url).load(window_source)
    TextRetriever(
        database_url, pipeline_models.embedding, pipeline_models.settings.embedding_id, 3
    ).prepare(window_source.snapshot_id)
    with TestClient(
        create_app(
            database_url,
            models=pipeline_models,
            tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
            text_policy=TextPolicy(mode="combined", per_query_k=1),
            execution_limits=ExecutionLimits(model_calls=2, tool_calls=1),
        )
    ) as client:
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": window_source.snapshot_id,
                "question": "Was Phil convicted of that fictional robbery?",
            },
        )
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["status"] == "answered"
        assert answer["execution"]["stop_reason"] is None
        assert answer["execution"]["model_calls"] == 2
        assert answer["text_pipeline"]["variants"]["fallback_reason"] == "fanout_budget"
        assert len(answer["text_pipeline"]["model_executions"]) == 1


def test_failed_optional_variant_transport_falls_back_without_poisoning_answer_budget(
    database_url: str,
    seed: SourceSnapshot,
    models: Models,
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    model_app = FastAPI()

    @model_app.get("/api/tags")
    def tags() -> dict[str, object]:
        return {
            "models": [
                {"model": "test-answer", "digest": "a" * 64},
                {"model": "test-embedding", "digest": "b" * 64},
            ]
        }

    @model_app.post("/api/chat")
    async def chat(request: Request) -> Response:
        body = await request.json()
        if "variants" in body["format"]["properties"]:
            return Response(" " * 270000, media_type="application/json")
        return Response(
            json.dumps(
                {
                    "model": "test-answer",
                    "done": True,
                    "prompt_eval_count": 11,
                    "eval_count": 9,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "answer": "I arrived in February 1990.",
                                "status": "answered",
                                "evidence_ids": ["phil-arrival-001"],
                                "unanswered": [],
                                "qualifications": [],
                            }
                        ),
                    },
                }
            ),
            media_type="application/json",
        )

    EvidenceStore(database_url).load(seed)
    TextRetriever(database_url, models.embedding, models.settings.embedding_id, 3).prepare(
        seed.snapshot_id
    )
    with http_server(model_app) as model_url:
        bounded = replace(
            models,
            llm=Ollama(
                model="test-answer",
                context_window=4096,
                additional_kwargs={"num_predict": 256},
                client=Client(host=model_url, transport=local_transport(model_url)),
            ),
        )
        with TestClient(
            create_app(
                database_url,
                models=bounded,
                tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
                text_policy=TextPolicy(mode="fusion"),
                execution_limits=ExecutionLimits(model_calls=5, tool_calls=3, seconds=10),
            )
        ) as client:
            response = client.post(
                "/v1/answers",
                json={
                    "snapshot_id": seed.snapshot_id,
                    "question": "When did Phil Mitchell arrive?",
                },
            )
    assert response.status_code == 200, response.text
    answer = response.json()["response"]
    assert answer["status"] == "answered"
    assert answer["execution"]["stop_reason"] is None
    assert answer["execution"]["model_calls"] == 3
    assert answer["text_pipeline"]["variants"]["fallback_reason"] == "variant_generation_failed"
    assert answer["text_pipeline"]["model_executions"][0]["failure_type"] == "malformed_output"


def test_expansion_preserves_reviewed_classification_qualifications(
    database_url: str,
    window_source: SourceSnapshot,
    pipeline_models: Models,
    tmp_path: Path,
) -> None:
    assert window_source.imported is not None
    EvidenceStore(database_url).load(window_source)
    passage = window_source.passages[0]
    claim = ContextClaim(
        claim_id="fictional-robbery-gap",
        kind="unclassified",
        character_ids=("phil-mitchell",),
        theme=None,
        classification_gap="This synthetic incident has no reviewed event category.",
        evidence=(
            ClaimEvidence(
                evidence_id=passage.evidence_id, start=0, end=len(passage.text), quote=passage.text
            ),
        ),
    )
    batch = EventBatch(
        snapshot_id=window_source.snapshot_id,
        snapshot_sha256=window_source.fingerprint,
        catalogue=window_source.imported.catalogue,
        extractor="authored-classification-control",
        claims=(),
        context_claims=(claim,),
    )
    EventGraph(database_url).install(
        batch,
        (
            EventReview(
                claim_id=claim.claim_id,
                claim_sha256=claim.fingerprint,
                verdict="supported",
                reviewer="authored structural reference",
                note="Synthetic classification, not canon.",
            ),
        ),
    )
    TextRetriever(
        database_url, pipeline_models.embedding, pipeline_models.settings.embedding_id, 3
    ).prepare(window_source.snapshot_id)
    with TestClient(
        create_app(
            database_url,
            models=pipeline_models,
            tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
            text_policy=TextPolicy(mode="expansion", per_query_k=1),
        )
    ) as client:
        response = client.post(
            "/v1/answers",
            json={
                "snapshot_id": window_source.snapshot_id,
                "question": "Was Phil convicted of that fictional robbery?",
            },
        )
    assert response.status_code == 200, response.text
    answer = response.json()["response"]
    assert answer["status"] == "answered"
    assert "Classification gap:" in answer["answer"]
    assert answer["context_claims"][0]["claim_id"] == claim.claim_id
    appendix = answer["text_pipeline"]
    assert set(appendix["final_context_ids"]).isdisjoint(appendix["dropped_evidence_ids"])


@pytest.mark.parametrize("pipeline_models", [{"variant_embedding_failure": True}], indirect=True)
def test_failed_secondary_query_retains_original_evidence_and_answer_capacity(
    database_url: str,
    window_source: SourceSnapshot,
    pipeline_models: Models,
    tmp_path: Path,
) -> None:
    EvidenceStore(database_url).load(window_source)
    TextRetriever(
        database_url, pipeline_models.embedding, pipeline_models.settings.embedding_id, 3
    ).prepare(window_source.snapshot_id)
    with TestClient(
        create_app(
            database_url,
            models=pipeline_models,
            tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
            text_policy=TextPolicy(mode="combined", per_query_k=1),
            execution_limits=ExecutionLimits(model_calls=5, tool_calls=3),
        )
    ) as client:
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": window_source.snapshot_id,
                "question": "Was Phil convicted of that fictional robbery?",
            },
        )
    assert result.status_code == 200, result.text
    response = result.json()["response"]
    assert response["status"] == "answered"
    assert response["execution"]["stop_reason"] is None
    assert "variant_retrieval_failed" in response["text_pipeline"]["fallback_reasons"]
    assert len(response["text_pipeline"]["rankings"]) == 1


@pytest.mark.parametrize(
    "pipeline_models",
    [{"variant": "Was Grant convicted of that fictional robbery?"}],
    indirect=True,
)
def test_drifting_generated_query_uses_visible_original_query_fallback(
    database_url: str,
    window_source: SourceSnapshot,
    pipeline_models: Models,
    tmp_path: Path,
) -> None:
    EvidenceStore(database_url).load(window_source)
    TextRetriever(
        database_url, pipeline_models.embedding, pipeline_models.settings.embedding_id, 3
    ).prepare(window_source.snapshot_id)
    with TestClient(
        create_app(
            database_url,
            models=pipeline_models,
            tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
            text_policy=TextPolicy(mode="combined", per_query_k=1),
            execution_limits=ExecutionLimits(model_calls=5, tool_calls=3),
        )
    ) as client:
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": window_source.snapshot_id,
                "question": "Was Phil convicted of that fictional robbery?",
            },
        )
    answer = result.json()["response"]
    assert answer["status"] == "answered"
    assert answer["text_pipeline"]["variants"]["fallback_reason"] == "unfaithful_variants"
    assert len(answer["text_pipeline"]["rankings"]) == 1
    assert answer["execution"]["model_calls"] == 3


def test_cli_exposes_expanded_spans_and_api_abstains_when_the_window_cannot_fit(
    database_url: str,
    window_source: SourceSnapshot,
    pipeline_models: Models,
    tmp_path: Path,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    EvidenceStore(database_url).load(window_source)
    TextRetriever(
        database_url, pipeline_models.embedding, pipeline_models.settings.embedding_id, 3
    ).prepare(window_source.snapshot_id)
    app = create_app(
        database_url,
        models=pipeline_models,
        tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
        text_policy=TextPolicy(mode="expansion", per_query_k=1),
    )
    with http_server(app) as url:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "--api-url",
                url,
                "ask",
                "Was Phil convicted of that fictional robbery?",
                "--snapshot",
                window_source.snapshot_id,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        receipt = json.loads(completed.stdout)
        assert receipt["response"]["status"] == "answered"
        assert len(receipt["response"]["citations"]) == 2
        with httpx.Client(base_url=url, trust_env=False) as client:
            for citation in receipt["response"]["citations"]:
                assert (
                    client.get(citation["resolve_path"]).json()["matches"][0]["text"]
                    == citation["text"]
                )
    with TestClient(
        create_app(
            database_url,
            models=pipeline_models,
            tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
            text_policy=TextPolicy(mode="expansion", per_query_k=1),
            execution_limits=ExecutionLimits(context_bytes=180),
        )
    ) as client:
        answer = client.post(
            "/v1/answers",
            json={
                "snapshot_id": window_source.snapshot_id,
                "question": "Was Phil convicted of that fictional robbery?",
            },
        ).json()["response"]
    assert answer["status"] == "insufficient_evidence"
    assert answer["citations"] == []
    assert answer["context"] == []
    assert answer["text_pipeline"]["expansion"]["truncated"]
    assert answer["execution"]["model_calls"] == 1


@pytest.mark.parametrize("window_source", [21], indirect=True)
def test_exhausted_model_budget_abstains_when_many_spans_exceed_citation_capacity(
    database_url: str,
    window_source: SourceSnapshot,
    pipeline_models: Models,
    tmp_path: Path,
) -> None:
    EvidenceStore(database_url).load(window_source)
    TextRetriever(
        database_url, pipeline_models.embedding, pipeline_models.settings.embedding_id, 3
    ).prepare(window_source.snapshot_id)
    with TestClient(
        create_app(
            database_url,
            models=pipeline_models,
            tracking_uri=f"sqlite:///{tmp_path}/tracking.db",
            text_policy=TextPolicy(mode="expansion", per_query_k=1),
            execution_limits=ExecutionLimits(model_calls=1, context_bytes=4000),
        ),
        raise_server_exceptions=False,
    ) as client:
        result = client.post(
            "/v1/answers",
            json={
                "snapshot_id": window_source.snapshot_id,
                "question": "Was Phil convicted of that fictional robbery?",
            },
        )
    assert result.status_code == 200, result.text
    answer = result.json()["response"]
    assert answer["status"] == "insufficient_evidence"
    assert answer["execution"]["stop_reason"] == "model_call_limit"
    assert len(answer["context"]) > 20
    assert answer["citations"] == []
