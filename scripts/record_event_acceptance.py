"""Capture actual crime/justice API/CLI answers and exact MLflow output readback."""

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psycopg
from mlflow import MlflowClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter
from record_family_acceptance import serve

from ask_phil.answering import application_fingerprint
from ask_phil.event_evaluation import score_events
from ask_phil.event_graph import EventGraph, EventQuery
from ask_phil.evidence import SourceSnapshot
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventReview, ExtractedEvents


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
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/crime-pilot-v1.json").read_bytes()
    )
    reference = json.loads(Path("data/references/crime-justice-v2.json").read_bytes())
    expected = ExtractedEvents(claims=reference["expected_claims"])
    cases = [
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
    ]
    responses: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    audits: dict[str, Any] = {}
    with psycopg.connect(args.database_url, autocommit=True) as admin:
        for phase, batch_file, review_file in (
            ("raw-pilot", "raw-claims.json", "raw-reviews.json"),
            ("reviewed-with-raw-retained", "reviewed-claims-v2.json", "reviewed-reviews-v2.json"),
        ):
            name = "ask_phil_crime_acceptance_" + uuid4().hex
            admin.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
            )
            database_url = make_conninfo(args.database_url, dbname=name)
            try:
                batch = EventBatch.model_validate_json((directory / batch_file).read_bytes())
                reviews = TypeAdapter(tuple[EventReview, ...]).validate_json(
                    (directory / review_file).read_bytes()
                )
                EvidenceStore(database_url).load(snapshot)
                audit = EventGraph(database_url).install(batch, reviews)
                audits[phase] = audit.admission.model_dump(mode="json")
                with (
                    serve(database_url, args.tracking_uri) as url,
                    httpx.Client(
                        base_url=url,
                        trust_env=False,
                        timeout=30,
                    ) as client,
                ):
                    first_receipt = None
                    for case_id, question, character, participant, event, bound in cases:
                        query = EventQuery(
                            kind="crime_history",
                            character_id=character,
                            participant_id=participant,
                            event_id=event,
                            max_events=bound,
                        )
                        response = client.post(
                            "/v1/answers",
                            json={
                                "snapshot_id": snapshot.snapshot_id,
                                "question": question,
                                "route": "graph",
                                "graph": query.model_dump(mode="json"),
                            },
                        )
                        response.raise_for_status()
                        receipt = response.json()
                        first_receipt = first_receipt or receipt
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
                        required = ExtractedEvents(
                            claims=tuple(c for c in expected.claims if c.event_id in required_ids)
                        )
                        responses.append(
                            inspect_answer(
                                client, phase, case_id, receipt["response"], required, snapshot
                            )
                        )
                    typed = client.post(
                        f"/v1/snapshots/{snapshot.snapshot_id}/events",
                        json={
                            "kind": "crime_history",
                            "character_id": "max-branning",
                            "participant_id": "bobby-beale",
                        },
                    )
                    typed.raise_for_status()
                    invalid = client.post(
                        "/v1/answers",
                        json={
                            "question": "Invalid mixed query",
                            "route": "graph",
                            "graph": {
                                "kind": "crime_history",
                                "character_id": "max-branning",
                                "direction": "ancestors",
                            },
                        },
                    )
                    assert invalid.status_code == 422
                    cli = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "ask_phil.cli",
                            "--api-url",
                            url,
                            "ask",
                            "Was Max guilty of the crash?",
                            "--snapshot",
                            snapshot.snapshot_id,
                            "--route",
                            "graph",
                            "--crime-history",
                            "--character",
                            "max-branning",
                            "--event",
                            "carl-crash",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=True,
                        env={**os.environ, "NO_PROXY": "127.0.0.1"},
                    )
                    required = ExtractedEvents(
                        claims=tuple(c for c in expected.claims if c.event_id == "carl-crash")
                    )
                    cli_record = inspect_answer(
                        client,
                        phase,
                        "cli-false-confession",
                        json.loads(cli.stdout)["response"],
                        required,
                        snapshot,
                    )
                    cli_record["transport"] = "cli"
                    responses.append(cli_record)
                    session = client.post("/v1/sessions")
                    session.raise_for_status()
                    created = session.json()
                    session_path = f"/v1/sessions/{created['session']['session_id']}"
                    headers = {"Authorization": f"Bearer {created['session_token']}"}
                    turn = client.post(
                        session_path + "/turns",
                        headers=headers,
                        json={
                            "snapshot_id": snapshot.snapshot_id,
                            "question": "Did Phil kill Stella?",
                            "route": "graph",
                            "graph": {"kind": "crime_history", "character_id": "phil-mitchell"},
                        },
                    )
                    turn.raise_for_status()
                    required = ExtractedEvents(
                        claims=tuple(c for c in expected.claims if c.event_id == "stella-death")
                    )
                    responses.append(
                        inspect_answer(
                            client,
                            phase,
                            "session-false-confession",
                            turn.json()["response"],
                            required,
                            snapshot,
                        )
                    )
                    reset = client.post(session_path + "/reset", headers=headers)
                    reset.raise_for_status()
                    assert reset.json()["generation"] == 1 and not reset.json()["history"]
                    lookup = client.get(f"/v1/snapshots/{snapshot.snapshot_id}/event-claims")
                    assert lookup.json() == audit.model_dump(mode="json")
                with (
                    serve(database_url, args.tracking_uri) as url,
                    httpx.Client(base_url=url, trust_env=False, timeout=30) as client,
                ):
                    assert first_receipt is not None
                    saved = client.get(
                        f"/v1/responses/{first_receipt['response']['response_id']}",
                        headers={
                            "Authorization": f"Bearer {first_receipt['read_token']}",
                        },
                    )
                    assert saved.json() == first_receipt["response"]
                checks.append(
                    dict(
                        phase=phase,
                        typed_tool=typed.json(),
                        invalid_mixed_query_http=422,
                        audit_readback_matches=True,
                        original_response_survives_api_restart=True,
                        event_session_and_reset=True,
                    )
                )
            finally:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
    tracking = MlflowClient(tracking_uri=args.tracking_uri)
    for record in responses:
        answer = record["response"]
        trace = tracking.get_trace(answer["trace_id"], flush=True)
        assert trace is not None
        root = next(s for s in trace.data.spans if s.name == "graph")
        tool = next(s for s in trace.data.spans if s.name == "crime_history")
        assert root.outputs == answer
        if "graph" in answer:
            assert tool.outputs == answer["graph"]
        else:
            assert answer["execution"]["stop_reason"] == "context_limit"
        assert answer["execution"]["model_calls"] == 0 and answer["execution"]["tool_calls"] == 1
        record.update(
            trace_output_matches=True,
            trace_span_names=[s.name for s in trace.data.spans],
            tool_output=tool.outputs,
        )
    payload = dict(
        captured_at=datetime.now(UTC).isoformat(),
        code_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        application_sha256=application_fingerprint(),
        snapshot_sha256=snapshot.fingerprint,
        admissions=audits,
        responses=responses,
        checks=checks,
        paid_serving_calls=0,
        serving_inference_usd=0,
        limitation=(
            "Exposed source-reviewed incidents; model extraction and reviewed curation "
            "are scored separately. No held-out, human or canon acceptance. "
            "Database and hosting costs excluded."
        ),
    )
    with args.output.open("x") as output:
        json.dump(payload, output, indent=2, ensure_ascii=False)
        output.write("\n")
    print(json.dumps(dict(output=str(args.output), responses=len(responses), traces_match=True)))
    return 0


def inspect_answer(
    client: httpx.Client,
    phase: str,
    case_id: str,
    answer: dict[str, Any],
    expected: ExtractedEvents,
    snapshot: SourceSnapshot,
) -> dict[str, Any]:
    for citation in answer["citations"]:
        evidence = client.get(citation["resolve_path"])
        evidence.raise_for_status()
        assert evidence.json()["matches"][0]["sha256"] == citation["sha256"]
    score = score_events(
        json.dumps({"claims": answer.get("graph", {}).get("claims", [])}), expected, snapshot
    )
    # These source-reviewed prohibitions concern the scoped acts, not unrelated crimes.
    forbidden = (
        "Max Branning committed the act",
        "I committed the act",
        "Ben Mitchell committed the act",
        "Max murdered Lucy",
        "Phil killed Stella",
        "acquitted, so innocent",
        "never committed a crime.",
    )
    found = [text for text in forbidden if text in answer["answer"]]
    return dict(
        phase=phase,
        case_id=case_id,
        transport="api",
        response=answer,
        citations_resolve=True,
        reference_comparison=score.model_dump(mode="json"),
        forbidden_guilt_conflations=found,
    )


if __name__ == "__main__":
    raise SystemExit(main())
