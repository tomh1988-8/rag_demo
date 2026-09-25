"""CLI client and explicit maintainer capture, import and indexing operations."""

import argparse
import getpass
import gzip
import json
import os
import sys
from pathlib import Path

import httpx
import psycopg

from ask_phil.evidence import SourceSnapshot
from ask_phil.ingestion import build_snapshot, capture_sources, read_batch
from ask_phil.openrouter import KEY_PATH, ProviderError, save_key
from ask_phil.source_records import CapturePlan, SourceBatch
from ask_phil.storage import EvidenceStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect captured EastEnders evidence.")
    parser.add_argument(
        "--api-url", default=os.environ.get("ASK_PHIL_API_URL", "http://127.0.0.1:8000")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "configure-openrouter", help="Privately save a provider-verified, capped OpenRouter key."
    )
    inspect = commands.add_parser("inspect", help="Retrieve matching passages through the API.")
    inspect.add_argument("query")
    inspect.add_argument("--snapshot", required=True)
    inspect.add_argument("--limit", type=int, default=10)
    load = commands.add_parser("load", help="Maintainer: load a captured fixture into PostgreSQL.")
    load.add_argument("fixture", type=Path)
    capture = commands.add_parser(
        "capture-sources", help="Maintainer: capture official public HTML/JSON sources."
    )
    capture.add_argument("plan", type=Path)
    capture.add_argument("output", type=Path)
    ingest = commands.add_parser(
        "import-sources", help="Maintainer: import a reviewed captured source batch."
    )
    ingest.add_argument("batch", type=Path)
    ingest.add_argument("--snapshot", required=True)
    report = commands.add_parser(
        "source-report", help="Inspect import coverage, exclusions and missing records."
    )
    report.add_argument("--snapshot", required=True)
    source = commands.add_parser(
        "source", help="Inspect a retained source, ordered spans and metadata."
    )
    source.add_argument("source_id")
    source.add_argument("--snapshot", required=True)
    identity = commands.add_parser(
        "resolve-character", help="Resolve a reviewed character name or alias."
    )
    identity.add_argument("name")
    identity.add_argument("--snapshot", required=True)
    ask = commands.add_parser("ask", help="Ask a question using the captured snapshot.")
    ask.add_argument("query")
    ask.add_argument("--snapshot", required=True)
    response = commands.add_parser(
        "response", help="Read the original answer using a saved receipt."
    )
    response.add_argument("receipt", type=Path)
    index = commands.add_parser(
        "index", help="Maintainer: embed a snapshot using configured models."
    )
    index.add_argument("--snapshot", required=True)
    args = parser.parse_args()
    try:
        if args.command == "configure-openrouter":
            if not sys.stdin.isatty():
                raise ProviderError("Run this command in an interactive terminal for hidden input.")
            key = getpass.getpass("OpenRouter key (hidden): ")
            with httpx.Client(timeout=20, trust_env=False, follow_redirects=False) as client:
                save_key(key, KEY_PATH, client)
            print("Key saved privately; provider lifetime credit limit verified at $5 or less.")
        elif args.command == "capture-sources":
            if args.output.exists():
                raise ValueError("Capture output already exists; choose a new path.")
            plan = CapturePlan.model_validate_json(args.plan.read_bytes())
            with httpx.Client(trust_env=False) as client:
                batch = SourceBatch(
                    format_version=1,
                    catalogue=plan.catalogue,
                    policies=plan.policies,
                    captures=capture_sources(plan.requests, client),
                )
            data = batch.model_dump_json().encode()
            with args.output.open("xb") as output:
                output.write(gzip.compress(data, mtime=0) if args.output.suffix == ".gz" else data)
            print(json.dumps({"output": str(args.output), "captured_sources": len(batch.captures)}))
        elif args.command in {"load", "index", "import-sources"}:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                parser.error("DATABASE_URL is required for the maintainer storage command.")
            if args.command in {"load", "import-sources"}:
                snapshot = (
                    build_snapshot(read_batch(args.batch), args.snapshot)
                    if args.command == "import-sources"
                    else SourceSnapshot.model_validate_json(args.fixture.read_text())
                )
                EvidenceStore(database_url).load(snapshot)
                print(
                    json.dumps(
                        {"snapshot_id": snapshot.snapshot_id, "sha256": snapshot.fingerprint}
                    )
                )
            else:
                from ask_phil.answering import AnswerService
                from ask_phil.models import Models

                Path("artifacts").mkdir(exist_ok=True)
                service = AnswerService(
                    database_url,
                    Models.from_environment(),
                    os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db"),
                )
                trace_id = service.prepare(args.snapshot)
                print(json.dumps({"snapshot_id": args.snapshot, "trace_id": trace_id}))
        else:
            timeout = 400 if args.command == "ask" else 10
            with httpx.Client(base_url=args.api_url, timeout=timeout, trust_env=False) as client:
                if args.command == "ask":
                    result = client.post(
                        "/v1/answers",
                        json={
                            "question": args.query,
                            "snapshot_id": args.snapshot,
                        },
                    )
                elif args.command == "response":
                    from ask_phil.answers import AnswerReceipt

                    receipt = AnswerReceipt.model_validate_json(args.receipt.read_text())
                    result = client.get(
                        f"/v1/responses/{receipt.response.response_id}",
                        headers={"Authorization": f"Bearer {receipt.read_token}"},
                    )
                elif args.command == "source-report":
                    result = client.get(f"/v1/snapshots/{args.snapshot}/sources")
                elif args.command == "source":
                    result = client.get(f"/v1/snapshots/{args.snapshot}/sources/{args.source_id}")
                elif args.command == "resolve-character":
                    result = client.get(
                        f"/v1/snapshots/{args.snapshot}/identities", params={"name": args.name}
                    )
                else:
                    result = client.get(
                        f"/v1/snapshots/{args.snapshot}/inspect",
                        params={"query": args.query, "limit": args.limit},
                    )
                result.raise_for_status()
                print(json.dumps(result.json(), indent=2, ensure_ascii=True))
    except httpx.HTTPStatusError as exc:
        print(f"API returned HTTP {exc.response.status_code}.", file=sys.stderr)
        return 1
    except httpx.HTTPError:
        print("Could not reach the evidence API.", file=sys.stderr)
        return 1
    except psycopg.Error:
        print("Evidence storage is unavailable.", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"Invalid fixture or configuration: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
