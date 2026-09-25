"""Capture bounded responses, then score separately reviewed immutable outputs."""

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mlflow import MlflowClient

from ask_phil.answering import AnswerService, application_fingerprint
from ask_phil.answers import AskRequest
from ask_phil.evaluation import QualityReview, score_answer_review
from ask_phil.evidence import SourceSnapshot
from ask_phil.models import Models
from ask_phil.openrouter import OpenRouterChat
from ask_phil.storage import EvidenceStore

REFERENCE = Path("data/references/answer-policy-v2.json")


def fingerprint(document: Any) -> str:
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def save(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=True) + "\n")


def capture(output: Path, case_ids: list[str], limit: int) -> None:
    dataset = json.loads(REFERENCE.read_text())
    cases = dataset["cases"]
    if case_ids:
        unknown = set(case_ids) - {c["case_id"] for c in cases}
        if unknown:
            raise ValueError(f"Unknown case IDs: {sorted(unknown)}")
        cases = [c for c in cases if c["case_id"] in case_ids]
    cases = cases[:limit]
    models = Models.from_environment()
    database = os.environ["DATABASE_URL"]
    service = AnswerService(
        database,
        models,
        os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/issue-4-mlflow.db"),
    )
    seeds = [
        Path("data/seed/phil-arrival-v1.json"),
        *sorted(Path("data/seed/policy").glob("*.json")),
    ]
    index_traces = []
    for path in seeds:
        snapshot = SourceSnapshot.model_validate_json(path.read_text())
        if snapshot.snapshot_id in {case["snapshot_id"] for case in cases}:
            EvidenceStore(database).load(snapshot)
            index_traces.append(service.prepare(snapshot.snapshot_id))
    experiment = service.tracking.get_experiment_by_name("ask-phil-offline_evaluation")
    experiment_id = (
        experiment.experiment_id
        if experiment
        else service.tracking.create_experiment(
            "ask-phil-offline_evaluation",
            artifact_location=Path("artifacts/mlflow").resolve().as_uri(),
        )
    )
    run = service.tracking.create_run(
        experiment_id,
        tags={
            "kind": "answer-policy-development-smoke",
            "expenditure_category": "offline_evaluation",
        },
    )
    document: dict[str, Any] = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "kind": "provider-development-smoke"
        if isinstance(models.llm, OpenRouterChat)
        else "local-development-smoke",
        "limitation": (
            "Exposed development cases and synthetic policy fixtures; no deployment, held-out"
            " or independently corroborated canon claim. Reviews are separate from generated "
            "answers."
        ),
        "run_id": run.info.run_id,
        "index_trace_ids": index_traces,
        "application_sha256": application_fingerprint(),
        "reference_file_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "model_settings": models.settings.model_dump(mode="json"),
        "budget": {
            "maximum_answer_calls": len(cases),
            "output_tokens_per_call": models.settings.output_tokens,
            "paid_api_calls": 0,
            "shared_trial_limit_usd": 5 if isinstance(models.llm, OpenRouterChat) else None,
            "retries": 0,
        },
        "cases": [],
        "state": "running",
    }
    save(output, document)
    try:
        for case in cases:
            receipt = service.ask(
                AskRequest(snapshot_id=case["snapshot_id"], question=case["question"]),
                category="offline_evaluation",
            )
            response = receipt.response.model_dump(mode="json")
            if receipt.response.provider_usage:
                document["budget"]["paid_api_calls"] += 1
            trace = service.tracking.get_trace(receipt.response.trace_id, flush=True)
            document["cases"].append(
                {
                    "reference": case,
                    "reference_sha256": fingerprint(case),
                    "response": response,
                    "response_sha256": fingerprint(response),
                    "trace": trace.to_dict(),
                }
            )
            save(output, document)
            print(
                f"{case['case_id']}: {response['status']} ({response['elapsed_ms']:.0f} ms)",
                flush=True,
            )
        document["state"] = "complete"
        save(output, document)
        for key in ("application_sha256", "reference_file_sha256", "lock_sha256"):
            service.tracking.log_param(run.info.run_id, key, document[key])
        service.tracking.log_artifact(run.info.run_id, str(output))
        service.tracking.set_terminated(run.info.run_id)
    except BaseException:
        document["state"] = "failed"
        save(output, document)
        service.tracking.set_terminated(run.info.run_id, status="FAILED")
        raise


def score(capture_path: Path, reviews_path: Path, output: Path) -> None:
    document = json.loads(capture_path.read_text())
    reviews = [
        QualityReview.model_validate(r) for r in json.loads(reviews_path.read_text())["reviews"]
    ]
    rows = {row["reference"]["case_id"]: row for row in document["cases"]}
    if (
        document["state"] != "complete"
        or len(reviews) != len(rows)
        or {r.case_id for r in reviews} != rows.keys()
    ):
        raise ValueError("Review must cover every case exactly once in a completed capture.")
    results = []
    for review in reviews:
        row = rows[review.case_id]
        if review.response_sha256 != fingerprint(
            row["response"]
        ) or review.reference_sha256 != fingerprint(row["reference"]):
            raise ValueError("Stale review: response or reference fingerprint differs.")
        if [f.fact for f in review.required_facts] != row["reference"]["required_facts"]:
            raise ValueError("Review must assess every required fact in reference order.")
        results.append(
            {
                "review": review.model_dump(mode="json"),
                "scores": score_answer_review(review).model_dump(mode="json"),
            }
        )
    result = {
        "capture_sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest(),
        "review_sha256": hashlib.sha256(reviews_path.read_bytes()).hexdigest(),
        "run_id": document["run_id"],
        "scorer": "reviewed-binary-dimensions-v1",
        "cases": results,
    }
    client = MlflowClient(
        tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/issue-4-mlflow.db")
    )
    client.get_run(document["run_id"])
    for row in results:
        for dimension, metric in row["scores"].items():
            if dimension == "critical_failures":
                client.log_metric(
                    document["run_id"], f"{row['review']['case_id']}.critical_failures", len(metric)
                )
                continue
            prefix = f"{row['review']['case_id']}.{dimension}"
            for name in ("passed", "assessed", "unassessed", "value"):
                if metric[name] is not None:
                    client.log_metric(document["run_id"], f"{prefix}.{name}", metric[name])
    save(output, result)
    client.log_artifact(document["run_id"], str(reviews_path))
    client.log_artifact(document["run_id"], str(output))
    print(
        f"Saved separate reviewed dimensions for {len(results)} cases; "
        f"MLflow run {document['run_id']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("capture")
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--case", action="append", default=[])
    collect.add_argument("--limit", type=int, choices=range(1, 21), default=13)
    assess = commands.add_parser("score")
    assess.add_argument("--capture", type=Path, required=True)
    assess.add_argument("--reviews", type=Path, required=True)
    assess.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a fresh output path; recorded evidence cannot be overwritten.")
    if args.command == "capture":
        capture(args.output, args.case, args.limit)
    else:
        score(args.capture, args.reviews, args.output)


if __name__ == "__main__":
    main()
