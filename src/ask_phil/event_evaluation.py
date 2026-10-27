"""Source-anchored crime/justice values and diagnostic projections, separate from grounding."""

from collections import Counter

from ask_phil.evidence import Record, SourceSnapshot
from ask_phil.parentage import evidence_resolves
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
    by_event_type: dict[str, ValueScore]
    scope: str = (
        "Exposed selected incidents and in-catalogue assertions only. Exact values include "
        "participant-role assignment, event type, basis, account status, polarity, certainty, "
        "story time/precision and evidence IDs. Ignore arbitrary claim/event ID spelling and "
        "label wording; incident grouping requires separate support review. Full-value duplicates "
        "collapse. Each dimension projects unique full assertions onto values plus passage IDs "
        "and event type, preserving multiplicity: identity sets, role multisets, assigned "
        "identity-role pairs (direction), polarity, timing, or account attribution. These are "
        "diagnostics, not independent per-claim accuracies. Grounding separately requires exact "
        "resolvable locators covering frozen supporting spans; it is not canon adjudication."
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


def score_events(raw: str, reference: ExtractedEvents, snapshot: SourceSnapshot) -> EventScore:
    expected = {c.assertion: c for c in reference.claims}
    try:
        parsed = ExtractedEvents.model_validate_json(raw)
    except ValueError:
        return EventScore(
            schema_valid=False, expected=len(expected), dimensions={}, by_event_type={}
        )
    predicted = {c.assertion: c for c in parsed.claims}
    values = _values(Counter(expected.keys()), Counter(predicted.keys())).model_dump()
    values["predicted"] = len(parsed.claims)
    passages = {p.evidence_id: p for p in snapshot.passages}
    resolved = grounded = 0
    for claim in parsed.claims:
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
    return EventScore(
        **values,
        schema_valid=True,
        duplicates=len(parsed.claims) - len(predicted),
        resolvable_spans=resolved,
        grounded=grounded,
        dimensions={
            kind: _values(
                Counter(_dimensions(c)[kind] for c in expected.values()),
                Counter(_dimensions(c)[kind] for c in predicted.values()),
            )
            for kind in ("identity", "role", "direction", "negation", "timing", "account")
        },
        by_event_type={
            kind: _values(
                Counter(k for k, c in expected.items() if c.event_type == kind),
                Counter(k for k, c in predicted.items() if c.event_type == kind),
            )
            for kind in sorted({c.event_type for c in (*reference.claims, *parsed.claims)})
        },
    )
