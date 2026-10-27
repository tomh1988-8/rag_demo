"""Capture actual crime/justice API/CLI answers and exact MLflow output readback."""

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


def assess_answer(
    answer: dict[str, Any],
    snapshot: SourceSnapshot,
    reference_bytes: bytes | None,
    *,
    event_ids: tuple[str, ...],
) -> dict[str, Any]:
    if reference_bytes is None:
        raise ValueError("Event assessment requires frozen reference bytes.")
    reference = json.loads(reference_bytes)
    expected = ExtractedEvents(claims=reference["expected_claims"])
    expected = ExtractedEvents(claims=tuple(c for c in expected.claims if c.event_id in event_ids))
    score = score_events(
        json.dumps({"claims": answer.get("graph", {}).get("claims", [])}), expected, snapshot
    )
    # Source-reviewed prohibitions concern the scoped acts, not unrelated crimes.
    forbidden = (
        "Max Branning committed the act",
        "I committed the act",
        "Ben Mitchell committed the act",
        "Max murdered Lucy",
        "Phil killed Stella",
        "acquitted, so innocent",
        "never committed a crime.",
    )
    return {
        "reference_comparison": score.model_dump(mode="json"),
        "forbidden_guilt_conflations": [text for text in forbidden if text in answer["answer"]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", required=True, help="Disposable local PostgreSQL admin URL."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-13-mlflow.db")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; existing evidence must be retained.")
    directory = Path("docs/implementation/issue-13")
    snapshot_path = Path("data/seed/crime-pilot-v1.json")
    reference_path = Path("data/references/crime-justice-v2.json")
    cases = []
    for case_id, question, character, participant, event, bound in (
        (
            "conviction-is-not-guilt",
            "Did Max murder Lucy because he was convicted?",
            "max-branning",
            None,
            "lucy-murder",
            10,
        ),
        (
            "narrative-commission",
            "Who killed Lucy and who was convicted?",
            "bobby-beale",
            None,
            "lucy-murder",
            10,
        ),
        (
            "shared-participants",
            "How were Max and Bobby involved in the same case?",
            "max-branning",
            "bobby-beale",
            None,
            10,
        ),
        (
            "victim-role",
            "Who was involved in the case concerning Lucy?",
            "lucy-beale",
            None,
            "lucy-murder",
            10,
        ),
        (
            "false-confession",
            "Did Phil kill Stella because he confessed?",
            "phil-mitchell",
            None,
            "stella-death",
            10,
        ),
        (
            "false-accusation",
            "Did Max cut the brakes because he admitted guilt?",
            "max-branning",
            None,
            "carl-crash",
            10,
        ),
        (
            "empty-is-not-negative",
            "Grant has never committed a crime, right?",
            "grant-mitchell",
            None,
            None,
            10,
        ),
        (
            "performer-is-not-character",
            "What crimes did Steve McFadden commit?",
            "steve-mcfadden",
            None,
            None,
            10,
        ),
        (
            "bounded-incidents",
            "Show one captured case involving Max",
            "max-branning",
            None,
            None,
            1,
        ),
        ("context-stop", "Show every captured case involving Max", "max-branning", None, None, 10),
    ):
        required_ids = (
            ("lucy-murder",)
            if case_id
            in (
                "conviction-is-not-guilt",
                "narrative-commission",
                "shared-participants",
                "victim-role",
            )
            else ("stella-death",)
            if case_id == "false-confession"
            else ("carl-crash",)
            if case_id in ("false-accusation", "bounded-incidents")
            else ()
        )
        cases.append(
            GraphCase(
                case_id,
                question,
                EventQuery(
                    kind="crime_history",
                    character_id=character,
                    participant_id=participant,
                    event_id=event,
                    max_events=bound,
                ),
                assess=partial(assess_answer, event_ids=required_ids),
            )
        )
    cases.extend(
        (
            GraphCase(
                "cli-false-confession",
                "Was Max guilty of the crash?",
                EventQuery(
                    kind="crime_history",
                    character_id="max-branning",
                    event_id="carl-crash",
                    max_events=20,
                ),
                transport="cli",
                assess=partial(
                    assess_answer,
                    event_ids=("carl-crash",),
                ),
            ),
            GraphCase(
                "session-false-confession",
                "Did Phil kill Stella?",
                EventQuery(kind="crime_history", character_id="phil-mitchell"),
                transport="session",
                assess=partial(
                    assess_answer,
                    event_ids=("stella-death",),
                ),
            ),
        )
    )
    phases = tuple(
        GraphPhase(
            name=phase,
            kind="events",
            snapshot=snapshot_path,
            reference=reference_path,
            batch=directory / batch_file,
            reviews=directory / review_file,
            cases=tuple(cases),
            typed_query=EventQuery(
                kind="crime_history", character_id="max-branning", participant_id="bobby-beale"
            ),
        )
        for phase, batch_file, review_file in (
            ("raw-pilot", "raw-claims.json", "raw-reviews.json"),
            ("reviewed-with-raw-retained", "reviewed-claims-v2.json", "reviewed-reviews-v2.json"),
        )
    )
    payload = GraphAcceptanceRun(
        args.database_url, tracking=MlflowClient(tracking_uri=args.tracking_uri)
    ).run(
        args.output,
        phases,
        metadata={
            "limitation": (
                "Exposed source-reviewed incidents; model extraction and reviewed curation "
                "are scored separately. No held-out, human or canon acceptance. "
                "Database and hosting costs excluded."
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
