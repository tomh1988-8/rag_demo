"""Capture, review and compare frozen development cases, or calibrate a support judge."""

import argparse
import json
import os
from decimal import Decimal
from functools import partial
from pathlib import Path

import httpx
from mlflow import MlflowClient

from ask_phil.evaluation import EvaluationRun, EvaluationTracking, review_capture
from ask_phil.models import OpenRouterSettings
from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile, read_key
from ask_phil.quality_comparison import ComparisonDataset, compare_development
from ask_phil.quality_workflow import capture_quality, reviewed_comparison_run
from ask_phil.semantic_judge import SupportDataset, SupportJudge, calibrate_support


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "score", "compare", "judge"))
    parser.add_argument(
        "--references", type=Path, default=Path("data/references/quality-comparison-v1.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--baseline-capture", type=Path)
    parser.add_argument("--baseline-review", type=Path)
    parser.add_argument("--candidate-capture", type=Path)
    parser.add_argument("--candidate-review", type=Path)
    parser.add_argument(
        "--changed-factor",
        choices=("repeat_control", "retrieval", "context", "prompt", "answer_settings"),
        default="repeat_control",
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8009")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--namespace", default=None)
    parser.add_argument("--max-cost-usd", type=Decimal, default=Decimal("1"))
    parser.add_argument("--model-profile", type=Path)
    parser.add_argument("--software-tests", type=Path)
    parser.add_argument("--judge-calibration", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new artifact path; retained evidence cannot be overwritten.")
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db")
    client = MlflowClient(tracking_uri=tracking_uri)
    tracking = EvaluationTracking(
        client,
        "ask-phil-quality-development",
        {
            "kind": "quality-" + args.mode,
            "expenditure_category": "serving" if args.mode == "capture" else "offline_evaluation",
        },
    )
    if args.mode == "capture":
        if not args.model_profile or not args.namespace:
            parser.error("Capture requires --model-profile and a unique run/partition --namespace.")
        profile = OpenRouterSettings.model_validate_json(args.model_profile.read_bytes())
        with httpx.Client(base_url=args.api_url, timeout=400, trust_env=False) as api:
            capture_quality(
                args.references,
                args.output,
                api,
                repeats=args.repeats,
                namespace=args.namespace,
                max_cost_usd=args.max_cost_usd,
                profile=profile,
                private_directory=Path("artifacts") / ("private-quality-" + args.output.stem),
                tracking=tracking,
                serving_tracking=client,
            )
    elif args.mode == "score":
        if args.capture is None or args.reviews is None:
            parser.error("Score requires --capture and --reviews.")
        review_capture(args.capture, args.reviews, args.references, args.output, tracking=tracking)
    elif args.mode == "compare":
        inputs = (
            args.baseline_capture,
            args.baseline_review,
            args.candidate_capture,
            args.candidate_review,
        )
        if any(path is None for path in inputs) or args.software_tests is None:
            parser.error("Compare requires both captures/reviews and separate --software-tests.")
        dataset = ComparisonDataset.model_validate_json(args.references.read_bytes())
        baseline = reviewed_comparison_run(dataset, args.baseline_capture, args.baseline_review)
        candidate = reviewed_comparison_run(dataset, args.candidate_capture, args.candidate_review)
        report = compare_development(
            dataset, baseline, candidate, changed_factor=args.changed_factor
        )
        judge_artifacts: tuple[Path, ...] = ()
        if args.judge_calibration:
            calibration = json.loads(args.judge_calibration.read_bytes())
            if calibration["state"] != "complete":
                parser.error("Only completed judge calibration artifacts can be associated.")
            report["judge_calibration_run_id"] = calibration.get("run_id")
            report["judge_calibration"] = calibration["calibration"]
            judge_artifacts = (args.judge_calibration,)
        else:
            report["judge_status"] = "not_attached"
        per_case = report.pop("per_case")
        with EvaluationRun(
            args.output,
            args.references,
            list(per_case),
            metadata=report,
            tracking=tracking,
            artifacts=(
                *inputs,
                args.software_tests,
                *judge_artifacts,
                Path("uv.lock"),
                Path(__file__),
                Path("data/references/quality-scorer-contracts-v1.json"),
            ),
        ) as run:
            for identifier, result in per_case.items():
                run.capture(identifier, partial(dict, comparison=result))
    else:
        if args.model_profile is None:
            parser.error("Judge requires an explicit --model-profile.")
        judge_dataset = SupportDataset.model_validate_json(args.references.read_bytes())
        if not judge_dataset.human_reviewed:
            parser.error("Human label review is pending; do not claim calibrated judge acceptance.")
        profile_value = json.loads(args.model_profile.read_bytes())
        judge_profile = OpenRouterProfile.model_validate(
            {
                key: profile_value[key]
                for key in OpenRouterProfile.model_fields
                if key in profile_value
            }
        )
        # At most $1 additional known spend; the preserved shared $5 ledger still governs.
        if not Decimal(0) < args.max_cost_usd <= Decimal(1):
            parser.error("Choose a positive judge slice budget no greater than $1.")
        from ask_phil.model_transport import cloud_transport

        with httpx.Client(
            timeout=judge_profile.request_timeout_seconds,
            trust_env=False,
            transport=cloud_transport(judge_profile.answer_model),
        ) as http:
            judge = SupportJudge(OpenRouterChat(judge_profile, read_key(), Budget(), http))
            calibrate_support(
                args.references,
                args.output,
                judge,
                max_cost_usd=args.max_cost_usd,
                tracking=tracking,
            )
    print("Saved", args.output)


if __name__ == "__main__":
    main()
