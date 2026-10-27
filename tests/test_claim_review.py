"""Maintainer review transitions at the agreed Claim admission boundary."""

import pytest
from test_event_claims import reference_batch as event_reference
from test_parentage import reference_batch
from test_relationship_claims import reference_batch as relationship_reference

from ask_phil.claims import ClaimReview
from ask_phil.parentage import admit_claims
from ask_phil.relationships import admit_relationships
from ask_phil.story_events import EventReview, admit_events


def test_supported_correction_retires_a_conflicting_claim_without_erasing_it() -> None:
    snapshot, original, reviews = reference_batch()
    correct = original.claims[0]
    mistaken = correct.model_copy(update={"claim_id": "mistaken-negation", "polarity": "negated"})
    batch = original.model_copy(update={"claims": (correct, mistaken)})
    initial = (
        reviews[0],
        reviews[0].model_copy(
            update={
                "claim_id": mistaken.claim_id,
                "claim_sha256": mistaken.fingerprint,
            }
        ),
    )
    assert all(d.status == "held" for d in admit_claims(snapshot, batch, initial).decisions)

    correction = ClaimReview(
        claim_id=mistaken.claim_id,
        claim_sha256=mistaken.fingerprint,
        verdict="superseded",
        superseded_by=(correct.claim_id,),
        reviewer="synthetic-admission-regression",
        note="The retained passage describes birth; the negation was an extraction error.",
    )
    result = admit_claims(snapshot, batch, (reviews[0], correction))

    assert result.decisions[0].status == "admitted"
    assert result.decisions[1].status == "held"
    assert "superseded" in result.decisions[1].reasons
    assert batch.claims == (correct, mistaken)
    assert initial[1].verdict == "supported"


@pytest.mark.parametrize("failure", ["missing", "stale", "unsupported", "cycle"])
def test_correction_cannot_bypass_replacement_support(failure: str) -> None:
    snapshot, batch, reviews = reference_batch()
    old, new = batch.claims[:2]
    replacement = reviews[1]
    if failure == "stale":
        replacement = replacement.model_copy(update={"claim_sha256": "0" * 64})
    elif failure == "unsupported":
        replacement = replacement.model_copy(update={"verdict": "unsupported"})
    elif failure == "cycle":
        replacement = replacement.model_copy(
            update={"verdict": "superseded", "superseded_by": (old.claim_id,)}
        )
    correction = ClaimReview(
        claim_id=old.claim_id,
        claim_sha256=old.fingerprint,
        verdict="superseded",
        superseded_by=("missing" if failure == "missing" else new.claim_id,),
        reviewer="synthetic-regression",
        note="This deliberately invalid correction must fail.",
    )
    with pytest.raises(ValueError, match="source-supported replacements"):
        admit_claims(snapshot, batch, (correction, replacement, *reviews[2:]))


def test_disputed_support_does_not_enter_established_parentage() -> None:
    snapshot, batch, reviews = reference_batch()
    disputed = reviews[0].model_copy(
        update={"verdict": "disputed", "note": "Unresolved source disagreement."}
    )
    report = admit_claims(snapshot, batch, (disputed, *reviews[1:]))
    assert report.decisions[0].status == "held"
    assert report.decisions[0].reasons == ("disputed",)


def test_corrected_relationship_timing_does_not_leave_an_episode_collision() -> None:
    snapshot, original, reviews = relationship_reference()
    correct = next(c for c in original.claims if c.relation == "marriage")
    mistaken = correct.model_copy(
        update={
            "claim_id": "mistaken-timing",
            "story_time": "around 1999",
            "time_precision": "approximate",
        }
    )
    supported = next(r for r in reviews if r.claim_id == correct.claim_id)
    correction = ClaimReview(
        claim_id=mistaken.claim_id,
        claim_sha256=mistaken.fingerprint,
        verdict="superseded",
        superseded_by=(correct.claim_id,),
        reviewer="synthetic-regression",
        note="Use the explicitly supported timing and retain the erroneous extraction.",
    )
    batch = original.model_copy(update={"claims": (correct, mistaken)})
    result = admit_relationships(snapshot, batch, (supported, correction))
    assert result.decisions[0].status == "admitted"
    assert result.decisions[1].status == "held"


def test_corrected_event_account_retires_the_conflict_but_keeps_the_false_account() -> None:
    snapshot, original, reviews = event_reference()
    correct = next(c for c in original.claims if c.event_type == "confession")
    mistaken = correct.model_copy(
        update={"claim_id": "mistaken-account", "account_status": "as_reported"}
    )
    supported = next(r for r in reviews if r.claim_id == correct.claim_id)
    correction = EventReview(
        claim_id=mistaken.claim_id,
        claim_sha256=mistaken.fingerprint,
        verdict="superseded",
        superseded_by=(correct.claim_id,),
        reviewer="synthetic-regression",
        note="The narrative identifies this confession as false; it cannot establish commission.",
    )
    batch = original.model_copy(update={"claims": (correct, mistaken)})
    result = admit_events(snapshot, batch, (supported, correction))
    assert result.decisions[0].status == "admitted"
    assert result.decisions[1].status == "held"
    assert correct.account_status == "explicitly_false"


def test_supported_review_cannot_turn_a_confession_into_a_corrective_commission_claim() -> None:
    snapshot, batch, reviews = event_reference()
    confession = next(c for c in batch.claims if c.event_type == "confession")
    mistaken = confession.model_copy(
        update={"claim_id": "invalid-commission", "event_type": "commission"}
    )
    review = next(r for r in reviews if r.claim_id == confession.claim_id)
    correction = review.model_copy(
        update={"verdict": "superseded", "superseded_by": (mistaken.claim_id,)}
    )
    invalid_support = review.model_copy(
        update={"claim_id": mistaken.claim_id, "claim_sha256": mistaken.fingerprint}
    )
    with pytest.raises(ValueError, match="replacement.*admission"):
        admit_events(
            snapshot,
            batch.model_copy(update={"claims": (confession, mistaken)}),
            (correction, invalid_support),
        )


@pytest.mark.parametrize("later_outcome", ["superseded", "disputed", "uncertain", "unsupported"])
def test_retired_claim_stays_retired_when_its_replacement_is_reviewed_again(
    later_outcome: str,
) -> None:
    snapshot, original, source_reviews = reference_batch()
    current = original.claims[0]
    old = current.model_copy(update={"claim_id": "earlier-negation", "polarity": "negated"})
    replacement = current.model_copy(update={"claim_id": "latest-parentage"})
    retired = ClaimReview(
        claim_id=old.claim_id,
        claim_sha256=old.fingerprint,
        verdict="superseded",
        superseded_by=(current.claim_id,),
        reviewer="synthetic-history-test",
        note="Original correction remains part of the history.",
    )
    prior = (retired, source_reviews[0])
    first_batch = original.model_copy(update={"claims": (old, current)})
    assert admit_claims(snapshot, first_batch, prior).decisions[1].status == "admitted"
    changed = ClaimReview.model_validate(
        {
            **source_reviews[0].model_dump(),
            "verdict": later_outcome,
            "superseded_by": (replacement.claim_id,) if later_outcome == "superseded" else (),
            "note": "Subsequent source interpretation; never revive the earlier negation.",
        }
    )
    new_reviews = (
        (
            retired,
            changed,
            source_reviews[0].model_copy(
                update={
                    "claim_id": replacement.claim_id,
                    "claim_sha256": replacement.fingerprint,
                }
            ),
        )
        if later_outcome == "superseded"
        else (retired, changed)
    )
    batch = original.model_copy(
        update={
            "claims": (old, current, replacement)
            if later_outcome == "superseded"
            else (old, current)
        }
    )
    result = admit_claims(snapshot, batch, new_reviews, prior_reviews=prior)
    assert result.decisions[0].status == result.decisions[1].status == "held"
    assert "superseded" in result.decisions[0].reasons
    if later_outcome == "superseded":
        assert result.decisions[2].status == "admitted"
