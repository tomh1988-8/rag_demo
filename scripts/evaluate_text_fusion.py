"""Capture four capped, uncached text ablations; score source spans separately."""

import argparse
import gzip
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psycopg
import uvicorn
from fastapi import FastAPI
from mlflow import MlflowClient
from psycopg import sql
from psycopg.conninfo import make_conninfo

from ask_phil.answering import application_fingerprint
from ask_phil.api import create_app
from ask_phil.evaluation import (
    CapturedAnswers,
    EvaluationRun,
    EvaluationTracking,
    RetrievalReference,
    score_retrieval,
)
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionLimits
from ask_phil.ingestion import build_snapshot, read_batch
from ask_phil.models import Models
from ask_phil.openrouter import Budget
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore
from ask_phil.text_evaluation import SpanExpectation, score_text_context
from ask_phil.text_retrieval import TextPolicy

REFERENCES = Path("data/references/text-fusion-v1.json")
MODES = ("baseline", "fusion", "expansion", "combined")
LIMITS = ExecutionLimits(
    model_calls=5,
    tool_calls=3,
    http_calls=16,
    seconds=90,
    context_bytes=4000,
    spend_usd=Decimal("0.30"),
    concurrency=1,
)


@contextmanager
def serve(app: FastAPI) -> Iterator[str]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 15
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            if not server.started:
                raise RuntimeError("Local capture API did not start.")
            yield f"http://127.0.0.1:{listener.getsockname()[1]}"
        finally:
            server.should_exit = True
            thread.join(timeout=15)
            if thread.is_alive():
                raise RuntimeError("Local capture API did not stop.")


def source() -> tuple[dict[str, Any], SourceSnapshot]:
    reference = json.loads(REFERENCES.read_bytes())
    path = Path(reference["source_file"])
    if hashlib.sha256(path.read_bytes()).hexdigest() != reference["source_file_sha256"]:
        raise ValueError("Frozen source input changed.")
    snapshot = build_snapshot(read_batch(path), reference["snapshot_id"])
    if snapshot.fingerprint != reference["snapshot_sha256"]:
        raise ValueError("Rebuilt source differs from the frozen comparison snapshot.")
    return reference, snapshot


def capture(admin_url: str, output: Path, tracking_uri: str, maximum: Decimal) -> None:
    if output.exists() or not 0 < maximum <= Decimal("0.50"):
        raise ValueError("Choose a fresh output directory and a positive cap no larger than $0.50.")
    reference, snapshot = source()
    models = Models.from_environment()
    before, unsettled = Budget().summary()
    if unsettled:
        raise ValueError("Preserve and settle outstanding shared-ledger reservations first.")
    output.mkdir(parents=True)
    identity = application_fingerprint()
    inputs = sorted(Path("src/ask_phil").glob("*.py")) + [
        Path(__file__),
        REFERENCES,
        Path(reference["source_file"]),
        Path("uv.lock"),
        Path(os.environ["ASK_PHIL_MODELS"]),
    ]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    (output / "software-inputs.json").write_text(json.dumps(hashes, indent=2) + "\n")
    cases = [c for c in reference["cases"] if c["split"] == "development"]
    if len(cases) != 4:
        raise ValueError("The frozen ticket plan requires exactly four development questions.")
    database_name = "ask_phil_fusion_" + uuid4().hex
    tracking = MlflowClient(tracking_uri=tracking_uri)
    with psycopg.connect(admin_url, autocommit=True) as admin:
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(database_name))
        )
        database = make_conninfo(admin_url, dbname=database_name)
        try:
            EvidenceStore(database).load(snapshot)
            models.verify()
            started = time.perf_counter()
            index = TextRetriever(
                database,
                models.embedding,
                models.settings.embedding_id,
                models.settings.embedding_dimensions,
            ).prepare(snapshot.snapshot_id)
            indexing_ms = (time.perf_counter() - started) * 1000
            for mode in MODES:
                policy = TextPolicy.model_validate({"mode": mode})
                metadata = {
                    "kind": "uncached-text-development-ablation",
                    "mode": mode,
                    "policy": policy.model_dump(),
                    "policy_sha256": policy.fingerprint,
                    "application_sha256": identity,
                    "software_inputs": hashes,
                    "model_settings": models.settings.model_dump(mode="json"),
                    "index": index.model_dump(),
                    "indexing_ms": indexing_ms,
                    "limits": LIMITS.model_dump(mode="json"),
                    "ledger_before_usd": before,
                    "maximum_additional_usd": str(maximum),
                    "maximum_paid_calls": 24,
                    "cache_enabled": False,
                    "repeats_per_question": 1,
                    "limitation": (
                        "Four exposed source-reviewed questions; no held-out or canon acceptance."
                    ),
                }
                with (
                    EvaluationRun(
                        output / f"{mode}.json",
                        REFERENCES,
                        [c["case_id"] for c in cases],
                        metadata=metadata,
                        artifacts=inputs,
                        tracking=EvaluationTracking(
                            tracking,
                            "ask-phil-text-fusion-development",
                            {
                                "mode": mode,
                                "expenditure_category": "offline_evaluation",
                            },
                        ),
                    ) as run,
                    serve(
                        create_app(
                            database,
                            models=models,
                            tracking_uri=tracking_uri,
                            text_policy=policy,
                            execution_limits=LIMITS,
                        )
                    ) as url,
                ):
                    with httpx.Client(base_url=url, timeout=110, trust_env=False) as client:
                        for position, case in enumerate(cases):
                            spent, pending = Budget().summary()
                            if pending or Decimal(str(spent - before)) + LIMITS.spend_usd > maximum:
                                raise ValueError(
                                    "Ticket spending cap cannot reserve the next request."
                                )
                            if application_fingerprint() != identity or any(
                                hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p)]
                                for p in inputs
                            ):
                                raise ValueError("Frozen capture software or inputs changed.")

                            private_receipt: dict[str, Any] = {}

                            def execute(
                                selected: dict[str, Any] = case,
                                cli: bool = position == 0,
                                receipt_state: dict[str, Any] = private_receipt,
                            ) -> dict[str, Any]:
                                start = time.perf_counter()
                                if cli:
                                    completed = subprocess.run(
                                        [
                                            sys.executable,
                                            "-m",
                                            "ask_phil.cli",
                                            "--api-url",
                                            url,
                                            "ask",
                                            selected["question"],
                                            "--snapshot",
                                            snapshot.snapshot_id,
                                        ],
                                        check=True,
                                        capture_output=True,
                                        text=True,
                                        timeout=110,
                                    )
                                    receipt = json.loads(completed.stdout)
                                else:
                                    reply = client.post(
                                        "/v1/answers",
                                        json={
                                            "snapshot_id": snapshot.snapshot_id,
                                            "question": selected["question"],
                                        },
                                    )
                                    reply.raise_for_status()
                                    receipt = reply.json()
                                elapsed = (time.perf_counter() - start) * 1000
                                response = receipt["response"]
                                receipt_state.update(receipt)
                                return {
                                    "response": response,
                                    "transport": "cli" if cli else "api",
                                    "complete_api_elapsed_ms": elapsed,
                                }

                            def verify(
                                row: dict[str, Any], receipt_state: dict[str, Any] = private_receipt
                            ) -> dict[str, Any]:
                                response = row["response"]
                                if (
                                    response["application_sha256"] != identity
                                    or response["text_pipeline"]["cache_enabled"]
                                ):
                                    raise ValueError(
                                        "Served response differs from the uncached frozen "
                                        "application."
                                    )
                                with tempfile.TemporaryDirectory() as directory:
                                    private = Path(directory) / "receipt.json"
                                    private.write_text(json.dumps(receipt_state))
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
                                        check=True,
                                        capture_output=True,
                                        text=True,
                                        timeout=20,
                                    )
                                cli_response = json.loads(readback.stdout)
                                trace = tracking.get_trace(response["trace_id"], flush=True)
                                root = next(s for s in trace.data.spans if s.name == "text_rag")
                                if cli_response != response or root.outputs != response:
                                    raise ValueError(
                                        "Saved CLI or original root-trace readback differs."
                                    )
                                for citation in response["citations"]:
                                    resolved = client.get(citation["resolve_path"])
                                    resolved.raise_for_status()
                                    expected = {
                                        k: v for k, v in citation.items() if k != "resolve_path"
                                    }
                                    if resolved.json()["matches"] != [expected]:
                                        raise ValueError(
                                            "Expanded citation does not resolve exactly."
                                        )
                                return {
                                    "cli_response": cli_response,
                                    "trace_response": root.outputs,
                                    "trace": trace.to_dict(),
                                }

                            row = run.capture(case["case_id"], execute, verify=verify)
                            spent, pending = Budget().summary()
                            run.annotate(ledger_after_usd=spent, unsettled_reservations=pending)
                            print(
                                f"{mode}/{case['case_id']}: {row['response']['status']}", flush=True
                            )
        finally:
            admin.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database_name))
            )


def score(directory: Path, output: Path) -> None:
    if output.exists():
        raise ValueError("Choose a fresh score output; recorded results cannot be overwritten.")
    reference, snapshot = source()
    results: dict[str, Any] = {
        "kind": "text-stage-metrics-v1",
        "cases": [],
        "reference_sha256": hashlib.sha256(REFERENCES.read_bytes()).hexdigest(),
    }
    for mode in MODES:
        path = directory / f"{mode}.json"
        if path.exists():
            captured = CapturedAnswers(path, REFERENCES)
        else:
            # Published raw traces are losslessly archived; parsing still binds
            # the original uncompressed capture/reference fingerprints.
            with tempfile.NamedTemporaryFile(suffix=".json") as retained:
                retained.write(gzip.decompress(path.with_suffix(".json.gz").read_bytes()))
                retained.flush()
                captured = CapturedAnswers(Path(retained.name), REFERENCES)
        for row in captured.cases.values():
            response = row["response"]
            record = response["text_pipeline"]
            case = row["reference"]
            labels = RetrievalReference.model_validate(
                {
                    key: case[key]
                    for key in (
                        "case_id",
                        "question",
                        "answerable",
                        "relevant_ids",
                    )
                }
                | {
                    "required_facts": [
                        {"fact": f["fact"], "sufficient_sets": f["sufficient_sets"]}
                        for f in case["required_facts"]
                    ]
                }
            )
            ranked = tuple(
                dict.fromkeys(
                    h["passage"]["evidence_id"]
                    for ranking in record["rankings"]
                    for h in ranking["hits"]
                )
            )
            fused = tuple(c["passage"]["evidence_id"] for c in record["fused_candidates"]) or ranked
            spans = tuple(
                tuple(SpanExpectation.model_validate(s) for s in f["span_sufficient_sets"][0])
                for f in case["required_facts"]
            )
            from ask_phil.answers import AnswerRecord

            actual = AnswerRecord.model_validate(response)
            results["cases"].append(
                {
                    "mode": mode,
                    "case_id": case["case_id"],
                    "status": response["status"],
                    "response_sha256": row["response_sha256"],
                    "candidate": score_retrieval(
                        labels, ranked, (), k=max(1, len(ranked))
                    ).model_dump(),
                    "fused": score_retrieval(
                        labels, fused, (), k=record["policy"]["selected_hits"]
                    ).model_dump(),
                    "context": score_text_context(
                        snapshot, spans, actual.context, answerable=case["answerable"]
                    ).model_dump(),
                    "complete_api_elapsed_ms": row["complete_api_elapsed_ms"],
                    "estimated_api_cost_usd": response["estimated_api_cost_usd"],
                    "usage": response["usage"],
                    "model_operations": response["execution"]["model_calls"],
                    "paid_calls": sum(
                        c["provider_usage"] is not None for c in record["model_executions"]
                    ),
                    "variant_proposals": record["variants"]["proposals"],
                    "fallback_reasons": record["fallback_reasons"],
                }
            )
    with output.open("x") as destination:
        destination.write(json.dumps(results, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("capture")
    collect.add_argument("--database-url", required=True)
    collect.add_argument("--output", type=Path, required=True)
    collect.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-24-mlflow.db")
    collect.add_argument("--max-additional-usd", type=Decimal, required=True)
    assess = commands.add_parser("score")
    assess.add_argument("--directory", type=Path, required=True)
    assess.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture":
        capture(args.database_url, args.output, args.tracking_uri, args.max_additional_usd)
    else:
        score(args.directory, args.output)


if __name__ == "__main__":
    main()
