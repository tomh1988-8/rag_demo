"""Capture actual API/CLI graph outcomes from the audited raw extraction batch."""

import argparse
import json
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
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
from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.family_graph import FamilyGraph
from ask_phil.parentage import ClaimBatch, ClaimReview
from ask_phil.storage import EvidenceStore


@contextmanager
def serve(database_url: str, tracking_uri: str) -> Iterator[str]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(
            uvicorn.Config(create_app(database_url, tracking_uri=tracking_uri), log_level="error")
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            if not server.started:
                raise RuntimeError("Acceptance HTTP server did not start.")
            yield f"http://127.0.0.1:{listener.getsockname()[1]}"
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("Acceptance HTTP server did not stop.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", required=True, help="Disposable local PostgreSQL admin URL."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-11-mlflow.db")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; acceptance records are immutable.")
    batch = ClaimBatch.model_validate_json(
        Path("docs/implementation/issue-11/claims.json").read_bytes()
    )
    reviews = TypeAdapter(tuple[ClaimReview, ...]).validate_json(
        Path("docs/implementation/issue-11/claim-reviews.json").read_bytes()
    )
    name = "ask_phil_family_acceptance_" + uuid4().hex
    records: list[dict[str, Any]] = []
    trace_checks: list[dict[str, Any]] = []
    with psycopg.connect(args.database_url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        database_url = make_conninfo(args.database_url, dbname=name)
        try:
            snapshot = SourceSnapshot.model_validate_json(
                Path("data/seed/family-pilot-v1.json").read_bytes()
            )
            EvidenceStore(database_url).load(snapshot)
            audit = FamilyGraph(database_url).install(batch, reviews)
            cases = [
                ("ben-ancestors", "ben-mitchell", "ancestors", 3, 20),
                ("phil-descendants", "phil-mitchell", "descendants", 3, 20),
                ("held-peggy", "peggy-mitchell", "descendants", 3, 20),
                ("adopted-sharon", "sharon-watts", "ancestors", 3, 20),
                ("adoptive-den", "den-watts", "descendants", 3, 20),
                ("uncovered-grant", "grant-mitchell", "ancestors", 3, 20),
                ("performer-id", "steve-mcfadden", "ancestors", 3, 20),
                ("path-limit", "ben-mitchell", "ancestors", 3, 1),
            ]
            with (
                serve(database_url, args.tracking_uri) as url,
                httpx.Client(base_url=url, trust_env=False, timeout=30) as client,
            ):
                for case_id, character, direction, depth, paths in cases:
                    request = {
                        "snapshot_id": snapshot.snapshot_id,
                        "route": "graph",
                        "question": f"Show biological {direction} of {character}",
                        "graph": {
                            "character_id": character,
                            "direction": direction,
                            "max_depth": depth,
                            "max_paths": paths,
                        },
                    }
                    started = time.perf_counter()
                    response = client.post("/v1/answers", json=request)
                    response.raise_for_status()
                    receipt = response.json()
                    answer = receipt["response"]
                    resolved = []
                    for citation in answer["citations"]:
                        evidence = client.get(citation["resolve_path"])
                        evidence.raise_for_status()
                        resolved.append(
                            evidence.json()["matches"][0]["sha256"] == citation["sha256"]
                        )
                    records.append(
                        {
                            "case_id": case_id,
                            "transport": "api",
                            "response": answer,
                            "http_elapsed_ms": (time.perf_counter() - started) * 1000,
                            "all_citations_resolve": all(resolved),
                        }
                    )
                original = receipt
                cli = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "ask_phil.cli",
                        "--api-url",
                        url,
                        "ask",
                        "Show biological descendants of Phil Mitchell",
                        "--route",
                        "graph",
                        "--character",
                        "phil-mitchell",
                        "--direction",
                        "descendants",
                        "--snapshot",
                        snapshot.snapshot_id,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
                cli_receipt = json.loads(cli.stdout)
                records.append(
                    {
                        "case_id": "cli-descendants",
                        "transport": "cli",
                        "response": cli_receipt["response"],
                    }
                )
                typed = client.post(
                    f"/v1/snapshots/{snapshot.snapshot_id}/family",
                    json={"character_id": "ben-mitchell", "direction": "ancestors"},
                )
                typed.raise_for_status()
                invalid = client.post(
                    "/v1/answers", json={"route": "graph", "question": "Invalid pairing"}
                )
                assert invalid.status_code == 422
                trace_client = MlflowClient(tracking_uri=args.tracking_uri)
                for record in records:
                    answer = record["response"]
                    trace = trace_client.get_trace(answer["trace_id"], flush=True)
                    assert trace is not None
                    span_names = [s.name for s in trace.data.spans]
                    assert "graph" in span_names and "family_graph" in span_names
                    assert answer["execution"]["model_calls"] == 0
                    trace_checks.append(
                        {
                            "trace_id": answer["trace_id"],
                            "span_names": span_names,
                            "zero_inference": True,
                        }
                    )
            with (
                serve(database_url, args.tracking_uri) as url,
                httpx.Client(base_url=url, trust_env=False) as client,
            ):
                saved = client.get(
                    f"/v1/responses/{original['response']['response_id']}",
                    headers={"Authorization": f"Bearer {original['read_token']}"},
                )
                saved.raise_for_status()
                assert saved.json() == original["response"]
                restarted = True
            expected = {
                ("ben-mitchell", "phil-mitchell"),
                ("ben-mitchell", "kathy-beale"),
                ("ben-mitchell", "phil-mitchell", "peggy-mitchell"),
            }
            actual = {tuple(p["characters"]) for p in records[0]["response"]["graph"]["paths"]}
            matched = len(expected & actual)
            record = {
                "application_sha256": application_fingerprint(),
                "snapshot_sha256": snapshot.fingerprint,
                "graph_sha256": audit.graph_sha256,
                "admission": audit.admission.model_dump(mode="json"),
                "responses": records,
                "typed_tool": typed.json(),
                "invalid_pairing_http": invalid.status_code,
                "original_response_survives_restart": restarted,
                "traces": trace_checks,
                "graph_reference_comparison": {
                    "expected_paths": sorted(expected),
                    "actual_paths": sorted(actual),
                    "precision": matched / len(actual),
                    "recall": matched / len(expected),
                    "f1": 2 * matched / (len(actual) + len(expected)),
                    "missing": [list(p) for p in sorted(expected - actual)],
                    "explanation": (
                        "Peggy edge correctly held for malformed model locator; "
                        "graph completeness fails."
                    ),
                },
                "paid_serving_calls": 0,
                "serving_inference_usd": 0,
                "limitation": (
                    "Actual raw-pilot projection has two admitted edges, "
                    "not complete family coverage. "
                    "Full-reference integration tests separately verify multi-hop semantics."
                ),
            }
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        json.dump(record, output, indent=2, ensure_ascii=False)
        output.write("\n")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "public_responses": len(records),
                "graph_scores": record["graph_reference_comparison"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
