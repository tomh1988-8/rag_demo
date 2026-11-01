"""Real self-hosted MLflow failures at the evaluation boundary."""

import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime, timedelta
from threading import Event

import httpx
import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from mlflow import MlflowClient
from starlette.types import ASGIApp
from test_answers_api import models as models
from test_feedback_api import feedback_client as feedback_client
from test_feedback_api import feedback_clock as feedback_clock
from test_feedback_delivery import mlflow_http as mlflow_http
from test_online_judges import CALIBRATION
from test_online_judges import bounded_judge as bounded_judge

from ask_phil.api import create_app
from ask_phil.feedback import FeedbackPolicy
from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.models import Models
from ask_phil.online_evaluation import OnlinePolicy
from ask_phil.online_workflow import OnlineEvaluation
from ask_phil.openrouter import Budget
from ask_phil.semantic_judge import SupportJudge


@pytest.mark.parametrize("assessment_name", ["online_evidence_checks", "online_context_support"])
@pytest.mark.parametrize("interruption", ["lost_acknowledgement", "cancellation"])
@pytest.mark.parametrize(
    "models",
    [
        {
            "draft": {
                "answer": "Phil Mitchell first arrived in February 1990.",
                "evidence_ids": ["phil-arrival-001"],
            }
        }
    ],
    indirect=True,
)
def test_missing_trace_outage_and_interrupted_export_survive_restart(
    feedback_client: TestClient,
    database_url: str,
    models: Models,
    mlflow_http: str,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
    bounded_judge: tuple[SupportJudge, Budget, dict[str, str]],
    assessment_name: str,
    interruption: str,
) -> None:
    judge, ledger, _ = bounded_judge
    support = assessment_name == "online_context_support"
    cancellation = Event()
    faults = {"hidden": False, "offline": False, "interrupt_export": False}
    proxy = FastAPI()

    @proxy.api_route("/{path:path}", methods=["GET", "POST", "PATCH", "DELETE"])
    async def forward(path: str, request: Request) -> Response:
        if faults["offline"]:
            return Response(status_code=503)
        if faults["hidden"] and request.method == "GET" and "/traces/" in path:
            return Response(
                json.dumps({"error_code": "RESOURCE_DOES_NOT_EXIST", "message": "Pending"}),
                status_code=404,
                media_type="application/json",
            )
        async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
            result = await client.request(
                request.method,
                mlflow_http + "/" + path,
                params=request.query_params,
                content=await request.body(),
                headers={"Content-Type": "application/json"},
            )
        if (
            faults["interrupt_export"]
            and request.method == "POST"
            and path.endswith("/assessments")
            and json.loads(await request.body())["assessment"]["assessment_name"] == assessment_name
        ):
            faults["interrupt_export"] = False
            if interruption == "lost_acknowledgement":
                return Response(status_code=503)
            cancellation.set()
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
                feedback_policy=FeedbackPolicy(auto_deliver=False),
            )
        ) as client:
            receipt = client.post(
                "/v1/answers",
                json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"},
            ).json()
        policy = OnlinePolicy(background_rate=1, retry_seconds=0.1, max_attempts=5)
        evaluation = OnlineEvaluation(
            database_url,
            uri,
            policy=policy,
            judge=judge if support else None,
            calibration=CALIBRATION if support else None,
            cancellation=cancellation,
        )
        faults["hidden"] = True
        assert evaluation.process().pending == 1
        faults["hidden"] = False
        faults["offline"] = True
        assert evaluation.process().pending == 1
        faults["offline"] = False
        faults["interrupt_export"] = True
        assert evaluation.process().pending == 1
        assert faults["interrupt_export"] is False
        now = datetime.now(UTC)
        waiting = evaluation.report(
            FeedbackCohort(
                served_from=now - timedelta(hours=1),
                served_until=now + timedelta(hours=1),
                feedback_as_of=now,
            )
        )
        assert waiting.jobs[0].checks is not None
        assert waiting.jobs[0].exported is False
        assert waiting.oldest_pending_seconds is not None
        charged = ledger.summary()
        assert charged == ((0.001, 0) if support else (0, 0))
        cancellation.clear()
        restarted = OnlineEvaluation(
            database_url,
            uri,
            policy=policy,
            judge=judge if support else None,
            calibration=CALIBRATION if support else None,
            cancellation=cancellation,
        )
        restarted.process()
        now = datetime.now(UTC)
        report = restarted.report(
            FeedbackCohort(
                served_from=now - timedelta(hours=1),
                served_until=now + timedelta(hours=1),
                feedback_as_of=now,
            )
        )
        assert report.completed == 1
        job = report.jobs[0]
        assert job.exported is True
        assert job.attempts == 4
        assert job.failure is None
        assert job.judge_calls == int(support)
        assert ledger.summary() == charged
        assessments = (
            MlflowClient(tracking_uri=mlflow_http)
            .get_trace(receipt["response"]["trace_id"])
            .info.assessments
        )
        assert len(assessments) == (2 if support else 1)
        assert {assessment.source.source_type for assessment in assessments} == (
            {"CODE", "LLM_JUDGE"} if support else {"CODE"}
        )
