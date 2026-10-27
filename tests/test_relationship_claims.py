import json
from pathlib import Path

import pytest

from ask_phil.evidence import SourceSnapshot
from ask_phil.parentage import ClaimReview
from ask_phil.relationships import RelationshipBatch, admit_relationships


def reference_batch() -> tuple[SourceSnapshot, RelationshipBatch, tuple[ClaimReview, ...]]:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/relationship-pilot-v1.json").read_bytes()
    )
    reference = json.loads(Path("data/references/relationships-v2.json").read_bytes())
    batch = RelationshipBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=reference["catalogue"],
        claims=reference["expected_claims"],
        extractor="reviewed-reference-fixture",
    )
    return snapshot, batch, support_reviews(batch)


def support_reviews(batch: RelationshipBatch) -> tuple[ClaimReview, ...]:
    return tuple(
        ClaimReview(
            claim_id=c.claim_id,
            claim_sha256=c.fingerprint,
            verdict="supported",
            reviewer="reference-or-explicitly-synthetic-rule-fixture",
            note="Checks admission rules; synthetic counterexamples are not canon assertions.",
        )
        for c in batch.claims
    )


def test_reviewed_histories_preserve_episodes_roles_and_uncertain_dates() -> None:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/relationship-pilot-v1.json").read_bytes()
    )
    reference = json.loads(Path("data/references/relationships-v1.json").read_bytes())
    batch = RelationshipBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=reference["catalogue"],
        claims=reference["expected_claims"],
        extractor="reviewed-reference-fixture",
    )
    reviews = tuple(
        ClaimReview(
            claim_id=c.claim_id,
            claim_sha256=c.fingerprint,
            verdict="supported",
            reviewer="source-reference-fixture",
            note="Identity, relationship meaning, episode and any ordering checked against source.",
        )
        for c in batch.claims
    )
    report = admit_relationships(snapshot, batch, reviews)
    assert len(report.decisions) == 12
    assert all(d.status == "admitted" for d in report.decisions)
    by_id = {c.claim_id: c for c in batch.claims}
    assert by_id["kat-alfie-marriage"].episode_id != by_id["kat-alfie-remarriage"].episode_id
    assert by_id["phil-kathy-marriage"].episode_id == by_id["phil-kathy-reconciliation"].episode_id
    assert by_id["phil-kathy-separation"].status == "unknown"
    assert by_id["denise-amy-step"].subject_id == "denise-fox"
    assert by_id["den-sharon-adoption"].relation == "adoptive_parent"


def test_repeated_marriages_cannot_collapse_into_one_episode() -> None:
    snapshot, original, _ = reference_batch()
    claims = tuple(
        c.model_copy(update={"episode_id": "collapsed-marriage"})
        for c in original.claims
        if c.claim_id.startswith("kat-alfie")
    )
    batch = original.model_copy(update={"claims": claims, "extractor": "synthetic-collapse"})
    decisions = admit_relationships(snapshot, batch, support_reviews(batch)).decisions
    assert all(d.status == "held" and "episode_collision" in d.reasons for d in decisions)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ({"polarity": "negated"}, "negated"),
        ({"certainty": "uncertain"}, "uncertain"),
        ({"subject_id": "steve-mcfadden"}, "identity"),
        ({"after_claim_id": "invented-event"}, "ordering"),
        ({"story_time": "2023-01-01", "time_precision": "unknown"}, "timing"),
    ],
)
def test_unsafe_history_assertions_are_retained_but_held(
    mutation: dict[str, str], reason: str
) -> None:
    snapshot, original, _ = reference_batch()
    claim = original.claims[0].model_copy(update=mutation)
    batch = original.model_copy(update={"claims": (claim,), "extractor": "synthetic-unsafe"})
    decision = admit_relationships(snapshot, batch, support_reviews(batch)).decisions[0]
    assert decision.status == "held" and reason in decision.reasons


def test_cyclic_or_held_predecessors_do_not_establish_ordering() -> None:
    snapshot, original, reviews = reference_batch()
    marriage, separation, reconciliation = original.claims[:3]
    cycle = marriage.model_copy(update={"after_claim_id": reconciliation.claim_id})
    batch = original.model_copy(update={"claims": (cycle, separation, reconciliation)})
    assert all(
        d.status == "held" and "ordering" in d.reasons
        for d in admit_relationships(snapshot, batch, support_reviews(batch)).decisions
    )
    batch = original.model_copy(update={"claims": (marriage, separation, reconciliation)})
    # A missing review on the marriage must not leave its descendants' ordering admitted.
    assert all(
        d.status == "held" for d in admit_relationships(snapshot, batch, reviews[1:3]).decisions
    )


def test_opposing_relationship_claims_are_held_instead_of_choosing_a_winner() -> None:
    snapshot, original, _ = reference_batch()
    positive = original.claims[3]
    negative = positive.model_copy(update={"claim_id": "opposing-affair", "polarity": "negated"})
    batch = original.model_copy(update={"claims": (positive, negative)})
    decisions = admit_relationships(snapshot, batch, support_reviews(batch)).decisions
    assert all(d.status == "held" and "contradiction" in d.reasons for d in decisions)


@pytest.mark.parametrize(
    "relation", ["biological_parent", "adoptive_parent", "step_parent", "ward"]
)
def test_social_roles_are_directed_and_never_convert_a_ward_to_adoption(relation: str) -> None:
    _, original, _ = reference_batch()
    # Deliberately synthetic meaning/direction example, not an added canon label.
    claim = original.claims[8].model_copy(update={"relation": relation})
    assert claim.participants == ("den-watts", "sharon-watts")
    assert claim.relation == relation
    reverse = claim.model_copy(update={"subject_id": "sharon-watts", "object_id": "den-watts"})
    assert reverse.participants != claim.participants


def test_changed_claims_and_false_evidence_cannot_reuse_a_support_review() -> None:
    snapshot, original, reviews = reference_batch()
    changed = original.claims[0].model_copy(update={"status": "current"})
    bad_quote = original.claims[1].model_copy(
        update={"evidence": (original.claims[1].evidence[0].model_copy(update={"start": 1}),)}
    )
    batch = original.model_copy(update={"claims": (changed, bad_quote)})
    decisions = admit_relationships(snapshot, batch, reviews[:2]).decisions
    assert decisions[0].status == "held" and "support_review_required" in decisions[0].reasons
    assert decisions[1].status == "held" and "evidence_span" in decisions[1].reasons


def test_arbitrary_episode_names_do_not_hide_contradictions_or_current_divorce() -> None:
    snapshot, original, _ = reference_batch()
    positive = original.claims[3]
    negative = positive.model_copy(
        update={
            "claim_id": "synthetic-denial",
            "episode_id": "different-label",
            "polarity": "negated",
        }
    )
    divorce = original.claims[5].model_copy(update={"status": "current"})
    batch = original.model_copy(update={"claims": (positive, negative, divorce)})
    decisions = admit_relationships(snapshot, batch, support_reviews(batch)).decisions
    assert all(d.status == "held" for d in decisions)
    assert "contradiction" in decisions[0].reasons
    assert "status" in decisions[2].reasons
