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
from ask_phil.parentage import ClaimBatch, ExtractedClaims
from ask_phil.parentage_evaluation import score_extraction
from ask_phil.parentage_extraction import EXTRACTION_PROMPT, ParentageLLM, extract_parentage
from ask_phil.relationship_evaluation import score_relationships
from ask_phil.relationship_extraction import RELATIONSHIP_PROMPT, extract_relationships
from ask_phil.relationships import ExtractedRelationships, RelationshipBatch
from ask_phil.tracing import experiment_for


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--relationships", action="store_true", help="Run the relationship-history slice."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", type=Path, default=Path("config/evaluation-sol-low.json"))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--tracking-uri")
    args = parser.parse_args()
    args.snapshot = args.snapshot or Path(
        "data/seed/relationship-pilot-v1.json"
        if args.relationships
        else "data/seed/family-pilot-v1.json"
    )
    args.reference = args.reference or Path(
        "data/references/relationships-v1.json"
        if args.relationships
        else "data/references/parentage-v1.json"
    )
    args.tracking_uri = args.tracking_uri or (
        "sqlite:///artifacts/issue-12-mlflow.db"
        if args.relationships
        else "sqlite:///artifacts/issue-11-mlflow.db"
    )
    if args.output.exists():
        parser.error("Output already exists; choose a new path. No paid call was made.")
    snapshot = SourceSnapshot.model_validate_json(args.snapshot.read_bytes())
    reference = json.loads(args.reference.read_bytes())
    if reference["snapshot_sha256"] != snapshot.fingerprint:
        parser.error("The frozen reference and source snapshot differ.")
    catalogue = IdentityCatalogue.model_validate(reference["catalogue"])
    output_cls = ExtractedRelationships if args.relationships else ExtractedClaims
    expected = output_cls.model_validate({"claims": reference["expected_claims"]})
    prompt = RELATIONSHIP_PROMPT if args.relationships else EXTRACTION_PROMPT
    profile = OpenRouterProfile.model_validate_json(args.profile.read_bytes(), extra="ignore")
    limits = ExecutionLimits(model_calls=1, tool_calls=0, capabilities=(), http_calls=3)
    budget = ExecutionBudget(limits)
    mlflow.set_tracking_uri(args.tracking_uri)
    tracking = MlflowClient(tracking_uri=args.tracking_uri)
    experiment_id = experiment_for(tracking, "offline_evaluation")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Claim the artifact path before spending; even failures retain accounting and raw output.
    with args.output.open("x") as output:
        batch: ClaimBatch | RelationshipBatch | None = None
        failure = None
        elapsed_ms = None
        with httpx.Client(
            timeout=profile.request_timeout_seconds,
            trust_env=False,
            follow_redirects=False,
            transport=cloud_transport(profile.answer_model),
        ) as client:
            chat = OpenRouterChat(profile, read_key(), Budget(), client)
            llm = ParentageLLM(chat, output_cls)
            with (
                budget.activate(),
                mlflow.start_span(
                    "relationship_extraction" if args.relationships else "parentage_extraction",
                    trace_destination=MlflowExperimentLocation(experiment_id),
                ) as span,
            ):
                span.set_inputs(
                    {"snapshot_sha256": snapshot.fingerprint, "catalogue": catalogue.model_dump()}
                )
                try:
                    batch, elapsed_ms = (
                        extract_relationships(snapshot, catalogue, llm)
                        if args.relationships
                        else extract_parentage(snapshot, catalogue, llm)
                    )
                except (ValueError, RuntimeError):
                    # Upstream exception text is deliberately excluded from the artifact.
                    failure = "extraction_failed"
                    span.set_status("ERROR")
                score = (
                    score_relationships(
                        llm.raw or "",
                        ExtractedRelationships.model_validate(expected.model_dump()),
                        snapshot,
                        reference.get("alternatives"),
                    )
                    if args.relationships
                    else score_extraction(
                        llm.raw or "",
                        ExtractedClaims.model_validate(expected.model_dump()),
                        snapshot,
                    )
                )
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
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                    "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
                    "schema_sha256": hashlib.sha256(
                        json.dumps(output_cls.model_json_schema(), sort_keys=True).encode()
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
                        "Agent-reviewed exposed labels; no held-out, human "
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
