"""Shared admission obligations exercised through the existing typed interfaces."""

from dataclasses import dataclass, replace

import pytest
from test_life_events import life_reference
from test_parentage import reference_batch as family_reference
from test_relationship_claims import reference_batch

from ask_phil.evidence import SourceSnapshot
from ask_phil.parentage import AdmissionDecision, ClaimBatch, ClaimReview, admit_claims
from ask_phil.relationships import RelationshipBatch, admit_relationships
from ask_phil.story_events import EventBatch, EventReview, admit_events


@dataclass(frozen=True)
class AdmissionCase:
    snapshot: SourceSnapshot
    batch: ClaimBatch | RelationshipBatch | EventBatch
    reviews: tuple[ClaimReview, ...]
    text: bool = False

    def decisions(self) -> tuple[AdmissionDecision, ...]:
        if isinstance(self.batch, EventBatch):
            reviews = tuple(EventReview.model_validate(r.model_dump()) for r in self.reviews)
            report = admit_events(self.snapshot, self.batch, reviews)
            return report.text_decisions if self.text else report.decisions
        if isinstance(self.batch, RelationshipBatch):
            return admit_relationships(self.snapshot, self.batch, self.reviews).decisions
        return admit_claims(self.snapshot, self.batch, self.reviews).decisions


@pytest.fixture(params=["family", "relationship", "event", "text"])
def admission_case(request: pytest.FixtureRequest) -> AdmissionCase:
    if request.param == "relationship":
        return AdmissionCase(*reference_batch())
    if request.param in {"event", "text"}:
        return AdmissionCase(*life_reference(), text=request.param == "text")
    return AdmissionCase(*family_reference())


@pytest.mark.parametrize("verdict", ["stale", "unsupported", "uncertain", "missing"])
def test_support_review_binds_the_exact_claim_content(
    admission_case: AdmissionCase, verdict: str
) -> None:
    case = admission_case
    original = case.decisions()[0]
    assert original.status == "admitted"
    reviews = tuple(
        r.model_copy(
            update={"claim_sha256": "0" * 64} if verdict == "stale" else {"verdict": verdict}
        )
        if r.claim_id == original.claim_id
        else r
        for r in case.reviews
        if verdict != "missing" or r.claim_id != original.claim_id
    )
    changed = replace(case, reviews=reviews).decisions()[0]
    assert changed.status == "held"
    assert changed.reasons == ("support_review_required",)
    assert case.decisions()[0] == original


def test_supported_review_cannot_admit_an_unresolvable_span(admission_case: AdmissionCase) -> None:
    case = admission_case
    claims = (
        case.batch.context_claims
        if isinstance(case.batch, EventBatch) and case.text
        else case.batch.claims
    )
    first = claims[0]
    malformed = first.model_copy(
        update={"evidence": (first.evidence[0].model_copy(update={"start": 999999}),)}
    )
    batch = case.batch.model_copy(
        update={"context_claims" if case.text else "claims": (malformed, *claims[1:])}
    )
    reviews = tuple(
        r.model_copy(update={"claim_sha256": malformed.fingerprint})
        if r.claim_id == malformed.claim_id
        else r
        for r in case.reviews
    )
    decision = replace(case, batch=batch, reviews=reviews).decisions()[0]
    assert decision.status == "held"
    assert decision.reasons == ("evidence_span",)


@pytest.mark.parametrize("invalid", ["snapshot", "duplicate_review", "unknown_review"])
def test_admission_rejects_mismatched_source_or_review_membership(
    admission_case: AdmissionCase, invalid: str
) -> None:
    case = admission_case
    if invalid == "snapshot":
        case = replace(case, batch=case.batch.model_copy(update={"snapshot_sha256": "0" * 64}))
        message = "different source snapshot"
    else:
        review = case.reviews[0]
        if invalid == "unknown_review":
            review = review.model_copy(update={"claim_id": "absent-claim"})
        case = replace(case, reviews=(*case.reviews, review))
        message = "uniquely identify claims"
    with pytest.raises(ValueError, match=message):
        case.decisions()
