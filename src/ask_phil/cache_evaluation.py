"""Descriptive cache workload arithmetic; semantic support requires supplied reviews."""

import math
from collections.abc import Sequence
from statistics import mean, median
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from ask_phil.cache_records import CacheDelivery
from ask_phil.evidence import Record


class CacheObservation(Record):
    phase: Literal["cold", "warm", "control"]
    delivery: CacheDelivery
    elapsed_ms: float = Field(ge=0, allow_inf_nan=False)
    end_to_end_ms: float = Field(ge=0, allow_inf_nan=False)
    cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    generation_id: UUID | None = None
    supported: bool | None = None
    compatible: bool | None = None

    @model_validator(mode="after")
    def eligible_hit(self) -> Self:
        if self.delivery.status == "hit" and not self.delivery.eligible:
            raise ValueError("A reported hit must be eligible for reuse.")
        return self


class CacheWorkloadMetrics(Record):
    requests: int
    eligible: int
    hits: int
    misses: int
    bypasses: int
    eligible_hit_rate: float | None
    all_request_hit_coverage: float | None
    reviewed_hits: int
    incorrect_hits: int
    incorrect_reuse_rate: float | None
    compatibility_checked_hits: int
    stale_hits: int
    stale_reuse_rate: float | None
    support_reviewed: int
    supported_share: float | None
    distinct_generations: int | None
    cost_usd: float | None
    known_cost_usd: float
    unknown_cost_requests: int
    mean_elapsed_ms: float | None
    mean_end_to_end_ms: float | None
    median_end_to_end_ms: float | None
    p95_end_to_end_ms: float | None
    interpretation: str = (
        "Hit rate is hits/eligible requests; coverage is hits/all requests. Incorrect reuse "
        "is unsupported/reviewed hits; stale reuse is incompatible/compatibility-checked hits. "
        "Support is supported/reviewed deliveries, not independent factual examples. "
        "Missing reviews and expense remain unavailable. End-to-end includes transport and "
        "response persistence; p95 uses nearest rank. Cold/warm results are workload observations."
    )


def summarize_cache_workload(rows: Sequence[CacheObservation]) -> CacheWorkloadMetrics:
    hits = [r for r in rows if r.delivery.status == "hit"]
    reviewed = [r for r in hits if r.supported is not None]
    checked = [r for r in hits if r.compatible is not None]
    support = [r for r in rows if r.supported is not None]
    eligible = sum(r.delivery.eligible for r in rows)
    known_cost = sum(r.cost_usd for r in rows if r.cost_usd is not None)
    unknown_cost = sum(r.cost_usd is None for r in rows)
    latencies = sorted(r.end_to_end_ms for r in rows)
    incorrect = sum(r.supported is False for r in reviewed)
    stale = sum(r.compatible is False for r in checked)
    return CacheWorkloadMetrics(
        requests=len(rows),
        eligible=eligible,
        hits=len(hits),
        misses=sum(r.delivery.status == "miss" for r in rows),
        bypasses=sum(r.delivery.status == "bypass" for r in rows),
        eligible_hit_rate=len(hits) / eligible if eligible else None,
        all_request_hit_coverage=len(hits) / len(rows) if rows else None,
        reviewed_hits=len(reviewed),
        incorrect_hits=incorrect,
        incorrect_reuse_rate=incorrect / len(reviewed) if reviewed else None,
        compatibility_checked_hits=len(checked),
        stale_hits=stale,
        stale_reuse_rate=stale / len(checked) if checked else None,
        support_reviewed=len(support),
        supported_share=sum(r.supported is True for r in support) / len(support)
        if support
        else None,
        distinct_generations=len({r.generation_id for r in rows})
        if all(r.generation_id is not None for r in rows)
        else None,
        cost_usd=None if unknown_cost else known_cost,
        known_cost_usd=known_cost,
        unknown_cost_requests=unknown_cost,
        mean_elapsed_ms=mean(r.elapsed_ms for r in rows) if rows else None,
        mean_end_to_end_ms=mean(latencies) if latencies else None,
        median_end_to_end_ms=median(latencies) if latencies else None,
        p95_end_to_end_ms=latencies[math.ceil(0.95 * len(latencies)) - 1] if latencies else None,
    )
