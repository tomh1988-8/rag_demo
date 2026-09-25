"""OpenRouter credentials and conservative, persistent trial spending controls."""

import json
import os
import sqlite3
from collections.abc import Sequence
from contextvars import ContextVar
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx
from llama_index.core.llms import ChatMessage, ChatResponse
from pydantic import Field

from ask_phil.evidence import Record

API = "https://openrouter.ai/api/v1"
KEY_PATH = Path(".secrets/openrouter.key")
BUDGET_PATH = Path("artifacts/openrouter-budget.sqlite")
CAP = Decimal("5")
MICRODOLLARS = Decimal("1000000")


class ProviderError(ValueError):
    """Safe public error: never include credentials or upstream response bodies."""


def money(value: object) -> Decimal:
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ProviderError("Provider returned invalid spending data.") from None
    if not amount.is_finite() or amount < 0:
        raise ProviderError("Provider returned invalid spending data.")
    return amount


def verify_key(client: httpx.Client, key: str) -> Decimal:
    """Read back the provider's lifetime key limit; this never sets a remote limit."""
    try:
        response = client.get(f"{API}/key", headers={"Authorization": f"Bearer {key}"})
        response.raise_for_status()
        data = response.json()["data"]
        limit = money(data.get("limit"))
        remaining = money(data.get("limit_remaining"))
        if (
            not 0 < limit <= CAP
            or "limit_reset" not in data
            or data["limit_reset"] is not None
            or remaining > limit
            or data.get("is_management_key", False)
        ):
            raise ProviderError("A non-resetting OpenRouter key limit of $5 or less is required.")
    except ProviderError:
        raise ProviderError(
            "A non-resetting OpenRouter key limit of $5 or less is required."
        ) from None
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        raise ProviderError(
            "Could not verify the OpenRouter key limit; no paid call was made."
        ) from None
    if remaining <= 0:
        raise ProviderError("The OpenRouter key budget is exhausted.")
    if data.get("include_byok_in_limit") is not True:
        raise ProviderError("Enable 'include BYOK usage in limit' on this capped OpenRouter key.")
    return remaining


def save_key(key: str, path: Path, client: httpx.Client) -> None:
    if path.exists() or path.is_symlink():
        raise ProviderError("Key file already exists; it was left unchanged.")
    if not key or any(char.isspace() for char in key):
        raise ProviderError("Invalid key input.")
    verify_key(client, key)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(key)


def read_key(path: Path = KEY_PATH) -> str:
    try:
        if path.stat().st_mode & 0o077:
            raise ProviderError("The OpenRouter key file must have mode 0600 or stricter.")
        key = path.read_text().strip()
        if not key or any(char.isspace() for char in key):
            raise ProviderError("Invalid OpenRouter key file.")
        return key
    except OSError:
        raise ProviderError("OpenRouter key missing; run ask-phil configure-openrouter.") from None


class Budget:
    """One $5 ledger across models/processes; uncertain requests retain their reservation."""

    def __init__(self, path: Path = BUDGET_PATH) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path, timeout=30) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS reservations "
                "(id TEXT PRIMARY KEY, microdollars INTEGER NOT NULL, settled INTEGER DEFAULT 0)"
            )

    def reserve(self, amount: Decimal) -> str:
        amount = money(amount)
        units = int((amount * MICRODOLLARS).to_integral_value(rounding=ROUND_CEILING))
        if units <= 0:
            raise ProviderError("A positive budget reservation is required.")
        identifier = uuid4().hex
        with sqlite3.connect(self.path, timeout=30) as conn:
            conn.execute("BEGIN IMMEDIATE")
            spent = conn.execute(
                "SELECT COALESCE(SUM(microdollars), 0) FROM reservations"
            ).fetchone()[0]
            if spent + units > int(CAP * MICRODOLLARS):
                raise ProviderError("The shared $5 trial budget cannot cover this request.")
            conn.execute(
                "INSERT INTO reservations(id, microdollars) VALUES (?, ?)", (identifier, units)
            )
        return identifier

    def settle(self, identifier: str, amount: Decimal) -> None:
        units = int((money(amount) * MICRODOLLARS).to_integral_value(rounding=ROUND_CEILING))
        with sqlite3.connect(self.path, timeout=30) as conn:
            # Settlement is idempotent. Never erase a reservation on missing/invalid usage.
            conn.execute(
                "UPDATE reservations SET microdollars=?, settled=1 WHERE id=? AND settled=0",
                (units, identifier),
            )


class OpenRouterProfile(Record):
    provider_type: Literal["openrouter"] = "openrouter"
    answer_model: str
    canonical_slug: str
    provider: str
    input_price_per_million: Decimal = Field(gt=0, le=2)
    output_price_per_million: Decimal = Field(gt=0, le=10)
    output_tokens: int = Field(default=4096, ge=256, le=8192)
    reasoning_effort: Literal["none", "low", "medium"] = "low"
    request_timeout_seconds: int = Field(default=180, ge=1, le=180)


class ProviderUsage(Record):
    reservation_id: str
    reserved_usd: float
    cost_usd: float | None = None
    request_id: str | None = None
    returned_model: str | None = None
    provider: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    reasoning_tokens: int | None = None


def answer_schema(value: Any) -> Any:
    """The answer's disjoint kind-tagged union also works as strict-output anyOf."""
    if isinstance(value, list):
        return [answer_schema(item) for item in value]
    if isinstance(value, dict):
        return {
            ("anyOf" if key == "oneOf" else key): answer_schema(item)
            for key, item in value.items()
            if key != "discriminator"
        }
    return value


class OpenRouterChat:
    """Small LlamaIndex chat boundary with explicit routing, no retries and no autologging."""

    def __init__(
        self, profile: OpenRouterProfile, key: str, budget: Budget, client: httpx.Client
    ) -> None:
        self.profile = profile
        self._key = key
        self._budget = budget
        self._client = client
        self._last_call = ContextVar[ProviderUsage | None]("openrouter_call", default=None)

    @property
    def last_call(self) -> ProviderUsage | None:
        return self._last_call.get()

    def _verify_endpoint(self) -> None:
        response = self._client.get(f"{API}/models/{self.profile.answer_model}/endpoints")
        response.raise_for_status()
        endpoints = response.json()["data"]["endpoints"]
        required = {"structured_outputs", "response_format", "reasoning", "max_tokens"}
        if not any(
            endpoint["tag"] == self.profile.provider
            and endpoint["name"].endswith(" | " + self.profile.canonical_slug)
            and required.issubset(endpoint["supported_parameters"])
            for endpoint in endpoints
        ):
            raise ProviderError("The configured model version/provider is unavailable; rebaseline.")

    def chat(self, messages: Sequence[ChatMessage], *, format: dict[str, Any]) -> ChatResponse:
        self._last_call.set(None)
        profile = self.profile
        body = {
            "model": profile.answer_model,
            "messages": [{"role": m.role.value, "content": m.content} for m in messages],
            "max_tokens": profile.output_tokens,
            "stream": False,
            "reasoning": {"effort": profile.reasoning_effort, "exclude": True},
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "answer",
                    "strict": True,
                    "schema": answer_schema(format),
                },
            },
            "provider": {
                "only": [profile.provider],
                "allow_fallbacks": False,
                "require_parameters": True,
                "max_price": {
                    "prompt": float(profile.input_price_per_million),
                    "completion": float(profile.output_price_per_million),
                    "request": 0,
                },
            },
        }
        encoded = json.dumps(body, ensure_ascii=False).encode()
        if len(encoded) > 16000:
            raise ProviderError("Request exceeds the 16000-byte trial input budget.")
        # UTF-8 byte count plus framing/schema allowance is a conservative reservation,
        # not measured usage. The verified provider lifetime cap is the billing authority.
        reservation = (
            (len(encoded) + 4096) * profile.input_price_per_million
            + profile.output_tokens * profile.output_price_per_million
        ) / MICRODOLLARS
        try:
            remaining = verify_key(self._client, self._key)
            if reservation > remaining:
                raise ProviderError("The provider budget cannot cover this request.")
            self._verify_endpoint()
            identifier = self._budget.reserve(reservation)
            accounting = ProviderUsage(reservation_id=identifier, reserved_usd=float(reservation))
            self._last_call.set(accounting)
            response = self._client.post(
                f"{API}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {self._key}"},
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage") or {}
            cost = money(usage["cost"]) if usage.get("cost") is not None else None
            accounting = ProviderUsage.model_validate(
                {
                    **accounting.model_dump(),
                    "cost_usd": float(cost) if cost is not None else None,
                    "request_id": data.get("id"),
                    "returned_model": data.get("model"),
                    "provider": data.get("provider"),
                    "input_tokens": usage.get("prompt_tokens"),
                    "output_tokens": usage.get("completion_tokens"),
                    "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get(
                        "reasoning_tokens"
                    ),
                }
            )
            self._last_call.set(accounting)
            if cost is not None:
                self._budget.settle(identifier, cost)
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop" or data.get("model") not in {
                profile.answer_model,
                profile.canonical_slug,
            }:
                raise ProviderError("Provider returned an incomplete or unexpected model response.")
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise ProviderError("Provider returned no usable answer.")
            return ChatResponse(
                message=ChatMessage(role="assistant", content=content),
                raw={
                    "prompt_eval_count": usage.get("prompt_tokens"),
                    "eval_count": usage.get("completion_tokens"),
                },
            )
        except ProviderError:
            raise
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError(
                "OpenRouter request failed; no automatic retry. Unknown spend remains reserved."
            ) from None
