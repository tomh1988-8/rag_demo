"""Capture capped route counterfactuals and score separately bound source reviews."""

import argparse
import gzip
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
from mlflow import MlflowClient

from ask_phil.answering import application_fingerprint
from ask_phil.answers import AnswerRecord
from ask_phil.api import create_app
from ask_phil.evaluation import CapturedAnswers, EvaluationRun, QualityReview
from ask_phil.execution import ExecutionLimits
from ask_phil.models import Models, OpenRouterSettings
from ask_phil.openrouter import Budget
from ask_phil.routing import Route, RoutingPolicy
from ask_phil.routing_evaluation import score_routing
from ask_phil.text_retrieval import TextPolicy
from scripts.evaluate_investigation import CLAIMS, REVIEWS, SNAPSHOT, database, install, serve

REFERENCES = Path("data/references/routing-v1.json")
LIMITS = ExecutionLimits(
    model_calls=8,
    tool_calls=4,
    http_calls=24,
    seconds=180,
    context_bytes=4000,
    spend_usd=Decimal("0.20"),
    concurrency=1,
)


def write(path: Path, value: object) -> None:
    with path.open("x") as target:
        target.write(json.dumps(value, indent=2) + "\n")


def capture(admin_url: str, output: Path, tracking_uri: str, maximum: Decimal) -> None:
    if output.exists() or not 0 < maximum <= Decimal("0.75"):
        raise ValueError(
            "Use a fresh capture directory and an additional cap no larger than $0.75."
        )
    references = json.loads(REFERENCES.read_bytes())
    if hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() != references["source_file_sha256"]:
        raise ValueError("Frozen source input changed.")
    cases = references["cases"]
    if len(cases) != 7 or any(c["split"] != "development" for c in cases):
        raise ValueError("Only the seven frozen development tasks can be executed.")
    models = Models.from_environment()
    if not isinstance(models.settings, OpenRouterSettings):
        raise ValueError("This comparison requires the explicitly selected capped cloud profile.")
    before, unsettled = Budget().summary()
    if unsettled:
        raise ValueError("Unsettled shared-ledger reservations require reconciliation first.")
    models.verify()
    output.mkdir(parents=True)
    inputs = sorted(Path("src/ask_phil").glob("*.py")) + [
        Path(__file__),
        Path("scripts/evaluate_investigation.py"),
        REFERENCES,
        SNAPSHOT,
        CLAIMS,
        REVIEWS,
        Path("uv.lock"),
        Path("pyproject.toml"),
        Path(os.environ["ASK_PHIL_MODELS"]),
        Path("config/routing-default.json"),
        *sorted(Path("config").glob("text-*.json")),
    ]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    write(output / "software-inputs.json", hashes)
    identity = application_fingerprint()
    paid = 0
    tracking = MlflowClient(tracking_uri=tracking_uri)
    arms = [
        (f"text-{mode}", "text_rag", mode, cases)
        for mode in ("baseline", "fusion", "expansion", "combined")
    ]
    arms += [("auto-baseline", "auto", "baseline", cases)]
    arms += [
        (
            "auto-combined",
            "auto",
            "combined",
            [
                c
                for c in cases
                if c["case_id"] in {"multi-family", "sufficient-text", "unsupported-theme"}
            ],
        )
    ]
    arms += [("graph", "graph", "baseline", [c for c in cases if c["graph"]])]
    arms += [
        (
            "investigation",
            "investigation",
            "baseline",
            [c for c in cases if c["case_id"] in {"multi-family", "sufficient-text"}],
        )
    ]
    with database(admin_url) as database_url:
        started = time.perf_counter()
        snapshot = install(database_url, models)
        indexing_ms = (time.perf_counter() - started) * 1000
        for arm, requested_route, mode, selected in arms:
            policy = TextPolicy.model_validate_json(Path(f"config/text-{mode}.json").read_bytes())
            metadata = {
                "kind": "uncached-routing-development-v1",
                "arm": arm,
                "application_sha256": identity,
                "snapshot_sha256": snapshot.fingerprint,
                "software_inputs": hashes,
                "model_settings": models.settings.model_dump(mode="json"),
                "text_policy": policy.model_dump(),
                "text_policy_sha256": policy.fingerprint,
                "routing_policy": RoutingPolicy.from_environment().model_dump(),
                "limits": LIMITS.model_dump(mode="json"),
                "cache_enabled": False,
                "selected_conventional_policy": "text-baseline",
                "repeats_per_case": 1,
                "indexing_ms": indexing_ms,
                "indexing_paid_cost_usd": 0,
                "offline_review_paid_cost_usd": 0,
                "ledger_before_usd": before,
                "maximum_additional_usd": str(maximum),
                "maximum_paid_calls": 64,
                "limitation": "Exposed development tasks; no held-out or human canon acceptance.",
            }
            with (
                EvaluationRun(
                    output / f"{arm}.json",
                    REFERENCES,
                    [c["case_id"] for c in selected],
                    metadata=metadata,
                    artifacts=inputs,
                ) as run,
                serve(
                    create_app(
                        database_url,
                        models=models,
                        tracking_uri=tracking_uri,
                        text_policy=policy,
                        execution_limits=LIMITS,
                    )
                ) as url,
                httpx.Client(base_url=url, timeout=210, trust_env=False) as client,
            ):
                for case in selected:
                    spent, pending = Budget().summary()
                    if pending or Decimal(str(spent - before)) + LIMITS.spend_usd > maximum:
                        raise ValueError("The additional run cap cannot reserve the next request.")
                    if paid + (0 if requested_route == "graph" else LIMITS.model_calls) > 64:
                        raise ValueError("The paid-call cap cannot reserve the next request.")
                    if any(
                        hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p)] for p in inputs
                    ):
                        raise ValueError("Frozen capture software or inputs changed.")
                    private: dict[str, Any] = {}

                    def execute(
                        selected: dict[str, Any] = case,
                        selected_arm: str = arm,
                        selected_route: str = requested_route,
                        receipt_state: dict[str, Any] = private,
                    ) -> dict[str, Any]:
                        began = time.perf_counter()
                        cli = (
                            selected_arm == "auto-baseline"
                            and selected["case_id"] == "biological-parents"
                        )
                        if cli:
                            completed = subprocess.run(
                                [
                                    sys.executable,
                                    "-m",
                                    "ask_phil.cli",
                                    "--api-url",
                                    url,
                                    "ask",
                                    selected["question"],
                                ],
                                check=True,
                                capture_output=True,
                                text=True,
                                timeout=210,
                            )
                            receipt_state.update(json.loads(completed.stdout))
                        else:
                            reply = client.post(
                                "/v1/answers",
                                json={
                                    "question": selected["question"],
                                    "route": selected_route,
                                    "graph": selected["graph"]
                                    if selected_route == "graph"
                                    else None,
                                },
                            )
                            reply.raise_for_status()
                            receipt_state.update(reply.json())
                        return {
                            "response": receipt_state["response"],
                            "transport": "cli" if cli else "api",
                            "complete_api_elapsed_ms": (time.perf_counter() - began) * 1000,
                        }

                    def verify(
                        row: dict[str, Any],
                        receipt_state: dict[str, Any] = private,
                        selected_arm: str = arm,
                        selected_id: str = case["case_id"],
                    ) -> dict[str, Any]:
                        response = row["response"]
                        if response["application_sha256"] != identity:
                            raise ValueError(
                                "The served application differs from the frozen software."
                            )
                        if response.get("text_pipeline", {}).get("cache_enabled", False):
                            raise ValueError("Answer caching must remain disabled.")
                        with tempfile.TemporaryDirectory() as directory:
                            receipt = Path(directory) / "private.json"
                            receipt.write_text(json.dumps(receipt_state))
                            readback = subprocess.run(
                                [
                                    sys.executable,
                                    "-m",
                                    "ask_phil.cli",
                                    "--api-url",
                                    url,
                                    "response",
                                    str(receipt),
                                ],
                                check=True,
                                capture_output=True,
                                text=True,
                                timeout=30,
                            )
                        cli_response = json.loads(readback.stdout)
                        trace = tracking.get_trace(response["trace_id"], flush=True)
                        root = trace.data.spans[0]
                        if cli_response != response or root.outputs != response:
                            raise ValueError(
                                "Original CLI/root-trace outputs differ from the response."
                            )
                        for citation in response["citations"]:
                            resolved = client.get(citation["resolve_path"])
                            resolved.raise_for_status()
                            if resolved.json()["matches"] != [
                                {k: v for k, v in citation.items() if k != "resolve_path"}
                            ]:
                                raise ValueError(
                                    "Citation does not resolve to the captured passage."
                                )
                        archive = output / f"{selected_arm}-{selected_id}-trace.json.gz"
                        raw = json.dumps(trace.to_dict(), indent=2).encode()
                        archive.write_bytes(gzip.compress(raw, mtime=0))
                        return {
                            "cli_response": cli_response,
                            "trace_response": root.outputs,
                            "trace_archive": archive.name,
                            "trace_sha256": hashlib.sha256(raw).hexdigest(),
                        }

                    row = run.capture(case["case_id"], execute, verify=verify)
                    response = row["response"]
                    paid += len(response.get("text_pipeline", {}).get("model_executions", []))
                    paid += len(response.get("investigation", {}).get("model_executions", []))
                    after, pending = Budget().summary()
                    run.annotate(
                        ledger_after_usd=after,
                        unsettled_reservations=pending,
                        paid_calls_so_far=paid,
                    )
                    print(
                        f"{arm}/{case['case_id']}: {response['status']} via {response['route']} "
                        f"(${after - before:.6f}; {paid} paid calls)",
                        flush=True,
                    )
    after, pending = Budget().summary()
    write(
        output / "expense.json",
        {
            "ledger_before_usd": before,
            "ledger_after_usd": after,
            "additional_usd": after - before,
            "unsettled_reservations": pending,
            "paid_calls": paid,
            "offline_review_paid_cost_usd": 0,
            "indexing_paid_cost_usd": 0,
        },
    )


def score(directory: Path, reviews: Path, output: Path) -> None:
    results: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.stem in {"software-inputs", "expense"}:
            continue
        capture = CapturedAnswers(path, REFERENCES)
        annotations = json.loads((reviews / f"{path.stem}.json").read_bytes())
        scored = capture.score([QualityReview.model_validate(r) for r in annotations["reviews"]])
        for case_id, row in capture.cases.items():
            answer = AnswerRecord.model_validate(row["response"])
            reference = row["reference"]
            allowed: tuple[Route, ...] = tuple(reference["allowed_routes"])
            metrics = score_routing(
                answer,
                graph_eligible=reference["graph_eligible"],
                allowed_routes=allowed,
                quality=scored[case_id].scores,
            )
            results.append(
                {
                    "arm": path.stem,
                    "case_id": case_id,
                    "routing": metrics.model_dump(),
                    "quality": scored[case_id].scores.model_dump(),
                    "complete_api_elapsed_ms": row["complete_api_elapsed_ms"],
                    "elapsed_ms": answer.elapsed_ms,
                    "response_id": str(answer.response_id),
                    "route": answer.route,
                    "routing_record": answer.routing.model_dump(mode="json")
                    if answer.routing
                    else None,
                }
            )
    write(
        output,
        {
            "version": "routing-comparison-v1",
            "cases": results,
            "limitation": "Development observations; route labels and task success are separate.",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--admin-url", required=True)
    capture_parser.add_argument("--output", type=Path, required=True)
    capture_parser.add_argument("--tracking-uri", required=True)
    capture_parser.add_argument("--maximum-additional-usd", type=Decimal, default=Decimal("0.75"))
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--captures", type=Path, required=True)
    score_parser.add_argument("--reviews", type=Path, required=True)
    score_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture":
        capture(args.admin_url, args.output, args.tracking_uri, args.maximum_additional_usd)
    else:
        score(args.captures, args.reviews, args.output)


if __name__ == "__main__":
    main()
