"""Capture real CLI conversations and score separately reviewed, hash-bound answers."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from mlflow import MlflowClient

from ask_phil.answering import application_fingerprint
from ask_phil.answers import AnswerReceipt
from ask_phil.evaluation import QualityReview, log_review_metrics, score_captured_answer
from ask_phil.evaluation import document_fingerprint as fingerprint
from ask_phil.models import OpenRouterSettings


def save(path: Path, document: dict[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=True) + "\n")


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
    dataset = json.loads(args.references.read_text())
    tracking = MlflowClient(
        tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db")
    )
    experiment = tracking.get_experiment_by_name("ask-phil-conversation-development")
    experiment_id = (
        experiment.experiment_id
        if experiment
        else tracking.create_experiment(
            "ask-phil-conversation-development",
            artifact_location=Path("artifacts/mlflow").resolve().as_uri(),
        )
    )
    run = tracking.create_run(
        experiment_id,
        tags={
            "kind": "conversation-" + args.mode,
            "expenditure_category": "serving" if args.mode == "capture" else "offline_evaluation",
        },
    )
    document: dict[str, Any] = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "state": "running",
        "run_id": run.info.run_id,
        "dataset_id": dataset["dataset_id"],
        "reference_file_sha256": hashlib.sha256(args.references.read_bytes()).hexdigest(),
        "application_sha256": application_fingerprint(),
        "recorder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "cases": [],
        "cost_usd": "0",
        "model_calls": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save(args.output, document)
    try:
        if args.mode == "capture":
            profile = OpenRouterSettings.model_validate_json(
                Path(os.environ["ASK_PHIL_MODELS"]).read_bytes()
            )
            worst_call = (
                Decimal(16000 + 4096) * profile.input_price_per_million
                + profile.output_tokens * profile.output_price_per_million
            ) / 1_000_000
            private = Path("artifacts") / ("private-" + args.output.stem)
            private.mkdir(mode=0o700, exist_ok=False)
            env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
            command = [sys.executable, "-m", "ask_phil.cli", "--api-url", args.api_url]
            cost = Decimal(0)
            calls = 0
            for step in dataset["steps"]:
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
                if step["operation"] == "ask":
                    if (
                        cost + worst_call
                        > Decimal(str(dataset["budget"]["max_additional_reported_usd"]))
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
                    if response.estimated_api_cost_usd is None:
                        raise ValueError("Unknown serving cost; retain reservation and stop.")
                    cost += Decimal(str(response.estimated_api_cost_usd))
                    calls += int(response.provider_usage is not None)
                    row = {
                        "case_id": step["case_id"],
                        "reference_sha256": fingerprint(step),
                        "response": response.model_dump(mode="json"),
                    }
                else:
                    result = subprocess.run(
                        [*command, "reset", str(session)],
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=True,
                    )
                    row = {"case_id": step["case_id"], "reset": json.loads(result.stdout)}
                document["cases"].append(row)
                document.update(cost_usd=str(cost), model_calls=calls)
                save(args.output, document)
                print(step["case_id"], "recorded", flush=True)
        else:
            if args.capture is None or args.reviews is None:
                raise ValueError("Scoring requires --capture and --reviews.")
            capture = json.loads(args.capture.read_text())
            if (
                capture["state"] != "complete"
                or capture["reference_file_sha256"] != document["reference_file_sha256"]
            ):
                raise ValueError("Capture must be complete and match these frozen references.")
            rows = {r["case_id"]: r for r in capture["cases"] if "response" in r}
            references = {s["case_id"]: s for s in dataset["steps"] if s["operation"] == "ask"}
            reviews = [
                QualityReview.model_validate(r)
                for r in json.loads(args.reviews.read_text())["reviews"]
            ]
            if len(reviews) != len(rows) or {r.case_id for r in reviews} != rows.keys():
                raise ValueError("Review every served response exactly once.")
            scored = tuple(
                score_captured_answer(
                    r,
                    rows[r.case_id]["response"],
                    references[r.case_id],
                    tuple(references[r.case_id]["expected_facts"]),
                )
                for r in reviews
            )
            document["cases"] = [r.model_dump(mode="json") for r in scored]
            document["capture_sha256"] = hashlib.sha256(args.capture.read_bytes()).hexdigest()
            document["reviews_sha256"] = hashlib.sha256(args.reviews.read_bytes()).hexdigest()
            document["scorer"] = "reviewed-binary-dimensions-v1"
            log_review_metrics(tracking, run.info.run_id, scored)
            tracking.log_artifact(run.info.run_id, str(args.capture))
            tracking.log_artifact(run.info.run_id, str(args.reviews))
        document["state"] = "complete"
        save(args.output, document)
        for key in (
            "reference_file_sha256",
            "application_sha256",
            "recorder_sha256",
            "lock_sha256",
            "model_calls",
            "cost_usd",
        ):
            tracking.log_param(run.info.run_id, key, document[key])
        for path in (args.references, args.output):
            tracking.log_artifact(run.info.run_id, str(path))
        tracking.set_terminated(run.info.run_id)
    except BaseException as exc:
        document.update(state="failed", failure_type=type(exc).__name__)
        save(args.output, document)
        tracking.set_terminated(run.info.run_id, status="FAILED")
        raise


if __name__ == "__main__":
    main()
