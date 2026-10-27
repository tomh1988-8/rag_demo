import json
from pathlib import Path

import pytest

from ask_phil.evidence import SourceSnapshot
from ask_phil.parentage import ClaimBatch, ClaimReview, ParentageClaim, admit_claims


def reference_batch() -> tuple[SourceSnapshot, ClaimBatch, tuple[ClaimReview, ...]]:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    reference = json.loads(Path("data/references/parentage-v1.json").read_text())
    batch = ClaimBatch(
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
            reviewer="independent-reference-fixture",
            note="The selected source span supports this identity, direction, meaning and timing.",
        )
        for c in batch.claims
    )
    return snapshot, batch, reviews


def test_reviewed_birth_claims_enter_the_tree_but_adoption_remains_a_claim() -> None:
    snapshot, batch, reviews = reference_batch()
    report = admit_claims(snapshot, batch, reviews)
    assert {d.claim_id for d in report.decisions if d.status == "admitted"} == {
        "phil-ben",
        "kathy-ben",
        "peggy-phil",
    }
    adoption = next(d for d in report.decisions if d.claim_id == "den-sharon-adoption")
    assert adoption.status == "held"
    assert "non_biological" in adoption.reasons
    assert batch.claims[-1].relation == "adoptive_parent"


def test_contradictory_parentage_cannot_enter_the_established_tree() -> None:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    reference = json.loads(Path("data/references/parentage-v1.json").read_text())
    positive = reference["expected_claims"][0]
    negative = {**positive, "claim_id": "negative-parentage", "polarity": "negated"}
    batch = ClaimBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=reference["catalogue"],
        claims=tuple(ParentageClaim.model_validate(c) for c in (positive, negative)),
        extractor="synthetic-contradiction-fixture",
    )
    reviews = tuple(
        ClaimReview(
            claim_id=c.claim_id,
            claim_sha256=c.fingerprint,
            verdict="supported",
            reviewer="synthetic-rule-fixture",
            note="Contradictory review test only.",
        )
        for c in batch.claims
    )
    report = admit_claims(snapshot, batch, reviews)
    assert all(d.status == "held" for d in report.decisions)
    assert all("contradiction" in d.reasons for d in report.decisions)


def test_a_reviewed_cycle_is_held_instead_of_becoming_ancestry() -> None:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    reference = json.loads(Path("data/references/parentage-v1.json").read_text())
    positive = reference["expected_claims"][0]
    reverse = {
        **positive,
        "claim_id": "reversed-parentage",
        "parent_id": "ben-mitchell",
        "child_id": "phil-mitchell",
    }
    batch = ClaimBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=reference["catalogue"],
        claims=tuple(ParentageClaim.model_validate(c) for c in (positive, reverse)),
        extractor="synthetic-cycle-fixture",
    )
    reviews = tuple(
        ClaimReview(
            claim_id=c.claim_id,
            claim_sha256=c.fingerprint,
            verdict="supported",
            reviewer="synthetic-rule-fixture",
            note="Cycle test, not a canon label.",
        )
        for c in batch.claims
    )
    report = admit_claims(snapshot, batch, reviews)
    assert all(d.status == "held" and "cycle" in d.reasons for d in report.decisions)


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"parent_id": "steve-mcfadden"}, "identity"),
        ({"certainty": "uncertain"}, "uncertain"),
        ({"relation": "step_parent"}, "non_biological"),
        ({"relation": "ward"}, "non_biological"),
        ({"polarity": "negated"}, "negated"),
    ],
)
def test_unsafe_claims_stay_available_for_review(change: dict[str, str], reason: str) -> None:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    reference = json.loads(Path("data/references/parentage-v1.json").read_text())
    batch = ClaimBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=reference["catalogue"],
        claims=(ParentageClaim.model_validate({**reference["expected_claims"][0], **change}),),
        extractor="synthetic",
    )
    decision = admit_claims(snapshot, batch, ()).decisions[0]
    assert decision.status == "held"
    assert reason in decision.reasons
    assert "support_review_required" in decision.reasons


def test_competing_fathers_are_held_even_when_both_have_positive_reviews() -> None:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    reference = json.loads(Path("data/references/parentage-v1.json").read_text())
    first = {**reference["expected_claims"][0], "parent_role": "father"}
    other = {**first, "claim_id": "competing-father", "parent_id": "den-watts"}
    batch = ClaimBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=reference["catalogue"],
        claims=tuple(ParentageClaim.model_validate(c) for c in (first, other)),
        extractor="synthetic-competing-parent-fixture",
    )
    reviews = tuple(
        ClaimReview(
            claim_id=c.claim_id,
            claim_sha256=c.fingerprint,
            verdict="supported",
            reviewer="synthetic-rule-fixture",
            note="Conflicting fathers, not canon labels.",
        )
        for c in batch.claims
    )
    assert all(
        "contradiction" in d.reasons for d in admit_claims(snapshot, batch, reviews).decisions
    )
