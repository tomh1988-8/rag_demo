"""Capture actual public HTTP outputs; this is not a generative-quality evaluator."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    reference_path = Path("data/references/phil-arrival-v1.json")
    reference = json.loads(reference_path.read_text())
    cases = []
    with httpx.Client(base_url=args.api_url, timeout=10, trust_env=False) as client:
        for case in reference["cases"]:
            response = client.get(
                f"/v1/snapshots/{reference['snapshot_id']}/inspect",
                params={"query": case["question"]},
            )
            response.raise_for_status()
            cases.append(
                {
                    "case_id": case["case_id"],
                    "expected_evidence_ids": case["expected_evidence_ids"],
                    "actual_response": response.json(),
                }
            )
    files = [
        *Path("src").rglob("*.py"),
        Path("pyproject.toml"),
        Path("uv.lock"),
        Path("data/seed/phil-arrival-v1.json"),
        reference_path,
        Path("scripts/record_baseline.py"),
    ]
    artifact = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "kind": "deterministic_passage_inspection",
        "limitations": "Two development cases; no generative quality or canon verification.",
        "python": platform.python_version(),
        "packages": {p: importlib.metadata.version(p) for p in ["fastapi", "psycopg", "httpx"]},
        "files_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)},
        "model_calls": 0,
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"Saved {len(cases)} actual responses to {args.output}")


if __name__ == "__main__":
    main()
