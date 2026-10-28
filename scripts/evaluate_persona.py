"""Capture exposed persona cases in a disposable database; retain real API/CLI/trace outputs."""

import argparse
import json
import os
import socket
import threading
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg
import uvicorn
from psycopg import sql
from psycopg.conninfo import make_conninfo

from ask_phil.answering import AnswerService
from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.models import Models
from ask_phil.persona_workflow import capture_persona
from ask_phil.storage import EvidenceStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--references", type=Path, default=Path("data/references/persona-v1.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repeats", type=int, choices=(1, 2), default=2)
    parser.add_argument("--max-cost-usd", type=Decimal, default=Decimal("1"))
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a fresh output path; existing evidence is immutable.")
    references = json.loads(args.references.read_bytes())
    admin = os.environ["ASK_PHIL_TEST_DATABASE_URL"]
    name = "ask_phil_persona_" + uuid4().hex
    with psycopg.connect(admin, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
        )
        try:
            database = make_conninfo(admin, dbname=name)
            models = Models.from_environment()
            tracking = os.environ.get(
                "MLFLOW_TRACKING_URI", "sqlite:///artifacts/issue-19-mlflow.db"
            )
            service = AnswerService(database, models, tracking)
            for path in sorted({c["snapshot_path"] for c in references["cases"]}):
                snapshot = SourceSnapshot.model_validate_json(Path(path).read_bytes())
                EvidenceStore(database).load(snapshot)
                service.prepare(snapshot.snapshot_id)
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                app = create_app(database, models=models, tracking_uri=tracking)
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
                        raise RuntimeError("Persona API did not start.")
                    with httpx.Client(
                        base_url=f"http://127.0.0.1:{listener.getsockname()[1]}",
                        trust_env=False,
                        timeout=240,
                    ) as client:
                        capture_persona(
                            args.references,
                            args.output,
                            client=client,
                            tracking=service.tracking,
                            profile=models.settings,
                            repeats=args.repeats,
                            max_cost_usd=args.max_cost_usd,
                        )
                finally:
                    server.should_exit = True
                    thread.join(timeout=10)
                    if thread.is_alive():
                        raise RuntimeError("Persona API did not stop.")
        finally:
            connection.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


if __name__ == "__main__":
    main()
