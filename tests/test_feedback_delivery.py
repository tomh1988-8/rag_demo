"""Actual self-hosted MLflow HTTP delivery with controlled service/time failures."""

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from mlflow import MlflowClient
from starlette.types import ASGIApp
from test_answers_api import models as models
from test_feedback_api import feedback_client as feedback_client
from test_feedback_api import feedback_clock as feedback_clock
from test_feedback_api import record_feedback_evidence

from ask_phil.api import create_app
from ask_phil.feedback import FeedbackPolicy, FeedbackStore
from ask_phil.feedback_delivery import deliver_feedback
from ask_phil.models import Models

pytestmark = pytest.mark.integration


@pytest.fixture
def mlflow_http(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_TIMEOUT", "1")
    monkeypatch.setenv("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "0")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    with (tmp_path / "mlflow-server.log").open("w") as log:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "mlflow",
                "server",
                "--backend-store-uri",
                f"sqlite:///{tmp_path}/http-mlflow.db",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--workers",
                "1",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            env={**os.environ, "MLFLOW_DISABLE_AGENT_HINT": "1"},
        )
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline and server.poll() is None:
                try:
                    if httpx.get(url + "/health", timeout=0.3, trust_env=False).is_success:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(0.1)
            else:
                pytest.fail("Local MLflow HTTP server did not start.")
            yield url
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)


def test_missing_trace_outage_lost_acknowledgement_and_restart_are_recoverable(
    feedback_client: TestClient,
    feedback_clock: list[datetime],
    database_url: str,
    models: Models,
    mlflow_http: str,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    faults = {"hidden_trace": False, "offline": False, "lose_acknowledgement": False}
    proxy = FastAPI()

    @proxy.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
    async def forward(path: str, request: Request) -> Response:
        if faults["offline"]:
            return Response(status_code=503)
        if faults["hidden_trace"] and request.method == "GET" and "/traces/" in path:
            return Response(
                json.dumps({"error_code": "RESOURCE_DOES_NOT_EXIST", "message": "Trace pending."}),
                status_code=404,
                media_type="application/json",
            )
        async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
            result = await client.request(
                request.method,
                mlflow_http + "/" + path,
                params=request.query_params,
                content=await request.body(),
                headers={"Content-Type": request.headers.get("content-type", "application/json")},
            )
        if (
            faults["lose_acknowledgement"]
            and request.method == "POST"
            and path.endswith("/assessments")
        ):
            faults["lose_acknowledgement"] = False
            return Response(status_code=503)
        return Response(
            result.content,
            status_code=result.status_code,
            media_type=result.headers.get("content-type", "application/json"),
        )

    with http_server(proxy) as tracking_uri:
        # Reuse the real captured fixture/index, with actual HTTP trace export.
        with TestClient(
            create_app(
                database_url,
                tracking_uri=tracking_uri,
                models=models,
                session_clock=lambda: feedback_clock[0],
                feedback_policy=FeedbackPolicy(auto_deliver=False),
            )
        ) as client:
            answer = client.post(
                "/v1/answers",
                json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"},
            ).json()
            response = answer["response"]
            path = f"/v1/responses/{response['response_id']}/feedback"
            headers = {"Authorization": f"Bearer {answer['read_token']}"}
            faults["hidden_trace"] = True
            accepted = client.post(
                path,
                headers=headers,
                json={
                    "submission_id": str(uuid4()),
                    "policy_version": "feedback-v1",
                    "rating": "not_helpful",
                    "categories": ["evidence"],
                },
            )
            assert accepted.status_code == 202
            store = FeedbackStore(database_url, clock=lambda: feedback_clock[0])
            assert deliver_feedback(store, tracking_uri).pending == 1
            assert client.get(path, headers=headers).json()["revisions"][0]["delivery_state"] == (
                "pending"
            )
            faults["hidden_trace"] = False
            faults["offline"] = True
            feedback_clock[0] += timedelta(seconds=6)
            assert deliver_feedback(store, tracking_uri).pending == 1
            faults["offline"] = False
            faults["lose_acknowledgement"] = True
            feedback_clock[0] += timedelta(seconds=6)
            assert deliver_feedback(store, tracking_uri).pending == 1
            assert not faults["lose_acknowledgement"], "The actual assessment POST was exercised."
        # A new API/store instance reuses the durable revision and stable assessment identity.
        feedback_clock[0] += timedelta(seconds=6)
        restarted = FeedbackStore(database_url, clock=lambda: feedback_clock[0])
        with TestClient(
            create_app(
                database_url,
                tracking_uri=tracking_uri,
                models=models,
                session_clock=lambda: feedback_clock[0],
            )
        ) as recovered:
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                inspected_response = recovered.get(path, headers=headers)
                if inspected_response.json()["revisions"][0]["delivery_state"] == "delivered":
                    break
                time.sleep(0.05)
            assert inspected_response.json()["revisions"][0]["delivery_state"] == "delivered"
        assert deliver_feedback(restarted, tracking_uri).delivered == 0
        assessments = (
            MlflowClient(tracking_uri=mlflow_http).get_trace(response["trace_id"]).info.assessments
        )
        assert len(assessments) == 1
        assert assessments[0].source.source_type == "HUMAN"
        inspected = restarted.inspect(
            response_id=UUID(response["response_id"]), token=answer["read_token"]
        )
        assert inspected.response.model_dump(mode="json") == response
        assert inspected.revisions[0].delivery_state == "delivered"
        assert inspected.revisions[0].attempts == 4
        record_feedback_evidence(
            "http-recovery",
            {
                "served_response": response,
                "feedback_receipt": accepted.json(),
                "inspection": inspected.model_dump(mode="json"),
                "assessments": [a.to_dictionary() for a in assessments],
                "tested_failures": ["hidden trace", "HTTP outage", "lost write acknowledgement"],
                "restart": "new API instance automatically delivered the retained revision",
            },
        )


def test_revised_feedback_rejects_incorrect_supersession_readback(
    feedback_client: TestClient,
    feedback_clock: list[datetime],
    database_url: str,
    models: Models,
    mlflow_http: str,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> None:
    faults = {"omit_override": False, "exercised": False}
    proxy = FastAPI()

    @proxy.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
    async def forward(path: str, request: Request) -> Response:
        async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
            result = await client.request(
                request.method,
                mlflow_http + "/" + path,
                params=request.query_params,
                content=await request.body(),
                headers={"Content-Type": "application/json"},
            )
        if (
            faults["omit_override"]
            and request.method == "GET"
            and "/assessments/" in path
            and result.is_success
        ):
            document = result.json()
            document["assessment"].pop("overrides", None)
            faults["exercised"] = True
            return Response(json.dumps(document), media_type="application/json")
        return Response(
            result.content,
            status_code=result.status_code,
            media_type=result.headers.get("content-type", "application/json"),
        )

    with http_server(proxy) as uri:
        with TestClient(
            create_app(
                database_url,
                models=models,
                tracking_uri=uri,
                session_clock=lambda: feedback_clock[0],
                feedback_policy=FeedbackPolicy(auto_deliver=False),
            )
        ) as client:
            receipt = client.post(
                "/v1/answers",
                json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"},
            ).json()
            response = receipt["response"]
            response_id = UUID(response["response_id"])
            path = f"/v1/responses/{response_id}/feedback"
            headers = {"Authorization": "Bearer " + receipt["read_token"]}
            first = client.post(
                path,
                headers=headers,
                json={
                    "submission_id": str(uuid4()),
                    "policy_version": "feedback-v1",
                    "rating": "helpful",
                },
            )
            assert first.status_code == 202
            store = FeedbackStore(database_url, tracking_uri=uri, clock=lambda: feedback_clock[0])
            assert deliver_feedback(store, uri).delivered == 1
            prior = store.inspect(response_id, receipt["read_token"]).revisions[0]
            revised = client.post(
                path,
                headers=headers,
                json={
                    "submission_id": str(uuid4()),
                    "policy_version": "feedback-v1",
                    "rating": "not_helpful",
                    "categories": ["evidence"],
                },
            )
            assert revised.status_code == 202
            assert revised.json()["revision"] == 2
            faults["omit_override"] = True
            delivery = deliver_feedback(store, uri)
            assert faults["exercised"]
            assert (delivery.delivered, delivery.pending) == (0, 1)
            pending = store.inspect(response_id, receipt["read_token"])
            assert pending.revisions[1].delivery_state == "pending"
            assert pending.revisions[1].last_failure == "ValueError"

            faults["omit_override"] = False
            feedback_clock[0] += timedelta(seconds=6)
            restarted = FeedbackStore(
                database_url, tracking_uri=uri, clock=lambda: feedback_clock[0]
            )
            assert deliver_feedback(restarted, uri).delivered == 1
            recovered = restarted.inspect(response_id, receipt["read_token"])
            assert recovered.response.model_dump(mode="json") == response
            assert recovered.revisions[1].assessment_id == pending.revisions[1].assessment_id
            assert recovered.revisions[1].delivery_state == "delivered"
            assert recovered.revisions[1].attempts == 2
            assessment = next(
                assessment
                for assessment in MlflowClient(tracking_uri=mlflow_http)
                .get_trace(response["trace_id"])
                .info.assessments
                if assessment.assessment_id == recovered.revisions[1].assessment_id
            )
            assert assessment.overrides == prior.assessment_id
            assert assessment.feedback is not None
            assert assessment.feedback.value == "not_helpful"


def test_expired_feedback_is_purged_and_cleanup_cannot_switch_mlflow_backends(
    feedback_client: TestClient,
    database_url: str,
    tmp_path: Path,
    feedback_clock: list[datetime],
) -> None:
    from ask_phil.feedback import FeedbackUnavailable

    answer = feedback_client.post(
        "/v1/answers", json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"}
    ).json()
    response = answer["response"]
    path = f"/v1/responses/{response['response_id']}/feedback"
    headers = {"Authorization": f"Bearer {answer['read_token']}"}
    assert (
        feedback_client.post(
            path,
            headers=headers,
            json={
                "submission_id": str(uuid4()),
                "policy_version": "feedback-v1",
                "rating": "helpful",
                "comment": "Remove this text after the retention period.",
            },
        ).status_code
        == 202
    )
    store = FeedbackStore(database_url, clock=lambda: feedback_clock[0])
    original_uri = f"sqlite:///{tmp_path}/feedback.db"
    assert deliver_feedback(store, original_uri).delivered == 1
    feedback_clock[0] += timedelta(days=31)
    assert feedback_client.get(path, headers=headers).status_code == 404
    # A configuration change must not mistake an empty different backend for deletion.
    cleanup = deliver_feedback(store, f"sqlite:///{tmp_path}/other-mlflow.db")
    assert cleanup.purged_interactions == 1
    assert cleanup.cleanup_pending == 1
    with pytest.raises(FeedbackUnavailable):
        store.inspect(UUID(response["response_id"]), answer["read_token"])
    original = MlflowClient(tracking_uri=original_uri)
    assert len(original.get_trace(response["trace_id"]).info.assessments) == 1
    assert deliver_feedback(store, original_uri).deleted == 1
    assert original.get_trace(response["trace_id"]).info.assessments == []
    assert deliver_feedback(store, original_uri).cleanup_pending == 0


def test_foreign_backend_cleanup_and_exports_do_not_starve_current_feedback(
    feedback_client: TestClient,
    feedback_clock: list[datetime],
    database_url: str,
    tmp_path: Path,
    models: Models,
) -> None:
    original_uri = f"sqlite:///{tmp_path}/feedback.db"
    current_uri = f"sqlite:///{tmp_path}/current-mlflow.db"
    policy = FeedbackPolicy(auto_deliver=False, delivery_batch_size=1)
    store = FeedbackStore(database_url, policy=policy, clock=lambda: feedback_clock[0])

    def submit(client: TestClient) -> dict[str, object]:
        answer = client.post(
            "/v1/answers",
            json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"},
        ).json()
        path = f"/v1/responses/{answer['response']['response_id']}/feedback"
        accepted = client.post(
            path,
            headers={"Authorization": f"Bearer {answer['read_token']}"},
            json={
                "submission_id": str(uuid4()),
                "policy_version": "feedback-v1",
                "rating": "helpful",
            },
        )
        assert accepted.status_code == 202
        response: dict[str, object] = answer["response"]
        return response

    submit(feedback_client)
    assert deliver_feedback(store, original_uri).delivered == 1
    feedback_clock[0] += timedelta(days=31)
    retained_original = submit(feedback_client)
    with TestClient(
        create_app(
            database_url,
            models=models,
            tracking_uri=current_uri,
            session_clock=lambda: feedback_clock[0],
            feedback_policy=policy,
        )
    ) as current:
        fresh = submit(current)
        result = deliver_feedback(store, current_uri)
        assert (result.delivered, result.pending, result.cleanup_pending) == (1, 1, 1)
    assert (
        len(
            MlflowClient(tracking_uri=current_uri)
            .get_trace(str(fresh["trace_id"]))
            .info.assessments
        )
        == 1
    )
    assert (
        MlflowClient(tracking_uri=original_uri)
        .get_trace(str(retained_original["trace_id"]))
        .info.assessments
        == []
    )
    assert deliver_feedback(store, original_uri).deleted == 1
    assert deliver_feedback(store, original_uri).delivered == 1
    assert deliver_feedback(store, original_uri).pending == 0
