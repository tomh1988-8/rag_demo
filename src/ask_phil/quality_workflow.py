"""Public API capture and frozen-review conversion for quality comparisons."""

import hashlib
import json
import os
import subprocess
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import TypeAdapter

from ask_phil.answering import application_fingerprint
from ask_phil.answers import SYSTEM_PROMPT, AnswerReceipt
from ask_phil.evaluation import (
    EvaluationRun,
    EvaluationTracking,
    QualityReview,
    RetrievalReference,
    document_fingerprint,
    score_captured_answer,
    score_retrieval,
)
from ask_phil.evidence import Identifier
from ask_phil.models import OpenRouterSettings
from ask_phil.openrouter import maximum_call_cost
from ask_phil.quality_comparison import (
    ComparisonConfiguration,
    ComparisonDataset,
    ComparisonObservation,
    ComparisonRun,
)

if TYPE_CHECKING:
    from mlflow import MlflowClient


def capture_quality(
    references: Path,
    output: Path,
    client: httpx.Client,
    *,
    repeats: int,
    namespace: str,
    private_directory: Path,
    max_cost_usd: Decimal | int,
    profile: OpenRouterSettings | None = None,
    tracking: EvaluationTracking | None = None,
    serving_tracking: "MlflowClient | None" = None,
) -> None:
    dataset = ComparisonDataset.model_validate_json(references.read_bytes())
    TypeAdapter(Identifier).validate_python(namespace)
    if any(case.split != "development" for case in dataset.cases):
        raise ValueError("Public comparison capture selects development cases only.")
    if not 1 <= repeats <= 3 or not 0 <= max_cost_usd <= 1:
        raise ValueError("Choose 1–3 repeats and a slice budget of $0–$1.")
    if output.exists():
        raise FileExistsError("Retain existing captures; choose a fresh path.")
    expanded = []
    for repeat in range(repeats):
        for case in dataset.cases:
            expanded.append(
                {
                    **case.model_dump(mode="json"),
                    "case_id": f"{case.case_id}-r{repeat}",
                    "comparison_case_id": case.case_id,
                    "repeat": repeat,
                }
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    expanded_path = output.with_suffix(".references.json")
    with expanded_path.open("x") as destination:
        json.dump({"dataset_id": dataset.dataset_id, "cases": expanded}, destination, indent=2)
        destination.write("\n")
    private_directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    private_directory.chmod(0o700)
    cost = Decimal(0)
    maximum_call = maximum_call_cost(profile) if profile else Decimal(0)
    sessions: dict[tuple[int, str], tuple[str, dict[str, str]]] = {}
    cases = {case.case_id: case for case in dataset.cases}
    configuration: ComparisonConfiguration | None = None
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    frozen_application = application_fingerprint()
    with EvaluationRun(
        output,
        expanded_path,
        [row["case_id"] for row in expanded],
        tracking=tracking,
        artifacts=(references, Path("uv.lock"), Path(__file__)),
        metadata={
            "kind": "public-api-quality-development-capture-v1",
            "dataset_sha256": dataset.fingerprint,
            "cache_mode": "off",
            "cache_namespace": namespace,
            "code_revision": revision,
            "application_sha256": frozen_application,
            "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
            "expenditure_category": "serving",
            "cost_usd": "0",
            "model_calls": 0,
        },
    ) as run:
        calls = 0

        def execute(row: dict[str, Any]) -> dict[str, Any]:
            nonlocal cost, calls, configuration
            if cost + maximum_call > max_cost_usd:
                raise ValueError("Slice budget cannot reserve another bounded serving call.")
            session_key = row["repeat"], row.get("session") or row["comparison_case_id"]
            if session_key not in sessions:
                created = client.post("/v1/sessions")
                created.raise_for_status()
                receipt = created.json()
                _private_json(private_directory / (row["case_id"] + ".session.json"), receipt)
                sessions[session_key] = (
                    "/v1/sessions/" + receipt["session"]["session_id"] + "/turns",
                    {"Authorization": "Bearer " + receipt["session_token"]},
                )
            path, headers = sessions[session_key]
            result = client.post(
                path,
                headers=headers,
                json={"question": row["question"], "snapshot_id": row["snapshot_id"]},
            )
            result.raise_for_status()
            receipt_value = AnswerReceipt.model_validate(result.json())
            _private_json(
                private_directory / (row["case_id"] + ".json"),
                receipt_value.model_dump(mode="json"),
            )
            response = receipt_value.response
            usage = response.provider_usage
            if response.estimated_api_cost_usd is None:
                run.annotate(
                    cost_usd=None,
                    known_cost_usd=str(cost),
                    failed_call_usage=usage.model_dump(mode="json") if usage else None,
                )
                raise ValueError("Unknown serving cost; retain the reservation and stop.")
            cost += Decimal(str(response.estimated_api_cost_usd))
            calls += int(usage is not None)
            run.annotate(cost_usd=str(cost), model_calls=calls)
            if response.snapshot_id != row["snapshot_id"]:
                raise ValueError("The public API answered from a different snapshot.")
            if response.application_sha256 != frozen_application:
                raise ValueError("Serving code changed or differs from the frozen source identity.")
            if response.model_settings is None:
                raise ValueError("This comparison requires a text answer model configuration.")
            actual = ComparisonConfiguration(
                configuration_id="single-query-uncached-v2",
                retrieval_version="original-query-v1",
                context_version="whole-passages-v2",
                context_bytes=1200,
                retrieval_k=3,
                answer_settings_sha256=document_fingerprint(
                    response.model_settings.model_dump(mode="json")
                ),
                prompt_sha256=response.prompt_sha256,
                snapshot_sha256=response.snapshot_sha256,
                cache_mode="off",
                cache_namespace=namespace,
            )
            if profile is not None and response.model_settings != profile:
                raise ValueError("The public API is not using the frozen model profile.")
            if profile is None and usage is not None:
                raise ValueError("Supply the paid model profile before live capture.")
            if response.baseline_version != "single-query-uncached-v2":
                raise ValueError("Capture requires the declared uncached single-query baseline.")
            if response.retrieval_k not in (0, 3):
                raise ValueError("Unexpected retrieval limit in the recorded response.")
            if configuration is not None and configuration != actual:
                raise ValueError("Serving controls changed during the frozen capture.")
            configuration = actual
            run.annotate(configuration=actual.model_dump(mode="json"))
            reference = RetrievalReference(
                case_id=row["comparison_case_id"],
                question=row["question"],
                answerable=row["expected_status"] in ("answered", "partial"),
                relevant_ids=tuple(p["evidence_id"] for p in row["evidence"]),
                required_facts=cases[row["comparison_case_id"]].required_facts,
            )
            stages: dict[str, float | None] = {
                "text_retrieval": None,
                "assembled_context": None,
                "answer_model": None,
            }
            if serving_tracking:
                trace = serving_tracking.get_trace(response.trace_id, flush=True)
                if trace is not None:
                    for span in trace.data.spans:
                        if span.name in stages and span.end_time_ns is not None:
                            stages[span.name] = (span.end_time_ns - span.start_time_ns) / 1_000_000
            return {
                "response": response.model_dump(mode="json"),
                "stage_ms": stages,
                "retrieval_score": score_retrieval(
                    reference,
                    tuple(h.passage.evidence_id for h in response.retrieved),
                    tuple(p.evidence_id for p in response.context),
                    k=3,
                ).model_dump(mode="json"),
            }

        for row in expanded:
            run.capture(row["case_id"], partial(execute, row))


def reviewed_comparison_run(
    dataset: ComparisonDataset, capture_path: Path, review_path: Path
) -> ComparisonRun:
    capture = json.loads(capture_path.read_bytes())
    review = json.loads(review_path.read_bytes())
    if capture["state"] != "complete" or review["state"] != "complete":
        raise ValueError("Both capture and frozen review must be complete.")
    if review["capture_sha256"] != hashlib.sha256(capture_path.read_bytes()).hexdigest():
        raise ValueError("The review belongs to a different capture.")
    if capture["dataset_sha256"] != dataset.fingerprint:
        raise ValueError("The capture belongs to a different frozen dataset.")
    scored = {row["case_id"]: row for row in review["cases"]}
    if len(scored) != len(review["cases"]) or set(scored) != set(capture["case_ids"]):
        raise ValueError("Review every captured observation exactly once.")
    if [row["case_id"] for row in capture["cases"]] != capture["case_ids"]:
        raise ValueError("Capture must contain its declared observations once in order.")
    for row in capture["cases"]:
        if row.get("state") != "complete":
            raise ValueError("Every captured observation must be complete.")
        annotation = QualityReview.model_validate(scored[row["case_id"]]["review"])
        original = row["reference"]
        checked = score_captured_answer(
            annotation,
            row["response"],
            original,
            tuple(fact["fact"] for fact in original["required_facts"]),
        )
        if checked.scores.model_dump(mode="json") != scored[row["case_id"]]["scores"]:
            raise ValueError("Recorded scores differ from their frozen review.")
        if document_fingerprint(row["response"]) != row["response_sha256"]:
            raise ValueError("The captured response fingerprint differs.")
    return ComparisonRun(
        dataset_sha256=dataset.fingerprint,
        code_revision=capture["code_revision"],
        application_sha256=capture["application_sha256"],
        configuration=ComparisonConfiguration.model_validate(capture["configuration"]),
        observations=tuple(
            ComparisonObservation(
                case_id=row["reference"]["comparison_case_id"],
                repeat=row["reference"]["repeat"],
                response_sha256=row["response_sha256"],
                quality=scored[row["case_id"]]["scores"],
                retrieval=row["retrieval_score"],
                serving_cost_usd=row["response"]["estimated_api_cost_usd"],
                elapsed_ms=row["response"]["elapsed_ms"],
                stage_ms=row["stage_ms"],
            )
            for row in capture["cases"]
        ),
    )


def _private_json(path: Path, document: dict[str, Any]) -> None:
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as output:
        json.dump(document, output)
