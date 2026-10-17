"""Capture bounded responses, then score separately reviewed immutable outputs."""

import argparse
import hashlib
import json
import os
from functools import partial
from pathlib import Path
from typing import Any

from mlflow import MlflowClient

from ask_phil.answering import AnswerService, application_fingerprint
from ask_phil.answers import AskRequest
from ask_phil.evaluation import (
    EvaluationRun,
    EvaluationTracking,
    review_capture,
)
from ask_phil.evidence import SourceSnapshot
from ask_phil.models import Models
from ask_phil.openrouter import OpenRouterChat
from ask_phil.storage import EvidenceStore

REFERENCE = Path("data/references/answer-policy-v2.json")


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
    document: dict[str, Any] = {
        "kind": "provider-development-smoke"
        if isinstance(models.llm, OpenRouterChat)
        else "local-development-smoke",
        "limitation": (
            "Exposed development cases and synthetic policy fixtures; no deployment, held-out"
            " or independently corroborated canon claim. Reviews are separate from generated "
            "answers."
        ),
        "index_trace_ids": index_traces,
        "application_sha256": application_fingerprint(),
        "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "model_settings": models.settings.model_dump(mode="json"),
        "budget": {
            "maximum_answer_calls": len(cases),
            "output_tokens_per_call": models.settings.output_tokens,
            "paid_api_calls": 0,
            "shared_trial_limit_usd": 5 if isinstance(models.llm, OpenRouterChat) else None,
            "retries": 0,
        },
    }
    tracking = EvaluationTracking(
        service.tracking,
        "ask-phil-offline_evaluation",
        {
            "kind": "answer-policy-development-smoke",
            "expenditure_category": "offline_evaluation",
        },
    )
    with EvaluationRun(
        output,
        REFERENCE,
        [case["case_id"] for case in cases],
        metadata=document,
        tracking=tracking,
    ) as run:

        def execute(case: dict[str, Any]) -> dict[str, Any]:
            receipt = service.ask(
                AskRequest(snapshot_id=case["snapshot_id"], question=case["question"]),
                category="offline_evaluation",
            )
            response = receipt.response.model_dump(mode="json")
            if receipt.response.provider_usage:
                document["budget"]["paid_api_calls"] += 1
            run.annotate(budget=document["budget"])
            trace = service.tracking.get_trace(receipt.response.trace_id, flush=True)
            return {"response": response, "trace": trace.to_dict()}

        for case in cases:
            row = run.capture(case["case_id"], partial(execute, case))
            response = row["response"]
            print(
                f"{case['case_id']}: {response['status']} ({response['elapsed_ms']:.0f} ms)",
                flush=True,
            )


def score(
    capture_path: Path, reviews_path: Path, output: Path, references: Path = REFERENCE
) -> None:
    client = MlflowClient(
        tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/issue-4-mlflow.db")
    )
    result = review_capture(
        capture_path,
        reviews_path,
        references,
        output,
        tracking=EvaluationTracking(
            client,
            "ask-phil-policy-response-review",
            {"kind": "answer-policy-response-review", "expenditure_category": "offline_evaluation"},
        ),
    )
    print(
        f"Saved separate reviewed dimensions for {len(result['cases'])} cases; "
        f"MLflow run {result['run_id']}"
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
    assess.add_argument("--references", type=Path, default=REFERENCE)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a fresh output path; recorded evidence cannot be overwritten.")
    if args.command == "capture":
        capture(args.output, args.case, args.limit)
    else:
        score(args.capture, args.reviews, args.output, args.references)


if __name__ == "__main__":
    main()
