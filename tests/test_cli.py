import gzip
import json
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
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


def test_maintainer_imports_sources_and_reader_inspects_them_over_http(
    live_api: str,
    database_url: str,
) -> None:
    command = [sys.executable, "-m", "ask_phil.cli"]
    loaded = subprocess.run(
        [
            *command,
            "import-sources",
            "data/sources/real-sources-v1.json.gz",
            "--snapshot",
            "cli-import",
        ],
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert loaded.returncode == 0, loaded.stderr
    assert json.loads(loaded.stdout)["snapshot_id"] == "cli-import"
    env = {k: v for k, v in os.environ.items() if k != "DATABASE_URL"}
    read = [*command, "--api-url", live_api]
    report = subprocess.run(
        [*read, "source-report", "--snapshot", "cli-import"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert report.returncode == 0, report.stderr
    assert len(json.loads(report.stdout)["sources"]) == 8
    identity = subprocess.run(
        [*read, "resolve-character", "Letitia Dean", "--snapshot", "cli-import"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert identity.returncode == 0, identity.stderr
    assert json.loads(identity.stdout)["status"] == "performer"
    captured = subprocess.run(
        [*read, "source", "episode", "--snapshot", "cli-import"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert captured.returncode == 0, captured.stderr
    assert json.loads(captured.stdout)["records"][0]["fields"]["airdate"] == "1985-02-19"


def test_rejected_import_does_not_publish_partial_sources_or_disturb_existing_evidence(
    live_api: str,
    database_url: str,
    tmp_path: Path,
) -> None:
    import hashlib

    batch = json.loads(gzip.decompress(Path("data/sources/real-sources-v1.json.gz").read_bytes()))
    final_source = batch["captures"][-1]
    final_source["content"] = "not json"
    final_source["sha256"] = hashlib.sha256(b"not json").hexdigest()
    invalid = tmp_path / "invalid-batch.json"
    invalid.write_text(json.dumps(batch))
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ask_phil.cli",
            "import-sources",
            str(invalid),
            "--snapshot",
            "rejected",
        ],
        env={**os.environ, "DATABASE_URL": database_url},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "malformed JSON" in result.stderr
    assert "Traceback" not in result.stderr
    with httpx.Client(base_url=live_api, trust_env=False) as client:
        assert client.get("/v1/snapshots/rejected/sources").status_code == 404
        preserved = client.get("/v1/snapshots/phil-arrival-v1/evidence/phil-arrival-001")
        assert preserved.status_code == 200
        assert (
            preserved.json()["snapshot_sha256"]
            == "26da379f1f9c27c0bf41ca4a200072280bf441f7e84eacee92c761cede134462"
        )
