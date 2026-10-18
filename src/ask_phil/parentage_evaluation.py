"""Exact reviewed-slice extraction scores, separating values from evidence support."""

from ask_phil.evidence import Record, SourceSnapshot
from ask_phil.parentage import ExtractedClaims, ParentageClaim


class ExtractionScore(Record):
    schema_valid: bool
    expected: int
    predicted: int | None = None
    duplicates: int | None = None
    true_positive: int | None = None
    resolvable_spans: int | None = None
    grounded: int | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    scope: str = (
        "Exact normalized values within each completely annotated selected input passage. "
        "Instances match on values and sorted unique passage IDs, independently of quote offsets. "
        "Claim IDs are ignored; semantic duplicates within a passage collapse and are counted. "
        "Grounding additionally requires the entire independently reviewed supporting span. "
        "These exposed development scores are not held-out or broad-corpus quality."
    )


def claim_values(claim: ParentageClaim) -> tuple[str, ...]:
    return (
        claim.parent_id,
        claim.child_id,
        claim.parent_role,
        claim.relation,
        claim.polarity,
        claim.certainty,
        claim.story_time,
        claim.time_precision,
    )


def _span_claim_key(claim: ParentageClaim) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return claim_values(claim), tuple(sorted({e.evidence_id for e in claim.evidence}))


def score_extraction(
    raw: str, reference: ExtractedClaims, snapshot: SourceSnapshot
) -> ExtractionScore:
    expected = {_span_claim_key(c): c for c in reference.claims}
    try:
        parsed = ExtractedClaims.model_validate_json(raw)
    except ValueError:
        return ExtractionScore(schema_valid=False, expected=len(expected))
    values = {_span_claim_key(c) for c in parsed.claims}
    true_positive = len(values & expected.keys())
    passages = {p.evidence_id: p for p in snapshot.passages}
    resolvable = grounded = 0
    for claim in parsed.claims:
        resolved = all(
            (p := passages.get(e.evidence_id)) is not None
            and 0 <= e.start < e.end <= len(p.text)
            and p.text[e.start : e.end] == e.quote
            for e in claim.evidence
        )
        resolvable += int(resolved)
        supported = expected.get(_span_claim_key(claim))
        grounded += int(
            resolved
            and supported is not None
            and all(
                any(
                    e.evidence_id == r.evidence_id and e.start <= r.start and e.end >= r.end
                    for e in claim.evidence
                )
                for r in supported.evidence
            )
        )
    precision = true_positive / len(values) if values else (1.0 if not expected else 0.0)
    recall = true_positive / len(expected) if expected else 1.0
    return ExtractionScore(
        schema_valid=True,
        expected=len(expected),
        predicted=len(parsed.claims),
        duplicates=len(parsed.claims) - len(values),
        true_positive=true_positive,
        resolvable_spans=resolvable,
        grounded=grounded,
        precision=precision,
        recall=recall,
        f1=2 * precision * recall / (precision + recall) if precision + recall else 0,
    )
