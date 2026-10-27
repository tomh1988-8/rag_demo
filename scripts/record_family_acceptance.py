"""Capture actual API/CLI graph outcomes from the audited raw extraction batch."""

import argparse
import json
from pathlib import Path
from typing import Any

from mlflow import MlflowClient

from ask_phil.family_graph import FamilyQuery
from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    expected = {
        ("ben-mitchell", "phil-mitchell"),
        ("ben-mitchell", "kathy-beale"),
        ("ben-mitchell", "phil-mitchell", "peggy-mitchell"),
    }
    actual = {tuple(p["characters"]) for p in records[0]["response"]["graph"]["paths"]}
    matched = len(expected & actual)
    return {
        "graph_reference_comparison": {
            "expected_paths": sorted(expected),
            "actual_paths": sorted(actual),
            "precision": matched / len(actual),
            "recall": matched / len(expected),
            "f1": 2 * matched / (len(actual) + len(expected)),
            "missing": [list(p) for p in sorted(expected - actual)],
            "explanation": (
                "Peggy edge correctly held for malformed model locator; graph completeness fails."
            ),
        }
    }


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
    cases = tuple(
        GraphCase(
            case_id,
            f"Show biological {direction} of {character}",
            FamilyQuery.model_validate(
                {
                    "character_id": character,
                    "direction": direction,
                    "max_depth": depth,
                    "max_paths": paths,
                }
            ),
        )
        for case_id, character, direction, depth, paths in (
            ("ben-ancestors", "ben-mitchell", "ancestors", 3, 20),
            ("phil-descendants", "phil-mitchell", "descendants", 3, 20),
            ("held-peggy", "peggy-mitchell", "descendants", 3, 20),
            ("adopted-sharon", "sharon-watts", "ancestors", 3, 20),
            ("adoptive-den", "den-watts", "descendants", 3, 20),
            ("uncovered-grant", "grant-mitchell", "ancestors", 3, 20),
            ("performer-id", "steve-mcfadden", "ancestors", 3, 20),
            ("path-limit", "ben-mitchell", "ancestors", 3, 1),
        )
    )
    phase = GraphPhase(
        name="raw-pilot",
        kind="family",
        snapshot=Path("data/seed/family-pilot-v1.json"),
        batch=Path("docs/implementation/issue-11/claims.json"),
        reviews=Path("docs/implementation/issue-11/claim-reviews.json"),
        cases=(
            *cases,
            GraphCase(
                "cli-descendants",
                "Show biological descendants of Phil Mitchell",
                FamilyQuery(character_id="phil-mitchell", direction="descendants"),
                transport="cli",
            ),
        ),
        typed_query=FamilyQuery(character_id="ben-mitchell", direction="ancestors"),
    )
    record = GraphAcceptanceRun(
        args.database_url, tracking=MlflowClient(tracking_uri=args.tracking_uri)
    ).run(
        args.output,
        (phase,),
        summarize=summarize,
        metadata={
            "limitation": (
                "Actual raw-pilot projection has two admitted edges, not complete family coverage. "
                "Full-reference integration tests separately verify multi-hop semantics."
            ),
        },
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "public_responses": len(record["responses"]),
                "graph_scores": record["graph_reference_comparison"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
