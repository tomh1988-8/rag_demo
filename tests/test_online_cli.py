"""Maintainer inspection through the approved CLI transport."""

import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from test_answers_api import models as models
from test_feedback_api import feedback_client as feedback_client
from test_feedback_api import feedback_clock as feedback_clock


def test_maintainer_cli_reports_and_inspects_original_online_evidence(
    feedback_client: TestClient, database_url: str, tmp_path: Path
) -> None:
    from ask_phil.online_evaluation import OnlinePolicy
    from ask_phil.online_workflow import OnlineEvaluation

    response = feedback_client.post(
        "/v1/answers", json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"}
    ).json()["response"]
    policy = OnlinePolicy(background_rate=1)
    policy_path = tmp_path / "online-policy.json"
    policy_path.write_text(policy.model_dump_json())
    uri = f"sqlite:///{tmp_path}/feedback.db"
    OnlineEvaluation(database_url, uri, policy=policy).process()
    environment = {
        **os.environ,
        "DATABASE_URL": database_url,
        "MLFLOW_TRACKING_URI": uri,
        "ASK_PHIL_ONLINE_POLICY": str(policy_path),
    }
    command = [sys.executable, "-m", "ask_phil.cli"]
    reported = subprocess.run(
        [*command, "online-report"], env=environment, capture_output=True, text=True
    )
    assert reported.returncode == 0, reported.stderr
    report = json.loads(reported.stdout)
    assert report["feedback"]["counts"]["eligible"] == 1
    assert report["completed"] == 1
    inspected = subprocess.run(
        [*command, "online-inspect", report["jobs"][0]["job_id"]],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(inspected.stdout)["response"] == response
    assert "read_token" not in inspected.stdout
