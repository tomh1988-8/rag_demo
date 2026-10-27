"""Source-anchored crime/justice values and diagnostic projections, separate from grounding."""

from collections import Counter
from collections.abc import Sequence

from pydantic import Field

from ask_phil.claims import evidence_resolves
from ask_phil.classified_facts import ContextClaim
from ask_phil.evidence import Record, SourceSnapshot
from ask_phil.parentage_evaluation import ExtractionScore
from ask_phil.story_events import EventClaim, ExtractedEvents

Key = tuple[object, ...]


class ValueScore(Record):
    expected: int
    predicted: int | None = None
    true_positive: int | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None


class EventScore(ExtractionScore):
    dimensions: dict[str, ValueScore]
    by_event_type: dict[str, ExtractionScore]
    context_score: ExtractionScore | None = None
    by_theme: dict[str, ExtractionScore] = Field(default_factory=dict)
    by_classification: dict[str, ExtractionScore] = Field(default_factory=dict)
    scope: str = (
        "Exposed selected incidents and in-catalogue assertions only. Exact values include "
        "participant-role assignment, event type, basis, account status, polarity, certainty, "
        "story time/precision and evidence IDs. Ignore arbitrary claim/event ID spelling and "
        "label wording; incident grouping requires separate support review. Full-value duplicates "
        "collapse. Each dimension projects unique full assertions onto values plus passage IDs "
        "and event type, preserving multiplicity: identity sets, role multisets, assigned "
        "identity-role pairs (direction), polarity, timing, or account attribution. These are "
        "diagnostics, not independent per-claim accuracies. Grounding separately requires exact "
        "resolvable locators covering frozen supporting spans; it is not canon adjudication. "
        "Text classifications are scored separately by kind, character subjects, theme and "
        "passage IDs; classification-gap wording is source-reviewed rather than exact-matched. "
        "A text classification never counts as an event or connection."
    )


def _values(expected: Counter[Key], predicted: Counter[Key]) -> ValueScore:
    correct = (expected & predicted).total()
    precision = correct / predicted.total() if predicted else (0.0 if expected else 1.0)
    recall = correct / expected.total() if expected else 1.0
    return ValueScore(
        expected=expected.total(),
        predicted=predicted.total(),
        true_positive=correct,
        precision=precision,
        recall=recall,
        f1=2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    )


def _dimensions(claim: EventClaim) -> dict[str, Key]:
    anchor = (claim.event_type, tuple(sorted({e.evidence_id for e in claim.evidence})))
    return {
        "identity": (*anchor, tuple(sorted({p.character_id for p in claim.participants}))),
        "role": (*anchor, tuple(sorted(p.role for p in claim.participants))),
        "direction": (*anchor, tuple(sorted((p.character_id, p.role) for p in claim.participants))),
        "negation": (*anchor, claim.polarity),
        "timing": (*anchor, claim.story_time, claim.time_precision),
        "account": (*anchor, claim.basis, claim.account_status, claim.certainty),
    }


def _score_claims(
    reference: Sequence[EventClaim | ContextClaim],
    claims: Sequence[EventClaim | ContextClaim],
    snapshot: SourceSnapshot,
) -> ExtractionScore:
    expected = {c.assertion: c for c in reference}
    predicted = {c.assertion: c for c in claims}
    values = _values(Counter(expected.keys()), Counter(predicted.keys())).model_dump()
    values["predicted"] = len(claims)
    passages = {p.evidence_id: p for p in snapshot.passages}
    resolved = grounded = 0
    for claim in claims:
        valid = evidence_resolves(claim.evidence, passages)
        resolved += int(valid)
        support = expected.get(claim.assertion)
        grounded += int(
            valid
            and support is not None
            and all(
                any(
                    e.evidence_id == r.evidence_id and e.start <= r.start and e.end >= r.end
                    for e in claim.evidence
                )
                for r in support.evidence
            )
        )
    return ExtractionScore(
        **values,
        schema_valid=True,
        duplicates=len(claims) - len(predicted),
        resolvable_spans=resolved,
        grounded=grounded,
    )


def score_events(raw: str, reference: ExtractedEvents, snapshot: SourceSnapshot) -> EventScore:
    expected = {c.assertion: c for c in reference.claims}
    try:
        parsed = ExtractedEvents.model_validate_json(raw)
    except ValueError:
        return EventScore(
            schema_valid=False,
            expected=len(expected),
            dimensions={},
            by_event_type={},
            context_score=ExtractionScore(
                schema_valid=False, expected=len({c.assertion for c in reference.context_claims})
            ),
        )
    predicted = {c.assertion: c for c in parsed.claims}
    return EventScore(
        **_score_claims(reference.claims, parsed.claims, snapshot).model_dump(exclude={"scope"}),
        dimensions={
            kind: _values(
                Counter(_dimensions(c)[kind] for c in expected.values()),
                Counter(_dimensions(c)[kind] for c in predicted.values()),
            )
            for kind in ("identity", "role", "direction", "negation", "timing", "account")
        },
        by_event_type={
            kind: _score_claims(
                [c for c in reference.claims if c.event_type == kind],
                [c for c in parsed.claims if c.event_type == kind],
                snapshot,
            )
            for kind in sorted({c.event_type for c in (*reference.claims, *parsed.claims)})
        },
        context_score=_score_claims(reference.context_claims, parsed.context_claims, snapshot),
        by_theme={
            theme: _score_claims(
                [c for c in reference.context_claims if c.theme == theme],
                [c for c in parsed.context_claims if c.theme == theme],
                snapshot,
            )
            for theme in sorted(
                {c.theme for c in (*reference.context_claims, *parsed.context_claims) if c.theme}
            )
        },
        by_classification={
            kind: _score_claims(
                [c for c in reference.context_claims if c.kind == kind],
                [c for c in parsed.context_claims if c.kind == kind],
                snapshot,
            )
            for kind in sorted(
                {c.kind for c in (*reference.context_claims, *parsed.context_claims)}
            )
        },
    )
