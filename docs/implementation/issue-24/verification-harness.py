"""Run final pytest with bounded local capture of unexpected source-integrity failures."""

import gzip
import hashlib
import json
import os
import sys
from uuid import uuid4
from pathlib import Path

os.environ["PREFECT_HOME"] = "/tmp/ask-phil-issue24-final-verification"
os.environ["PREFECT_SERVER_ANALYTICS_ENABLED"] = "false"
os.environ["MLFLOW_DISABLE_AGENT_HINT"] = "1"

import pytest
from pydantic import ValidationError


class SourceFailureCapture:
    def __init__(self) -> None:
        self.run_id = uuid4().hex

    def pytest_runtest_makereport(self, item: pytest.Item, call: pytest.CallInfo[None]) -> None:
        if call.excinfo is None:
            return
        error = call.excinfo.value
        payloads: list[tuple[str, bytes, str | None]] = []
        if isinstance(error, ValidationError):
            for failure in error.errors(include_url=False):
                value = failure.get("input")
                if isinstance(value, dict) and isinstance(value.get("content"), str) and {"source_id", "sha256"} <= value.keys():
                    payloads.append(("capture-content", value["content"].encode("utf-8", "surrogatepass"), str(value["sha256"])))
        elif isinstance(error, json.JSONDecodeError):
            if any(str(frame.path).endswith(("ask_phil/storage.py", "ask_phil/ingestion.py")) for frame in call.excinfo.traceback):
                payloads.append(("source-json", error.doc.encode("utf-8", "surrogatepass"), None))
        if not payloads:
            return
        destination = Path("artifacts/issue-24/source-integrity-failures") / self.run_id
        destination.mkdir(parents=True, exist_ok=True, mode=0o700)
        identity = hashlib.sha256((item.nodeid + call.when).encode()).hexdigest()[:20]
        records = []
        for index, (kind, raw, expected) in enumerate(payloads):
            if len(raw) > 25_000_000:
                continue
            filename = f"{identity}-{index}.gz"
            path = destination / filename
            with path.open("xb") as retained:
                retained.write(gzip.compress(raw, mtime=0))
            path.chmod(0o600)
            records.append({"kind": kind, "payload": filename, "bytes": len(raw),
                            "actual_sha256": hashlib.sha256(raw).hexdigest(), "expected_sha256": expected})
        with (destination / f"{identity}.json").open("x") as output:
            json.dump({"nodeid": item.nodeid, "phase": call.when, "exception": type(error).__name__,
                       "payloads": records}, output, indent=2)


if __name__ == "__main__":
    sys.exit(pytest.main([
        "-q", "--maxfail=1", "--tb=short", "-p", "no:cacheprovider", "--disable-warnings",
        "--test-database-url", "postgresql://ask_phil:local-demo-only@127.0.0.1:55424/postgres",
        "--junitxml=docs/implementation/issue-24/software-tests.xml",
    ], plugins=[SourceFailureCapture()]))
