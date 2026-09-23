"""CLI client; only the explicit maintainer load command accesses PostgreSQL."""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
import psycopg

from ask_phil.evidence import SourceSnapshot
from ask_phil.storage import EvidenceStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect captured EastEnders evidence.")
    parser.add_argument(
        "--api-url", default=os.environ.get("ASK_PHIL_API_URL", "http://127.0.0.1:8000")
    )
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Retrieve matching passages through the API.")
    inspect.add_argument("query")
    inspect.add_argument("--snapshot", required=True)
    inspect.add_argument("--limit", type=int, default=10)
    load = commands.add_parser("load", help="Maintainer: load a captured fixture into PostgreSQL.")
    load.add_argument("fixture", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "load":
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                parser.error("DATABASE_URL is required for the maintainer load command.")
            snapshot = SourceSnapshot.model_validate_json(args.fixture.read_text())
            EvidenceStore(database_url).load(snapshot)
            print(json.dumps({"snapshot_id": snapshot.snapshot_id, "sha256": snapshot.fingerprint}))
        else:
            with httpx.Client(base_url=args.api_url, timeout=10, trust_env=False) as client:
                response = client.get(
                    f"/v1/snapshots/{args.snapshot}/inspect",
                    params={"query": args.query, "limit": args.limit},
                )
                response.raise_for_status()
                print(json.dumps(response.json(), indent=2, ensure_ascii=True))
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
