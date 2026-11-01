from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from test_answers_api import models as models
from test_family_graph import family_batch as family_batch
from test_family_graph import install_family
from test_feedback_api import feedback_client as feedback_client
from test_feedback_api import feedback_clock as feedback_clock
from test_feedback_api import record_feedback_evidence
from test_investigation_api import decision, finish, publish
from test_investigation_api import investigator_models as investigator_models

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.feedback import FeedbackPolicy, FeedbackStore
from ask_phil.feedback_delivery import deliver_feedback
from ask_phil.models import Models
from ask_phil.parentage import ClaimBatch

pytestmark = pytest.mark.integration


def test_feedback_cannot_acknowledge_a_write_rejected_by_postgresql(
    feedback_client: TestClient, database_url: str
) -> None:
    answer = feedback_client.post(
        "/v1/answers", json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"}
    ).json()
    path = f"/v1/responses/{answer['response']['response_id']}/feedback"
    headers = {"Authorization": f"Bearer {answer['read_token']}"}
    with psycopg.connect(database_url, autocommit=True) as admin:
        database = sql.Identifier(admin.info.dbname)
        admin.execute(
            sql.SQL("ALTER DATABASE {} SET default_transaction_read_only = on").format(database)
        )
        try:
            rejected = feedback_client.post(
                path,
                headers=headers,
                json={
                    "submission_id": str(uuid4()),
                    "policy_version": "feedback-v1",
                    "rating": "helpful",
                },
            )
            assert rejected.status_code == 503
            assert "feedback_id" not in rejected.json()
        finally:
            admin.execute(
                sql.SQL("ALTER DATABASE {} RESET default_transaction_read_only").format(database)
            )
    assert feedback_client.get(path, headers=headers).json()["revisions"] == []


def test_feedback_capability_outlives_chat_and_redacts_its_own_bearer_value(
    feedback_client: TestClient, feedback_clock: list[datetime]
) -> None:
    session = feedback_client.post("/v1/sessions").json()
    sid = session["session"]["session_id"]
    session_headers = {"Authorization": f"Bearer {session['session_token']}"}
    feedback_clock[0] += timedelta(minutes=30)
    answer = feedback_client.post(
        f"/v1/sessions/{sid}/turns",
        headers=session_headers,
        json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"},
    ).json()
    path = f"/v1/sessions/{sid}/responses/{answer['response']['response_id']}/feedback"
    headers = {"Authorization": f"Bearer {session['feedback_token']}"}
    feedback_clock[0] += timedelta(hours=3)
    assert feedback_client.get(f"/v1/sessions/{sid}", headers=session_headers).status_code == 404
    accepted = feedback_client.post(
        path,
        headers=headers,
        json={
            "submission_id": str(uuid4()),
            "policy_version": "feedback-v1",
            "rating": "skip",
            "comment": session["feedback_token"],
        },
    )
    assert accepted.status_code == 202
    assert accepted.json()["expires_at"] == session["feedback_expires_at"]
    inspected = feedback_client.get(path, headers=headers)
    assert inspected.json()["response"] == answer["response"]
    assert inspected.json()["revisions"][0]["submission"]["comment"] == "[REDACTED]"
    assert session["feedback_token"] not in inspected.text
    feedback_clock[0] += timedelta(days=30)
    assert feedback_client.get(path, headers=headers).status_code == 404


def test_invalid_response_ids_are_private_even_before_any_answer_has_been_served(
    feedback_client: TestClient,
) -> None:
    session = feedback_client.post("/v1/sessions").json()
    sid = session["session"]["session_id"]
    path = f"/v1/sessions/{sid}/responses/{uuid4()}/feedback"
    response = feedback_client.post(
        path,
        json={
            "submission_id": str(uuid4()),
            "policy_version": "feedback-v1",
            "rating": "helpful",
        },
        headers={"Authorization": f"Bearer {session['feedback_token']}"},
    )
    assert response.status_code == 404
    assert "trace" not in response.json()


def test_feedback_preserves_healthy_graph_and_investigation_execution_lineage(
    database_url: str,
    family_batch: ClaimBatch,
    seed: SourceSnapshot,
    investigator_models: Callable[[list[dict[str, Any]]], Models],
    tmp_path: Path,
) -> None:
    install_family(database_url, family_batch)
    part = "When did Phil arrive?"
    configured = investigator_models(
        [decision("text_search", {"query": part, "k": 1}, part), finish(part)]
    )
    publish(database_url, seed, configured)
    uri = f"sqlite:///{tmp_path}/routes.db"
    store = FeedbackStore(database_url)
    with TestClient(
        create_app(
            database_url,
            models=configured,
            tracking_uri=uri,
            feedback_policy=FeedbackPolicy(auto_deliver=False),
        )
    ) as client:
        for request in (
            {
                "snapshot_id": family_batch.snapshot_id,
                "question": "Who are Ben's ancestors?",
                "route": "graph",
                "graph": {"character_id": "ben-mitchell", "direction": "ancestors"},
            },
            {"snapshot_id": seed.snapshot_id, "question": part, "route": "investigation"},
        ):
            answered = client.post("/v1/answers", json=request)
            assert answered.status_code == 200
            receipt = answered.json()
            response = receipt["response"]
            assert response["route"] == request["route"]
            # The reviewed family pilot has explicit incomplete ancestry coverage.
            assert response["status"] == ("partial" if request["route"] == "graph" else "answered")
            assert response["citations"]
            path = f"/v1/responses/{response['response_id']}/feedback"
            headers = {"Authorization": f"Bearer {receipt['read_token']}"}
            assert (
                client.post(
                    path,
                    headers=headers,
                    json={
                        "submission_id": str(uuid4()),
                        "policy_version": "feedback-v1",
                        "rating": "helpful",
                    },
                ).status_code
                == 202
            )
            assert deliver_feedback(store, uri).delivered == 1
            inspected = client.get(path, headers=headers).json()
            assert inspected["response"] == response
            assert len(inspected["revisions"]) == 1
            assert inspected["revisions"][0]["delivery_state"] == "delivered"
            record_feedback_evidence(f"{request['route']}-feedback", inspected)
            assert (
                store.inspect(UUID(response["response_id"]), receipt["read_token"]).response.route
                == (request["route"])
            )
