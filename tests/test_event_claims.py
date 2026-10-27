import json
from pathlib import Path

import pytest

from ask_phil.evidence import SourceSnapshot
from ask_phil.identity import IdentityCatalogue
from ask_phil.story_events import EventBatch, EventClaim, EventReview, admit_events


@pytest.mark.parametrize("basis", ["narrative", "allegation", "confession", "legal_outcome"])
def test_legal_outcomes_and_confessions_cannot_establish_commission(basis: str) -> None:
    # A synthetic assertion using a real locator is deliberately unsupported.
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/phil-arrival-v1.json").read_bytes()
    )
    catalogue = IdentityCatalogue.model_validate(
        json.loads(Path("data/sources/core-profiles-plan-v2.json").read_bytes())["catalogue"]
    )
    passage = snapshot.passages[0]
    claim = EventClaim.model_validate(
        dict(
            claim_id="synthetic-guilt-conflation",
            event_id="synthetic-case",
            event_label="Synthetic case, not canon",
            event_type="commission",
            basis=basis,
            participants=({"character_id": "phil-mitchell", "role": "perpetrator"},),
            account_status="as_reported",
            polarity="affirmed",
            certainty="certain",
            story_time="unknown",
            time_precision="unknown",
            evidence=(
                {
                    "evidence_id": passage.evidence_id,
                    "start": 0,
                    "end": len(passage.text),
                    "quote": passage.text,
                },
            ),
        )
    )
    batch = EventBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=catalogue,
        claims=(claim,),
        extractor="synthetic-counterexample",
    )
    review = EventReview(
        claim_id=claim.claim_id,
        claim_sha256=claim.fingerprint,
        verdict="supported",
        reviewer="synthetic-rule-fixture",
        note="A generic support verdict cannot upgrade a legal account to guilt.",
        narrative_commission=False,
    )
    decision = admit_events(snapshot, batch, (review,)).decisions[0]
    assert decision.status == "held" and "commission_support" in decision.reasons


@pytest.mark.parametrize(
    "change, reason",
    [
        (
            {"participants": [{"character_id": "phil-mitchell", "role": "convicted"}]},
            "participant_role",
        ),
        ({"certainty": "uncertain"}, "uncertain"),
        ({"polarity": "negated"}, "negated"),
        ({"story_time": "2001-03-01"}, "timing"),
        ({"participants": [{"character_id": "steve-mcfadden", "role": "perpetrator"}]}, "identity"),
    ],
)
def test_unsafe_event_assertions_remain_held(change: dict[str, object], reason: str) -> None:
    snapshot, batch, reviews = synthetic_batch()
    claim = EventClaim.model_validate({**batch.claims[0].model_dump(), **change})
    batch = batch.model_copy(update={"claims": (claim,)})
    review = reviews[0].model_copy(update={"claim_sha256": claim.fingerprint})
    decision = admit_events(snapshot, batch, (review,)).decisions[0]
    assert decision.status == "held" and reason in decision.reasons


def synthetic_batch() -> tuple[SourceSnapshot, EventBatch, tuple[EventReview, ...]]:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/phil-arrival-v1.json").read_bytes()
    )
    catalogue = IdentityCatalogue.model_validate(
        json.loads(Path("data/sources/core-profiles-plan-v2.json").read_bytes())["catalogue"]
    )
    passage = snapshot.passages[0]
    claim = EventClaim.model_validate(
        dict(
            claim_id="synthetic-claim",
            event_id="synthetic-case",
            event_label="Synthetic case",
            event_type="commission",
            basis="narrative",
            participants=[{"character_id": "phil-mitchell", "role": "perpetrator"}],
            account_status="as_reported",
            polarity="affirmed",
            certainty="certain",
            story_time="unknown",
            time_precision="unknown",
            evidence=[
                dict(
                    evidence_id=passage.evidence_id,
                    start=0,
                    end=len(passage.text),
                    quote=passage.text,
                )
            ],
        )
    )
    batch = EventBatch(
        snapshot_id=snapshot.snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        catalogue=catalogue,
        claims=(claim,),
        extractor="synthetic-counterexample",
    )
    review = EventReview(
        claim_id=claim.claim_id,
        claim_sha256=claim.fingerprint,
        verdict="supported",
        reviewer="synthetic-rule-fixture",
        note="Synthetic rules only; this is not a source support judgment.",
        narrative_commission=True,
    )
    return snapshot, batch, (review,)


def reference_batch() -> tuple[SourceSnapshot, EventBatch, tuple[EventReview, ...]]:
    from pydantic import TypeAdapter

    directory = Path("docs/implementation/issue-13")
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/crime-pilot-v1.json").read_bytes()
    )
    batch = EventBatch.model_validate_json((directory / "reference-claims.json").read_bytes())
    reviews = TypeAdapter(tuple[EventReview, ...]).validate_json(
        (directory / "reference-reviews.json").read_bytes()
    )
    return snapshot, batch, reviews


def test_reviewed_roles_are_admitted_without_upgrading_legal_stages_to_guilt() -> None:
    snapshot, batch, reviews = reference_batch()
    report = admit_events(snapshot, batch, reviews)
    assert len(report.decisions) == 17
    assert all(d.status == "admitted" for d in report.decisions)
    commissions = [c for c in batch.claims if c.event_type == "commission"]
    assert [(p.character_id, p.role) for c in commissions for p in c.participants] == [
        ("bobby-beale", "perpetrator"),
        ("lucy-beale", "victim"),
    ]


def test_changed_source_values_and_bad_locators_cannot_reuse_reviews() -> None:
    snapshot, batch, reviews = reference_batch()
    first, second = batch.claims[:2]
    changed = first.model_copy(update={"event_type": "conviction"})
    malformed = second.model_copy(
        update={"evidence": (second.evidence[0].model_copy(update={"start": 1}),)}
    )
    changed_batch = batch.model_copy(update={"claims": (changed, malformed)})
    decisions = admit_events(snapshot, changed_batch, reviews[:2]).decisions
    assert all(d.status == "held" for d in decisions)
    assert "support_review_required" in decisions[0].reasons
    assert "evidence_span" in decisions[1].reasons


def test_opposing_or_inconsistently_grouped_accounts_are_held() -> None:
    snapshot, batch, reviews = reference_batch()
    claim = batch.claims[4]
    opposing = claim.model_copy(update={"claim_id": "synthetic-denial", "polarity": "negated"})
    decisions = admit_events(
        snapshot, batch.model_copy(update={"claims": (claim, opposing)}), (reviews[4],)
    ).decisions
    assert all(d.status == "held" and "contradiction" in d.reasons for d in decisions)
    mislabeled = batch.claims[3].model_copy(update={"event_label": "A different incident"})
    decisions = admit_events(
        snapshot, batch.model_copy(update={"claims": (claim, mislabeled)}), (reviews[4], reviews[3])
    ).decisions
    assert all(d.status == "held" and "event_collision" in d.reasons for d in decisions)
