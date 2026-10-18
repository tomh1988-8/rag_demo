"""Observable request-budget arithmetic at the agreed bounded-execution seam."""

from decimal import Decimal
from threading import Event

import httpx
import pytest
from pydantic import ValidationError

from ask_phil.execution import ExecutionBudget, ExecutionLimits, ExecutionStopped
from ask_phil.model_transport import local_transport


def test_unknown_usage_retains_reservation_and_blocks_another_model_call() -> None:
    budget = ExecutionBudget(ExecutionLimits(model_calls=3, spend_usd=Decimal("0.02")))
    budget.model_call(Decimal("0.015"))
    budget.settle(None)
    with pytest.raises(ExecutionStopped, match="spend_limit"):
        budget.model_call(Decimal("0.006"))
    assert budget.record().model_calls == 1
    assert budget.record().reserved_usd == Decimal("0.015")


@pytest.mark.parametrize(
    "settings",
    [
        {"seconds": float("inf")},
        {"spend_usd": "NaN"},
        {"model_calls": -1},
        {"retries": 1},
        {"capabilities": ["shell"]},
    ],
)
def test_execution_policy_rejects_unbounded_work_and_write_capabilities(
    settings: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ExecutionLimits.model_validate(settings)


def test_cancelled_execution_cannot_start_any_further_tool_or_model_work() -> None:
    cancellation = Event()
    budget = ExecutionBudget(ExecutionLimits(), cancellation=cancellation)
    budget.tool_call("text_retrieval")
    cancellation.set()
    with pytest.raises(ExecutionStopped, match="cancelled"):
        budget.model_call(Decimal(0))
    with pytest.raises(ExecutionStopped, match="cancelled"):
        budget.tool_call("text_retrieval")
    assert budget.record().model_calls == 0
    assert budget.record().tool_calls == 1
    assert budget.record().stop_reason == "cancelled"


@pytest.mark.parametrize(
    "url,method",
    [
        ("http://example.invalid/api/chat", "POST"),
        ("http://127.0.0.1:11435/api/pull", "POST"),
        ("http://127.0.0.1:11435/api/chat?url=https://example.invalid", "POST"),
        ("http://127.0.0.1:11435/api/chat", "DELETE"),
    ],
)
def test_model_resources_reject_undeclared_authority_before_network_access(
    url: str,
    method: str,
) -> None:
    budget = ExecutionBudget(ExecutionLimits())
    with (
        budget.activate(),
        httpx.Client(transport=local_transport("http://127.0.0.1:11435")) as client,
    ):
        with pytest.raises(ExecutionStopped, match="endpoint_denied"):
            client.request(method, url)
    assert budget.record().http_calls == 0


def test_deadline_and_call_caps_stop_work_before_consuming_another_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [100.0]
    monkeypatch.setattr("ask_phil.execution.time.monotonic", lambda: now[0])
    budget = ExecutionBudget(ExecutionLimits(seconds=2))
    assert budget.remaining_seconds == 2
    now[0] = 102.1
    with pytest.raises(ExecutionStopped, match="timeout"):
        budget.model_call(Decimal(0))
    assert budget.record().model_calls == 0


def test_known_settlement_releases_only_the_current_call_reservation() -> None:
    budget = ExecutionBudget(ExecutionLimits(model_calls=3, spend_usd=Decimal("0.03")))
    budget.model_call(Decimal("0.015"))
    budget.settle(None)
    budget.model_call(Decimal("0.01"))
    budget.settle(Decimal("0.002"))
    assert budget.record().reserved_usd == Decimal("0.017")
    budget.model_call(Decimal("0.01"))
    assert budget.record().reserved_usd == Decimal("0.027")
