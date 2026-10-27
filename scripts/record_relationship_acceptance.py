"""Record actual public answers from raw-pilot and explicitly curated projections."""

import argparse
import json
from functools import partial
from pathlib import Path
from typing import Any

from mlflow import MlflowClient

from ask_phil.evidence import SourceSnapshot
from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase
from ask_phil.relationship_evaluation import score_relationships
from ask_phil.relationship_graph import RelationshipQuery
from ask_phil.relationships import ExtractedRelationships


def assess_answer(
    answer: dict[str, Any],
    snapshot: SourceSnapshot,
    reference_bytes: bytes | None,
    *,
    character: str,
    partner: str | None,
) -> dict[str, Any]:
    if reference_bytes is None:
        raise ValueError("Relationship assessment requires frozen reference bytes.")
    reference = json.loads(reference_bytes)
    expected = ExtractedRelationships(claims=reference["expected_claims"])
    required = ExtractedRelationships(
        claims=tuple(
            c
            for c in expected.claims
            if character in (c.subject_id, c.object_id)
            and (partner is None or partner in (c.subject_id, c.object_id))
        )
    )
    score = score_relationships(
        json.dumps({"claims": answer.get("graph", {}).get("claims", [])}),
        required,
        snapshot,
        reference.get("alternatives"),
    )
    return {"reference_comparison": score.model_dump(mode="json")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", required=True, help="Disposable PostgreSQL admin connection."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-12-mlflow.db")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; evidence records are immutable.")
    directory = Path("docs/implementation/issue-12")
    snapshot_path = Path("data/seed/relationship-pilot-v1.json")
    reference_path = Path("data/references/relationships-v2.json")
    cases = []
    for case_id, character, partner, bound in (
        ("repeated-marriages", "kat-slater", "alfie-moon", 20),
        ("separation-is-not-divorce", "phil-mitchell", "kathy-beale", 20),
        ("affair", "phil-mitchell", "sharon-watts", 20),
        ("divorce", "grant-mitchell", "sharon-watts", 20),
        ("adoptive-parent", "sharon-watts", "den-watts", 20),
        ("adoptive-direction", "den-watts", "sharon-watts", 20),
        ("step-parent", "denise-fox", "amy-mitchell", 20),
        ("step-direction", "amy-mitchell", "denise-fox", 20),
        ("biological-parent", "ben-mitchell", "phil-mitchell", 20),
        ("both-biological-parents", "ben-mitchell", None, 20),
        ("empty-is-not-negative", "kat-slater", "den-watts", 20),
        ("performer-is-not-character", "shane-richie", None, 20),
        ("bounded", "phil-mitchell", "kathy-beale", 1),
    ):
        cases.append(
            GraphCase(
                case_id,
                f"Explain the history of {character} and {partner}",
                RelationshipQuery(
                    kind="relationship_history",
                    character_id=character,
                    partner_id=partner,
                    max_events=bound,
                ),
                assess=partial(
                    assess_answer,
                    character=character,
                    partner=partner,
                ),
            )
        )
    cases.append(
        GraphCase(
            "cli-marriages",
            "Explain Kat and Alfie's marriages",
            RelationshipQuery(
                kind="relationship_history", character_id="kat-slater", partner_id="alfie-moon"
            ),
            transport="cli",
        )
    )
    phases = tuple(
        GraphPhase(
            name=phase,
            kind="relationships",
            snapshot=snapshot_path,
            reference=reference_path,
            batch=directory / batch_file,
            reviews=directory / review_file,
            cases=tuple(cases),
            typed_query=RelationshipQuery(kind="relationship_history", character_id="kat-slater"),
        )
        for phase, batch_file, review_file in (
            ("raw-pilot", "raw-claims.json", "raw-claim-reviews.json"),
            (
                "reviewed-with-raw-retained",
                "reviewed-claims-v2.json",
                "reviewed-claim-reviews-v2.json",
            ),
        )
    )
    payload = GraphAcceptanceRun(
        args.database_url, tracking=MlflowClient(tracking_uri=args.tracking_uri)
    ).run(
        args.output,
        phases,
        metadata={
            "limitation": (
                "Raw model failures are retained. The second projection admits pre-pilot "
                "agent-reviewed claims and retains all raw candidates/holds. It demonstrates "
                "curated capability, not successful automatic extraction or held-out/canon "
                "acceptance. Hosting/database costs excluded."
            ),
        },
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "responses": len(payload["responses"]),
                "traces_match": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
