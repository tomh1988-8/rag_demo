"""Automatic choices through real API, PostgreSQL tools and actual MLflow traces."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from mlflow import MlflowClient

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionLimits
from ask_phil.models import Models
from ask_phil.parentage import ClaimBatch
from ask_phil.storage import EvidenceStore
from ask_phil.text_retrieval import TextPolicy

pytestmark = pytest.mark.integration
pytest_plugins = ("test_investigation_api",)


def test_ordinary_question_uses_admitted_biological_graph_and_retains_actual_choice(
    database_url: str,
    family_batch: ClaimBatch,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    from test_family_graph import install_family
    from test_investigation_api import publish

    install_family(database_url, family_batch)
    snapshot = EvidenceStore(database_url).snapshot(family_batch.snapshot_id)
    models = investigator_models([])
    publish(database_url, snapshot, models)
    uri = f"sqlite:///{tmp_path}/routing.db"
    with TestClient(create_app(database_url, models=models, tracking_uri=uri)) as client:
        result = client.post(
            "/v1/answers",
            json={"question": "Who are Ben Mitchell's biological parents?", "route": "auto"},
        )
        assert result.status_code == 200, result.text
        receipt = result.json()
        answer = receipt["response"]
        assert answer["route"] == "graph"
        assert not answer.get("route_override", False)
        assert answer["execution"]["model_calls"] == 0
        assert {c["evidence_id"] for c in answer["citations"]} == {"family-ben-birth"}
        assert answer["routing"]["eligibility"]["eligible"]
        assert answer["routing"]["selection"] == "automatic"
        assert [s["route"] for s in answer["routing"]["stages"]] == ["graph"]
        trace = MlflowClient(tracking_uri=uri).get_trace(answer["trace_id"], flush=True)
        assert trace.data.spans[0].outputs == answer
        original = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": "Bearer " + receipt["read_token"]},
        )
        assert original.json() == answer


@pytest.mark.parametrize("model_limit,failure", [(4, False), (6, True)])
def test_failed_or_unaffordable_escalation_preserves_the_supported_partial_answer(
    database_url: str,
    family_batch: ClaimBatch,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
    model_limit: int,
    failure: bool,
) -> None:
    from test_family_graph import install_family
    from test_investigation_api import finish, publish

    install_family(database_url, family_batch)
    snapshot = EvidenceStore(database_url).snapshot(family_batch.snapshot_id)
    part = "Who are Ben Mitchell's biological parents and grandmother?"
    first = finish(part)["action"]["draft"]
    first.update(
        status="partial",
        evidence_ids=["family-ben-birth"],
        answer="Kathy and I are Ben's biological parents. His grandmother is unresolved.",
        unanswered=["Who is Ben Mitchell's biological grandmother?"],
    )
    outputs = [first]
    if failure:
        outputs.append({"invalid": True, "_usage": {"prompt_eval_count": None, "eval_count": None}})
    models = investigator_models(outputs)
    publish(database_url, snapshot, models)
    uri = f"sqlite:///{tmp_path}/recovery.db"
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=uri,
            text_policy=TextPolicy(per_query_k=1, selected_hits=1),
            execution_limits=ExecutionLimits(
                model_calls=model_limit, tool_calls=2, context_bytes=6000
            ),
        )
    ) as client:
        result = client.post("/v1/answers", json={"question": part})
        assert result.status_code == 200, result.text
        receipt = result.json()
        answer = receipt["response"]
        assert answer["status"] == "partial"
        assert answer["answer"] == first["answer"]
        assert [c["evidence_id"] for c in answer["citations"]] == ["family-ben-birth"]
        reasons = {c["reason"] for c in answer["routing"]["checks"]}
        if failure:
            assert "retained_prior_support" in reasons
            assert answer["routing"]["stop_reason"] == "malformed_output"
            assert len(answer["routing"]["stages"]) == 2
            assert answer["usage"]["input_tokens"] is None
            assert answer["usage"]["output_tokens"] is None
            assert answer["routing"]["stages"][0]["accounting"]["usage"]["input_tokens"] == 40
        else:
            assert "no_escalation_budget" in reasons
            assert len(answer["routing"]["stages"]) == 1
            assert answer["execution"]["model_calls"] == 2
        original = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": "Bearer " + receipt["read_token"]},
        )
        assert original.json() == answer


def test_sufficient_text_does_not_investigate_a_complex_looking_question(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    from test_investigation_api import finish, publish

    draft = finish("When did Phil arrive?")["action"]["draft"]
    models = investigator_models([draft])
    publish(database_url, seed, models)
    uri = f"sqlite:///{tmp_path}/sufficient.db"
    with TestClient(create_app(database_url, models=models, tracking_uri=uri)) as client:
        result = client.post(
            "/v1/answers",
            json={"question": "Explain when Phil arrived and how the captured date supports it."},
        )
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["status"] == "answered"
        assert answer["route"] == "text_rag"
        assert [s["route"] for s in answer["routing"]["stages"]] == ["text_rag"]
        assert {c["reason"] for c in answer["routing"]["checks"]} >= {"sufficient_text_evidence"}
        assert answer["usage"] == {"input_tokens": 40, "output_tokens": 60, "embedding_tokens": 7}
        assert answer["text_pipeline"]["cache_enabled"] is False


def test_evidence_gap_investigates_with_prior_support_and_one_shared_budget(
    database_url: str,
    family_batch: ClaimBatch,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    from test_family_graph import install_family
    from test_investigation_api import decision, finish, publish

    install_family(database_url, family_batch)
    snapshot = EvidenceStore(database_url).snapshot(family_batch.snapshot_id)
    part = "Who are Ben Mitchell's biological parents and grandmother?"
    first = finish(part)["action"]["draft"]
    first.update(
        status="partial",
        evidence_ids=["family-ben-birth"],
        answer="Kathy and I are Ben's biological parents. His grandmother is unresolved.",
        unanswered=["Who is Ben Mitchell's biological grandmother?"],
    )
    final = finish(part, "family-peggy-phil")
    final["coverage"][0]["evidence_ids"] = ["family-ben-birth", "family-peggy-phil"]
    final["action"]["draft"].update(
        evidence_ids=["family-ben-birth", "family-peggy-phil"],
        answer="Kathy and I are Ben's biological parents. My mother Peggy is his grandmother.",
    )
    models = investigator_models(
        [
            first,
            decision(
                "family",
                {"character_id": "ben-mitchell", "direction": "ancestors", "max_depth": 2},
                part,
            ),
            final,
        ]
    )
    publish(database_url, snapshot, models)
    uri = f"sqlite:///{tmp_path}/escalation.db"
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=uri,
            text_policy=TextPolicy(per_query_k=1, selected_hits=1),
            execution_limits=ExecutionLimits(model_calls=6, tool_calls=2, context_bytes=6000),
        )
    ) as client:
        result = client.post("/v1/answers", json={"question": part})
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["status"] == "answered"
        assert answer["route"] == "investigation"
        assert {c["evidence_id"] for c in answer["citations"]} == {
            "family-ben-birth",
            "family-peggy-phil",
        }
        assert answer["execution"]["model_calls"] == 4
        assert answer["execution"]["tool_calls"] == 2
        assert answer["usage"] == {"input_tokens": 120, "output_tokens": 180, "embedding_tokens": 7}
        assert answer["investigation"]["initial_context_ids"] == ["family-ben-birth"]
        assert answer["text_pipeline"]["final_context_ids"] == ["family-ben-birth"]
        stages = answer["routing"]["stages"]
        assert [s["route"] for s in stages] == ["text_rag", "investigation"]
        assert stages[1]["execution_before"]["model_calls"] == 2
        assert stages[1]["execution_before"]["tool_calls"] == 1
        trace = MlflowClient(tracking_uri=uri).get_trace(answer["trace_id"], flush=True)
        assert trace.data.spans[0].outputs == answer


@pytest.mark.parametrize("override", [False, True])
def test_unsupported_thematic_graph_uses_text_or_an_explicit_qualified_empty_override(
    database_url: str,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
    override: bool,
) -> None:
    from test_investigation_api import publish

    models = investigator_models(
        [
            {
                "status": "insufficient_evidence",
                "answer": "The captured evidence cannot establish that theme.",
                "evidence_ids": [],
                "unanswered": [],
                "qualifications": [],
            }
        ]
    )
    publish(database_url, seed, models)
    request: dict[str, Any] = {
        "question": "How is Phil Mitchell connected to the theme of betrayal?"
    }
    if override:
        request.update(route="graph", graph={"kind": "theme", "character_id": "phil-mitchell"})
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/theme.db")
    ) as client:
        result = client.post("/v1/answers", json=request)
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["status"] == "insufficient_evidence"
        assert answer["citations"] == []
        assert answer.get("route_override", False) is override
        if override:
            assert answer["graph"]["status"] == "ineligible"
            assert not answer["routing"]["eligibility"]["eligible"]
        else:
            assert answer["route"] == "text_rag"
            assert "text_fallback" in {c["reason"] for c in answer["routing"]["checks"]}


@pytest.mark.parametrize(
    "question,evidence",
    [
        (
            "Explain the relationship history between Sharon Watts and Den Watts.",
            "history-den-adoption",
        ),
        ("Show Sharon Watts's pregnancy and death history.", "sharon-christmas-pregnancy"),
        ("How are Ben Mitchell and Peggy Mitchell connected?", "family-peggy-phil"),
    ],
)
def test_automatic_questions_execute_each_other_supported_graph_family(
    database_url: str,
    connection_snapshot: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
    question: str,
    evidence: str,
) -> None:
    from test_investigation_api import publish

    models = investigator_models([])
    publish(database_url, connection_snapshot, models)
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=f"sqlite:///{tmp_path}/families.db",
            execution_limits=ExecutionLimits(context_bytes=6000),
        )
    ) as client:
        result = client.post("/v1/answers", json={"question": question})
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["route"] == "graph"
        assert evidence in {c["evidence_id"] for c in answer["citations"]}
        assert answer["execution"]["model_calls"] == 0
        assert answer["execution"]["tool_calls"] == 1
        assert answer["routing"]["eligibility"]["eligible"]


def test_empty_eligible_graph_falls_back_to_text_within_the_same_publication(
    database_url: str,
    connection_snapshot: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    from test_investigation_api import publish

    models = investigator_models(
        [
            {
                "status": "insufficient_evidence",
                "answer": "I can't establish this connection in the captured material.",
                "evidence_ids": [],
                "unanswered": [],
                "qualifications": [],
            }
        ]
    )
    publish(database_url, connection_snapshot, models)
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=f"sqlite:///{tmp_path}/empty.db",
            execution_limits=ExecutionLimits(model_calls=2, tool_calls=2, context_bytes=6000),
        )
    ) as client:
        result = client.post(
            "/v1/answers", json={"question": "How are Kat Slater and Ben Mitchell connected?"}
        )
        assert result.status_code == 200, result.text
        answer = result.json()["response"]
        assert answer["route"] == "text_rag"
        assert answer["status"] == "insufficient_evidence"
        assert [s["route"] for s in answer["routing"]["stages"]] == ["graph", "text_rag"]
        assert answer["routing"]["stages"][0]["graph"]["status"] == "empty"
        assert "graph_evidence_gap" in {c["reason"] for c in answer["routing"]["checks"]}
        assert answer["execution"]["tool_calls"] == 2
        assert answer["snapshot_sha256"] == connection_snapshot.fingerprint
