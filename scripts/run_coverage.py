"""Resume bounded coverage extraction; existing attempts are never repeated."""

import argparse
import json
from pathlib import Path

import httpx
from mlflow import MlflowClient

from ask_phil.coverage import CoverageRun
from ask_phil.model_transport import cloud_transport
from ask_phil.openrouter import Budget, OpenRouterProfile, read_key


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-batches", type=int, default=1)
    parser.add_argument("--profile", type=Path, default=Path("config/evaluation-sol-low.json"))
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-20-mlflow.db")
    args = parser.parse_args()
    profile = OpenRouterProfile.model_validate_json(args.profile.read_bytes(), extra="ignore")
    with httpx.Client(
        timeout=profile.request_timeout_seconds,
        trust_env=False,
        transport=cloud_transport(profile.answer_model),
    ) as client:
        summary = CoverageRun(
            profile,
            read_key(),
            client,
            budget=Budget(),
            tracking=MlflowClient(tracking_uri=args.tracking_uri),
        ).run(args.plan, args.output, max_batches=args.max_batches)
    print(json.dumps(summary, indent=2))
    return int(any(row["state"] in {"failed", "running"} for row in summary["batches"]))


if __name__ == "__main__":
    raise SystemExit(main())
