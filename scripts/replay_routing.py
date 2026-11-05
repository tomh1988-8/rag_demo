"""Replay retained provider completions through the current API without paid inference."""

import argparse
import gzip
import json
import tempfile
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient

from ask_phil.answering import application_fingerprint
from ask_phil.api import create_app
from ask_phil.execution import ExecutionLimits
from ask_phil.models import Models, OpenRouterSettings, embedding_from_environment
from ask_phil.openrouter import Budget, OpenRouterChat
from ask_phil.text_retrieval import TextPolicy
from scripts.evaluate_investigation import database, install
from scripts.evaluate_routing import write


def replay(admin_url: str, captures: Path, output: Path, tracking_uri: str) -> None:
    if output.exists():
        raise ValueError("Retain previous replay evidence; choose a new output path.")
    shared_before = Budget().summary()
    settings = OpenRouterSettings.model_validate_json(
        Path("config/openrouter-sol.json").read_bytes()
    )
    _, embedding = embedding_from_environment()
    pending: list[dict[str, Any]] = []
    observed: list[bool] = []

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/key"):
            return httpx.Response(
                200, json={"data": {"limit": 5, "limit_remaining": 5, "limit_reset": None}}
            )
        if request.url.path.endswith("/endpoints"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "endpoints": [
                            {
                                "tag": settings.provider,
                                "name": "Replay | " + settings.canonical_slug,
                                "supported_parameters": [
                                    "structured_outputs",
                                    "response_format",
                                    "reasoning",
                                    "max_tokens",
                                ],
                            }
                        ]
                    }
                },
            )
        if request.url.path != "/api/v1/chat/completions" or not pending:
            raise ValueError("Replay requested an unrecorded provider operation.")
        expected = pending.pop(0)
        observed.append(json.loads(request.content)["messages"] == expected["messages"])
        execution = expected["execution"]
        usage = execution["provider_usage"]
        return httpx.Response(
            200,
            json={
                "id": "synthetic-replay",
                "provider": usage["provider"],
                "model": usage["returned_model"],
                "choices": [
                    {"finish_reason": "stop", "message": {"content": execution["content"]}}
                ],
                "usage": {
                    "prompt_tokens": usage["input_tokens"],
                    "completion_tokens": usage["output_tokens"],
                    "cost": usage["cost_usd"],
                    "completion_tokens_details": {"reasoning_tokens": usage["reasoning_tokens"]},
                },
            },
        )

    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as directory, database(admin_url) as database_url:
        # Synthetic billing uses an isolated test ledger; the original paid ledger
        # is neither used by the mock transport nor changed, copied or reset.
        models = Models(
            settings,
            embedding,
            OpenRouterChat(
                settings,
                "synthetic-replay-key",
                Budget(Path(directory) / "synthetic.sqlite"),
                httpx.Client(transport=httpx.MockTransport(provider)),
            ),
        )
        install(database_url, models)
        for path in sorted(captures.glob("*.json")):
            document = json.loads(path.read_bytes())
            if document.get("kind") != "uncached-routing-development-v1":
                continue
            policy = TextPolicy.model_validate(document["text_policy"])
            with TestClient(
                create_app(
                    database_url,
                    models=models,
                    tracking_uri=tracking_uri,
                    text_policy=policy,
                    execution_limits=ExecutionLimits.model_validate(document["limits"]),
                )
            ) as client:
                for row in document["cases"]:
                    pending.clear()
                    observed.clear()
                    trace = json.loads(
                        gzip.decompress((captures / row["trace_archive"]).read_bytes())
                    )
                    for span in sorted(
                        trace["data"]["spans"], key=lambda s: s["start_time_unix_nano"]
                    ):
                        if span["name"] not in {"answer_model", "investigator_decision"}:
                            continue
                        attributes = span["attributes"]
                        messages = json.loads(attributes["mlflow.spanInputs"])
                        pending.append(
                            {
                                "messages": [
                                    {
                                        "role": m["role"],
                                        "content": "".join(
                                            b["text"]
                                            for b in m["blocks"]
                                            if b["block_type"] == "text"
                                        ),
                                    }
                                    for m in messages
                                ],
                                "execution": {
                                    **json.loads(attributes["mlflow.spanOutputs"]),
                                    "provider_usage": json.loads(attributes["provider_usage"]),
                                },
                            }
                        )
                    original = row["response"]
                    requested = original["routing"]["requested_route"]
                    result = client.post(
                        "/v1/answers",
                        json={
                            "question": original["question"],
                            "route": requested,
                            "graph": row["reference"]["graph"] if requested == "graph" else None,
                        },
                    )
                    result.raise_for_status()
                    answer = result.json()["response"]
                    fields = ("answer", "status", "route", "context", "citations", "unanswered")
                    unchanged = {key: answer.get(key) == original.get(key) for key in fields}
                    rows.append(
                        {
                            "arm": path.stem,
                            "case_id": row["case_id"],
                            "original_response_id": original["response_id"],
                            "all_model_messages_unchanged": all(observed) and not pending,
                            "replayed_model_calls": len(observed),
                            "unchanged": unchanged,
                        }
                    )
                    print(path.stem, row["case_id"], all(unchanged.values()), flush=True)
    if Budget().summary() != shared_before:
        raise ValueError("The original shared ledger changed during replay.")
    write(
        output,
        {
            "application_sha256": application_fingerprint(),
            "capture_commit": "8f63213",
            "paid_calls": 0,
            "shared_ledger_unchanged": True,
            "cases": rows,
            "limitation": "Retained completions replayed at the external HTTP boundary; this is "
            "software/context consistency evidence, not fresh model-quality or latency evidence.",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-url", required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tracking-uri", required=True)
    args = parser.parse_args()
    replay(args.admin_url, args.captures, args.output, args.tracking_uri)


if __name__ == "__main__":
    main()
