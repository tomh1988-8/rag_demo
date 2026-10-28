"""Frozen reviews of final persona answers; style never offsets factual or harm failures."""

from typing import Any, Literal

from pydantic import StrictBool

from ask_phil.evaluation import AnswerQuality, QualityReview, score_captured_answer
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
    if review.quality.case_id != reference["case_id"]:
        raise ValueError("Review must name the frozen case.")
    if not reference["serious_harm"] and review.harm is not None:
        raise ValueError("Harm is inapplicable on this reference; use null.")
    factual = score_captured_answer(
        review.quality, response, reference, tuple(reference["required_facts"])
    ).scores
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
