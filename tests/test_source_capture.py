import json
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from ask_phil.ingestion import read_batch
from ask_phil.source_records import CapturePlan, SourceRequest


def test_interrupted_capture_resumes_retained_payloads_without_fetching_them_again(
    tmp_path: Path,
) -> None:
    from ask_phil.ingestion import capture_plan

    batch = read_batch(Path("data/sources/real-sources-v1.json.gz"))
    plan = CapturePlan(
        **batch.model_dump(exclude={"captures"}),
        requests=tuple(
            SourceRequest.model_validate(c.model_dump(exclude={"content", "sha256", "captured_at"}))
            for c in batch.captures
        ),
    )
    payloads = {str(c.url): c.content for c in batch.captures}

    def interrupted(request: httpx.Request) -> httpx.Response:
        if str(request.url) == str(plan.requests[1].url):
            return httpx.Response(429)
        return httpx.Response(200, text=payloads[str(request.url)])

    with httpx.Client(transport=httpx.MockTransport(interrupted)) as client:
        with pytest.raises(ValueError, match="429"):
            capture_plan(plan, client, tmp_path)

    def resumed(request: httpx.Request) -> httpx.Response:
        if str(request.url) == str(plan.requests[0].url):
            raise AssertionError("A retained capture must survive a new client/process.")
        return httpx.Response(200, text=payloads[str(request.url)])

    with httpx.Client(transport=httpx.MockTransport(resumed)) as client:
        captured = capture_plan(
            CapturePlan.model_validate_json(plan.model_dump_json()), client, tmp_path
        )
    assert [c.content for c in captured.captures] == [c.content for c in batch.captures]
    assert captured.captures[0].captured_at < captured.captures[-1].captured_at
    # A completed checkpoint is usable without any source service.
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(503))) as client:
        assert capture_plan(plan, client, tmp_path) == captured


def test_resume_rejects_a_changed_plan_and_tampered_capture_before_network_access(
    tmp_path: Path,
) -> None:
    from ask_phil.ingestion import capture_plan

    batch = read_batch(Path("data/sources/real-sources-v1.json.gz"))
    plan = CapturePlan(
        **batch.model_dump(exclude={"captures"}),
        requests=tuple(
            SourceRequest.model_validate(c.model_dump(exclude={"content", "sha256", "captured_at"}))
            for c in batch.captures
        ),
    )
    payloads = {str(c.url): c.content for c in batch.captures}
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=payloads[str(r.url)]))
    ) as client:
        capture_plan(plan, client, tmp_path)

    def offline(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Unexpected network access")

    with httpx.Client(transport=httpx.MockTransport(offline)) as client:
        changed = plan.model_copy(update={"requests": tuple(reversed(plan.requests))})
        with pytest.raises(ValueError, match="different plan"):
            capture_plan(changed, client, tmp_path)
        path = tmp_path / "captures" / (plan.requests[-1].source_id + ".json")
        data = json.loads(path.read_text())
        data["content"] += "tampered"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="fingerprint"):
            capture_plan(plan, client, tmp_path)


def test_capture_plan_rejects_duplicate_request_identifiers_before_capture() -> None:
    from pydantic import ValidationError

    plan = CapturePlan.model_validate_json(
        Path("data/sources/real-sources-plan-v1.json").read_bytes()
    )
    data = plan.model_dump()
    data["requests"] = (plan.requests[0], plan.requests[0])
    with pytest.raises(ValidationError, match="unique"):
        CapturePlan.model_validate(data)


def test_cli_resumes_a_completed_capture_and_refuses_to_replace_its_frozen_output(
    tmp_path: Path,
) -> None:
    from ask_phil.ingestion import capture_plan

    plan_path = Path("data/sources/real-sources-plan-v1.json")
    plan = CapturePlan.model_validate_json(plan_path.read_bytes())
    original = read_batch(Path("data/sources/real-sources-v1.json.gz"))
    payloads = {str(c.url): c.content for c in original.captures}
    checkpoint = tmp_path / "checkpoint"
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=payloads[str(r.url)]))
    ) as client:
        captured = capture_plan(plan, client, checkpoint)
    output = tmp_path / "batch.json.gz"
    command = [
        sys.executable,
        "-m",
        "ask_phil.cli",
        "capture-sources",
        str(plan_path),
        str(output),
        "--checkpoint-dir",
        str(checkpoint),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    assert completed.returncode == 0, completed.stderr
    assert read_batch(output) == captured
    frozen_bytes = output.read_bytes()
    repeated = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    assert repeated.returncode == 1
    assert "already exists" in repeated.stderr
    assert output.read_bytes() == frozen_bytes


def test_resuming_capture_keeps_the_batch_byte_limit_including_retained_payloads(
    tmp_path: Path,
) -> None:
    from ask_phil.ingestion import capture_plan

    plan = CapturePlan.model_validate_json(
        Path("data/sources/real-sources-plan-v1.json").read_bytes()
    )
    # Five 4.1 MB payloads individually fit, but their combined 20.5 MB must fail.
    # Stop after four first, then start a fresh capture client against the same journal.
    large = "x" * 4_100_000
    fifth = str(plan.requests[4].url)

    def interrupted(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429 if str(request.url) == fifth else 200, text=large)

    with httpx.Client(transport=httpx.MockTransport(interrupted)) as client:
        with pytest.raises(ValueError, match="429"):
            capture_plan(plan, client, tmp_path)
    retained_urls = {str(r.url) for r in plan.requests[:4]}

    def resumed(request: httpx.Request) -> httpx.Response:
        assert str(request.url) not in retained_urls
        return httpx.Response(200, text=large)

    with httpx.Client(transport=httpx.MockTransport(resumed)) as client:
        with pytest.raises(ValueError, match="byte limit"):
            capture_plan(plan, client, tmp_path)
