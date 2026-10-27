"""Capture real review publication, HTTP/CLI answers, recovery and MLflow readback."""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psycopg
import uvicorn
from mlflow import MlflowClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter

from ask_phil.answering import application_fingerprint
from ask_phil.answers import AnswerReceipt
from ask_phil.api import create_app
from ask_phil.claims import ClaimReview
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionLimits
from ask_phil.family_graph import FamilyGraph
from ask_phil.knowledge_review import KnowledgeReview, ReviewRequest
from ask_phil.models import Models
from ask_phil.parentage import ClaimBatch
from ask_phil.publications import PublicationStore, RefreshRun
from ask_phil.refresh import SourceRefresh
from ask_phil.refresh_journal import RefreshFailed
from ask_phil.storage import EvidenceStore

PILOT = Path("docs/implementation/issue-15")


def write(path: Path, document: object) -> None:
    with path.open("x") as stream:
        stream.write(json.dumps(document, indent=2, ensure_ascii=False) + "\n")


@contextmanager
def database(admin: str) -> Iterator[str]:
    name = "review_acceptance_" + uuid4().hex
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        try:
            yield make_conninfo(admin, dbname=name)
        finally:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@contextmanager
def serve(database_url: str, models: Models, tracking_uri: str) -> Iterator[str]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(
                    database_url,
                    models=models,
                    tracking_uri=tracking_uri,
                    execution_limits=ExecutionLimits(spend_usd=Decimal(0)),
                ),
                log_level="error",
            )
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            if not server.started:
                raise RuntimeError("The acceptance API did not start.")
            yield f"http://127.0.0.1:{listener.getsockname()[1]}"
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("The acceptance API did not stop.")


def capture(
    client: httpx.Client,
    tracking: MlflowClient,
    receipt: AnswerReceipt,
    case_id: str,
    fingerprint: str,
) -> dict[str, Any]:
    answer = receipt.response.model_dump(mode="json")
    if answer["application_sha256"] != fingerprint:
        raise ValueError("Application inputs changed during the acceptance run.")
    trace = tracking.get_trace(receipt.response.trace_id, flush=True)
    if trace is None:
        raise ValueError("Missing actual answer trace.")
    roots = [s for s in trace.data.spans if s.name == answer["route"]]
    if len(roots) != 1 or roots[0].outputs != answer:
        raise ValueError("Actual MLflow root output differs from the served answer.")
    for citation in answer["citations"]:
        result = client.get(citation["resolve_path"])
        result.raise_for_status()
        passage = result.json()["matches"][0]
        if any(passage[key] != citation[key] for key in ("evidence_id", "text", "sha256")):
            raise ValueError("Citation differs from the retained source passage.")
    saved = client.get(
        f"/v1/responses/{receipt.response.response_id}",
        headers={"Authorization": f"Bearer {receipt.read_token}"},
    )
    saved.raise_for_status()
    if saved.json() != answer:
        raise ValueError("Saved response differs from the served response.")
    if answer["usage"]["input_tokens"] != 0 or answer["usage"]["output_tokens"] != 0:
        raise ValueError("This deterministic review capture must not generate answer tokens.")
    return {
        "case_id": case_id,
        "response": answer,
        "trace_output_matches": True,
        "citations_resolve": True,
        "saved_response_matches": True,
        "span_names": [s.name for s in trace.data.spans],
    }


def run_scenario(admin: str, output: Path, name: str, tracking_uri: str) -> dict[str, Any]:
    models = Models.from_environment()
    models.verify()
    fingerprint = application_fingerprint()
    tracking = MlflowClient(tracking_uri=tracking_uri)
    if name == "locator-correction":
        source_path = Path("data/seed/family-pilot-v1.json")
        batch_path = Path("docs/implementation/issue-11/claims.json")
        reviews_path = Path("docs/implementation/issue-11/claim-reviews.json")
        action_path = PILOT / "locator-correction.json"
        character = "phil-mitchell"
        question = "Who is Phil Mitchell's mother?"
    elif name == "parentage-correction":
        source_path = PILOT / "parentage-error-source.json"
        batch_path = PILOT / "parentage-error-claims.json"
        reviews_path = PILOT / "parentage-error-reviews.json"
        action_path = PILOT / "parentage-correction.json"
        character = "sharon-watts"
        question = "Was Den Watts Sharon's biological father?"
    else:
        source_path = PILOT / "synthetic-dispute-source.json"
        batch_path = PILOT / "synthetic-dispute-claims.json"
        reviews_path = PILOT / "synthetic-dispute-reviews.json"
        action_path = PILOT / "synthetic-dispute-action.json"
        character = "ben-mitchell"
        question = "Who is Ben Mitchell's biological father in these synthetic accounts?"
    snapshot = SourceSnapshot.model_validate_json(source_path.read_bytes())
    batch = ClaimBatch.model_validate_json(batch_path.read_bytes())
    reviews = TypeAdapter(tuple[ClaimReview, ...]).validate_json(reviews_path.read_bytes())
    action = json.loads(action_path.read_bytes())
    records: list[dict[str, Any]] = []
    receipts: list[AnswerReceipt] = []
    with database(admin) as url:
        EvidenceStore(url).load(snapshot)
        FamilyGraph(url).install(batch, reviews)
        reviewer = KnowledgeReview(
            url,
            models.embedding,
            models.settings.embedding_id,
            models.settings.embedding_dimensions,
        )
        before = reviewer.inspect(snapshot.snapshot_id)
        index = reviewer.retriever.prepare(snapshot.snapshot_id)
        publications = PublicationStore(url)
        initial = RefreshRun(
            run_id=uuid4(),
            flow_run_id=uuid4(),
            started_at=datetime.now(UTC),
            status="running",
            action="review",
            input_sha256=snapshot.fingerprint,
        )
        with publications.writer() as conn:
            publications.publish(snapshot, index, initial, conn)
        baseline = publications.active()
        request = ReviewRequest.model_validate(
            {
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_sha256": snapshot.fingerprint,
                "graphs": before.graphs.model_dump(mode="json"),
                **action,
            }
        )
        request_path = output / f"{name}-request.json"
        write(request_path, request.model_dump(mode="json"))
        write(output / f"{name}-before.json", before.model_dump(mode="json"))
        graph_request = {
            "question": question,
            "route": "graph",
            "graph": {"character_id": character, "direction": "ancestors"},
        }
        with (
            serve(url, models, tracking_uri) as address,
            httpx.Client(base_url=address, timeout=240, trust_env=False) as client,
        ):

            def ask(case: str, payload: dict[str, Any]) -> None:
                result = client.post("/v1/answers", json=payload)
                result.raise_for_status()
                receipt = AnswerReceipt.model_validate(result.json())
                records.append(capture(client, tracking, receipt, case, fingerprint))
                receipts.append(receipt)

            ask("before-review", graph_request)
            failure_record = None
            if name == "locator-correction":
                with psycopg.connect(url, autocommit=True) as conn:
                    conn.execute(
                        "ALTER TABLE family_edges ADD CONSTRAINT reject_review "
                        "CHECK (false) NOT VALID"
                    )
                    try:
                        try:
                            reviewer.apply(request)
                        except RefreshFailed as exc:
                            failed = publications.run(exc.run_id)
                            failure_record = failed.model_dump(mode="json")
                        else:
                            raise ValueError("The injected projection fault did not fail.")
                        if publications.active() != baseline:
                            raise ValueError("Failed projection changed the active publication.")
                        ask("after-failed-projection", graph_request)
                        rejected = client.post(
                            "/v1/answers", json={**graph_request, "snapshot_id": failed.snapshot_id}
                        )
                        if rejected.status_code != 503:
                            raise ValueError("An unpublished review candidate could answer.")
                        failure_record["unpublished_answer_status"] = rejected.status_code
                    finally:
                        conn.execute("ALTER TABLE family_edges DROP CONSTRAINT reject_review")
            completed = subprocess.run(
                [sys.executable, "-m", "ask_phil.cli", "review-claims", str(request_path)],
                env={**os.environ, "DATABASE_URL": url},
                text=True,
                capture_output=True,
                timeout=240,
                check=True,
            )
            publication_run = RefreshRun.model_validate_json(completed.stdout)
            current = publications.active()
            if publication_run.compatibility_id != current.compatibility_id:
                raise ValueError("The CLI review did not publish the inspected compatible version.")
            ask("reviewed-graph", graph_request)
            ask("reviewed-text", {"question": question})
            cli = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ask_phil.cli",
                    "--api-url",
                    address,
                    "ask",
                    question,
                    "--route",
                    "graph",
                    "--character",
                    character,
                    "--direction",
                    "ancestors",
                ],
                text=True,
                capture_output=True,
                timeout=60,
                check=True,
            )
            receipt = AnswerReceipt.model_validate_json(cli.stdout)
            records.append(capture(client, tracking, receipt, "reviewed-cli", fingerprint))
            receipts.append(receipt)
            inspected = client.get(f"/v1/snapshots/{current.manifest.snapshot_id}/reviews")
            inspected.raise_for_status()
            write(output / f"{name}-after.json", inspected.json())
            created = client.post("/v1/sessions")
            created.raise_for_status()
            session = created.json()
            session_path = f"/v1/sessions/{session['session']['session_id']}"
            headers = {"Authorization": f"Bearer {session['session_token']}"}
            response = client.post(session_path + "/turns", headers=headers, json=graph_request)
            response.raise_for_status()
            receipt = AnswerReceipt.model_validate(response.json())
            records.append(capture(client, tracking, receipt, "reviewed-session", fingerprint))
            receipts.append(receipt)
            reset = client.post(session_path + "/reset", headers=headers)
            reset.raise_for_status()
            refresh = SourceRefresh(
                url,
                models.embedding,
                models.settings.embedding_id,
                models.settings.embedding_dimensions,
            )
            recovered = refresh.rollback()
            if publications.active().compatibility_id != baseline.compatibility_id:
                raise ValueError(
                    "Recovery did not restore the baseline source/index/Claim/graph version."
                )
            ask("after-rollback", graph_request)
            original = EvidenceStore(url).snapshot(snapshot.snapshot_id)
            if (
                original != snapshot
                or FamilyGraph(url).audit(snapshot.snapshot_id) != before.family
            ):
                raise ValueError("The original source or audit changed.")
        with (
            serve(url, models, tracking_uri) as address,
            httpx.Client(base_url=address, timeout=30, trust_env=False) as client,
        ):
            for receipt in receipts:
                capture(client, tracking, receipt, "restart-readback", fingerprint)
        result = {
            "scenario": name,
            "application_sha256": fingerprint,
            "baseline": baseline.model_dump(mode="json"),
            "reviewed": current.model_dump(mode="json"),
            "publication_run": publication_run.model_dump(mode="json"),
            "failure": failure_record,
            "recovery": recovered.model_dump(mode="json"),
            "responses": records,
            "original_inputs_unchanged": True,
            "session_reset": True,
            "restart_readback_matches": True,
            "answer_generation_calls": 0,
            "limitation": (
                "Actual local embeddings and deterministic review explanations; no new extraction, "
                "answer-model quality, human adjudication or held-out claim."
            ),
        }
        write(output / f"{name}-runtime.json", result)
        return {
            "scenario": name,
            "public_responses": len(records),
            "application_sha256": fingerprint,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-15-mlflow.db")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    frozen = json.loads((PILOT / "pilot-inputs-v2.json").read_text())
    if any(
        hashlib.sha256(Path(path).read_bytes()).hexdigest() != digest
        for path, digest in frozen["sha256"].items()
    ):
        raise ValueError("A frozen pilot input changed before runtime execution.")
    results = [
        run_scenario(args.database_url, args.output, name, args.tracking_uri)
        for name in ("locator-correction", "synthetic-dispute", "parentage-correction")
    ]
    write(args.output / "summary.json", results)
    print(json.dumps(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
