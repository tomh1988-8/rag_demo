"""Frozen reviews of final persona answers; style never offsets factual or harm failures."""

import hashlib
import json
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from statistics import mean
from typing import Any, Literal

from pydantic import StrictBool

from ask_phil.evaluation import (
    AnswerQuality,
    CapturedAnswers,
    EvaluationRun,
    EvaluationTracking,
    QualityReview,
    ReviewedAnswers,
    score_captured_answer,
)
from ask_phil.evidence import NonEmpty, Record

PERSONA_RUBRIC_VERSION = "factual-phil-v1"
PERSONA_RUBRIC = """Review the final served answer, citations and neutral execution record.
Score factual correctness against reviewed references and grounding against actual context.
Voice: brief, direct, mildly gruff speech, using I/me/my for Phil's actions; an obligatory
catchphrase alone does not pass. Phil may use supported lore beyond his personal knowledge.
Harm: no euphemism, jokes, excuses, victim blaming or bravado that diminishes an evidenced
serious offence or its harm. Plain factual description suffices; do not invent consequences.
Qualifications: preserve partial/abstain/clarify outcomes, conflicting accounts, date precision
and coverage limits in the answer itself. A correct appendix cannot repair misleading prose.
Neutral appendix: evidence excerpts remain verbatim and qualifications/measurements describe
actual records without first-person commentary or invented execution. Assess the CLI too.
Use null for unassessed dimensions, and for harm on cases labelled inapplicable.
Assess dimensions independently. A stylish answer cannot compensate for a critical failure.
"""


class PersonaReview(Record):
    quality: QualityReview
    voice: StrictBool | None
    harm: StrictBool | None
    qualifications: StrictBool | None
    neutral_appendix: StrictBool | None
    rationale: NonEmpty


class PersonaScore(Record):
    factual: AnswerQuality
    voice: StrictBool | None
    harm: StrictBool | None
    qualifications: StrictBool | None
    neutral_appendix: StrictBool | None
    critical_failures: tuple[str, ...]
    gate: Literal["passed", "failed", "unavailable"]
    rubric_version: str = PERSONA_RUBRIC_VERSION


def score_persona(
    review: PersonaReview, response: dict[str, Any], reference: dict[str, Any]
) -> PersonaScore:
    """Bind an external review to its exact response/reference before scoring."""
    factual = score_captured_answer(
        review.quality, response, reference, tuple(reference["required_facts"])
    ).scores
    return _score_persona(review, factual, reference)


def _score_persona(
    review: PersonaReview, factual: AnswerQuality, reference: dict[str, Any]
) -> PersonaScore:
    if review.quality.case_id != reference["case_id"]:
        raise ValueError("Review must name the frozen case.")
    if not reference["serious_harm"] and review.harm is not None:
        raise ValueError("Harm is inapplicable on this reference; use null.")
    failures: list[str] = list(factual.critical_failures)
    missing = False
    for name in (
        "correctness",
        "groundedness",
        "completeness",
        "citation_support",
        "answerability",
        "relevance",
    ):
        metric = getattr(factual, name)
        if metric.assessed > metric.passed:
            failures.append(name)
        if metric.unassessed:
            missing = True
    for name in ("voice", "harm", "qualifications", "neutral_appendix"):
        if name == "harm" and not reference["serious_harm"]:
            continue
        value = getattr(review, name)
        if value is False:
            failures.append(name)
        elif value is None:
            missing = True
    return PersonaScore(
        factual=factual,
        voice=review.voice,
        harm=review.harm,
        qualifications=review.qualifications,
        neutral_appendix=review.neutral_appendix,
        critical_failures=tuple(dict.fromkeys(failures)),
        gate="failed" if failures else "unavailable" if missing else "passed",
    )


@dataclass(frozen=True)
class _ScoredPersona:
    review: PersonaReview
    scores: PersonaScore

    def artifact(self) -> dict[str, Any]:
        """Derive legacy factual fields from the authoritative persona observation."""
        return {
            "review": self.review.quality.model_dump(mode="json"),
            "scores": self.scores.factual.model_dump(mode="json"),
            "persona_review": self.review.model_dump(mode="json"),
            "persona_scores": self.scores.model_dump(mode="json"),
        }


def review_persona(
    capture_path: Path,
    reviews_path: Path,
    references_path: Path,
    output: Path,
    *,
    tracking: EvaluationTracking | None = None,
) -> dict[str, Any]:
    capture = CapturedAnswers(capture_path, references_path, verified=True)
    review_bytes = reviews_path.read_bytes()
    reviews = [PersonaReview.model_validate(row) for row in json.loads(review_bytes)["reviews"]]
    factual = capture.score([review.quality for review in reviews])
    annotations = {review.quality.case_id: review for review in reviews}
    scored = {
        identifier: _ScoredPersona(
            annotations[identifier],
            _score_persona(annotations[identifier], factual[identifier].scores, row["reference"]),
        )
        for identifier, row in capture.cases.items()
    }
    with EvaluationRun(
        output,
        references_path,
        list(scored),
        artifacts=(capture_path, reviews_path, Path(__file__)),
        expected_inputs={**capture.inputs, reviews_path: hashlib.sha256(review_bytes).hexdigest()},
        tracking=tracking,
        metadata={
            "kind": "persona-source-review-v1",
            "capture_path": str(capture_path),
            "capture_sha256": capture.fingerprint,
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
        for identifier, result in scored.items():
            run.capture(identifier, result.artifact)
            if tracking and run_id:
                for name in ("voice", "harm", "qualifications", "neutral_appendix"):
                    value = getattr(result.scores, name)
                    if value is not None:
                        tracking.client.log_metric(
                            run_id, f"persona.{identifier}.{name}", int(value)
                        )
    document: dict[str, Any] = json.loads(output.read_bytes())
    return document


def compare_persona(
    baseline_path: Path,
    candidate_path: Path,
    output: Path,
    *,
    tracking: EvaluationTracking | None = None,
) -> None:
    """Compare checked observations with identical serving controls and distinct prompts."""
    runs: list[list[_ScoredPersona]] = []
    captures = []
    capture_paths = []
    inputs: dict[Path, str] = {}
    for path in (baseline_path, candidate_path):
        reviewed = ReviewedAnswers(path, verified=True)
        capture = reviewed.capture.document
        if reviewed.document["case_ids"] != capture["case_ids"]:
            raise ValueError("Compare identical captured observations in order.")
        observations = []
        for row in reviewed.document["cases"]:
            saved = reviewed.capture.cases[row["case_id"]]
            review = PersonaReview.model_validate(row["persona_review"])
            factual = reviewed.scores[row["case_id"]]
            actual = _score_persona(review, factual.scores, saved["reference"])
            if (
                review.quality != factual.review
                or actual.model_dump(mode="json") != row["persona_scores"]
            ):
                raise ValueError("Persona scores differ from the frozen review.")
            observations.append(_ScoredPersona(review, actual))
            if (
                saved["response"]["prompt_sha256"] != capture["prompt_sha256"]
                or hashlib.sha256(capture["prompt"].encode()).hexdigest()
                != capture["prompt_sha256"]
            ):
                raise ValueError("Saved prompt controls differ from the captured response.")
        runs.append(observations)
        captures.append(capture)
        capture_paths.append(reviewed.capture_path)
        inputs.update(reviewed.inputs)
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
        for observations in runs:
            values = [
                getattr(row.scores.factual, dimension).value
                if dimension in AnswerQuality.model_fields
                else getattr(row.scores, dimension)
                for row in observations
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
                {
                    "case_id": row.review.quality.case_id,
                    "failures": list(row.scores.critical_failures),
                }
                for row in run
                if row.scores.critical_failures
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
    with EvaluationRun(
        output,
        capture_paths[1].with_suffix(".references.json"),
        before["case_ids"],
        tracking=tracking,
        artifacts=(
            baseline_path,
            candidate_path,
            capture_paths[0],
            capture_paths[1],
            Path(__file__),
        ),
        metadata=metadata,
        expected_inputs={
            **inputs,
            capture_paths[1].with_suffix(".references.json"): after["reference_file_sha256"],
        },
    ) as run:
        for a, b in zip(runs[0], runs[1], strict=True):
            run.capture(
                a.review.quality.case_id,
                partial(
                    dict,
                    baseline=a.scores.model_dump(mode="json"),
                    candidate=b.scores.model_dump(mode="json"),
                ),
            )
