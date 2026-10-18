"""One bounded extraction call on the frozen, independently reviewed parentage slice."""

import argparse
import hashlib
import json
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx
import mlflow
from mlflow import MlflowClient
from mlflow.entities import MlflowExperimentLocation

from ask_phil.answering import application_fingerprint
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionBudget, ExecutionLimits
from ask_phil.identity import IdentityCatalogue
from ask_phil.model_transport import cloud_transport
from ask_phil.openrouter import BUDGET_PATH, Budget, OpenRouterChat, OpenRouterProfile, read_key
from ask_phil.parentage import ExtractedClaims
from ask_phil.parentage_evaluation import score_extraction
from ask_phil.parentage_extraction import EXTRACTION_PROMPT, ParentageLLM, extract_parentage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=Path("config/evaluation-sol-low.json"))
    parser.add_argument("--snapshot", type=Path, default=Path("data/seed/family-pilot-v1.json"))
    parser.add_argument("--reference", type=Path, default=Path("data/references/parentage-v1.json"))
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-11-mlflow.db")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new path. No paid call was made.")
    snapshot = SourceSnapshot.model_validate_json(args.snapshot.read_bytes())
    reference = json.loads(args.reference.read_bytes())
    if reference["snapshot_sha256"] != snapshot.fingerprint:
        parser.error("The frozen reference and source snapshot differ.")
    catalogue = IdentityCatalogue.model_validate(reference["catalogue"])
    expected = ExtractedClaims.model_validate({"claims": reference["expected_claims"]})
    profile = OpenRouterProfile.model_validate_json(args.profile.read_bytes(), extra="ignore")
    limits = ExecutionLimits(model_calls=1, tool_calls=0, capabilities=(), http_calls=3)
    budget = ExecutionBudget(limits)
    mlflow.set_tracking_uri(args.tracking_uri)
    tracking = MlflowClient(tracking_uri=args.tracking_uri)
    name = "ask-phil-offline_evaluation"
    experiment = tracking.get_experiment_by_name(name)
    experiment_id = (
        experiment.experiment_id
        if experiment
        else tracking.create_experiment(
            name, artifact_location=str(Path("artifacts/mlflow").resolve().as_uri())
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Claim the artifact path before spending; even failures retain accounting and raw output.
    with args.output.open("x") as output:
        batch = None
        failure = None
        elapsed_ms = None
        with httpx.Client(
            timeout=profile.request_timeout_seconds,
            trust_env=False,
            follow_redirects=False,
            transport=cloud_transport(profile.answer_model),
        ) as client:
            chat = OpenRouterChat(profile, read_key(), Budget(), client)
            llm = ParentageLLM(chat)
            with (
                budget.activate(),
                mlflow.start_span(
                    "parentage_extraction",
                    trace_destination=MlflowExperimentLocation(experiment_id),
                ) as span,
            ):
                span.set_inputs(
                    {"snapshot_sha256": snapshot.fingerprint, "catalogue": catalogue.model_dump()}
                )
                try:
                    batch, elapsed_ms = extract_parentage(snapshot, catalogue, llm)
                except (ValueError, RuntimeError):
                    # Upstream exception text is deliberately excluded from the artifact.
                    failure = "extraction_failed"
                    span.set_status("ERROR")
                score = score_extraction(llm.raw or "", expected, snapshot)
                with sqlite3.connect(f"file:{BUDGET_PATH}?mode=ro", uri=True) as ledger:
                    spent, unsettled = ledger.execute(
                        "SELECT SUM(microdollars), SUM(CASE WHEN settled=0 THEN 1 ELSE 0 END) "
                        "FROM reservations"
                    ).fetchone()
                record = {
                    "captured_at": datetime.now(UTC).isoformat(),
                    "code_revision": subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], text=True
                    ).strip(),
                    "application_sha256": application_fingerprint(),
                    "prompt_sha256": hashlib.sha256(EXTRACTION_PROMPT.encode()).hexdigest(),
                    "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
                    "schema_sha256": hashlib.sha256(
                        json.dumps(ExtractedClaims.model_json_schema(), sort_keys=True).encode()
                    ).hexdigest(),
                    "profile": profile.model_dump(mode="json"),
                    "expenditure_category": "offline_evaluation",
                    "raw": llm.raw,
                    "batch": batch.model_dump(mode="json") if batch else None,
                    "score": score.model_dump(mode="json"),
                    "usage": chat.last_call.model_dump(mode="json") if chat.last_call else None,
                    "execution": budget.record().model_dump(mode="json"),
                    "elapsed_ms": elapsed_ms,
                    "failure": failure,
                    "trace_id": span.trace_id,
                    "shared_ledger_usd": spent / 1000000,
                    "unsettled_reservations": unsettled,
                    "limitation": (
                        "Four agent-reviewed exposed labels; no held-out, human "
                        "or independent canon acceptance."
                    ),
                }
                span.set_outputs(record)
            tracking.get_trace(record["trace_id"], flush=True)
            json.dump(record, output, indent=2, ensure_ascii=False)
            output.write("\n")
    print(json.dumps({"output": str(args.output), "score": record["score"], "failure": failure}))
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
