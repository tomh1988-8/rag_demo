"""Narrow support checks through the external provider and evaluation seams."""

from decimal import Decimal
from pathlib import Path

import httpx
import pytest


def test_busy_online_evaluation_is_pending_and_provider_failure_is_inspectable(
    tmp_path: Path,
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from ask_phil.execution import ExecutionPolicies
    from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
    from ask_phil.semantic_judge import SupportInput, SupportJudge, SupportPassage

    entered, release = Event(), Event()

    def provider(request: httpx.Request) -> httpx.Response:
        entered.set()
        assert release.wait(3)
        return httpx.Response(503, json={"error": "Bearer synthetic-provider-secret"})

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        judge = SupportJudge(
            OpenRouterChat(
                OpenRouterProfile(
                    answer_model="test/model",
                    canonical_slug="test/model-v1",
                    provider="test",
                    input_price_per_million=Decimal(1),
                    output_price_per_million=Decimal(2),
                ),
                "synthetic-test-key",
                Budget(tmp_path / "budget.sqlite"),
                client,
            ),
            policies=ExecutionPolicies(online_enabled=True),
        )
        supplied = SupportInput(
            answer="Phil delivers three red chairs.",
            context=(SupportPassage(evidence_id="chairs", text="Phil delivers three red chairs."),),
        )
        with ThreadPoolExecutor(max_workers=1) as workers:
            first = workers.submit(judge.assess_online, supplied)
            try:
                assert entered.wait(2)
                pending = judge.assess_online(supplied)
                assert pending.status == "pending"
                assert pending.execution.model_calls == 0
            finally:
                release.set()
            failed = first.result(timeout=3)
            assert failed.status == "failed"
            assert failed.execution.stop_reason == "provider_failure"
            assert "synthetic-provider-secret" not in failed.model_dump_json()


@pytest.mark.parametrize("enabled,expected", [(False, "disabled"), (True, "skipped")])
def test_online_evaluation_obeys_its_own_disable_and_call_budget(
    tmp_path: Path,
    enabled: bool,
    expected: str,
) -> None:
    from ask_phil.execution import ExecutionLimits, ExecutionPolicies
    from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
    from ask_phil.semantic_judge import SupportInput, SupportJudge, SupportPassage

    def provider(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Disabled or budget-skipped evaluation must not contact a provider.")

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        judge = SupportJudge(
            OpenRouterChat(
                OpenRouterProfile(
                    answer_model="test/model",
                    canonical_slug="test/model-v1",
                    provider="test",
                    input_price_per_million=Decimal(1),
                    output_price_per_million=Decimal(2),
                ),
                "synthetic-test-key",
                Budget(tmp_path / "budget.sqlite"),
                client,
            ),
            policies=ExecutionPolicies(
                online_enabled=enabled,
                online_evaluation=ExecutionLimits(model_calls=0),
            ),
        )
        result = judge.assess_online(
            SupportInput(
                answer="Phil delivers three red chairs.",
                context=(
                    SupportPassage(evidence_id="chairs", text="Phil delivers three red chairs."),
                ),
            )
        )
    assert result.status == expected
    assert result.execution.model_calls == 0


@pytest.mark.parametrize("exhausted", ["provider", "shared_ledger"])
def test_online_evaluation_spending_exhaustion_is_skipped_with_its_actual_reason(
    tmp_path: Path,
    exhausted: str,
) -> None:
    from ask_phil.execution import ExecutionPolicies
    from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
    from ask_phil.semantic_judge import SupportInput, SupportJudge, SupportPassage

    budget = Budget(tmp_path / "budget.sqlite")
    if exhausted == "shared_ledger":
        budget.reserve(Decimal(5))

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 5,
                        "limit_reset": None,
                        "limit_remaining": 0 if exhausted == "provider" else 5,
                    }
                },
            )
        assert request.url.path.endswith("/endpoints"), "No paid call is authorized."
        return httpx.Response(
            200,
            json={
                "data": {
                    "endpoints": [
                        {
                            "tag": "test",
                            "name": "Test | test/model-v1",
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

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        judge = SupportJudge(
            OpenRouterChat(
                OpenRouterProfile(
                    answer_model="test/model",
                    canonical_slug="test/model-v1",
                    provider="test",
                    input_price_per_million=Decimal(1),
                    output_price_per_million=Decimal(2),
                ),
                "synthetic-test-key",
                budget,
                client,
            ),
            policies=ExecutionPolicies(online_enabled=True),
        )
        result = judge.assess_online(
            SupportInput(
                answer="Phil delivers three red chairs.",
                context=(
                    SupportPassage(evidence_id="chairs", text="Phil delivers three red chairs."),
                ),
            )
        )
        assert result.status == "skipped"
        assert result.execution.stop_reason == "spend_limit"
        assert judge.chat.last_call is None


def test_maximum_call_reservation_uses_the_shared_input_and_output_ceiling() -> None:
    from ask_phil.openrouter import OpenRouterProfile, maximum_call_cost

    profile = OpenRouterProfile(
        answer_model="test/model",
        canonical_slug="test/model-v1",
        provider="test",
        input_price_per_million=Decimal("2"),
        output_price_per_million=Decimal("10"),
        output_tokens=8192,
    )
    assert maximum_call_cost(profile) == Decimal("0.122112")


def test_missing_context_is_unavailable_without_judge_inference(tmp_path: Path) -> None:
    from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
    from ask_phil.semantic_judge import SupportInput, SupportJudge

    def provider(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Missing context must not trigger a paid call.")

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        judge = SupportJudge(
            OpenRouterChat(
                OpenRouterProfile(
                    answer_model="test/model",
                    canonical_slug="test/model-v1",
                    provider="test",
                    input_price_per_million=Decimal("1"),
                    output_price_per_million=Decimal("2"),
                ),
                "synthetic-test-key",
                Budget(tmp_path / "budget.sqlite"),
                client,
            )
        )
        assessment = judge.assess(
            SupportInput(answer="Phil delivers three red chairs.", context=None)
        )
    assert assessment.supported is None
    assert assessment.usage is None
    assert assessment.cost_usd == 0


def test_calibration_exposes_false_passes_variation_and_human_review_status() -> None:
    from ask_phil.evaluation import document_fingerprint
    from ask_phil.semantic_judge import (
        JudgeObservation,
        SupportAssessment,
        SupportDataset,
        calibration_report,
        support_variant,
    )

    dataset = SupportDataset.model_validate_json(
        Path("data/references/support-judge-v1.json").read_bytes()
    )
    example = next(e for e in dataset.examples if e.case_id == "books-wrong-day")
    original = support_variant(example.supplied, "original")
    assessment = SupportAssessment(
        supported=True,
        evidence_ids=("books-borrow",),
        reason="Deliberately wrong judge decision for the independently false Friday answer.",
        input_sha256=document_fingerprint(original.model_dump(mode="json")),
        judge_settings_sha256="a" * 64,
        usage=None,
        cost_usd=0,
    )
    observations = (
        JudgeObservation(
            case_id=example.case_id, variant="original", repeat=0, assessment=assessment
        ),
        JudgeObservation(
            case_id=example.case_id,
            variant="original",
            repeat=1,
            assessment=assessment.model_copy(update={"supported": False}),
        ),
    )
    report = calibration_report(dataset, observations)
    assert report["judge_validation"]["false_passes"] == 1
    assert report["judge_validation"]["negative_labels"] == 1
    assert report["judge_validation"]["agreement"] == 0
    assert report["disagreements"][0]["case_id"] == "books-wrong-day"
    assert report["repeat_changes"] == 1
    assert report["eligible_to_enable"] is False
    assert report["coverage_complete"] is False


def test_support_judge_uses_only_supplied_data_and_rejects_invented_citations(
    tmp_path: Path,
) -> None:
    import json

    from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
    from ask_phil.semantic_judge import SupportDataset, SupportJudge

    example = next(
        row
        for row in SupportDataset.model_validate_json(
            Path("data/references/support-judge-v1.json").read_bytes()
        ).examples
        if row.case_id == "books-wrong-day"
    )

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 5,
                        "limit_remaining": 5,
                        "limit_reset": None,
                    }
                },
            )
        if request.url.path.endswith("/endpoints"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "endpoints": [
                            {
                                "tag": "test",
                                "name": "Test | test/model-v1",
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
        body = json.loads(request.content)
        supplied = json.loads(body["messages"][1]["content"])
        assert set(supplied) == {"answer", "context"}
        assert "Helpful" not in json.dumps(body)
        assert "reviewed_label" not in json.dumps(body)
        return httpx.Response(
            200,
            json={
                "model": "test/model-v1",
                "usage": {"cost": 0.001},
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "supported": True,
                                    "evidence_ids": ["invented-passage"],
                                    "reason": "A deliberately invalid provider response.",
                                }
                            )
                        },
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        judge = SupportJudge(
            OpenRouterChat(
                OpenRouterProfile(
                    answer_model="test/model",
                    canonical_slug="test/model-v1",
                    provider="test",
                    input_price_per_million=Decimal("1"),
                    output_price_per_million=Decimal("2"),
                ),
                "synthetic-test-key",
                Budget(tmp_path / "budget.sqlite"),
                client,
            )
        )
        with pytest.raises(ValueError, match="supplied context"):
            judge.assess(example.supplied)


def test_judge_cannot_be_enabled_without_an_independent_validation_partition() -> None:
    from ask_phil.evaluation import document_fingerprint
    from ask_phil.semantic_judge import (
        JudgeObservation,
        SupportAssessment,
        SupportDataset,
        calibration_plan,
        calibration_report,
        support_variant,
    )

    supplied = SupportDataset.model_validate_json(
        Path("data/references/support-judge-v1.json").read_bytes()
    )
    # Synthetic software input only; the real pending label artifact remains unchanged.
    dataset = supplied.model_copy(
        update={
            "human_reviewed": True,
            "examples": tuple(e for e in supplied.examples if e.split == "judge_calibration"),
        }
    )
    examples = {e.case_id: e for e in dataset.examples}
    observations = tuple(
        JudgeObservation(
            case_id=row["example_id"],
            variant=row["variant"],
            repeat=row["repeat"],
            assessment=SupportAssessment(
                supported=examples[row["example_id"]].reviewed_label,
                evidence_ids=(),
                reason="Synthetic matching labels isolate the coverage gate.",
                input_sha256=document_fingerprint(
                    support_variant(
                        examples[row["example_id"]].supplied, row["variant"]
                    ).model_dump(mode="json")
                ),
                judge_settings_sha256="a" * 64,
                usage=None,
                cost_usd=0,
            ),
        )
        for row in calibration_plan(dataset)
    )
    report = calibration_report(dataset, observations)
    assert report["judge_validation"]["selected_cases"] == 0
    assert report["eligible_to_enable"] is False


def test_calibration_preserves_unknown_judge_spending_and_its_reservation(tmp_path: Path) -> None:
    import json

    from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
    from ask_phil.semantic_judge import SupportJudge, calibrate_support

    references = json.loads(Path("data/references/support-judge-v1.json").read_bytes())
    references["human_reviewed"] = True  # Explicitly synthetic software input.
    reference_path = tmp_path / "labels.json"
    reference_path.write_text(json.dumps(references))

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 5,
                        "limit_remaining": 5,
                        "limit_reset": None,
                    }
                },
            )
        if request.url.path.endswith("/endpoints"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "endpoints": [
                            {
                                "tag": "test",
                                "name": "Test | test/model-v1",
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
                "model": "test/model-v1",
                "usage": {},
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "supported": True,
                                    "evidence_ids": ["chairs-delivery"],
                                    "reason": "The supplied passage states three red chairs.",
                                }
                            )
                        },
                    }
                ],
            },
        )

    output = tmp_path / "judge.json"
    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        judge = SupportJudge(
            OpenRouterChat(
                OpenRouterProfile(
                    answer_model="test/model",
                    canonical_slug="test/model-v1",
                    provider="test",
                    input_price_per_million=Decimal("1"),
                    output_price_per_million=Decimal("2"),
                ),
                "synthetic-test-key",
                Budget(tmp_path / "budget.sqlite"),
                client,
            )
        )
        with pytest.raises(ValueError, match="Unknown judge cost"):
            calibrate_support(reference_path, output, judge, max_cost_usd=Decimal("1"))
    captured = json.loads(output.read_bytes())
    assert captured["state"] == "failed"
    assert captured["cost_usd"] is None
    assert captured["known_cost_usd"] == "0"
    assert captured["failed_call_usage"]["cost_usd"] is None
    assert captured["failed_call_usage"]["reserved_usd"] > 0
