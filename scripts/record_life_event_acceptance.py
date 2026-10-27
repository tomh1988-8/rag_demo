"""Record actual life-event API/CLI/session outcomes with exact trace readback."""

import argparse
import json
from functools import partial
from pathlib import Path
from typing import Any

from mlflow import MlflowClient

from ask_phil.event_evaluation import score_events
from ask_phil.event_graph import EventQuery
from ask_phil.evidence import SourceSnapshot
from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase
from ask_phil.story_events import ExtractedEvents


def assess(
    answer: dict[str, Any],
    snapshot: SourceSnapshot,
    reference_bytes: bytes | None,
    *,
    event_ids: tuple[str, ...],
) -> dict[str, Any]:
    if reference_bytes is None:
        raise ValueError("Life-event assessment requires the frozen reference.")
    reference = ExtractedEvents(claims=json.loads(reference_bytes)["expected_claims"])
    expected = ExtractedEvents(claims=tuple(c for c in reference.claims if c.event_id in event_ids))
    return {
        "reference_comparison": score_events(
            json.dumps({"claims": answer.get("graph", {}).get("claims", [])}), expected, snapshot
        ).model_dump(mode="json")
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", required=True, help="Disposable local PostgreSQL admin URL."
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-14-mlflow.db")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; prior evidence must be retained.")
    cases = []
    for case_id, character, participant, event, question, expected in (
        (
            "peggy-pregnancy",
            "peggy-mitchell",
            None,
            "peggy-pregnancy",
            "When was Peggy pregnant?",
            ("peggy-pregnancy",),
        ),
        (
            "exact-story-time",
            "sharon-watts",
            None,
            "sharon-christmas-pregnancy",
            "When did Sharon discover this pregnancy?",
            ("sharon-christmas-pregnancy",),
        ),
        (
            "uncertain-paternity",
            "sharon-watts",
            None,
            "sharon-uncertain-paternity",
            "Does Sharon's pregnancy prove Phil was the father?",
            ("sharon-uncertain-paternity",),
        ),
        (
            "funeral-is-not-death-date",
            "peggy-mitchell",
            None,
            "peggy-death",
            "Did Peggy die on 4 July 2016?",
            ("peggy-death",),
        ),
        ("lucy-death", "lucy-beale", None, "lucy-death", "When did Lucy die?", ("lucy-death",)),
        (
            "hallucination-not-witness",
            "peggy-mitchell",
            "pat-butcher",
            "peggy-death",
            "Was Pat physically present at Peggy's death?",
            (),
        ),
        (
            "pregnancy-not-parentage",
            "peggy-mitchell",
            "phil-mitchell",
            "peggy-pregnancy",
            "Does this pregnancy tool supply a family connection?",
            (),
        ),
        (
            "unclassified-not-edge",
            "grant-mitchell",
            "sharon-watts",
            None,
            "Does the tape revelation create a life-event edge?",
            (),
        ),
        (
            "coappearance-not-presence",
            "ian-beale",
            "lucy-beale",
            "lucy-death",
            "Was Ian present at Lucy's death?",
            (),
        ),
        (
            "unknown-character",
            "steve-mcfadden",
            None,
            None,
            "What life events involved Steve McFadden?",
            (),
        ),
    ):
        cases.append(
            GraphCase(
                case_id,
                question,
                EventQuery(
                    kind="life_events",
                    character_id=character,
                    participant_id=participant,
                    event_id=event,
                ),
                assess=partial(assess, event_ids=expected),
            )
        )
    for kind, question in (
        ("theme", "Does a shared domestic-abuse or manosphere theme create a connection?"),
        ("unclassified", "What graph category covers the tape revelation?"),
    ):
        cases.append(
            GraphCase(
                kind,
                question,
                EventQuery.model_validate(
                    {
                        "kind": kind,
                        "character_id": "grant-mitchell",
                        "participant_id": "sharon-watts",
                    }
                ),
                assess=partial(assess, event_ids=()),
            )
        )
    cases.extend(
        (
            GraphCase(
                "bounded",
                "Show one reviewed event involving Peggy",
                EventQuery(
                    kind="life_events",
                    character_id="peggy-mitchell",
                    max_events=1,
                ),
                assess=partial(assess, event_ids=("peggy-death",)),
            ),
            GraphCase(
                "cli-pregnancy",
                "What supports Sharon's pregnancy and date?",
                EventQuery(
                    kind="life_events",
                    character_id="sharon-watts",
                    event_id="sharon-christmas-pregnancy",
                ),
                transport="cli",
                assess=partial(assess, event_ids=("sharon-christmas-pregnancy",)),
            ),
            GraphCase(
                "session-death",
                "What supports Peggy's death and date?",
                EventQuery(
                    kind="life_events",
                    character_id="peggy-mitchell",
                    event_id="peggy-death",
                ),
                transport="session",
                assess=partial(assess, event_ids=("peggy-death",)),
            ),
        )
    )
    directory = Path("docs/implementation/issue-14")
    phases = tuple(
        GraphPhase(
            name=name,
            kind="events",
            snapshot=Path("data/seed/life-events-pilot-v1.json"),
            reference=Path("data/references/life-events-v1.json"),
            batch=directory / f"{prefix}-claims.json",
            reviews=directory / f"{prefix}-reviews.json",
            cases=tuple(cases),
        )
        for name, prefix in (("raw-pilot", "raw"), ("reviewed-with-raw-retained", "reviewed"))
    )
    result = GraphAcceptanceRun(
        args.database_url, tracking=MlflowClient(tracking_uri=args.tracking_uri)
    ).run(
        args.output,
        phases,
        metadata={
            "limitation": "Exposed source-reviewed life events. Raw extraction quality remains "
            "separate from curated capability; no held-out, human or independent canon acceptance.",
        },
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "responses": len(result["responses"]),
                "state": result["state"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
