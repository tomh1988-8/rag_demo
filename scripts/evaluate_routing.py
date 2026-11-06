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
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from mlflow import MlflowClient

from ask_phil.answering import application_fingerprint
from ask_phil.answers import AnswerRecord
from ask_phil.api import create_app
from ask_phil.evaluation import EvaluationRun, QualityReview
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionLimits
from ask_phil.family_graph import FamilyGraph
from ask_phil.ingestion import build_snapshot, read_batch
from ask_phil.models import Models, OpenRouterSettings
from ask_phil.openrouter import Budget
from ask_phil.parentage import ClaimBatch, ClaimReview
from ask_phil.publications import PublicationStore, RefreshRun
from ask_phil.retrieval import TextRetriever
from ask_phil.routing import Route, RoutingPolicy, RoutingRules
from ask_phil.routing_evaluation import routing_comparison, score_routing
from ask_phil.storage import EvidenceStore
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


def recorded_calls(response: dict[str, Any]) -> int:
    return sum(
        len((response.get(stage) or {}).get("model_executions", []))
        for stage in ("text_pipeline", "investigation")
    )


def install_ordered(database_url: str, models: Models, reference: dict[str, Any]) -> SourceSnapshot:
    snapshot = build_snapshot(read_batch(Path(reference["source_file"])), reference["snapshot_id"])
    if snapshot.fingerprint != reference["snapshot_sha256"]:
        raise ValueError("The ordered corpus differs from the frozen reference.")
    projection = json.loads(Path(reference["family_projection"]).read_bytes())
    EvidenceStore(database_url).load(snapshot)
    FamilyGraph(database_url).install(
        ClaimBatch.model_validate(projection["batch"]),
        tuple(ClaimReview.model_validate(r) for r in projection["reviews"]),
    )
    rules = RoutingRules.load(database_url, snapshot, LIMITS)
    if any(
        rules.eligibility(case["question"]).eligible != case["graph_eligible"]
        for case in reference["cases"]
    ):
        raise ValueError("Admitted graph coverage differs from the frozen eligibility labels.")
    index = TextRetriever(
        database_url,
        models.embedding,
        models.settings.embedding_id,
        models.settings.embedding_dimensions,
    ).prepare(snapshot.snapshot_id)
    publications = PublicationStore(database_url)
    run = RefreshRun(
        run_id=uuid4(),
        flow_run_id=uuid4(),
        started_at=datetime.now(UTC),
        status="running",
        action="review",
        input_sha256=snapshot.fingerprint,
    )
    with publications.writer() as conn:
        publications.publish(snapshot, index, run, conn)
    return snapshot


def capture(
    admin_url: str,
    output: Path,
    tracking_uri: str,
    maximum: Decimal,
    cohort: str = "legacy",
    prior_capture: Path | None = None,
    selected_arms: list[str] | None = None,
    prior_captures: tuple[Path, ...] = (),
) -> None:
    if output.exists() or not 0 < maximum <= Decimal("0.75"):
        raise ValueError(
            "Use a fresh capture directory and an additional cap no larger than $0.75."
        )
    references_path = (
        REFERENCES if cohort == "legacy" else Path("data/references/routing-ordered-v2.json")
    )
    references = json.loads(references_path.read_bytes())
    source_path = Path(references["source_file"])
    if hashlib.sha256(source_path.read_bytes()).hexdigest() != references["source_file_sha256"]:
        raise ValueError("Frozen source input changed.")
    cases = references["cases"]
    if len(cases) != (7 if cohort == "legacy" else 2) or any(
        c["split"] != "development" for c in cases
    ):
        raise ValueError("Only the frozen development tasks can be executed.")
    plan = routing_comparison(references_path)
    pending_arms = plan.pending(output, *prior_captures, arms=selected_arms)
    if not pending_arms:
        raise ValueError("The comparison has no unattempted selected work.")
    if prior_captures and prior_capture is None:
        raise ValueError("A continuation requires its cumulative prior expense record.")
    models = Models.from_environment()
    if not isinstance(models.settings, OpenRouterSettings):
        raise ValueError("This comparison requires the explicitly selected capped cloud profile.")
    before, unsettled = Budget().summary()
    if unsettled:
        raise ValueError("Unsettled shared-ledger reservations require reconciliation first.")
    anchor = before
    paid = initial_paid = 0
    limits = LIMITS
    if cohort == "ordered" and prior_capture is None:
        raise ValueError("The supplement requires the completed prior expense record.")
    if prior_capture is not None:
        prior = json.loads(prior_capture.read_bytes())
        if prior["unsettled_reservations"] or prior["ledger_after_usd"] != before:
            raise ValueError("Prior capture expense must match the preserved current ledger.")
        anchor = prior["ledger_before_usd"]
        paid = initial_paid = int(prior["paid_calls"])
        if not 0 <= paid <= 64:
            raise ValueError("Invalid cumulative paid-call count.")
    if cohort == "ordered":
        limits = LIMITS.model_copy(update={"spend_usd": Decimal("0.30")})
    models.verify()
    output.mkdir(parents=True)
    inputs = sorted(Path("src/ask_phil").glob("*.py")) + [
        Path(__file__),
        Path("scripts/evaluate_investigation.py"),
        references_path,
        source_path,
        SNAPSHOT,
        CLAIMS,
        REVIEWS,
        Path("uv.lock"),
        Path("pyproject.toml"),
        Path(os.environ["ASK_PHIL_MODELS"]),
        Path("config/routing-default.json"),
        *sorted(Path("config").glob("text-*.json")),
    ]
    if cohort == "ordered":
        inputs.append(Path(references["family_projection"]))
    if prior_capture is not None:
        inputs.append(prior_capture)
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    write(output / "software-inputs.json", hashes)
    identity = application_fingerprint()
    tracking = MlflowClient(tracking_uri=tracking_uri)
    cases_by_id = {case["case_id"]: case for case in cases}
    try:
        with plan.record(output, prior=prior_captures), database(admin_url) as database_url:
            started = time.perf_counter()
            snapshot = (
                install(database_url, models)
                if cohort == "legacy"
                else install_ordered(database_url, models, references)
            )
            indexing_ms = (time.perf_counter() - started) * 1000
            for arm, identifiers in pending_arms.items():
                requested_route = "text_rag" if arm.startswith("text-") else arm.split("-")[0]
                mode = arm.split("-")[-1] if "-" in arm else "baseline"
                selected = [cases_by_id[case_id] for case_id in identifiers]
                policy = TextPolicy.model_validate_json(
                    Path(f"config/text-{mode}.json").read_bytes()
                )
                metadata = {
                    "kind": "uncached-routing-development-v1",
                    "cohort": cohort,
                    "arm": arm,
                    "comparison_plan_sha256": plan.fingerprint,
                    "application_sha256": identity,
                    "snapshot_sha256": snapshot.fingerprint,
                    "software_inputs": hashes,
                    "model_settings": models.settings.model_dump(mode="json"),
                    "text_policy": policy.model_dump(),
                    "text_policy_sha256": policy.fingerprint,
                    "routing_policy": RoutingPolicy.from_environment().model_dump(),
                    "limits": limits.model_dump(mode="json"),
                    "cache_enabled": False,
                    "selected_conventional_policy": "text-baseline",
                    "repeats_per_case": 1,
                    "indexing_ms": indexing_ms,
                    "indexing_paid_cost_usd": 0,
                    "offline_review_paid_cost_usd": 0,
                    "ledger_before_usd": anchor,
                    "cohort_ledger_before_usd": before,
                    "maximum_additional_usd": str(maximum),
                    "maximum_paid_calls": 64,
                    "limitation": (
                        "Exposed development tasks; no held-out or human canon acceptance."
                    ),
                }
                with (
                    EvaluationRun(
                        output / f"{arm}.json",
                        references_path,
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
                            execution_limits=limits,
                        )
                    ) as url,
                    httpx.Client(base_url=url, timeout=210, trust_env=False) as client,
                ):
                    for case in selected:
                        spent, pending = Budget().summary()
                        if pending or Decimal(str(spent - anchor)) + limits.spend_usd > maximum:
                            raise ValueError(
                                "The additional run cap cannot reserve the next request."
                            )
                        if paid + (0 if requested_route == "graph" else limits.model_calls) > 64:
                            raise ValueError("The paid-call cap cannot reserve the next request.")
                        if any(
                            hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p)]
                            for p in inputs
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
                        paid += recorded_calls(response)
                        after, pending = Budget().summary()
                        run.annotate(
                            ledger_after_usd=after,
                            unsettled_reservations=pending,
                            paid_calls_so_far=paid,
                        )
                        print(
                            f"{arm}/{case['case_id']}: {response['status']} "
                            f"via {response['route']} "
                            f"(${after - anchor:.6f}; {paid} cumulative paid calls)",
                            flush=True,
                        )
    finally:
        paid = initial_paid
        for arm in plan.arms:
            path = output / f"{arm}.json"
            if not path.exists():
                continue
            for row in json.loads(path.read_bytes())["cases"]:
                response = row.get("response")
                if isinstance(response, dict):
                    paid += recorded_calls(response)
        after, pending = Budget().summary()
        write(
            output / "expense.json",
            {
                "ledger_before_usd": anchor,
                "cohort_ledger_before_usd": before,
                "ledger_after_usd": after,
                "additional_usd": after - anchor,
                "cohort_additional_usd": after - before,
                "unsettled_reservations": pending,
                "paid_calls": paid,
                "cohort_paid_calls": paid - initial_paid,
                "offline_review_paid_cost_usd": 0,
                "indexing_paid_cost_usd": 0,
            },
        )


def score(
    directory: Path,
    reviews: Path,
    output: Path,
    references: Path = REFERENCES,
    prior_captures: tuple[Path, ...] = (),
) -> None:
    plan = routing_comparison(references)
    results: list[dict[str, Any]] = []
    for arm, capture in plan.captures(directory, *prior_captures).items():
        annotations = json.loads((reviews / f"{arm}.json").read_bytes())
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
                    "arm": arm,
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
            "state": "complete",
            "comparison_plan": plan.document,
            "comparison_plan_sha256": plan.fingerprint,
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
    capture_parser.add_argument("--cohort", choices=("legacy", "ordered"), default="legacy")
    capture_parser.add_argument("--prior-capture", type=Path)
    capture_parser.add_argument("--prior-captures", type=Path, action="append", default=[])
    capture_parser.add_argument("--arm", action="append", dest="arms")
    score_parser = sub.add_parser("score")
    score_parser.add_argument("--captures", type=Path, required=True)
    score_parser.add_argument("--reviews", type=Path, required=True)
    score_parser.add_argument("--output", type=Path, required=True)
    score_parser.add_argument("--references", type=Path, default=REFERENCES)
    score_parser.add_argument("--prior-captures", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.command == "capture":
        capture(
            args.admin_url,
            args.output,
            args.tracking_uri,
            args.maximum_additional_usd,
            args.cohort,
            args.prior_capture,
            args.arms,
            tuple(args.prior_captures),
        )
    else:
        score(args.captures, args.reviews, args.output, args.references, tuple(args.prior_captures))


if __name__ == "__main__":
    main()
