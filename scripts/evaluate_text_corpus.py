"""Record uncached retrieval and real API/CLI answers for a frozen text corpus."""

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
from ask_phil.answers import AnswerReceipt, assemble_context
from ask_phil.evaluation import (
    QualityReview,
    RetrievalReference,
    log_review_metrics,
    score_captured_answer,
    score_retrieval,
)
from ask_phil.evaluation import (
    document_fingerprint as fingerprint,
)
from ask_phil.models import OpenRouterSettings, embedding_from_environment
from ask_phil.publications import PublicationStore
from ask_phil.retrieval import TextRetriever


def save(path: Path, document: dict[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2, ensure_ascii=True) + "\n")


def score_capture(references: Path, capture_path: Path, reviews_path: Path, output: Path) -> None:
    capture = json.loads(capture_path.read_text())
    cases = {c["case_id"]: c for c in json.loads(references.read_text())["cases"]}
    rows = {r["case_id"]: r for r in capture["cases"]}
    reviews = [
        QualityReview.model_validate(r) for r in json.loads(reviews_path.read_text())["reviews"]
    ]
    if (
        capture["state"] != "complete"
        or capture["reference_file_sha256"] != hashlib.sha256(references.read_bytes()).hexdigest()
        or len(rows) != len(capture["cases"])
        or len(reviews) != len(rows)
        or {r.case_id for r in reviews} != rows.keys()
    ):
        raise ValueError("Review every captured case exactly once against its frozen references.")
    scored = []
    for review in reviews:
        row = rows[review.case_id]
        case = cases[review.case_id]
        scored.append(
            score_captured_answer(
                review, row["response"], case, tuple(f["fact"] for f in case["required_facts"])
            )
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "capture_sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest(),
        "reviews_sha256": hashlib.sha256(reviews_path.read_bytes()).hexdigest(),
        "reference_file_sha256": hashlib.sha256(references.read_bytes()).hexdigest(),
        "scorer": "reviewed-binary-dimensions-v1",
        "cases": [r.model_dump(mode="json") for r in scored],
    }
    tracking = MlflowClient(
        tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db")
    )
    experiment = tracking.get_experiment_by_name("ask-phil-corpus-response-review")
    experiment_id = (
        experiment.experiment_id
        if experiment
        else tracking.create_experiment(
            "ask-phil-corpus-response-review",
            artifact_location=Path("artifacts/mlflow").resolve().as_uri(),
        )
    )
    run = tracking.create_run(
        experiment_id,
        tags={
            "kind": "frozen-corpus-served-response-review",
            "expenditure_category": "offline_evaluation",
            "generation_expenditure_category": "serving",
        },
    )
    result["run_id"] = run.info.run_id
    save(output, result)
    try:
        tracking.log_param(run.info.run_id, "answer_model_calls_in_review", 0)
        tracking.log_param(run.info.run_id, "review_model_cost_usd", 0)
        for key in ("capture_sha256", "reviews_sha256", "reference_file_sha256", "scorer"):
            tracking.log_param(run.info.run_id, key, result[key])
        log_review_metrics(tracking, run.info.run_id, tuple(scored))
        for path in (references, capture_path, reviews_path, output):
            tracking.log_artifact(run.info.run_id, str(path))
        tracking.set_terminated(run.info.run_id)
    except BaseException:
        tracking.set_terminated(run.info.run_id, status="FAILED")
        raise
    print(f"Saved reviewed dimensions for {len(scored)} cases; MLflow run {run.info.run_id}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("retrieval", "capture", "score"))
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-cost-usd", type=Decimal, default=Decimal("1"))
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new evidence path; captures cannot be overwritten.")
    if args.mode == "score":
        if not args.capture or not args.reviews:
            parser.error("Scoring requires --capture and --reviews.")
        score_capture(args.references, args.capture, args.reviews, args.output)
        return
    dataset = json.loads(args.references.read_text())
    cases = dataset["cases"]
    if args.case:
        unknown = set(args.case) - {c["case_id"] for c in cases}
        if unknown:
            parser.error(f"Unknown cases: {sorted(unknown)}")
        cases = [c for c in cases if c["case_id"] in args.case]
    if not 1 <= len(cases) <= 30 or not Decimal("0") < args.max_cost_usd <= Decimal("1"):
        parser.error("Use 1–30 cases and a positive slice budget no greater than $1.")
    settings, embedding = embedding_from_environment()
    embedding.verify(settings.embedding_digest)
    database = os.environ["DATABASE_URL"]
    publication = PublicationStore(database).active()
    if (
        publication.manifest.snapshot_id != dataset["snapshot_id"]
        or publication.manifest.snapshot_sha256 != dataset["snapshot_sha256"]
    ):
        parser.error("Publish the exact reviewed snapshot before recording evidence.")
    retriever = TextRetriever(
        database, embedding, settings.embedding_id, settings.embedding_dimensions
    )
    profile = None
    worst_call_cost = Decimal("0")
    if args.mode == "capture":
        profile = OpenRouterSettings.model_validate_json(
            Path(os.environ["ASK_PHIL_MODELS"]).read_bytes()
        )
        # Same conservative maximum as the trial adapter's byte/token reservation.
        worst_call_cost = (
            Decimal(16000 + 4096) * profile.input_price_per_million
            + profile.output_tokens * profile.output_price_per_million
        ) / Decimal(1_000_000)
    document: dict[str, Any] = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "kind": "local-embedding-component-evaluation"
        if args.mode == "retrieval"
        else "live-provider-api-and-cli-development",
        "reference_file_sha256": hashlib.sha256(args.references.read_bytes()).hexdigest(),
        "application_sha256": application_fingerprint(),
        "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "publication": publication.model_dump(mode="json"),
        "maximum_calls": len(cases) if profile else 0,
        "maximum_slice_cost_usd": str(args.max_cost_usd),
        "shared_nonresetting_trial_cap_usd": "5",
        "cost_usd": "0",
        "retries": 0,
        "cases": [],
        "state": "running",
        "limitation": "Exposed development cases, selected passage labels, no held-out or "
        "independent canon accuracy claim. Software checks are separate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Receipts contain private read tokens and belong only in the ignored artifacts tree.
    receipts = Path("artifacts") / ("receipts-" + args.output.stem)
    if profile:
        receipts.mkdir(exist_ok=False)
    with args.output.open("x") as output:
        output.write(json.dumps(document, indent=2) + "\n")
    cost = Decimal("0")
    try:
        for case in cases:
            reference = RetrievalReference.model_validate(
                {key: case[key] for key in RetrievalReference.model_fields}
            )
            row: dict[str, Any] = {
                "case_id": reference.case_id,
                "reference_sha256": fingerprint(case),
            }
            if profile:
                if cost + worst_call_cost > args.max_cost_usd:
                    raise ValueError("Slice budget cannot reserve another bounded request.")
                # Persist an attempted call before HTTP. An interruption remains visible.
                row["state"] = "attempting"
                document["cases"].append(row)
                save(args.output, document)
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "ask_phil.cli",
                        "--api-url",
                        args.api_url,
                        "ask",
                        reference.question,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=410,
                    check=False,
                )
                if completed.returncode:
                    row["state"] = "transport_failed_cost_unknown"
                    raise ValueError(
                        "CLI/API request failed; inspect original receipts before retry."
                    )
                receipt = AnswerReceipt.model_validate_json(completed.stdout)
                (receipts / f"{reference.case_id}.json").write_text(receipt.model_dump_json())
                response = receipt.response
                row.update(
                    state="complete",
                    response=response.model_dump(mode="json"),
                    response_sha256=fingerprint(response.model_dump(mode="json")),
                )
                usage = response.provider_usage
                cost += (
                    Decimal(str(usage.cost_usd))
                    if usage and usage.cost_usd is not None
                    else worst_call_cost
                )
                document["cost_usd"] = str(cost)
                if (
                    response.model_settings != profile
                    or response.snapshot_sha256 != dataset["snapshot_sha256"]
                ):
                    raise ValueError("Served response differs from frozen model or snapshot.")
                retrieved_ids = tuple(h.passage.evidence_id for h in response.retrieved)
                context_ids = tuple(p.evidence_id for p in response.context)
                if usage is None or usage.cost_usd is None:
                    raise ValueError("Unknown provider spend; retain reservation and inspect.")
            else:
                retrieval = retriever.retrieve(dataset["snapshot_id"], reference.question, k=3)
                context = assemble_context(retrieval.hits)
                retrieved_ids = tuple(h.passage.evidence_id for h in retrieval.hits)
                context_ids = tuple(p.evidence_id for p in context)
                row.update(retrieved_ids=retrieved_ids, context_ids=context_ids)
                document["cases"].append(row)
            row["retrieval_score"] = score_retrieval(
                reference, retrieved_ids, context_ids, k=3
            ).model_dump(mode="json")
            save(args.output, document)
            print(
                f"{reference.case_id}: context_sufficient="
                f"{row['retrieval_score']['context_sufficient']}; total cost ${cost}",
                flush=True,
            )
        document["state"] = "complete"
    except BaseException:
        document["state"] = "failed"
        raise
    finally:
        save(args.output, document)


if __name__ == "__main__":
    main()
