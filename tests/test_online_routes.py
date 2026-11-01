"""Original-evidence evaluation across routes and conversation resets."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from test_answers_api import models as models
from test_family_graph import family_batch as family_batch
from test_family_graph import install_family
from test_feedback_api import feedback_client as feedback_client
from test_feedback_api import feedback_clock as feedback_clock
from test_investigation_api import decision, finish, publish
from test_investigation_api import investigator_models as investigator_models

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.feedback import FeedbackPolicy
from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.models import Models
from ask_phil.online_evaluation import OnlinePolicy
from ask_phil.online_workflow import OnlineEvaluation
from ask_phil.parentage import ClaimBatch


def test_graph_and_investigation_assessments_preserve_the_actual_route_evidence(
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
    uri = f"sqlite:///{tmp_path}/online-routes.db"
    responses = []
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
                "route": "graph",
                "question": "Who are Ben's ancestors?",
                "graph": {"character_id": "ben-mitchell", "direction": "ancestors"},
            },
            {"snapshot_id": seed.snapshot_id, "route": "investigation", "question": part},
            {
                "snapshot_id": family_batch.snapshot_id,
                "route": "graph",
                "question": "Who are Sharon's biological parents?",
                "graph": {"character_id": "sharon-watts", "direction": "ancestors"},
            },
        ):
            answered = client.post("/v1/answers", json=request)
            answered.raise_for_status()
            responses.append(answered.json()["response"])
    evaluation = OnlineEvaluation(database_url, uri, policy=OnlinePolicy(background_rate=1))
    assert evaluation.process().completed == 3
    now = datetime.now(UTC)
    report = evaluation.report(
        FeedbackCohort(
            served_from=now - timedelta(hours=1),
            served_until=now + timedelta(hours=1),
            feedback_as_of=now,
        )
    )
    assert {evaluation.inspect(j.job_id).response.route for j in report.jobs} == {
        "graph",
        "investigation",
    }
    for job, original in zip(report.jobs, responses, strict=True):
        assert evaluation.inspect(job.job_id).response.model_dump(mode="json") == original
        assert job.checks is not None
        if original["citations"]:
            assert job.checks.citation_integrity is True
        else:
            assert job.checks.citation_integrity is None
            assert job.checks.context_available is False
            assert job.support is None
            assert job.checks.reference_correctness is None


def test_follow_up_and_reset_feedback_assess_the_two_original_turns(
    feedback_client: TestClient,
    database_url: str,
    tmp_path: Path,
) -> None:
    session = feedback_client.post("/v1/sessions").json()
    sid = session["session"]["session_id"]
    headers = {"Authorization": "Bearer " + session["session_token"]}
    responses = []
    for question in ("When did Phil arrive?", "When did he first arrive?"):
        answered = feedback_client.post(
            f"/v1/sessions/{sid}/turns",
            headers=headers,
            json={"snapshot_id": "phil-arrival-v1", "question": question},
        )
        answered.raise_for_status()
        responses.append(answered.json()["response"])
    assert (
        feedback_client.post(f"/v1/sessions/{sid}/reset", headers=headers).json()["history"] == []
    )
    for response in responses:
        feedback_client.post(
            f"/v1/sessions/{sid}/responses/{response['response_id']}/feedback",
            headers={"Authorization": "Bearer " + session["feedback_token"]},
            json={
                "submission_id": str(uuid4()),
                "policy_version": "feedback-v1",
                "rating": "helpful",
            },
        ).raise_for_status()
    evaluation = OnlineEvaluation(
        database_url, f"sqlite:///{tmp_path}/feedback.db", policy=OnlinePolicy(background_rate=0)
    )
    assert evaluation.process().completed == 2
    now = datetime.now(UTC)
    report = evaluation.report(
        FeedbackCohort(
            served_from=now - timedelta(hours=1),
            served_until=now + timedelta(hours=1),
            feedback_as_of=now,
        )
    )
    assert (report.feedback.counts.eligible, report.feedback.counts.positive) == (2, 2)
    turns = [evaluation.inspect(j.job_id).response.conversation for j in report.jobs]
    assert {turn.turn_number for turn in turns if turn is not None} == {1, 2}
