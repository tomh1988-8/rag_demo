"""External HTTP substitutes; budget and secret storage use real local files."""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from llama_index.core.llms import ChatMessage

from ask_phil.openrouter import (
    Budget,
    OpenRouterChat,
    OpenRouterProfile,
    ProviderError,
    save_key,
    verify_key,
)


@pytest.mark.parametrize("limit,reset", [(None, None), (6, None), (5, "monthly"), (0, None)])
def test_uncapped_or_resetting_key_is_rejected(limit: float | None, reset: str | None) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json={"data": {"limit": limit, "limit_reset": reset, "limit_remaining": 5}}
            )
        )
    )
    with pytest.raises(ProviderError, match="non-resetting"):
        verify_key(client, "test-key")


def test_only_verified_key_is_saved_privately(tmp_path: Path) -> None:
    def reply(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/key"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(
            200,
            json={
                "data": {
                    "limit": 5,
                    "limit_reset": None,
                    "limit_remaining": 4.8,
                    "include_byok_in_limit": True,
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(reply))
    path = tmp_path / ".secrets" / "openrouter.key"
    save_key("test-key", path, client)
    assert path.read_text() == "test-key"
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    with pytest.raises(ProviderError, match="already exists"):
        save_key("other-key", path, client)


def test_provider_errors_do_not_disclose_key(tmp_path: Path) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(401, json={"error": "secret-test-key"})
        )
    )
    path = tmp_path / ".secrets" / "openrouter.key"
    with pytest.raises(ProviderError) as error:
        save_key("secret-test-key", path, client)
    assert "secret-test-key" not in str(error.value)
    assert error.value.__cause__ is None
    assert not path.exists()


def test_budget_survives_restart_and_concurrent_reservations(tmp_path: Path) -> None:
    path = tmp_path / "budget.sqlite"
    Budget(path)

    def reserve(_: int) -> bool:
        try:
            Budget(path).reserve(Decimal("1"))
        except ProviderError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(reserve, range(12))) == 5
    with pytest.raises(ProviderError, match="budget"):
        Budget(path).reserve(Decimal("0.01"))


def test_known_cost_settles_but_unknown_call_keeps_reservation(tmp_path: Path) -> None:
    budget = Budget(tmp_path / "budget.sqlite")
    first = budget.reserve(Decimal("3"))
    budget.reserve(Decimal("2"))  # Interrupted/unknown; never refunded.
    budget.settle(first, Decimal("0.01"))
    Budget(tmp_path / "budget.sqlite").reserve(Decimal("2.99"))
    with pytest.raises(ProviderError):
        budget.reserve(Decimal("0.01"))


@pytest.mark.parametrize("failure", [False, True])
def test_cloud_call_is_bounded_and_records_billing_without_secrets(
    tmp_path: Path,
    failure: bool,
) -> None:
    paid_requests = []
    profile = OpenRouterProfile(
        answer_model="test/model",
        canonical_slug="test/model-v1",
        provider="test-provider",
        input_price_per_million=Decimal("0.15"),
        output_price_per_million=Decimal("0.47"),
        output_tokens=4096,
        reasoning_effort="low",
    )

    def reply(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 5,
                        "limit_reset": None,
                        "limit_remaining": 5,
                        "include_byok_in_limit": True,
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
                                "tag": "test-provider",
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
        paid_requests.append(body)
        assert body["provider"]["only"] == ["test-provider"]
        assert body["provider"]["allow_fallbacks"] is False
        assert body["provider"]["require_parameters"] is True
        assert body["provider"]["max_price"] == {"prompt": 0.15, "completion": 0.47, "request": 0}
        assert body["max_tokens"] == 4096
        assert body["stream"] is False
        assert "temperature" not in body
        assert body["response_format"]["json_schema"]["strict"] is True
        if failure:
            raise httpx.ReadTimeout("secret-test-key")
        return httpx.Response(
            200,
            json={
                "id": "request-1",
                "model": "test/model-v1",
                "provider": "Test",
                "choices": [{"finish_reason": "stop", "message": {"content": '{"answer":"yes"}'}}],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": 50,
                    "cost": 0.00003,
                    "completion_tokens_details": {"reasoning_tokens": 30},
                },
            },
        )

    chat = OpenRouterChat(
        profile,
        "secret-test-key",
        Budget(tmp_path / "budget.sqlite"),
        httpx.Client(transport=httpx.MockTransport(reply)),
    )
    if failure:
        with pytest.raises(ProviderError) as error:
            chat.chat([ChatMessage(role="user", content="Hello")], format={"type": "object"})
        assert "secret-test-key" not in str(error.value)
        assert error.value.__cause__ is None
        assert chat.last_call is not None and chat.last_call.cost_usd is None
    else:
        result = chat.chat([ChatMessage(role="user", content="Hello")], format={"type": "object"})
        assert result.message.content == '{"answer":"yes"}'
        assert isinstance(result.raw, dict)
        assert result.raw["eval_count"] == 50
        assert chat.last_call is not None and chat.last_call.cost_usd == 0.00003
        assert chat.last_call.reasoning_tokens == 30
    assert len(paid_requests) == 1  # No retries, including ambiguous timeouts.
    assert "secret-test-key" not in chat.last_call.model_dump_json()


def test_provider_cap_is_checked_before_every_paid_request(tmp_path: Path) -> None:
    calls = []

    def reply(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(
            200, json={"data": {"limit": 50, "limit_reset": None, "limit_remaining": 50}}
        )

    profile = OpenRouterProfile(
        answer_model="test/model",
        canonical_slug="test/model-v1",
        provider="test",
        input_price_per_million=Decimal("0.15"),
        output_price_per_million=Decimal("0.47"),
    )
    chat = OpenRouterChat(
        profile,
        "test-key",
        Budget(tmp_path / "budget.sqlite"),
        httpx.Client(transport=httpx.MockTransport(reply)),
    )
    with pytest.raises(ProviderError):
        chat.chat([ChatMessage(role="user", content="Hello")], format={"type": "object"})
    assert calls == ["/api/v1/key"]


@pytest.mark.parametrize("remaining,byok", [(0, True), (5, False), (5, None)])
def test_depleted_or_partially_counted_budget_is_rejected(
    remaining: int,
    byok: bool | None,
) -> None:
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "data": {
                        "limit": 5,
                        "limit_reset": None,
                        "limit_remaining": remaining,
                        "include_byok_in_limit": byok,
                    }
                },
            )
        )
    )
    with pytest.raises(ProviderError):
        verify_key(client, "test-key")


def test_key_setup_refuses_noninteractive_input() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ask_phil.cli", "configure-openrouter"],
        input="private-test-key",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "interactive terminal" in result.stderr
    assert "private-test-key" not in result.stdout + result.stderr
