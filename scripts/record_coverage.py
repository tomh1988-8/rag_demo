"""Exercise reviewed roster questions against one full source and all three claim projections."""

import argparse
import json
from functools import partial
from pathlib import Path
from typing import Any

from mlflow import MlflowClient
from pydantic import TypeAdapter

from ask_phil.claims import ClaimEvidence, evidence_resolves
from ask_phil.connection_graph import ConnectionQuery
from ask_phil.evidence import SourceSnapshot
from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase, GraphQuery


def assess(
    answer: dict[str, Any], snapshot: SourceSnapshot, reference: bytes | None, *, case_id: str
) -> dict[str, Any]:
    if reference is None:
        raise ValueError("Coverage acceptance needs independently reviewed questions.")
    dataset = json.loads(reference)
    case = next(row for row in dataset["cases"] if row["case_id"] == case_id)
    expected = dataset["expected_claims"]
    result = answer.get("graph", {})
    paths = {tuple(path["characters"]) for path in result.get("paths", [])}
    claims = {claim["claim_id"] for claim in result.get("claims", [])}
    spans = [
        ClaimEvidence.model_validate(span)
        for claim in result.get("claims", [])
        for span in claim["evidence"]
    ] + [
        ClaimEvidence.model_validate(span)
        for path in result.get("paths", [])
        for edge in path["edges"]
        for span in edge["evidence"]
    ]
    values_correct = all(
        expected.get(claim["claim_id"]) == claim for claim in result.get("claims", [])
    )
    for path in result.get("paths", []):
        values_correct &= len(path["edges"]) == len(path["characters"]) - 1
        for index, edge in enumerate(path["edges"]):
            pair = (edge["parent_id"], edge["child_id"])
            values_correct &= set(pair) == set(path["characters"][index : index + 2])
            supporting = {
                cid: claim
                for cid, claim in expected.items()
                if (claim.get("parent_id"), claim.get("child_id")) == pair
                and claim.get("relation") == "biological_parent"
                and claim["polarity"] == "affirmed"
                and claim["certainty"] == "certain"
            }
            values_correct &= bool(supporting) and set(edge["claim_ids"]) == set(supporting)
            values_correct &= edge["evidence"] == [
                span for cid in sorted(supporting) for span in supporting[cid]["evidence"]
            ]
    return {
        "component_scores": {
            "result_correct": result.get("status") == case["expected_status"]
            and paths == {tuple(p) for p in case.get("expected_paths", [])}
            and claims == set(case.get("expected_claims", [])),
            "values_correct": values_correct,
            "locators_resolve": evidence_resolves(
                tuple(spans), {p.evidence_id: p for p in snapshot.passages}
            ),
        },
        "source_review": "Final prose support and values require separate recorded review.",
        "forbidden_text_absent": all(
            text not in answer["answer"] for text in case["forbidden_text"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-20-mlflow.db")
    args = parser.parse_args()
    reference = json.loads(args.cases.read_bytes())
    cases = tuple(
        GraphCase(
            row["case_id"],
            row["question"],
            TypeAdapter(GraphQuery).validate_python(row["query"]),
            transport=row["transport"],
            assess=partial(assess, case_id=row["case_id"]),
        )
        for row in reference["cases"]
    )
    run = GraphAcceptanceRun(
        args.database_url, tracking=MlflowClient(tracking_uri=args.tracking_uri)
    )
    result = run.run(
        args.output,
        (
            GraphPhase(
                "core-roster",
                "connections",
                args.snapshot,
                args.claims,
                args.reviews,
                cases,
                typed_query=ConnectionQuery(
                    kind="connection", character_id="peggy-mitchell", target_id="phil-mitchell"
                ),
                reference=args.cases,
            ),
        ),
    )
    checks = [r["component_scores"] for r in result["responses"]]
    passed = all(all(row.values()) for row in checks)
    print(json.dumps({"responses": len(checks), "component_checks_pass": passed}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
