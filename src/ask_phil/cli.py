"""CLI client and explicit maintainer capture, import and indexing operations."""

import argparse
import getpass
import gzip
import json
import os
import sys
from pathlib import Path
from uuid import UUID

import httpx
import psycopg

from ask_phil.evidence import SourceSnapshot
from ask_phil.ingestion import build_snapshot, capture_plan, capture_sources, read_batch
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
    inspect.add_argument("--snapshot", help="Defaults to the active publication.")
    inspect.add_argument("--limit", type=int, default=10)
    load = commands.add_parser("load", help="Maintainer: load a captured fixture into PostgreSQL.")
    load.add_argument("fixture", type=Path)
    capture = commands.add_parser(
        "capture-sources", help="Maintainer: capture official public HTML/JSON sources."
    )
    capture.add_argument("plan", type=Path)
    capture.add_argument("output", type=Path)
    capture.add_argument(
        "--checkpoint-dir",
        type=Path,
        help="Retain successful captures and resume this exact plan after interruption.",
    )
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
    ask.add_argument("--snapshot", help="Defaults to the active publication.")
    ask.add_argument("--session", type=Path, help="Private receipt from start-session.")
    ask.add_argument("--route", choices=("text_rag", "graph"), default="text_rag")
    ask.add_argument("--character", help="Reviewed character ID for an explicit graph query.")
    graph_kind = ask.add_mutually_exclusive_group()
    graph_kind.add_argument("--direction", choices=("ancestors", "descendants"))
    graph_kind.add_argument(
        "--history", action="store_true", help="Query reviewed relationship history."
    )
    graph_kind.add_argument(
        "--crime-history", action="store_true", help="Query reviewed crime and justice roles."
    )
    ask.add_argument("--participant", help="Optional second character for --crime-history.")
    ask.add_argument("--event", help="Optional reviewed incident ID for --crime-history.")
    ask.add_argument("--partner", help="Optional second character for --history.")
    ask.add_argument("--max-events", type=int, default=20)
    ask.add_argument("--depth", type=int, default=3)
    ask.add_argument("--max-paths", type=int, default=20)
    family_install = commands.add_parser(
        "install-family", help="Maintainer: admit reviewed claims and derive an immutable graph."
    )
    family_install.add_argument("batch", type=Path)
    family_install.add_argument("reviews", type=Path)
    family_audit = commands.add_parser(
        "family-claims", help="Inspect retained claims and admission reviews."
    )
    family_audit.add_argument("--snapshot", required=True)
    history_install = commands.add_parser(
        "install-relationships", help="Maintainer: admit reviewed relationship history claims."
    )
    history_install.add_argument("batch", type=Path)
    history_install.add_argument("reviews", type=Path)
    history_audit = commands.add_parser(
        "relationship-claims", help="Inspect retained relationship claims and admission reviews."
    )
    history_audit.add_argument("--snapshot", required=True)
    event_install = commands.add_parser(
        "install-events", help="Maintainer: admit reviewed crime and justice assertions."
    )
    event_install.add_argument("batch", type=Path)
    event_install.add_argument("reviews", type=Path)
    event_audit = commands.add_parser(
        "event-claims", help="Inspect retained event claims and reviews."
    )
    event_audit.add_argument("--snapshot", required=True)
    session = commands.add_parser("start-session", help="Create a bounded anonymous conversation.")
    session.add_argument("receipt", type=Path, help="New private local session receipt file.")
    reset = commands.add_parser("reset", help="Clear reference context, keeping saved answers.")
    reset.add_argument("receipt", type=Path)
    chat = commands.add_parser("chat", help="Talk to Ask Phil; use /reset or /quit.")
    chat.add_argument("--snapshot", help="Defaults to the active publication on each turn.")
    response = commands.add_parser(
        "response", help="Read the original answer using a saved receipt."
    )
    response.add_argument("receipt", type=Path)
    index = commands.add_parser(
        "index", help="Maintainer: embed a snapshot using configured models."
    )
    index.add_argument("--snapshot", required=True)
    refresh = commands.add_parser(
        "refresh-sources", help="Maintainer: run a reviewed refresh through Prefect and publish."
    )
    refresh.add_argument("input", type=Path)
    refresh.add_argument("--live", action="store_true", help="Input is a capture plan to fetch.")
    commands.add_parser(
        "rollback-snapshot", help="Maintainer: restore the prior compatible source/index pair."
    )
    publication = commands.add_parser("publication", help="Inspect the active snapshot manifest.")
    publication.add_argument("--previous", action="store_true")
    runs = commands.add_parser("refresh-runs", help="Inspect recorded refresh/recovery outcomes.")
    runs.add_argument("run_id", type=UUID, nargs="?")
    runs.add_argument("--limit", type=int, default=20)
    runs.add_argument(
        "--captures", action="store_true", help="Inspect retained captures for a run."
    )
    args = parser.parse_args()
    if args.command == "ask":
        if args.route == "graph" and (
            not args.character or not (args.direction or args.history or args.crime_history)
        ):
            parser.error(
                "--route graph requires --character and --direction, --history or --crime-history."
            )
        if args.route != "graph" and (
            args.character
            or args.direction
            or args.history
            or args.partner
            or args.crime_history
            or args.participant
            or args.event
        ):
            parser.error("Graph query arguments require --route graph.")
        if args.partner and not args.history:
            parser.error("--partner requires --history.")
        if args.participant and not args.crime_history:
            parser.error("--participant requires --crime-history.")
        if args.event and not args.crime_history:
            parser.error("--event requires --crime-history.")
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
                batch = (
                    capture_plan(plan, client, args.checkpoint_dir)
                    if args.checkpoint_dir
                    else SourceBatch(
                        format_version=1,
                        catalogue=plan.catalogue,
                        policies=plan.policies,
                        captures=capture_sources(plan.requests, client),
                    )
                )
            data = batch.model_dump_json().encode()
            with args.output.open("xb") as output:
                output.write(gzip.compress(data, mtime=0) if args.output.suffix == ".gz" else data)
            print(json.dumps({"output": str(args.output), "captured_sources": len(batch.captures)}))
        elif args.command in {
            "load",
            "index",
            "import-sources",
            "refresh-sources",
            "rollback-snapshot",
            "install-family",
            "install-relationships",
            "install-events",
        }:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                parser.error("DATABASE_URL is required for the maintainer storage command.")
            if args.command in {"refresh-sources", "rollback-snapshot"}:
                from ask_phil.models import ModelConfigurationError, embedding_from_environment
                from ask_phil.refresh import SourceRefresh

                try:
                    settings, embedding = embedding_from_environment()
                    refresh_service = SourceRefresh(
                        database_url,
                        embedding,
                        settings.embedding_id,
                        settings.embedding_dimensions,
                    )
                    if args.command == "refresh-sources":
                        embedding.verify(settings.embedding_digest)
                        refresh_input = (
                            CapturePlan.model_validate_json(args.input.read_bytes())
                            if args.live
                            else read_batch(args.input)
                        )
                        outcome = refresh_service.run(refresh_input)
                    else:
                        outcome = refresh_service.rollback()
                except ModelConfigurationError as exc:
                    raise ValueError(str(exc)) from None
                print(outcome.model_dump_json())
            elif args.command == "install-events":
                from pydantic import TypeAdapter

                from ask_phil.event_graph import EventGraph
                from ask_phil.story_events import EventBatch, EventReview

                event_reviews = TypeAdapter(tuple[EventReview, ...]).validate_json(
                    args.reviews.read_bytes()
                )
                event_audit_record = EventGraph(database_url).install(
                    EventBatch.model_validate_json(args.batch.read_bytes()), event_reviews
                )
                print(event_audit_record.model_dump_json())
            elif args.command in {"install-family", "install-relationships"}:
                from pydantic import TypeAdapter

                from ask_phil.family_graph import FamilyGraph
                from ask_phil.parentage import ClaimBatch, ClaimReview
                from ask_phil.relationship_graph import RelationshipGraph
                from ask_phil.relationships import RelationshipBatch

                reviews = TypeAdapter(tuple[ClaimReview, ...]).validate_json(
                    args.reviews.read_bytes()
                )
                audit = (
                    FamilyGraph(database_url).install(
                        ClaimBatch.model_validate_json(args.batch.read_bytes()), reviews
                    )
                    if args.command == "install-family"
                    else RelationshipGraph(database_url).install(
                        RelationshipBatch.model_validate_json(args.batch.read_bytes()), reviews
                    )
                )
                print(audit.model_dump_json())
            elif args.command in {"load", "import-sources"}:
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
            timeout = 400 if args.command in {"ask", "chat"} else 10
            with httpx.Client(base_url=args.api_url, timeout=timeout, trust_env=False) as client:
                if args.command == "chat":
                    return chat_session(client, args.snapshot)
                elif args.command == "start-session":
                    from ask_phil.sessions import SessionReceipt

                    # Refuse an existing file before creating a remote session.
                    with os.fdopen(
                        os.open(args.receipt, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
                    ) as output:
                        try:
                            created = client.post("/v1/sessions")
                            created.raise_for_status()
                            session_receipt = SessionReceipt.model_validate(created.json())
                            output.write(session_receipt.model_dump_json())
                        except Exception:
                            args.receipt.unlink(missing_ok=True)
                            raise
                    print(
                        json.dumps(
                            {
                                "session": session_receipt.session.model_dump(mode="json"),
                                "receipt": str(args.receipt),
                                "feedback_expires_at": (
                                    session_receipt.feedback_expires_at.isoformat()
                                ),
                            }
                        )
                    )
                    return 0
                elif args.command == "reset":
                    session_path, session_headers = session_access(args.receipt)
                    result = client.post(session_path + "/reset", headers=session_headers)
                elif args.command == "ask":
                    ask_path, session_headers = (
                        session_access(args.session) if args.session else (None, {})
                    )
                    result = client.post(
                        ask_path + "/turns" if ask_path else "/v1/answers",
                        headers=session_headers,
                        json={
                            "question": args.query,
                            "snapshot_id": args.snapshot,
                            "route": args.route,
                            "graph": (
                                {
                                    "kind": "crime_history",
                                    "character_id": args.character,
                                    "participant_id": args.participant,
                                    "event_id": args.event,
                                    "max_events": args.max_events,
                                }
                                if args.crime_history
                                else {
                                    "kind": "relationship_history",
                                    "character_id": args.character,
                                    "partner_id": args.partner,
                                    "max_events": args.max_events,
                                }
                                if args.history
                                else {
                                    "character_id": args.character,
                                    "direction": args.direction,
                                    "max_depth": args.depth,
                                    "max_paths": args.max_paths,
                                }
                            )
                            if args.route == "graph"
                            else None,
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
                elif args.command == "family-claims":
                    result = client.get(f"/v1/snapshots/{args.snapshot}/family-claims")
                elif args.command == "relationship-claims":
                    result = client.get(f"/v1/snapshots/{args.snapshot}/relationship-claims")
                elif args.command == "event-claims":
                    result = client.get(f"/v1/snapshots/{args.snapshot}/event-claims")
                elif args.command == "source":
                    result = client.get(f"/v1/snapshots/{args.snapshot}/sources/{args.source_id}")
                elif args.command == "resolve-character":
                    result = client.get(
                        f"/v1/snapshots/{args.snapshot}/identities", params={"name": args.name}
                    )
                elif args.command == "publication":
                    result = client.get(
                        "/v1/publication/previous" if args.previous else "/v1/publication"
                    )
                elif args.command == "refresh-runs":
                    if args.captures and args.run_id is None:
                        parser.error("--captures requires a run ID.")
                    path = f"/v1/refresh-runs/{args.run_id}" if args.run_id else "/v1/refresh-runs"
                    result = client.get(
                        path + ("/captures" if args.captures else ""), params={"limit": args.limit}
                    )
                else:
                    result = client.get(
                        f"/v1/snapshots/{args.snapshot}/inspect"
                        if args.snapshot
                        else "/v1/inspect",
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


def session_access(path: Path) -> tuple[str, dict[str, str]]:
    from ask_phil.sessions import SessionReceipt

    try:
        receipt = SessionReceipt.model_validate_json(path.read_text())
    except ValueError:
        raise ValueError("Invalid private session receipt.") from None
    return (
        f"/v1/sessions/{receipt.session.session_id}",
        {"Authorization": f"Bearer {receipt.session_token}"},
    )


def chat_session(client: httpx.Client, snapshot_id: str | None) -> int:
    from ask_phil.sessions import SessionReceipt

    created = client.post("/v1/sessions")
    created.raise_for_status()
    receipt = SessionReceipt.model_validate(created.json())
    path = f"/v1/sessions/{receipt.session.session_id}"
    headers = {"Authorization": f"Bearer {receipt.session_token}"}
    print("Ask Phil. Use /reset to clear context, /quit to leave.")
    while True:
        try:
            question = input("You> ").strip()
        except EOFError:
            return 0
        if question == "/quit":
            return 0
        if not question:
            continue
        if question == "/reset":
            result = client.post(path + "/reset", headers=headers)
        else:
            result = client.post(
                path + "/turns",
                headers=headers,
                json={"question": question, "snapshot_id": snapshot_id},
            )
        result.raise_for_status()
        print(json.dumps(result.json(), indent=2, ensure_ascii=True))


if __name__ == "__main__":
    raise SystemExit(main())
