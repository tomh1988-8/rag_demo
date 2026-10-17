"""Retained issue-9 acceptance harness: judge frozen answers without regenerating them."""

import argparse
import hashlib
import json
import os
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any

import httpx
from mlflow import MlflowClient

from ask_phil.evaluation import EvaluationRun, EvaluationTracking, document_fingerprint
from ask_phil.openrouter import (
    Budget,
    OpenRouterChat,
    OpenRouterProfile,
    maximum_call_cost,
    read_key,
)
from ask_phil.semantic_judge import SUPPORT_RUBRIC_SHA256, SupportInput, SupportJudge


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", required=True, type=Path)
    parser.add_argument("--calibration", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-cost-usd", type=Decimal, default=Decimal("1"))
    args = parser.parse_args()
    if args.output.exists() or not Decimal(0) < args.max_cost_usd <= Decimal(1):
        parser.error("Choose a fresh output and a positive slice budget no greater than $1.")
    values = json.loads(args.profile.read_bytes())
    profile = OpenRouterProfile.model_validate(
        {key: values[key] for key in OpenRouterProfile.model_fields if key in values}
    )
    calibration = json.loads(args.calibration.read_bytes())
    gate = calibration["calibration"]
    if (
        calibration["state"] != "complete"
        or not gate["eligible_to_enable"]
        or gate["rubric_sha256"] != SUPPORT_RUBRIC_SHA256
        or gate["judge_settings_sha256"] != document_fingerprint(profile.model_dump(mode="json"))
    ):
        parser.error("The frozen rubric/profile must match a completed eligible calibration.")
    plan = json.loads(args.references.read_bytes())
    cases = plan["cases"]
    artifacts = [
        args.calibration,
        args.profile,
        Path(__file__),
        Path("uv.lock"),
        Path("src/ask_phil/semantic_judge.py"),
    ]
    captures = {row["capture_path"]: row["capture_sha256"] for row in cases}
    inputs = [
        *plan["review_artifacts"],
        *({"path": path, "sha256": digest} for path, digest in captures.items()),
        plan["source_hashes"]["retained_source_batch"],
        plan["source_hashes"]["frozen_dataset"],
    ]
    for item in inputs:
        path = Path(item["path"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            parser.error("A frozen source capture or independent annotation changed.")
        artifacts.append(path)
    for row in cases:
        supplied = SupportInput.model_validate(row["supplied"])
        if document_fingerprint(supplied.model_dump(mode="json")) != row["input_sha256"]:
            parser.error("A frozen support input differs from its independently reviewed hash.")
        if row["reviewed_label"] is not None and type(row["reviewed_label"]) is not bool:
            parser.error("Support labels must be independently reviewed true, false or null.")
    tracking = EvaluationTracking(
        MlflowClient(tracking_uri=os.environ["MLFLOW_TRACKING_URI"]),
        "ask-phil-quality-development",
        {"kind": "support-application", "expenditure_category": "offline_evaluation"},
    )
    with httpx.Client(timeout=profile.request_timeout_seconds, trust_env=False) as http:
        judge = SupportJudge(OpenRouterChat(profile, read_key(), Budget(), http))
        cost = Decimal(0)
        results: list[dict[str, Any]] = []
        with EvaluationRun(
            args.output,
            args.references,
            [row["case_id"] for row in cases],
            tracking=tracking,
            artifacts=artifacts,
            metadata={
                "kind": "retained-development-support-application-v1",
                "expenditure_category": "offline_evaluation",
                "cost_usd": "0",
                "rubric_sha256": SUPPORT_RUBRIC_SHA256,
                "judge_profile": profile.model_dump(mode="json"),
                "calibration_run_id": calibration["run_id"],
                "reviewer_type": "AGENT",
                "human_reviewed_answers": False,
                "limitation": "Context-only support; original question, correctness and "
                "completeness are outside this judge input. Null references cannot establish "
                "agreement or a false pass. This application does not broaden calibration.",
            },
        ) as run:

            def assess(row: dict[str, Any]) -> dict[str, Any]:
                nonlocal cost
                supplied = SupportInput.model_validate(row["supplied"])
                if supplied.context and cost + maximum_call_cost(profile) > args.max_cost_usd:
                    raise ValueError("Application slice cannot reserve another bounded call.")
                try:
                    assessment = judge.assess(supplied)
                except BaseException:
                    usage = judge.chat.last_call
                    if usage and usage.cost_usd is not None:
                        cost += Decimal(str(usage.cost_usd))
                    run.annotate(
                        cost_usd=str(cost) if not usage or usage.cost_usd is not None else None,
                        known_cost_usd=str(cost),
                        failed_call_usage=usage.model_dump(mode="json") if usage else None,
                    )
                    raise
                if assessment.cost_usd is None:
                    run.annotate(
                        cost_usd=None,
                        known_cost_usd=str(cost),
                        failed_call_usage=assessment.usage.model_dump(mode="json")
                        if assessment.usage
                        else None,
                    )
                    raise ValueError("Unknown judge cost; retain the reservation and stop.")
                cost += Decimal(str(assessment.cost_usd))
                run.annotate(cost_usd=str(cost))
                result = {
                    "assessment": assessment.model_dump(mode="json"),
                    "reviewed_label": row["reviewed_label"],
                    "agrees": assessment.supported == row["reviewed_label"]
                    if row["reviewed_label"] is not None
                    else None,
                }
                results.append({"case_id": row["case_id"], **result})
                return result

            for row in cases:
                run.capture(row["case_id"], partial(assess, row))
            known = [row for row in results if row["reviewed_label"] is not None]
            disagreements = [row for row in known if not row["agrees"]]
            run.annotate(
                summary={
                    "observations": len(results),
                    "reviewed_boolean_labels": len(known),
                    "unassessed_labels": len(results) - len(known),
                    "agreement": sum(row["agrees"] for row in known) / len(known)
                    if known
                    else None,
                    "disagreements": disagreements,
                    "decisions_without_reference_label": [
                        {
                            "case_id": row["case_id"],
                            "assessment": row["assessment"],
                            "disposition": "requires_review_not_scored",
                        }
                        for row in results
                        if row["reviewed_label"] is None
                        and row["assessment"]["supported"] is not None
                    ],
                    "false_passes": sum(
                        row["reviewed_label"] is False and row["assessment"]["supported"] is True
                        for row in known
                    ),
                    "negative_labels": sum(row["reviewed_label"] is False for row in known),
                    "paid_calls": sum(row["assessment"]["usage"] is not None for row in results),
                    "unavailable": sum(row["assessment"]["supported"] is None for row in results),
                }
            )
    print("Saved", args.output)


if __name__ == "__main__":
    main()
