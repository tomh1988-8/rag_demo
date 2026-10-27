"""Frozen relationship-slice scores: values, roles, grounding, episodes and order."""

from collections import Counter, defaultdict
from itertools import combinations, permutations, product
from math import perm

from ask_phil.evidence import Record, SourceSnapshot
from ask_phil.parentage import evidence_resolves
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
    alignment_limited: bool = False
    by_relation: dict[str, RelationScore]
    scope: str = (
        "Exposed, completely annotated in-catalogue spans only. Match values and unique passage "
        "IDs, with frozen timing alternatives; ignore arbitrary claim/episode IDs. Romantic "
        "pairs are symmetric; parent/guardian roles are directed. Distinct episode instances "
        "retain multiplicity; duplicates within the same episode collapse. One-to-one value "
        "matching ignores ID spelling. Ambiguous alignments maximize episode agreement, then "
        "ordering; over 4096 alternatives leaves those two scores unavailable. Raw duplicates "
        "and full-reference-span grounding are separate. Missing episode pairs fail. "
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


def _values(expected: Counter[Key], predicted: Counter[Key]) -> RelationScore:
    count = (expected & predicted).total()
    expected_count, predicted_count = expected.total(), predicted.total()
    precision = count / predicted_count if predicted_count else (0.0 if expected_count else 1.0)
    recall = count / expected_count if expected_count else 1.0
    return RelationScore(
        expected=expected_count,
        predicted=predicted_count,
        true_positive=count,
        precision=precision,
        recall=recall,
        f1=2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    )


def _episode_scores(
    expected: dict[Key, list[RelationshipClaim]],
    predicted: dict[Key, list[RelationshipClaim]],
    pairs: tuple[tuple[RelationshipClaim, RelationshipClaim], ...],
) -> tuple[int | None, int | None]:
    """Choose a consistent ID-free alignment, without factorial unbounded scoring."""
    choices = []
    alternatives = 1
    for key in expected.keys() & predicted.keys():
        refs, candidates = expected[key], predicted[key]
        alternatives *= perm(max(len(refs), len(candidates)), min(len(refs), len(candidates)))
        if alternatives > 4096:
            return None, None
        if len(refs) >= len(candidates):
            choices.append(
                [
                    {
                        ref.claim_id: candidate
                        for ref, candidate in zip(selection, candidates, strict=True)
                    }
                    for selection in permutations(refs, len(candidates))
                ]
            )
        else:
            choices.append(
                [
                    {
                        ref.claim_id: candidate
                        for ref, candidate in zip(refs, selection, strict=True)
                    }
                    for selection in permutations(candidates, len(refs))
                ]
            )
    by_id = {c.claim_id: c for group in expected.values() for c in group}
    best = (0, 0)
    for selection in product(*choices):
        matched = {cid: candidate for group in selection for cid, candidate in group.items()}
        reverse = {candidate.claim_id: cid for cid, candidate in matched.items()}
        correct_pairs = sum(
            left.claim_id in matched
            and right.claim_id in matched
            and (
                (left.episode_id == right.episode_id)
                == (matched[left.claim_id].episode_id == matched[right.claim_id].episode_id)
            )
            for left, right in pairs
        )
        correct_order = 0
        for cid, candidate in matched.items():
            required = by_id.get(by_id[cid].after_claim_id or "")
            actual = by_id.get(reverse.get(candidate.after_claim_id or "", ""))
            if required is not None and actual is not None:
                correct_order += int(
                    actual.episode_id == required.episode_id
                    and actual.assertion == required.assertion
                    and actual.status == required.status
                    and actual.polarity == required.polarity
                    and actual.certainty == required.certainty
                )
        best = max(best, (correct_pairs, correct_order))
    return best


def score_relationships(
    raw: str,
    reference: ExtractedRelationships,
    snapshot: SourceSnapshot,
    alternatives: dict[str, tuple[str, ...]] | None = None,
) -> RelationshipScore:
    # Episode identifiers distinguish instances within each side; their spelling is
    # never compared across reference and prediction.
    refs = tuple({(relationship_key(c), c.episode_id): c for c in reference.claims}.values())
    expected: dict[Key, list[RelationshipClaim]] = defaultdict(list)
    for claim in refs:
        expected[relationship_key(claim)].append(claim)
    pairs = tuple(
        (left, right)
        for left, right in combinations(refs, 2)
        if left.participants == right.participants
    )
    order_count = sum(c.after_claim_id is not None for c in reference.claims)
    kinds = {c.relation for c in reference.claims}
    try:
        parsed = ExtractedRelationships.model_validate_json(raw)
    except ValueError:
        return RelationshipScore(
            schema_valid=False,
            expected=len(refs),
            episode_pairs_expected=len(pairs),
            ordering_expected=order_count,
            by_relation={
                k: RelationScore(expected=sum(c.relation == k for c in refs)) for k in sorted(kinds)
            },
        )
    aliases = {
        relationship_key(c, variant): relationship_key(c)
        for c in reference.claims
        for variant in (alternatives or {}).get(c.claim_id, ())
    }
    unique: dict[tuple[Key, str], RelationshipClaim] = {}
    passages = {p.evidence_id: p for p in snapshot.passages}
    resolved = grounded = 0
    for claim in parsed.claims:
        key = relationship_key(claim)
        key = aliases.get(key, key)
        unique.setdefault((key, claim.episode_id), claim)
        supported = expected.get(key, [])
        valid_spans = evidence_resolves(claim.evidence, passages)
        resolved += int(valid_spans)
        grounded += int(
            valid_spans
            and any(
                all(
                    any(
                        e.evidence_id == r.evidence_id and e.start <= r.start and e.end >= r.end
                        for e in claim.evidence
                    )
                    for r in support.evidence
                )
                for support in supported
            )
        )
    predicted: dict[Key, list[RelationshipClaim]] = defaultdict(list)
    for (key, _), claim in unique.items():
        predicted[key].append(claim)
    correct_pairs, ordering_correct = _episode_scores(expected, predicted, pairs)
    by_relation: dict[str, RelationScore] = {
        kind: _values(
            Counter({k: len(group) for k, group in expected.items() if group[0].relation == kind}),
            Counter({k: len(group) for k, group in predicted.items() if group[0].relation == kind}),
        )
        for kind in sorted(kinds | {c.relation for c in parsed.claims})
    }
    values = _values(
        Counter({k: len(v) for k, v in expected.items()}),
        Counter({k: len(v) for k, v in predicted.items()}),
    ).model_dump()
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
        alignment_limited=correct_pairs is None,
        by_relation=by_relation,
    )
