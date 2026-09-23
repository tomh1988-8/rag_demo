import json
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration


@pytest.fixture
def live_api(database_url: str, seed: SourceSnapshot) -> Iterator[str]:
    EvidenceStore(database_url).load(seed)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(create_app(database_url), log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started, "Test API did not start."
            yield f"http://127.0.0.1:{listener.getsockname()[1]}"
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive(), "Test API did not stop."


def test_cli_inspects_evidence_via_http_without_database_credentials(live_api: str) -> None:
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ask_phil.cli",
            "--api-url",
            live_api,
            "inspect",
            "When does Phil Mitchell first arrive in Walford?",
            "--snapshot",
            "phil-arrival-v1",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert [p["evidence_id"] for p in body["matches"]] == ["phil-arrival-001"]
    assert body["source"]["support_status"] == "source_supported"


def test_cli_reports_an_empty_fixture_result_and_exits_nonzero_on_http_failure(
    live_api: str,
) -> None:
    command = [sys.executable, "-m", "ask_phil.cli", "--api-url", live_api, "inspect"]
    empty = subprocess.run(
        [*command, "Who is Phil Mitchell's mother?", "--snapshot", "phil-arrival-v1"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert empty.returncode == 0, empty.stderr
    assert json.loads(empty.stdout)["matches"] == []
    missing = subprocess.run(
        [*command, "Phil", "--snapshot", "missing-snapshot"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert missing.returncode == 1
    assert "HTTP 404" in missing.stderr
    assert "Traceback" not in missing.stderr
