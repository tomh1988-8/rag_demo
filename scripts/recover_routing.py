"""Recover interrupted ordered captures from original storage without model calls."""

import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx
import psycopg
from mlflow import MlflowClient

from ask_phil.answers import AnswerRecord
from ask_phil.api import create_app
from ask_phil.evaluation import CapturedAnswers, document_fingerprint
from ask_phil.ingestion import build_snapshot, read_batch
from ask_phil.openrouter import Budget
from ask_phil.responses import ResponseLedger
from ask_phil.routing_evaluation import routing_comparison
from ask_phil.storage import EvidenceStore
from scripts.evaluate_investigation import database, serve
from scripts.evaluate_routing import write


def recover(
    admin_url: str, original_url: str, captures: Path, output: Path, tracking_uri: str
) -> None:
    if output.exists():
        raise ValueError("Recovery requires a new output directory; preserve the original files.")
    before, pending = Budget().summary()
    if pending:
        raise ValueError("Reconcile unsettled spending before recovery.")
    reference_path = Path("data/references/routing-ordered-v1.json")
    references = json.loads(reference_path.read_bytes())
    snapshot = build_snapshot(
        read_batch(Path(references["source_file"])), references["snapshot_id"]
    )
    if snapshot.fingerprint != references["snapshot_sha256"]:
        raise ValueError("The frozen recovery source changed.")
    tracking = MlflowClient(tracking_uri=tracking_uri)
    output.mkdir(parents=True)
    files = sorted(captures.glob("text-*.json"))
    if {p.stem for p in files} != {"text-baseline", "text-fusion"}:
        raise ValueError("Recover only the two interrupted ordered arms.")
    observations: list[dict[str, Any]] = []
    paid = 43
    with routing_comparison(reference_path).record(output), database(admin_url) as verification_url:
        EvidenceStore(verification_url).load(snapshot)
        with (
            psycopg.connect(original_url, connect_timeout=5) as original,
            serve(create_app(verification_url)) as url,
            httpx.Client(base_url=url, timeout=30, trust_env=False) as client,
        ):
            for path in files:
                document = json.loads(path.read_bytes())
                if document["case_ids"] != [row["case_id"] for row in document["cases"]]:
                    raise ValueError("Recovery cannot manufacture missing observations.")
                for row in document["cases"]:
                    response = row["response"]
                    if row["response_sha256"] != document_fingerprint(response):
                        raise ValueError("The saved response changed.")
                    persisted = original.execute(
                        "SELECT document FROM answer_responses WHERE response_id = %s",
                        (response["response_id"],),
                    ).fetchone()
                    if persisted is None or persisted[0] != response:
                        raise ValueError("The original immutable response does not match.")
                    trace = tracking.get_trace(response["trace_id"], flush=True)
                    if trace.data.spans[0].outputs != response:
                        raise ValueError("The original MLflow output does not match.")
                    # A fresh read capability exposes the exact copied document only in a
                    # disposable verification database. No original capability is changed.
                    receipt = ResponseLedger(verification_url).save(
                        AnswerRecord.model_validate(response)
                    )
                    with tempfile.TemporaryDirectory() as directory:
                        private = Path(directory) / "receipt.json"
                        private.write_text(receipt.model_dump_json())
                        readback = subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "ask_phil.cli",
                                "--api-url",
                                url,
                                "response",
                                str(private),
                            ],
                            capture_output=True,
                            text=True,
                            check=True,
                            timeout=30,
                        )
                    cli_response = json.loads(readback.stdout)
                    if cli_response != response:
                        raise ValueError("Recovered CLI readback differs.")
                    for citation in response["citations"]:
                        resolved = client.get(citation["resolve_path"])
                        resolved.raise_for_status()
                        if resolved.json()["matches"] != [
                            {k: v for k, v in citation.items() if k != "resolve_path"}
                        ]:
                            raise ValueError("Recovered citation does not resolve.")
                    raw = json.dumps(trace.to_dict(), indent=2).encode()
                    archive = f"{path.stem}-{row['case_id']}-trace.json.gz"
                    (output / archive).write_bytes(gzip.compress(raw, mtime=0))
                    observations.append(
                        {
                            "arm": path.stem,
                            "case_id": row["case_id"],
                            "response_sha256": row["response_sha256"],
                            "original_state": row["state"],
                            "original_verification_state": row.get("verification_state"),
                            "original_trace_sha256": row.get("trace_sha256"),
                            "original_response_store_matches": True,
                            "original_mlflow_output_matches": True,
                            "isolated_cli_readback_matches": True,
                            "citations_resolve": True,
                        }
                    )
                    row.update(
                        cli_response=cli_response,
                        trace_response=trace.data.spans[0].outputs,
                        trace_archive=archive,
                        trace_sha256=hashlib.sha256(raw).hexdigest(),
                        verification_state="complete",
                        state="complete",
                    )
                    paid += len(response["text_pipeline"]["model_executions"])
                document.update(
                    state="complete",
                    recovery={
                        "original_capture": str(path),
                        "original_capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "method": "Original database and MLflow equality; isolated CLI readback "
                        "with a newly issued capability for an exact document copy.",
                    },
                )
                write(output / path.name, document)
                CapturedAnswers(output / path.name, reference_path, verified=True)
    if Budget().summary() != (before, 0):
        raise ValueError("Recovery must not spend or reserve inference credit.")
    write(output / "recovery.json", {"paid_calls": 0, "observations": observations})
    write(
        output / "expense.json",
        {
            "ledger_before_usd": 0.975588,
            "ledger_after_usd": before,
            "unsettled_reservations": 0,
            "paid_calls": paid,
            "recovery_paid_calls": 0,
            "recovery_paid_cost_usd": 0,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-url", required=True)
    parser.add_argument("--original-database-url", required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", required=True)
    args = parser.parse_args()
    recover(
        args.admin_url, args.original_database_url, args.captures, args.output, args.tracking_uri
    )


if __name__ == "__main__":
    main()
