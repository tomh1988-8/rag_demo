"""Cached deliveries keep one generation for context-only semantic assessment."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from test_answer_cache import ask
from test_answer_cache import cache_client as cache_client
from test_answer_cache import cache_clock as cache_clock
from test_answer_cache import cache_models as cache_models
from test_answers_api import models as models
from test_refresh import prefect_backend as prefect_backend
from test_source_windows import window_source as window_source

from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionPolicies
from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.online_evaluation import OnlinePolicy
from ask_phil.online_judging import OnlineJudgeScope, ScopedSupportControl
from ask_phil.online_workflow import OnlineEvaluation
from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
from ask_phil.semantic_judge import SupportInput, SupportJudge, SupportPassage

pytestmark = pytest.mark.integration


def test_cached_deliveries_reuse_one_semantic_result_without_becoming_independent_examples(
    cache_client: TestClient,
    database_url: str,
    window_source: SourceSnapshot,
    tmp_path: Path,
    prefect_backend: None,
) -> None:
    cold = ask(cache_client)["response"]
    warm = ask(cache_client)["response"]
    supported = "Synthetic fixture: I was accused of a fictional robbery."
    assert cold["answer"] == supported
    assert warm["answer"] == supported
    calibration = Path("docs/implementation/issue-9/judge-calibration.json")
    profile = OpenRouterProfile.model_validate(
        json.loads(calibration.read_bytes())["judge_profile"]
    )
    context = tuple(
        SupportPassage(evidence_id=p["evidence_id"], text=p["text"]) for p in cold["context"]
    )
    scope = OnlineJudgeScope.model_validate_json(
        Path("data/references/online-support-scope-v1.json").read_bytes()
    ).model_copy(
        update={
            "scope_id": "cache-authored-fixture-v1",
            "reviewer": "Authored source contract; no live model or human calibration claim.",
            "controls": tuple(
                ScopedSupportControl(
                    case_id="cache-supported" if label else "cache-contradicted",
                    supplied=SupportInput(answer=answer, context=context),
                    snapshot_sha256=window_source.fingerprint,
                    expected_supported=label,
                    review_note="Fixture distinguishes accusation from conviction.",
                )
                for answer, label in (
                    (supported, True),
                    ("Synthetic fixture: I was convicted of that fictional robbery.", False),
                )
            ),
        }
    )
    scope_path = tmp_path / "authored-scope.json"
    scope_path.write_text(scope.model_dump_json())

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
                                "tag": profile.provider,
                                "name": "Test | " + profile.canonical_slug,
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
        supplied = json.loads(json.loads(request.content)["messages"][1]["content"])
        assert supplied == SupportInput(answer=supported, context=context).model_dump(mode="json")
        return httpx.Response(
            200,
            json={
                "id": "controlled-cache-judgment",
                "model": profile.answer_model,
                "provider": "OpenAI",
                "usage": {"cost": 0.001, "prompt_tokens": 100, "completion_tokens": 20},
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "supported": True,
                                    "evidence_ids": [window_source.passages[0].evidence_id],
                                    "reason": "Fixture explicitly states accused.",
                                }
                            ),
                        },
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        judge = SupportJudge(
            OpenRouterChat(profile, "synthetic-key", Budget(tmp_path / "judge.sqlite"), client),
            policies=ExecutionPolicies(online_enabled=True),
        )
        evaluation = OnlineEvaluation(
            database_url,
            f"sqlite:///{tmp_path}/cache.db",
            policy=OnlinePolicy(background_rate=1),
            judge=judge,
            calibration=calibration,
            scope=scope_path,
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
    assert report.support_scored == 2
    assert report.distinct_support_generations == 1
    assert report.online_judge_calls == 1
    assert sum(j.support_reused for j in report.jobs) == 1
    assert report.online_judge_cost_usd == 0.001
    assert {str(j.generation_id) for j in report.jobs} == {cold["generation_id"]}
