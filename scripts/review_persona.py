"""Score frozen final-answer persona reviews without regenerating answers."""

import argparse
import os
from pathlib import Path

from mlflow import MlflowClient

from ask_phil.evaluation import EvaluationTracking
from ask_phil.persona_evaluation import compare_persona, review_persona


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    assess = commands.add_parser("score")
    assess.add_argument("--capture", type=Path, required=True)
    assess.add_argument("--reviews", type=Path, required=True)
    assess.add_argument("--references", type=Path, required=True)
    assess.add_argument("--output", type=Path, required=True)
    comparison = commands.add_parser("compare")
    comparison.add_argument("--baseline", type=Path, required=True)
    comparison.add_argument("--candidate", type=Path, required=True)
    comparison.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a fresh output path; retain existing reviews.")
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    tracking = (
        EvaluationTracking(
            MlflowClient(tracking_uri=tracking_uri),
            "ask-phil-persona-evaluation",
            {
                "kind": "persona-source-review"
                if args.command == "score"
                else "persona-comparison",
                "expenditure_category": "offline_evaluation",
            },
        )
        if tracking_uri
        else None
    )
    if args.command == "score":
        result = review_persona(
            args.capture, args.reviews, args.references, args.output, tracking=tracking
        )
        print(f"Scored {len(result['cases'])} final persona responses without model calls.")
    else:
        compare_persona(args.baseline, args.candidate, args.output, tracking=tracking)
        print("Saved the controlled persona comparison without model calls.")


if __name__ == "__main__":
    main()
