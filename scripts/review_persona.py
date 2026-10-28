"""Score frozen final-answer persona reviews without regenerating answers."""

import argparse
import hashlib
import json
import os
from functools import partial
from pathlib import Path
from statistics import mean
from typing import Any

from mlflow import MlflowClient

from ask_phil.evaluation import EvaluationRun, EvaluationTracking, document_fingerprint
from ask_phil.persona_evaluation import (
    PERSONA_RUBRIC,
    PERSONA_RUBRIC_VERSION,
    PersonaReview,
    score_persona,
)


def score(
    capture_path: Path, reviews_path: Path, references_path: Path, output: Path
) -> dict[str, Any]:
    capture = json.loads(capture_path.read_bytes())
    reference_list = json.loads(references_path.read_bytes())["cases"]
    references = {c["case_id"]: c for c in reference_list}
    if len(references) != len(reference_list) or capture["state"] != "complete":
        raise ValueError("Review complete captures with unique frozen references.")
    if capture["reference_file_sha256"] != hashlib.sha256(references_path.read_bytes()).hexdigest():
        raise ValueError("Capture differs from the frozen reference file.")
    identifiers = [row["case_id"] for row in capture["cases"]]
    if (
        identifiers != capture["case_ids"]
        or len(set(identifiers)) != len(identifiers)
        or set(identifiers) != references.keys()
    ):
        raise ValueError("Review every declared captured case exactly once.")
    reviews = [
        PersonaReview.model_validate(row)
        for row in json.loads(reviews_path.read_bytes())["reviews"]
    ]
    annotations = {r.quality.case_id: r for r in reviews}
    if len(annotations) != len(reviews) or annotations.keys() != references.keys():
        raise ValueError("Provide one persona review per captured response.")
    scored = []
    for row in capture["cases"]:
        reference = references[row["case_id"]]
        response = row["response"]
        if (
            row["state"] != "complete"
            or row.get("verification_state") != "complete"
            or row["reference"] != reference
            or row["reference_sha256"] != document_fingerprint(reference)
            or row["response_sha256"] != document_fingerprint(response)
            or row.get("cli_response") != response
            or row.get("trace_response") != response
        ):
            raise ValueError("Persona capture lacks matching verified final API/CLI/trace records.")
        review = annotations[row["case_id"]]
        result = score_persona(review, response, reference)
        scored.append(
            {
                "review": review.quality.model_dump(mode="json"),
                "scores": result.factual.model_dump(mode="json"),
                "persona_review": review.model_dump(mode="json"),
                "persona_scores": result.model_dump(mode="json"),
            }
        )
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    tracking = (
        EvaluationTracking(
            MlflowClient(tracking_uri=tracking_uri),
            "ask-phil-persona-evaluation",
            {"kind": "persona-source-review", "expenditure_category": "offline_evaluation"},
        )
        if tracking_uri
        else None
    )
    with EvaluationRun(
        output,
        references_path,
        identifiers,
        artifacts=(capture_path, reviews_path, Path(__file__)),
        tracking=tracking,
        metadata={
            "kind": "persona-source-review-v1",
            "capture_path": str(capture_path),
            "capture_sha256": hashlib.sha256(capture_path.read_bytes()).hexdigest(),
            "reviews_path": str(reviews_path),
            "rubric_version": PERSONA_RUBRIC_VERSION,
            "rubric": PERSONA_RUBRIC,
            "reviewer_type": "AGENT",
            "human_adjudicated": False,
            "expenditure_category": "offline_evaluation",
            "model_calls": 0,
            "cost_usd": "0",
        },
    ) as run:
        run_id = json.loads(output.read_bytes()).get("run_id")
        for identifier, scored_row in zip(identifiers, scored, strict=True):
            run.capture(identifier, partial(dict, scored_row))
            if tracking and run_id:
                for name in ("voice", "harm", "qualifications", "neutral_appendix"):
                    value = scored_row["persona_scores"][name]
                    if value is not None:
                        tracking.client.log_metric(
                            run_id, f"persona.{identifier}.{name}", int(value)
                        )
    document: dict[str, Any] = json.loads(output.read_bytes())
    return document


def compare(baseline_path: Path, candidate_path: Path, output: Path) -> None:
    """Compare reviewed saved observations only when the serving controls agree."""
    runs = []
    captures = []
    for path in (baseline_path, candidate_path):
        scored = json.loads(path.read_bytes())
        capture_path = Path(scored["capture_path"])
        capture = json.loads(capture_path.read_bytes())
        if (
            scored["state"] != "complete"
            or capture["state"] != "complete"
            or scored["capture_sha256"] != hashlib.sha256(capture_path.read_bytes()).hexdigest()
            or scored["case_ids"] != capture["case_ids"]
        ):
            raise ValueError("Compare complete reviews bound to their captured answers.")
        for row, saved in zip(scored["cases"], capture["cases"], strict=True):
            actual = score_persona(
                PersonaReview.model_validate(row["persona_review"]),
                saved["response"],
                saved["reference"],
            )
            if actual.model_dump(mode="json") != row["persona_scores"]:
                raise ValueError("Persona scores differ from the frozen review.")
            if (
                saved["response"]["prompt_sha256"] != capture["prompt_sha256"]
                or hashlib.sha256(capture["prompt"].encode()).hexdigest()
                != capture["prompt_sha256"]
            ):
                raise ValueError("Saved prompt controls differ from the captured response.")
        runs.append(scored)
        captures.append(capture)
    before, after = captures
    if before["case_ids"] != after["case_ids"] or before["prompt_sha256"] == after["prompt_sha256"]:
        raise ValueError("A prompt comparison needs identical observations and distinct prompts.")
    controls = (
        "question",
        "snapshot_id",
        "snapshot_sha256",
        "model_settings",
        "context",
        "retrieval_k",
        "baseline_version",
        "route",
    )
    for a, b in zip(before["cases"], after["cases"], strict=True):
        if a["reference"] != b["reference"] or any(
            a["response"][key] != b["response"][key] for key in controls
        ):
            raise ValueError(
                "Persona comparison controls differ; do not attribute changes to style."
            )
    dimensions: dict[str, Any] = {}
    for dimension in (
        "correctness",
        "groundedness",
        "completeness",
        "citation_support",
        "answerability",
        "relevance",
        "voice",
        "harm",
        "qualifications",
        "neutral_appendix",
    ):
        groups = []
        for run in runs:
            values = [
                row["scores"][dimension]["value"]
                if dimension in row["scores"]
                else row["persona_scores"][dimension]
                for row in run["cases"]
            ]
            known = [v for v in values if v is not None]
            groups.append(
                {
                    "mean": mean(known) if known else None,
                    "assessed_observations": len(known),
                    "unavailable_observations": len(values) - len(known),
                }
            )
        dimensions[dimension] = {"baseline": groups[0], "candidate": groups[1]}
    metadata: dict[str, Any] = {
        "kind": "controlled-persona-prompt-comparison-v1",
        "changed_factor": "persona_prompt",
        "controls_match": True,
        "dimensions": dimensions,
        "observations_per_variant": len(before["cases"]),
        "critical_failures": {
            role: [
                {"case_id": row["case_id"], "failures": row["persona_scores"]["critical_failures"]}
                for row in run["cases"]
                if row["persona_scores"]["critical_failures"]
            ]
            for role, run in zip(("baseline", "candidate"), runs, strict=True)
        },
        "observed_variation": {},
        "cost_and_latency": {},
        "limitation": "Exposed source-based agent reviews and two repeats, not human-adjudicated "
        "canon or held-out acceptance. No composite score hides critical failures. "
        "The outside-knowledge reference includes an unrequested Jane fact; its "
        "conservative coverage failure remains separate from killer identification.",
        "model_calls": 0,
        "cost_usd": "0",
        "expenditure_category": "offline_evaluation",
    }
    for role, capture in zip(("baseline", "candidate"), captures, strict=True):
        responses = [r["response"] for r in capture["cases"]]
        supported = [r for r in responses if r["status"] in {"answered", "partial"}]
        metadata["observed_variation"][role] = {
            "mandated_opener_count": sum(
                r["answer"].startswith("Right, listen.") for r in supported
            ),
            "supported_replies": len(supported),
            "per_case": {
                name: {
                    "distinct_answers": len(
                        {
                            r["response"]["answer"]
                            for r in capture["cases"]
                            if r["case_id"].rsplit("-r", 1)[0] == name
                        }
                    ),
                    "repeats": sum(
                        r["case_id"].rsplit("-r", 1)[0] == name for r in capture["cases"]
                    ),
                }
                for name in dict.fromkeys(r["case_id"].rsplit("-r", 1)[0] for r in capture["cases"])
            },
        }
        costs = [r["estimated_api_cost_usd"] for r in responses]
        metadata["cost_and_latency"][role] = {
            "reported_serving_cost_usd": sum(costs) if all(c is not None for c in costs) else None,
            "mean_response_elapsed_ms": mean(r["elapsed_ms"] for r in responses),
            "actual_model_calls": sum(r["execution"]["model_calls"] for r in responses),
        }
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    tracking = (
        EvaluationTracking(
            MlflowClient(tracking_uri=tracking_uri),
            "ask-phil-persona-evaluation",
            {"kind": "persona-comparison", "expenditure_category": "offline_evaluation"},
        )
        if tracking_uri
        else None
    )
    with EvaluationRun(
        output,
        Path(runs[1]["capture_path"]).with_suffix(".references.json"),
        before["case_ids"],
        tracking=tracking,
        artifacts=(
            baseline_path,
            candidate_path,
            Path(runs[0]["capture_path"]),
            Path(runs[1]["capture_path"]),
            Path(__file__),
        ),
        metadata=metadata,
    ) as run:
        for a, b in zip(runs[0]["cases"], runs[1]["cases"], strict=True):
            run.capture(
                a["case_id"],
                partial(dict, baseline=a["persona_scores"], candidate=b["persona_scores"]),
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    assess = commands.add_parser("score")
    assess.add_argument("--capture", type=Path, required=True)
    assess.add_argument("--reviews", type=Path, required=True)
    assess.add_argument("--references", type=Path, required=True)
    assess.add_argument("--output", type=Path, required=True)
    comparison = commands.add_parser("compare")
    comparison.add_argument("--baseline", type=Path, required=True)
    comparison.add_argument("--candidate", type=Path, required=True)
    comparison.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a fresh output path; retain existing reviews.")
    if args.command == "score":
        result = score(args.capture, args.reviews, args.references, args.output)
        print(f"Scored {len(result['cases'])} final persona responses without model calls.")
    else:
        compare(args.baseline, args.candidate, args.output)
        print("Saved the controlled persona comparison without model calls.")


if __name__ == "__main__":
    main()
