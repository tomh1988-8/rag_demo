"""Finite request authority and accounting shared by serving and evaluation."""

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from decimal import Decimal
from pathlib import Path
from threading import Event
from typing import Literal

from pydantic import Field

from ask_phil.evidence import Record


class ExecutionLimits(Record):
    model_calls: int = Field(default=2, ge=0, le=20)
    tool_calls: int = Field(default=1, ge=0, le=20)
    http_calls: int = Field(default=8, ge=0, le=100)
    seconds: float = Field(default=180, gt=0, le=600, allow_inf_nan=False)
    context_bytes: int = Field(default=1200, ge=2, le=1200)
    spend_usd: Decimal = Field(default=Decimal("0.15"), ge=0, le=1, allow_inf_nan=False)
    retries: Literal[0] = 0
    capabilities: tuple[Literal["text_retrieval"], ...] = ("text_retrieval",)
    concurrency: int = Field(default=4, ge=1, le=4)


class ExecutionPolicies(Record):
    serving: ExecutionLimits = ExecutionLimits()
    offline_evaluation: ExecutionLimits = ExecutionLimits(concurrency=1)
    online_evaluation: ExecutionLimits = ExecutionLimits(
        model_calls=1,
        tool_calls=0,
        capabilities=(),
        seconds=30,
        concurrency=1,
    )
    online_enabled: bool = False

    @classmethod
    def from_environment(cls) -> "ExecutionPolicies":
        path = os.environ.get("ASK_PHIL_EXECUTION_POLICY")
        if path is None:
            return cls()
        try:
            return cls.model_validate_json(Path(path).read_bytes())
        except (OSError, ValueError):
            raise ValueError("Execution policy could not be loaded.") from None


class ExecutionRecord(Record):
    limits: ExecutionLimits
    model_calls: int
    tool_calls: int
    http_calls: int
    reserved_usd: Decimal
    stop_reason: str | None


class ExecutionStopped(RuntimeError):
    """A safe, stable stop reason; never carries an upstream error or tool data."""


class ExecutionBudget:
    def __init__(self, limits: ExecutionLimits, *, cancellation: Event | None = None) -> None:
        self.limits = limits
        self.started = time.monotonic()
        self.cancellation = cancellation if cancellation is not None else Event()
        self._model_calls = 0
        self._tool_calls = 0
        self._http_calls = 0
        self._reserved = Decimal(0)
        self._last_reservation = Decimal(0)
        self._stop_reason: str | None = None

    @property
    def remaining_seconds(self) -> float:
        return max(0, self.limits.seconds - (time.monotonic() - self.started))

    def stop(self, reason: str) -> None:
        self.record_stop(reason)
        raise ExecutionStopped(self._stop_reason)

    def record_stop(self, reason: str) -> None:
        if self._stop_reason is None:
            self._stop_reason = reason

    def check(self) -> None:
        if self._stop_reason:
            raise ExecutionStopped(self._stop_reason)
        if self.cancellation.is_set():
            self.stop("cancelled")
        if self.remaining_seconds <= 0:
            self.stop("timeout")
        if self._reserved > self.limits.spend_usd:
            self.stop("spend_limit")

    def tool_call(self, capability: str) -> None:
        self.check()
        if capability not in self.limits.capabilities:
            self.stop("capability_denied")
        if self._tool_calls >= self.limits.tool_calls:
            self.stop("tool_call_limit")
        self._tool_calls += 1

    def http_call(self) -> None:
        self.check()
        if self._http_calls >= self.limits.http_calls:
            self.stop("http_call_limit")
        self._http_calls += 1

    def model_call(self, reservation: Decimal) -> None:
        self.check()
        if not reservation.is_finite() or reservation < 0:
            raise ValueError("A finite nonnegative reservation is required.")
        if self._model_calls >= self.limits.model_calls:
            self.stop("model_call_limit")
        if self._reserved + reservation > self.limits.spend_usd:
            self.stop("spend_limit")
        self._model_calls += 1
        self._reserved += reservation
        self._last_reservation = reservation

    def settle(self, actual_usd: Decimal | None) -> None:
        if actual_usd is not None:
            if not actual_usd.is_finite() or actual_usd < 0:
                raise ValueError("A finite nonnegative settlement is required.")
            self._reserved += actual_usd - self._last_reservation
            self._last_reservation = actual_usd

    def record(self) -> ExecutionRecord:
        return ExecutionRecord(
            limits=self.limits,
            model_calls=self._model_calls,
            tool_calls=self._tool_calls,
            http_calls=self._http_calls,
            reserved_usd=self._reserved,
            stop_reason=self._stop_reason,
        )

    @contextmanager
    def activate(self) -> Iterator[None]:
        token = current_execution.set(self)
        try:
            yield
        finally:
            current_execution.reset(token)


current_execution: ContextVar[ExecutionBudget | None] = ContextVar("execution", default=None)


def database_options(*, read_only: bool = False, finalizing: bool = False) -> str:
    """Bound database operations, allowing a fixed cleanup window for saved outcomes."""
    budget = None if finalizing else current_execution.get()
    milliseconds = max(1, min(5000, int(budget.remaining_seconds * 1000))) if budget else 5000
    return (
        "-c default_transaction_read_only=on " if read_only else ""
    ) + f"-c statement_timeout={milliseconds} -c lock_timeout={milliseconds}"


def read_options() -> str:
    return database_options(read_only=True)
