"""Frozen relationship-slice scores: values, roles, grounding, episodes and order."""

from itertools import combinations

from ask_phil.evidence import Record, SourceSnapshot
from ask_phil.relationships import ExtractedRelationships, RelationshipClaim

Key = tuple[str, ...]


class RelationScore(Record):
    expected: int
    predicted: int | None = None
    true_positive: int | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None


class RelationshipScore(RelationScore):
    schema_valid: bool
    duplicates: int | None = None
    resolvable_spans: int | None = None
    grounded: int | None = None
    episode_pairs_expected: int
    episode_pairs_correct: int | None = None
    ordering_expected: int
    ordering_predicted: int | None = None
    ordering_correct: int | None = None
    by_relation: dict[str, RelationScore]
    scope: str = (
        "Exposed, completely annotated in-catalogue spans only. Match values and unique passage "
        "IDs, with frozen timing alternatives; ignore arbitrary claim/episode IDs. Romantic "
        "pairs are symmetric; parent/guardian roles are directed. Unique values determine "
        "precision/recall; raw duplicates and full-reference-span grounding are separate. "
        "Episode membership and explicit order are scored separately, including missing pairs. "
        "This conservative grounding proxy is not independent semantic/canon adjudication."
    )


def relationship_key(claim: RelationshipClaim, story_time: str | None = None) -> Key:
    return (
        *claim.participants,
        claim.relation,
        claim.status,
        claim.polarity,
        claim.certainty,
        story_time if story_time is not None else claim.story_time,
        claim.time_precision,
        *sorted({e.evidence_id for e in claim.evidence}),
    )


def _values(expected: set[Key], predicted: set[Key]) -> RelationScore:
    count = len(expected & predicted)
    precision = count / len(predicted) if predicted else (0.0 if expected else 1.0)
    recall = count / len(expected) if expected else 1.0
    return RelationScore(
        expected=len(expected),
        predicted=len(predicted),
        true_positive=count,
        precision=precision,
        recall=recall,
        f1=2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    )


def score_relationships(
    raw: str,
    reference: ExtractedRelationships,
    snapshot: SourceSnapshot,
    alternatives: dict[str, tuple[str, ...]] | None = None,
) -> RelationshipScore:
    expected = {relationship_key(c): c for c in reference.claims}
    pairs = tuple(
        (left, right)
        for left, right in combinations(expected.values(), 2)
        if left.participants == right.participants
    )
    order_count = sum(c.after_claim_id is not None for c in reference.claims)
    kinds = {c.relation for c in reference.claims}
    try:
        parsed = ExtractedRelationships.model_validate_json(raw)
    except ValueError:
        return RelationshipScore(
            schema_valid=False,
            expected=len(expected),
            episode_pairs_expected=len(pairs),
            ordering_expected=order_count,
            by_relation={
                k: RelationScore(expected=sum(c.relation == k for c in expected.values()))
                for k in sorted(kinds)
            },
        )
    aliases = {
        relationship_key(c, variant): relationship_key(c)
        for c in reference.claims
        for variant in (alternatives or {}).get(c.claim_id, ())
    }
    unique: dict[Key, RelationshipClaim] = {}
    matched: dict[str, RelationshipClaim] = {}
    predicted_to_reference: dict[str, str] = {}
    passages = {p.evidence_id: p for p in snapshot.passages}
    resolved = grounded = 0
    for claim in parsed.claims:
        key = relationship_key(claim)
        key = aliases.get(key, key)
        unique.setdefault(key, claim)
        supported = expected.get(key)
        if supported is not None:
            matched.setdefault(supported.claim_id, claim)
            predicted_to_reference[claim.claim_id] = supported.claim_id
        valid_spans = all(
            (p := passages.get(e.evidence_id)) is not None
            and 0 <= e.start < e.end <= len(p.text)
            and p.text[e.start : e.end] == e.quote
            for e in claim.evidence
        )
        resolved += int(valid_spans)
        grounded += int(
            valid_spans
            and supported is not None
            and all(
                any(
                    e.evidence_id == r.evidence_id and e.start <= r.start and e.end >= r.end
                    for e in claim.evidence
                )
                for r in supported.evidence
            )
        )
    correct_pairs = sum(
        left.claim_id in matched
        and right.claim_id in matched
        and (
            (left.episode_id == right.episode_id)
            == (matched[left.claim_id].episode_id == matched[right.claim_id].episode_id)
        )
        for left, right in pairs
    )
    ordering_correct = sum(
        c.after_claim_id is not None
        and c.claim_id in matched
        and predicted_to_reference.get(matched[c.claim_id].after_claim_id or "") == c.after_claim_id
        for c in reference.claims
    )
    by_relation: dict[str, RelationScore] = {
        kind: _values(
            {k for k, c in expected.items() if c.relation == kind},
            {k for k, c in unique.items() if c.relation == kind},
        )
        for kind in sorted(kinds | {c.relation for c in parsed.claims})
    }
    values = _values(set(expected), set(unique)).model_dump()
    # Overall prediction volume is raw; per-relation prediction volumes are unique values.
    values["predicted"] = len(parsed.claims)
    return RelationshipScore(
        **values,
        schema_valid=True,
        duplicates=len(parsed.claims) - len(unique),
        resolvable_spans=resolved,
        grounded=grounded,
        episode_pairs_expected=len(pairs),
        episode_pairs_correct=correct_pairs,
        ordering_expected=order_count,
        ordering_predicted=sum(c.after_claim_id is not None for c in parsed.claims),
        ordering_correct=ordering_correct,
        by_relation=by_relation,
    )
