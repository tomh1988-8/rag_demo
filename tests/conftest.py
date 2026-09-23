import os
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo

from ask_phil.evidence import SourceSnapshot


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
