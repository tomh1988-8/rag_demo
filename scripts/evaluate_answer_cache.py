"""Capture a bounded development cold/warm workload, then summarize independent reviews.

Use a new empty PostgreSQL cache namespace and a separate development workload.
The serving app and this recorder must share the local MLflow backend. Capture
refuses an existing output directory; reviewing saved outcomes never calls models.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from mlflow import MlflowClient

from ask_phil.answers import AnswerReceipt
from ask_phil.cache_evaluation import CacheObservation, summarize_cache_workload
from ask_phil.evaluation import document_fingerprint
from ask_phil.openrouter import OpenRouterProfile, maximum_call_cost


def save(path: Path, document: object) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n")


def summarize(directory: Path, reviews: Path | None) -> dict[str, Any]:
    rows = json.loads((directory / "captures.json").read_bytes())
    labels = json.loads(reviews.read_bytes()) if reviews else {}
    observations = []
    for row in rows:
        raw = dict(row["observation"])
        label = labels.get(row["case_id"], {})
        if label and not label.get("review_note"):
            raise ValueError("Every supplied review needs an evidence-based rationale.")
        raw.update({key: label[key] for key in ("supported", "compatible") if key in label})
        observations.append(CacheObservation.model_validate(raw))
    report = {
        "version": "cache-workload-v1",
        "captures_sha256": document_fingerprint(rows),
        "reviews_sha256": document_fingerprint(labels) if reviews else None,
        "all": summarize_cache_workload(observations).model_dump(mode="json"),
        "phases": {
            phase: summarize_cache_workload(
                [r for r in observations if r.phase == phase]
            ).model_dump(mode="json")
            for phase in ("cold", "warm", "control")
        },
        "cases": {
            row["case_id"]: observation.model_dump(mode="json")
            for row, observation in zip(rows, observations, strict=True)
        },
    }
    save(directory / ("reviewed-summary.json" if reviews else "summary.json"), report)
    return report


def capture(args: argparse.Namespace) -> None:
    plan = json.loads(args.workload.read_bytes())
    requests = plan["requests"]
    if (
        plan.get("partition") != "development"
        or not isinstance(plan.get("namespace"), str)
        or not requests
        or len(requests) > 20
        or len({r["case_id"] for r in requests}) != len(requests)
        or not 0 < args.max_cost_usd <= 0.5
    ):
        raise ValueError("Use a named, isolated development plan of at most 20 requests and $0.50.")
    profile = OpenRouterProfile.model_validate_json(args.profile.read_bytes())
    maximum = float(maximum_call_cost(profile))
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "plan.json", plan)
    save(args.output / "profile.json", profile.model_dump(mode="json"))
    tracking = MlflowClient(tracking_uri=args.tracking_uri)
    sessions: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    spent = 0.0
    identity = None
    with httpx.Client(base_url=args.api_url, timeout=210, trust_env=False) as client:
        for selected in requests:
            if spent + maximum > args.max_cost_usd:
                raise ValueError("Workload cannot reserve another bounded answer call.")
            request = dict(selected["request"])
            if request.get("route", "auto") not in {"text_rag", "auto"}:
                raise ValueError(
                    "This workload records conventional text and clarification controls."
                )
            path = "/v1/answers"
            headers = {}
            if selected.get("session"):
                name = selected["session"]
                if name not in sessions:
                    created = client.post("/v1/sessions")
                    created.raise_for_status()
                    sessions[name] = created.json()
                session = sessions[name]
                path = "/v1/sessions/" + session["session"]["session_id"] + "/turns"
                headers = {"Authorization": "Bearer " + session["session_token"]}
            began = time.perf_counter()
            reply = client.post(path, headers=headers, json=request)
            reply.raise_for_status()
            receipt = AnswerReceipt.model_validate(reply.json())
            elapsed = (time.perf_counter() - began) * 1000
            response = receipt.response
            if response.cache is None:
                raise ValueError("The response lacks cache measurements.")
            observation = CacheObservation(
                phase=selected["phase"],
                delivery=response.cache,
                elapsed_ms=response.elapsed_ms,
                end_to_end_ms=elapsed,
                cost_usd=response.estimated_api_cost_usd,
                generation_id=response.generation_id or response.response_id,
            )
            row = {
                "case_id": selected["case_id"],
                "request": request,
                "response": response.model_dump(mode="json"),
                "observation": observation.model_dump(mode="json"),
            }
            rows.append(row)
            # Preserve every actual result before checking its interpretation.
            save(args.output / "captures.json", rows)
            if (
                response.model_settings is not None
                and OpenRouterProfile.model_validate(
                    response.model_settings.model_dump(mode="json"), extra="ignore"
                )
                != profile
            ):
                raise ValueError("The observed model differs from the frozen workload profile.")
            trace = tracking.get_trace(response.trace_id, flush=True)
            root = trace.data.spans[0]
            if root.outputs != response.model_dump(mode="json"):
                raise ValueError("Serving trace differs from the actual public response.")
            if root.attributes.get("cache_namespace") != plan["namespace"]:
                raise ValueError("The app is not using this isolated workload namespace.")
            current = (response.application_sha256, response.snapshot_sha256, response.publication)
            identity = identity or current
            if current != identity or (
                selected["phase"] == "cold" and response.cache.status == "hit"
            ):
                raise ValueError(
                    "The workload changed identity or its cold cache was already warm."
                )
            for citation in response.citations:
                resolved = client.get(citation.resolve_path)
                resolved.raise_for_status()
                if not any(
                    p["sha256"] == citation.sha256 and p["text"] == citation.text
                    for p in resolved.json()["matches"]
                ):
                    raise ValueError(
                        "A served citation does not resolve to its recorded source span."
                    )
            row["trace_and_citations_verified"] = True
            save(args.output / "captures.json", rows)
            if response.estimated_api_cost_usd is None:
                raise ValueError("Unknown expense must be reconciled before another request.")
            spent += response.estimated_api_cost_usd
            if response.text_pipeline and response.text_pipeline.policy.mode != "baseline":
                raise ValueError("This initial workload budget permits only baseline answer calls.")
    summarize(args.output, None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--tracking-uri",
        default=os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db"),
    )
    parser.add_argument("--workload", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--profile", type=Path, default=Path("config/openrouter-sol.json"))
    parser.add_argument("--max-cost-usd", type=float, default=0.25)
    parser.add_argument("--summarize", type=Path)
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    try:
        if args.summarize:
            print(json.dumps(summarize(args.summarize, args.reviews)["all"], indent=2))
        elif args.workload and args.output:
            capture(args)
        else:
            parser.error("Supply --workload and --output, or --summarize.")
    except (ValueError, OSError, httpx.HTTPError):
        print(
            "Workload stopped; preserve captured outcomes and investigate before retrying.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
