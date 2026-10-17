import os
import socket
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
import uvicorn
from psycopg import sql
from psycopg.conninfo import make_conninfo
from starlette.types import ASGIApp

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.storage import EvidenceStore


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--test-database-url",
        default=os.environ.get("ASK_PHIL_TEST_DATABASE_URL"),
        help="Disposable PostgreSQL connection with permission to create test databases.",
    )


@pytest.fixture
def seed() -> SourceSnapshot:
    return SourceSnapshot.model_validate_json(Path("data/seed/phil-arrival-v1.json").read_text())


@pytest.fixture
def http_server() -> Callable[[ASGIApp], AbstractContextManager[str]]:
    @contextmanager
    def serve(app: ASGIApp) -> Iterator[str]:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
            thread = threading.Thread(
                target=server.run, kwargs={"sockets": [listener]}, daemon=True
            )
            thread.start()
            try:
                deadline = time.monotonic() + 5
                while not server.started and thread.is_alive() and time.monotonic() < deadline:
                    time.sleep(0.01)
                assert server.started, "Test HTTP server did not start."
                yield f"http://127.0.0.1:{listener.getsockname()[1]}"
            finally:
                server.should_exit = True
                thread.join(timeout=5)
                assert not thread.is_alive(), "Test HTTP server did not stop."

    return serve


@pytest.fixture
def live_api(
    database_url: str,
    seed: SourceSnapshot,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
) -> Iterator[str]:
    EvidenceStore(database_url).load(seed)
    with http_server(create_app(database_url)) as url:
        yield url


@pytest.fixture
def database_url(request: pytest.FixtureRequest) -> Iterator[str]:
    admin_url = request.config.getoption("--test-database-url")
    if not isinstance(admin_url, str) or not admin_url:
        pytest.fail("Set ASK_PHIL_TEST_DATABASE_URL to a disposable PostgreSQL admin connection.")
    name = "ask_phil_test_" + uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        try:
            yield make_conninfo(admin_url, dbname=name)
        finally:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
