"""Capture composed connections and all four graph contracts with actual trace readback."""

import argparse
import json
from functools import partial
from pathlib import Path
from typing import Any, Literal

from mlflow import MlflowClient

from ask_phil.claims import ClaimEvidence, evidence_resolves
from ask_phil.connection_evaluation import ConnectionReference, score_connection
from ask_phil.connection_graph import ConnectionResult
from ask_phil.event_graph import EventQuery
from ask_phil.evidence import SourceSnapshot
from ask_phil.family_graph import FamilyQuery
from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase
from ask_phil.relationship_graph import RelationshipQuery


def assess_connection(
    answer: dict[str, Any],
    snapshot: SourceSnapshot,
    reference_bytes: bytes | None,
    *,
    case_id: str,
) -> dict[str, Any]:
    if reference_bytes is None:
        raise ValueError("Connection evaluation requires the frozen reviewed reference.")
    reference = ConnectionReference.model_validate_json(reference_bytes)
    case = next(c for c in reference.cases if c.case_id == case_id)
    scores = score_connection(
        ConnectionResult.model_validate(answer["graph"]), case, reference, snapshot
    )
    return {
        "component_scores": scores.model_dump(mode="json"),
        "reference_case_id": case_id,
        "forbidden_answer_text_absent": all(t not in answer["answer"] for t in case.forbidden_text),
        "final_answer_support": "Pending independent source review; component scores are separate.",
    }


def assess_existing_family(
    answer: dict[str, Any],
    snapshot: SourceSnapshot,
    reference_bytes: bytes | None,
    *,
    kind: str,
) -> dict[str, Any]:
    if reference_bytes is None:
        raise ValueError("The family checks require the frozen reviewed reference.")
    reference = ConnectionReference.model_validate_json(reference_bytes)
    graph = answer["graph"]
    if kind == "family":
        correct = {tuple(p["characters"]) for p in graph["paths"]} == {
            ("ben-mitchell", "phil-mitchell"),
            ("ben-mitchell", "kathy-beale"),
            ("ben-mitchell", "phil-mitchell", "peggy-mitchell"),
        }
        expected = {c.claim_id: c for c in reference.family_claims}
        edges = [e for p in graph["paths"] for e in p["edges"]]
        meaning = all(
            cid in expected
            and expected[cid].relation == "biological_parent"
            and (expected[cid].parent_id, expected[cid].child_id) == (e["parent_id"], e["child_id"])
            for e in edges
            for cid in e["claim_ids"]
        )
        spans = [s for e in edges for s in e["evidence"]]
    else:
        claims = (
            [c for c in reference.relationship_claims if c.claim_id == "den-sharon-adoption"]
            if kind == "relationship"
            else [c for c in reference.event_claims if c.event_id == "lucy-murder"]
        )
        correct = {c["claim_id"] for c in graph["claims"]} == {c.claim_id for c in claims}
        expected_documents = {c.claim_id: c.model_dump(mode="json") for c in claims}
        meaning = all(expected_documents.get(c["claim_id"]) == c for c in graph["claims"])
        spans = [s for c in graph["claims"] for s in c["evidence"]]
    return {
        "component_scores": {
            "result_correct": correct,
            "step_meanings_correct": meaning,
            "provenance_resolves": evidence_resolves(
                tuple(ClaimEvidence.model_validate(s) for s in spans),
                {p.evidence_id: p for p in snapshot.passages},
            ),
        },
        "final_answer_support": "Pending independent source review; component scores are separate.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True, help="Disposable PostgreSQL admin URL.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-16-mlflow.db")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; prior evidence must be retained.")
    reference_path = Path("data/references/connections-v1.json")
    reference = ConnectionReference.model_validate_json(reference_path.read_bytes())
    names = {c.character_id: c.name for c in reference.catalogue.characters}
    by_id = {c.case_id: c for c in reference.cases}
    cases = [
        GraphCase(
            case.case_id,
            f"How are {names.get(case.character_id, case.character_id)} and "
            f"{names.get(case.target_id, case.target_id)} connected?",
            case.query,
            assess=partial(assess_connection, case_id=case.case_id),
        )
        for case in reference.cases
    ]
    variations: tuple[tuple[str, str, Literal["cli", "session"]], ...] = (
        ("grandparent-cli", "biological-grandchild", "cli"),
        ("roles-cli", "misleading-conviction", "cli"),
        ("composed-session", "composed-family-event", "session"),
        ("no-path-session", "no-path", "session"),
    )
    for identifier, original, transport in variations:
        cases.append(
            GraphCase(
                identifier,
                "Explain this evidenced character connection.",
                by_id[original].query,
                transport=transport,
                assess=partial(assess_connection, case_id=original),
            )
        )
    cases.extend(
        (
            GraphCase(
                "family-contract",
                "Who are Ben's biological ancestors?",
                FamilyQuery(character_id="ben-mitchell", direction="ancestors"),
                assess=partial(assess_existing_family, kind="family"),
            ),
            GraphCase(
                "relationship-contract",
                "How are Den and Sharon related?",
                RelationshipQuery(
                    kind="relationship_history", character_id="sharon-watts", partner_id="den-watts"
                ),
                assess=partial(assess_existing_family, kind="relationship"),
            ),
            GraphCase(
                "event-contract",
                "What are Max and Bobby's different roles?",
                EventQuery(
                    kind="crime_history", character_id="max-branning", participant_id="bobby-beale"
                ),
                assess=partial(assess_existing_family, kind="event"),
            ),
        )
    )
    phase = GraphPhase(
        name="connections",
        kind="connections",
        snapshot=Path("data/seed/connections-pilot-v1.json"),
        batch=reference_path,
        reviews=Path("docs/implementation/issue-16/claim-reviews.json"),
        cases=tuple(cases),
        reference=reference_path,
    )
    tracking = MlflowClient(tracking_uri=args.tracking_uri)
    document = GraphAcceptanceRun(args.database_url, tracking=tracking).run(
        args.output,
        (phase,),
        metadata={
            "purpose": (
                "Reviewed composition capability; "
                "extraction and held-out model quality are separate."
            ),
            "graph_families": [
                "biological",
                "relationship_history",
                "shared_events",
                "connections",
            ],
            "reference_review": reference.review_note,
        },
        summarize=lambda rows: {
            "component_summary": {
                dimension: {
                    "passed": sum(r["component_scores"][dimension] for r in rows),
                    "cases": len(rows),
                }
                for dimension in ("result_correct", "step_meanings_correct", "provenance_resolves")
            }
        },
    )
    print(
        json.dumps(
            {
                "state": document["state"],
                "responses": len(document["responses"]),
                "component_summary": document["component_summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
