"""Record uncached retrieval and real API/CLI answers for a frozen text corpus."""

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
from ask_phil.answers import AnswerReceipt, AnswerRecord, assemble_context
from ask_phil.evaluation import (
    EvaluationRun,
    EvaluationTracking,
    RetrievalReference,
    review_capture,
    score_retrieval,
)
from ask_phil.models import OpenRouterSettings, embedding_from_environment
from ask_phil.publications import PublicationStore
from ask_phil.retrieval import TextRetriever


def score_capture(references: Path, capture_path: Path, reviews_path: Path, output: Path) -> None:
    tracking = MlflowClient(
        tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db")
    )
    result = review_capture(
        capture_path,
        reviews_path,
        references,
        output,
        tracking=EvaluationTracking(
            tracking,
            "ask-phil-corpus-response-review",
            {
                "kind": "frozen-corpus-served-response-review",
                "expenditure_category": "offline_evaluation",
                "generation_expenditure_category": "serving",
            },
        ),
    )
    print(
        f"Saved reviewed dimensions for {len(result['cases'])} cases; "
        f"MLflow run {result['run_id']}."
    )


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
        "kind": "local-embedding-component-evaluation"
        if args.mode == "retrieval"
        else "live-provider-api-and-cli-development",
        "application_sha256": application_fingerprint(),
        "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "publication": publication.model_dump(mode="json"),
        "maximum_calls": len(cases) if profile else 0,
        "maximum_slice_cost_usd": str(args.max_cost_usd),
        "shared_nonresetting_trial_cap_usd": "5",
        "cost_usd": "0",
        "retries": 0,
        "limitation": "Exposed development cases, selected passage labels, no held-out or "
        "independent canon accuracy claim. Software checks are separate.",
    }
    # Receipts contain private read tokens and belong only in the ignored artifacts tree.
    receipts = Path("artifacts") / ("receipts-" + args.output.stem)
    if profile:
        receipts.mkdir(mode=0o700, exist_ok=False)
    cost = Decimal("0")
    with EvaluationRun(
        args.output, args.references, [case["case_id"] for case in cases], metadata=document
    ) as run:

        def execute(case: dict[str, Any]) -> dict[str, Any]:
            nonlocal cost
            reference = RetrievalReference.model_validate(
                {key: case[key] for key in RetrievalReference.model_fields}
            )
            row: dict[str, Any] = {}
            if profile:
                if cost + worst_call_cost > args.max_cost_usd:
                    raise ValueError("Slice budget cannot reserve another bounded request.")
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
                    run.annotate(stop_reason="transport_failed_cost_unknown")
                    raise ValueError(
                        "CLI/API request failed; inspect original receipts before retry."
                    )
                receipt = AnswerReceipt.model_validate_json(completed.stdout)
                with (receipts / f"{reference.case_id}.json").open("x") as receipt_file:
                    os.chmod(receipt_file.name, 0o600)
                    receipt_file.write(receipt.model_dump_json())
                response = receipt.response
                row.update(
                    response=response.model_dump(mode="json"),
                )
                usage = response.provider_usage
                cost += (
                    Decimal(str(usage.cost_usd))
                    if usage and usage.cost_usd is not None
                    else worst_call_cost
                )
                run.annotate(cost_usd=str(cost))
                retrieved_ids = tuple(h.passage.evidence_id for h in response.retrieved)
                context_ids = tuple(p.evidence_id for p in response.context)
            else:
                retrieval = retriever.retrieve(dataset["snapshot_id"], reference.question, k=3)
                context = assemble_context(retrieval.hits)
                retrieved_ids = tuple(h.passage.evidence_id for h in retrieval.hits)
                context_ids = tuple(p.evidence_id for p in context)
                row.update(retrieved_ids=retrieved_ids, context_ids=context_ids)
            row["retrieval_score"] = score_retrieval(
                reference, retrieved_ids, context_ids, k=3
            ).model_dump(mode="json")
            return row

        for case in cases:
            row = run.capture(case["case_id"], partial(execute, case))
            if profile:
                response = AnswerRecord.model_validate(row["response"])
                if (
                    response.model_settings != profile
                    or response.snapshot_sha256 != dataset["snapshot_sha256"]
                ):
                    raise ValueError("Served response differs from frozen model or snapshot.")
                if response.provider_usage is None or response.provider_usage.cost_usd is None:
                    run.annotate(stop_reason="unknown_provider_spend")
                    raise ValueError("Unknown provider spend; retain reservation and inspect.")
            print(
                f"{case['case_id']}: context_sufficient="
                f"{row['retrieval_score']['context_sufficient']}; total cost ${cost}",
                flush=True,
            )


if __name__ == "__main__":
    main()
