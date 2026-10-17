"""Capture real CLI conversations and review frozen, independently labelled answers."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any

from mlflow import MlflowClient

from ask_phil.answering import application_fingerprint
from ask_phil.answers import AnswerReceipt, AnswerRecord
from ask_phil.evaluation import EvaluationRun, EvaluationTracking, review_capture
from ask_phil.models import OpenRouterSettings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("capture", "score"))
    parser.add_argument(
        "--references", type=Path, default=Path("data/references/conversation-v1.json")
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8008")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new artifact path; retained evidence cannot be overwritten.")
    tracking = EvaluationTracking(
        MlflowClient(
            tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db")
        ),
        "ask-phil-conversation-development",
        {
            "kind": "conversation-" + args.mode,
            "expenditure_category": "serving" if args.mode == "capture" else "offline_evaluation",
        },
    )
    if args.mode == "score":
        if args.capture is None or args.reviews is None:
            parser.error("Scoring requires --capture and --reviews.")
        result = review_capture(
            args.capture, args.reviews, args.references, args.output, tracking=tracking
        )
        print(f"Saved reviewed dimensions for {len(result['cases'])} responses.")
        return

    dataset = json.loads(args.references.read_bytes())
    profile = OpenRouterSettings.model_validate_json(
        Path(os.environ["ASK_PHIL_MODELS"]).read_bytes()
    )
    worst_call = (
        Decimal(16000 + 4096) * profile.input_price_per_million
        + profile.output_tokens * profile.output_price_per_million
    ) / 1_000_000
    private = Path("artifacts") / ("private-" + args.output.stem)
    private.mkdir(mode=0o700, exist_ok=False)
    env = {key: value for key, value in os.environ.items() if key != "DATABASE_URL"}
    command = [sys.executable, "-m", "ask_phil.cli", "--api-url", args.api_url]
    document: dict[str, Any] = {
        "kind": "conversation-capture",
        "expenditure_category": "serving",
        "dataset_id": dataset["dataset_id"],
        "application_sha256": application_fingerprint(),
        "recorder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "cost_usd": "0",
        "model_calls": 0,
    }
    cost = Decimal(0)
    calls = 0
    with EvaluationRun(
        args.output,
        args.references,
        [step["case_id"] for step in dataset["steps"]],
        metadata=document,
        tracking=tracking,
    ) as run:

        def execute(step: dict[str, Any]) -> dict[str, Any]:
            nonlocal cost, calls
            session = private / (step["session"] + ".json")
            if not session.exists():
                subprocess.run(
                    [*command, "start-session", str(session)],
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            if step["operation"] == "reset":
                reset = subprocess.run(
                    [*command, "reset", str(session)],
                    env=env,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {"reset": json.loads(reset.stdout)}
            if (
                cost + worst_call > Decimal(str(dataset["budget"]["max_additional_reported_usd"]))
                or calls >= dataset["budget"]["max_paid_calls"]
            ):
                raise ValueError("Conversation sample budget exhausted before next turn.")
            result = subprocess.run(
                [*command, "ask", step["question"], "--session", str(session)],
                env=env,
                capture_output=True,
                text=True,
                timeout=400,
                check=True,
            )
            receipt = AnswerReceipt.model_validate_json(result.stdout)
            with (private / (step["case_id"] + ".json")).open("x") as output:
                os.chmod(output.name, 0o600)
                output.write(receipt.model_dump_json())
            response = receipt.response
            calls += int(response.provider_usage is not None)
            if response.estimated_api_cost_usd is not None:
                cost += Decimal(str(response.estimated_api_cost_usd))
            run.annotate(cost_usd=str(cost), model_calls=calls)
            return {"response": response.model_dump(mode="json")}

        for step in dataset["steps"]:
            row = run.capture(step["case_id"], partial(execute, step))
            if "response" in row:
                response = AnswerRecord.model_validate(row["response"])
                if response.estimated_api_cost_usd is None:
                    run.annotate(stop_reason="unknown_provider_spend")
                    raise ValueError("Unknown serving cost; retain reservation and stop.")
            print(step["case_id"], "recorded", flush=True)


if __name__ == "__main__":
    main()
