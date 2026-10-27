"""Capture three source-reviewed text cases using the real local and capped cloud providers."""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psycopg
from mlflow import MlflowClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter

from ask_phil.answering import application_fingerprint
from ask_phil.evaluation import EvaluationRun
from ask_phil.event_graph import EventGraph
from ask_phil.evidence import SourceSnapshot
from ask_phil.models import Models
from ask_phil.openrouter import Budget
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventReview


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True, help="Disposable PostgreSQL admin URL.")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-14-mlflow.db")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; previous evidence must be retained.")
    reference_path = Path("data/references/life-text-v1.json")
    reference_bytes = reference_path.read_bytes()
    reference = json.loads(reference_bytes)
    for case in reference["cases"]:
        if args.output.with_name(f"{args.output.stem}-{case['case_id']}.json").exists():
            parser.error("A response artifact exists; choose a new output prefix.")
    directory = Path("docs/implementation/issue-14")
    inputs = [
        Path("data/seed/life-events-pilot-v1.json"),
        directory / "reviewed-claims.json",
        directory / "reviewed-reviews.json",
        Path(os.environ["ASK_PHIL_MODELS"]),
    ]
    frozen = {path: path.read_bytes() for path in inputs}
    snapshot = SourceSnapshot.model_validate_json(frozen[inputs[0]])
    batch = EventBatch.model_validate_json(frozen[inputs[1]])
    reviews = TypeAdapter(tuple[EventReview, ...]).validate_json(frozen[inputs[2]])
    identity = application_fingerprint()
    before, unsettled = Budget().summary()
    if unsettled or len(reference["cases"]) != 3:
        raise ValueError("This capture requires three cases and a settled shared ledger.")
    models = Models.from_environment()
    models.verify()
    name = "ask_phil_text_acceptance_" + uuid4().hex
    with (
        EvaluationRun(
            args.output,
            reference_path,
            [c["case_id"] for c in reference["cases"]],
            artifacts=inputs,
            metadata={
                "kind": "live-classified-text-acceptance",
                "application_sha256": identity,
                "code_revision": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip(),
                "snapshot_sha256": snapshot.fingerprint,
                "input_sha256": {str(p): hashlib.sha256(b).hexdigest() for p, b in frozen.items()},
                "ledger_before_usd": before,
                "maximum_calls": 3,
                "retries": 0,
                "scope": (
                    "Exposed source-based text cases with real embeddings and generation; "
                    "no held-out or canon acceptance."
                ),
            },
        ) as run,
        psycopg.connect(args.database_url, autocommit=True) as admin,
    ):
        if reference_path.read_bytes() != reference_bytes or any(
            p.read_bytes() != b for p, b in frozen.items()
        ):
            raise ValueError("Frozen capture inputs changed before execution.")
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        database_url = make_conninfo(args.database_url, dbname=name)
        try:
            EvidenceStore(database_url).load(snapshot)
            audit = EventGraph(database_url).install(batch, reviews)
            index = TextRetriever(
                database_url,
                models.embedding,
                models.settings.embedding_id,
                models.settings.embedding_dimensions,
            ).prepare(snapshot.snapshot_id)
            run.annotate(graph_sha256=audit.graph_sha256, index=index.model_dump(mode="json"))
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            with tempfile.TemporaryFile() as log:
                process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "ask_phil.api:create_app",
                        "--factory",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--log-level",
                        "error",
                    ],
                    env={
                        **os.environ,
                        "DATABASE_URL": database_url,
                        "MLFLOW_TRACKING_URI": args.tracking_uri,
                    },
                    stdout=log,
                    stderr=log,
                )
                try:
                    with httpx.Client(
                        base_url=f"http://127.0.0.1:{port}", timeout=200, trust_env=False
                    ) as client:
                        deadline = time.monotonic() + 30
                        while True:
                            try:
                                ready = client.get(
                                    f"/v1/snapshots/{snapshot.snapshot_id}/evidence/{snapshot.passages[0].evidence_id}"
                                )
                                ready.raise_for_status()
                                break
                            except httpx.HTTPError:
                                if process.poll() is not None or time.monotonic() >= deadline:
                                    raise RuntimeError(
                                        "The local acceptance API failed to start."
                                    ) from None
                                time.sleep(0.1)
                        tracking = MlflowClient(tracking_uri=args.tracking_uri)
                        for case in reference["cases"]:

                            def capture(case: dict[str, Any] = case) -> dict[str, object]:
                                response = client.post(
                                    "/v1/answers",
                                    json={
                                        "question": case["question"],
                                        "snapshot_id": snapshot.snapshot_id,
                                    },
                                )
                                response.raise_for_status()
                                receipt = response.json()
                                answer = receipt["response"]
                                # Persist public output before any verification may fail.
                                retained = args.output.with_name(
                                    f"{args.output.stem}-{case['case_id']}.json"
                                )
                                with retained.open("x") as destination:
                                    json.dump(answer, destination, indent=2)
                                    destination.write("\n")
                                if (
                                    answer["application_sha256"] != identity
                                    or answer["snapshot_sha256"] != snapshot.fingerprint
                                    or answer["model_settings"]
                                    != models.settings.model_dump(mode="json")
                                ):
                                    raise ValueError(
                                        "The running application changed during capture."
                                    )
                                trace = tracking.get_trace(answer["trace_id"], flush=True)
                                root = next(s for s in trace.data.spans if s.parent_id is None)
                                if root.outputs != answer:
                                    raise ValueError(
                                        "Actual trace output differs from the served answer."
                                    )
                                for citation in answer["citations"]:
                                    evidence = client.get(citation["resolve_path"])
                                    evidence.raise_for_status()
                                    if evidence.json()["matches"][0]["text"] != citation["text"]:
                                        raise ValueError("A citation does not resolve.")
                                saved = client.get(
                                    f"/v1/responses/{answer['response_id']}",
                                    headers={
                                        "Authorization": f"Bearer {receipt['read_token']}",
                                    },
                                )
                                saved.raise_for_status()
                                if saved.json() != answer:
                                    raise ValueError(
                                        "Saved response differs from the served answer."
                                    )
                                return {
                                    "response": answer,
                                    "trace_output_matches": True,
                                    "citations_resolve": True,
                                    "saved_response_matches": True,
                                }

                            run.capture(case["case_id"], capture)
                            spent, unsettled = Budget().summary()
                            run.annotate(ledger_after_usd=spent, unsettled_reservations=unsettled)
                            if unsettled:
                                raise ValueError(
                                    "Unsettled provider reservation; stop without retry."
                                )
                        spent, unsettled = Budget().summary()
                        run.annotate(ledger_after_usd=spent, unsettled_reservations=unsettled)
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    print(json.dumps({"output": str(args.output), "cases": 3}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
