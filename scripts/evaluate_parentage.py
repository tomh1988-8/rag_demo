"""One bounded Claim extraction call on a frozen, source-reviewed slice."""

import argparse
import json
from pathlib import Path

import httpx
from mlflow import MlflowClient

from ask_phil.claim_extraction import (
    ClaimExtractionRun,
    ExtractionInputMismatch,
    validate_extraction_inputs,
)
from ask_phil.model_transport import cloud_transport
from ask_phil.openrouter import Budget, OpenRouterProfile, read_key


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    slice_options = parser.add_mutually_exclusive_group()
    slice_options.add_argument(
        "--relationships", action="store_true", help="Run the relationship-history slice."
    )
    slice_options.add_argument("--events", action="store_true", help="Run a story-event slice.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=Path("config/evaluation-sol-low.json"))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--tracking-uri")
    args = parser.parse_args()
    if args.events:
        default_snapshot, default_reference, issue = "crime-pilot-v1", "crime-justice-v2", 13
    elif args.relationships:
        default_snapshot, default_reference, issue = "relationship-pilot-v1", "relationships-v2", 12
    else:
        default_snapshot, default_reference, issue = "family-pilot-v1", "parentage-v1", 11
    args.snapshot = args.snapshot or Path(f"data/seed/{default_snapshot}.json")
    args.reference = args.reference or Path(f"data/references/{default_reference}.json")
    args.tracking_uri = args.tracking_uri or f"sqlite:///artifacts/issue-{issue}-mlflow.db"
    if args.output.exists():
        parser.error("Output already exists; choose a new path. No paid call was made.")
    try:
        validate_extraction_inputs(
            args.snapshot, args.reference, relationships=args.relationships, events=args.events
        )
    except ExtractionInputMismatch as exc:
        parser.error(str(exc))
    profile = OpenRouterProfile.model_validate_json(args.profile.read_bytes(), extra="ignore")
    try:
        with httpx.Client(
            timeout=profile.request_timeout_seconds,
            trust_env=False,
            follow_redirects=False,
            transport=cloud_transport(profile.answer_model),
        ) as client:
            record = ClaimExtractionRun(
                profile,
                read_key(),
                client,
                budget=Budget(),
                tracking=MlflowClient(tracking_uri=args.tracking_uri),
            ).run(
                args.snapshot,
                args.reference,
                args.output,
                relationships=args.relationships,
                events=args.events,
            )
    except ExtractionInputMismatch as exc:
        parser.error(str(exc))
    failure = record["failure"]
    print(json.dumps({"output": str(args.output), "score": record["score"], "failure": failure}))
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
