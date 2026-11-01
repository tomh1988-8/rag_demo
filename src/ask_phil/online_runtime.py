"""Local automatic online evaluation lifecycle and provider configuration."""

import json
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Event

import httpx

from ask_phil.execution import ExecutionPolicies
from ask_phil.model_transport import cloud_transport
from ask_phil.online_evaluation import OnlinePolicy
from ask_phil.online_workflow import OnlineEvaluation
from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile, read_key
from ask_phil.semantic_judge import SupportJudge


@contextmanager
def configured_online(
    database_url: str,
    tracking_uri: str,
    *,
    policy: OnlinePolicy | None = None,
    cancellation: Event | None = None,
) -> Iterator[OnlineEvaluation]:
    if (policy is not None and not policy.enabled) or os.environ.get(
        "ASK_PHIL_ONLINE_ENABLED", "true"
    ).lower() != "true":
        yield OnlineEvaluation(database_url, tracking_uri, policy=policy, cancellation=cancellation)
        return
    calibration = os.environ.get("ASK_PHIL_ONLINE_CALIBRATION")
    if calibration is None:
        yield OnlineEvaluation(database_url, tracking_uri, policy=policy, cancellation=cancellation)
        return
    path = Path(calibration)
    profile = OpenRouterProfile.model_validate(json.loads(path.read_bytes())["judge_profile"])
    with httpx.Client(
        timeout=5,
        trust_env=False,
        follow_redirects=False,
        transport=cloud_transport(profile.answer_model),
    ) as client:
        judge = SupportJudge(
            OpenRouterChat(profile, read_key(), Budget(), client),
            policies=ExecutionPolicies.from_environment(),
        )
        yield OnlineEvaluation(
            database_url,
            tracking_uri,
            policy=policy,
            judge=judge,
            calibration=path,
            scope=Path(os.environ["ASK_PHIL_ONLINE_SCOPE"])
            if "ASK_PHIL_ONLINE_SCOPE" in os.environ
            else None,
            cancellation=cancellation,
        )


def online_worker(
    database_url: str,
    tracking_uri: str,
    stop: Event,
    wake: Event,
    policy: OnlinePolicy | None = None,
) -> None:
    while not stop.is_set():
        interval = 10.0
        try:
            effective = policy or OnlinePolicy.from_environment()
            interval = effective.interval_seconds
            with configured_online(
                database_url, tracking_uri, policy=effective, cancellation=stop
            ) as evaluation:
                evaluation.process()
        except Exception as exc:
            # Safe failure class only. Committed interactions remain discoverable after recovery.
            logging.getLogger(__name__).warning(
                "Online workflow unavailable: %s", type(exc).__name__
            )
        wake.wait(interval)
        wake.clear()
