"""Capture one unclassified-fact answer through the existing public capture workflow."""

import argparse
import hashlib
import json
import socket
import threading
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psycopg
import uvicorn
from mlflow import MlflowClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter

from ask_phil.api import create_app
from ask_phil.claims import ClaimReview
from ask_phil.connection_evaluation import ConnectionReference
from ask_phil.event_graph import EventGraph
from ask_phil.evidence import SourceSnapshot
from ask_phil.family_graph import FamilyGraph
from ask_phil.models import Models
from ask_phil.openrouter import Budget
from ask_phil.parentage import ClaimBatch
from ask_phil.persona_workflow import capture_persona
from ask_phil.publications import PublicationStore, RefreshRun
from ask_phil.relationship_graph import RelationshipGraph
from ask_phil.relationships import RelationshipBatch
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventReview


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    directory = Path("docs/implementation/issue-20")
    output = directory / "text-runtime.json"
    if output.exists():
        raise FileExistsError("Retain the original paid answer; no automatic repeat.")
    snapshot_path = Path("artifacts/issue-20-snapshot.json")
    snapshot = SourceSnapshot.model_validate_json(snapshot_path.read_bytes())
    graph = ConnectionReference.model_validate_json((directory / "graph/claims.json").read_bytes())
    if graph.snapshot_sha256 != snapshot.fingerprint:
        raise ValueError("Text acceptance must share the reviewed graph/source snapshot.")
    reviews = json.loads((directory / "graph/reviews.json").read_bytes())
    reference = json.loads(Path("data/references/core-graph-text-v1.json").read_bytes())
    if len(reference["cases"]) != 1 or Budget().summary()[1]:
        raise ValueError("Capture requires one reviewed case and a settled shared ledger.")
    for case in reference["cases"]:
        case.update(
            snapshot_path=str(snapshot_path),
            snapshot_file_sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        )
    reference_path = directory / "text-reference.json"
    with reference_path.open("x") as destination:
        destination.write(json.dumps(reference, indent=2, ensure_ascii=False) + "\n")
    models = Models.from_environment()
    models.verify()
    tracking_uri = "sqlite:///artifacts/issue-20-mlflow.db"
    database = "ask_phil_core_text_" + uuid4().hex
    with psycopg.connect(args.database_url, autocommit=True) as admin:
        admin.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(database))
        )
        database_url = make_conninfo(args.database_url, dbname=database)
        try:
            EvidenceStore(database_url).load(snapshot)
            common: dict[str, Any] = dict(
                snapshot_id=snapshot.snapshot_id,
                snapshot_sha256=snapshot.fingerprint,
                catalogue=graph.catalogue,
                extractor="retained-reviewed-reference-composition",
            )
            FamilyGraph(database_url).install(
                ClaimBatch(**common, claims=graph.family_claims),
                TypeAdapter(tuple[ClaimReview, ...]).validate_python(reviews["family"]),
            )
            RelationshipGraph(database_url).install(
                RelationshipBatch(**common, claims=graph.relationship_claims),
                TypeAdapter(tuple[ClaimReview, ...]).validate_python(reviews["relationship"]),
            )
            EventGraph(database_url).install(
                EventBatch(
                    **common, claims=graph.event_claims, context_claims=graph.context_claims
                ),
                TypeAdapter(tuple[EventReview, ...]).validate_python(reviews["event"]),
            )
            index = TextRetriever(
                database_url,
                models.embedding,
                models.settings.embedding_id,
                models.settings.embedding_dimensions,
            ).prepare(snapshot.snapshot_id)
            publications = PublicationStore(database_url)
            with publications.writer() as connection:
                publication = publications.publish(
                    snapshot,
                    index,
                    RefreshRun(
                        run_id=uuid4(),
                        flow_run_id=uuid4(),
                        started_at=datetime.now(UTC),
                        status="running",
                        input_sha256=graph.origins["plan"],
                    ),
                    connection,
                )
            with (directory / "text-publication.json").open("x") as destination:
                destination.write(publications.active().model_dump_json(indent=2) + "\n")
            if publication.status != "published":
                raise ValueError("The coherent full-corpus publication was not installed.")
            app = create_app(database_url, models=models, tracking_uri=tracking_uri)
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
                thread = threading.Thread(
                    target=server.run, kwargs={"sockets": [listener]}, daemon=True
                )
                thread.start()
                try:
                    deadline = time.monotonic() + 10
                    while not server.started and thread.is_alive() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    if not server.started:
                        raise RuntimeError("The text acceptance API did not start.")
                    with httpx.Client(
                        base_url=f"http://127.0.0.1:{listener.getsockname()[1]}",
                        trust_env=False,
                        timeout=240,
                    ) as client:
                        capture_persona(
                            reference_path,
                            output,
                            client=client,
                            tracking=MlflowClient(tracking_uri=tracking_uri),
                            profile=models.settings,
                            repeats=1,
                            max_cost_usd=Decimal("0.25"),
                        )
                finally:
                    server.should_exit = True
                    thread.join(timeout=10)
                    if thread.is_alive():
                        raise RuntimeError("The text acceptance API did not stop.")
        finally:
            admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))


if __name__ == "__main__":
    main()
