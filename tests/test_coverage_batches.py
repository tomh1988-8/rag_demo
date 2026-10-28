"""Restartable coverage uses the agreed extraction boundary and a controlled provider."""

import hashlib
import json
from pathlib import Path

import httpx
import pytest
from mlflow import MlflowClient

from ask_phil.openrouter import Budget, OpenRouterProfile


def test_a_shared_story_cannot_leak_between_coverage_splits() -> None:
    from ask_phil.coverage import CoveragePlan

    batch = {
        "kind": "family",
        "snapshot": "source.json",
        "snapshot_file_sha256": "a" * 64,
        "reference": "reference.json",
        "reference_sha256": "b" * 64,
        "story_groups": ["lucy-birth"],
        "reference_complete": True,
        "review_note": "Both pages describe the same birth.",
        "gaps": ["Selected birth only."],
    }
    with pytest.raises(ValueError, match="split"):
        CoveragePlan.model_validate(
            {
                "version": 1,
                "roster": ["ian-beale", "lucy-beale"],
                "batches": [
                    dict(
                        batch, batch_id="ian", character_id="ian-beale", split="exposed_development"
                    ),
                    dict(batch, batch_id="lucy", character_id="lucy-beale", split="held_out"),
                ],
            }
        )


@pytest.mark.parametrize("finish_reason", ["stop", "length"])
def test_completed_or_failed_batches_resume_without_repeating_paid_work(
    tmp_path: Path, finish_reason: str
) -> None:
    from ask_phil.coverage import CoverageRun

    source = Path("data/seed/family-pilot-v1.json")
    reference = Path("data/references/parentage-v1.json")
    expected = json.loads(reference.read_bytes())
    plan = {
        "version": 1,
        "roster": ["ben-mitchell", "peggy-mitchell"],
        "batches": [
            {
                "batch_id": name,
                "character_id": name,
                "kind": "family",
                "snapshot": str(source.resolve()),
                "snapshot_file_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "reference": str(reference.resolve()),
                "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
                "split": "exposed_development",
                "story_groups": ["mitchell-parentage"],
                "reference_complete": True,
                "review_note": "Synthetic orchestration case; labels reuse reviewed pilot.",
                "gaps": ["Selected spans only; other profile history is unannotated."],
            }
            for name in ("ben-mitchell", "peggy-mitchell")
        ],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    profile = OpenRouterProfile.model_validate_json(
        Path("config/evaluation-sol-low.json").read_bytes(), extra="ignore"
    )
    tracking = MlflowClient(tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}")
    tracking.create_experiment(
        "ask-phil-offline_evaluation", artifact_location=(tmp_path / "traces").as_uri()
    )

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200, json={"data": {"limit": 5, "limit_reset": None, "limit_remaining": 5}}
            )
        if request.url.path.endswith("/endpoints"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "endpoints": [
                            {
                                "tag": "openai",
                                "name": "OpenAI | openai/gpt-6-sol-20260922",
                                "supported_parameters": [
                                    "structured_outputs",
                                    "response_format",
                                    "reasoning",
                                    "max_tokens",
                                ],
                            }
                        ]
                    }
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "synthetic-coverage",
                "model": profile.canonical_slug,
                "provider": "OpenAI",
                "choices": [
                    {
                        "finish_reason": finish_reason,
                        "message": {"content": json.dumps({"claims": expected["expected_claims"]})},
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.00001},
            },
        )

    budget = Budget(tmp_path / "budget.sqlite")
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        runner = CoverageRun(profile, "synthetic-key", client, budget=budget, tracking=tracking)
        first = runner.run(plan_path, tmp_path / "run", max_batches=1)
        attempted_state = "complete" if finish_reason == "stop" else "failed"
        assert [row["state"] for row in first["batches"]] == [attempted_state, "pending"]
        retained = (tmp_path / "run/ben-mitchell.json").read_bytes()
        second = runner.run(plan_path, tmp_path / "run", max_batches=1)
        third = runner.run(plan_path, tmp_path / "run", max_batches=1)

    assert (
        second["state"]
        == third["state"]
        == ("complete" if finish_reason == "stop" else "incomplete")
    )
    assert (tmp_path / "run/ben-mitchell.json").read_bytes() == retained
    assert budget.summary() == (0.00002, 0)
