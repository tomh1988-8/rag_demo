"""Evidence-backed parentage claims and explicit admission into the biological tree."""

import hashlib
from typing import Literal, Self

from pydantic import Field, model_validator

from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record, SourceSnapshot
from ask_phil.identity import IdentityCatalogue


class ClaimEvidence(Record):
    evidence_id: Identifier
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: NonEmpty


class ParentageClaim(Record):
    claim_id: Identifier
    parent_id: Identifier
    child_id: Identifier
    parent_role: Literal["parent", "mother", "father"]
    relation: Literal["biological_parent", "adoptive_parent", "step_parent", "ward"]
    polarity: Literal["affirmed", "negated"]
    certainty: Literal["certain", "uncertain"]
    story_time: NonEmpty
    time_precision: Literal["exact", "approximate", "relative", "unknown"]
    evidence: tuple[ClaimEvidence, ...] = Field(min_length=1, max_length=4)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ExtractedClaims(Record):
    claims: tuple[ParentageClaim, ...] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_claims(self) -> Self:
        if len({c.claim_id for c in self.claims}) != len(self.claims):
            raise ValueError("Claim identifiers must be unique within an extraction.")
        return self


class ClaimBatch(ExtractedClaims):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    catalogue: IdentityCatalogue
    extractor: NonEmpty

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ClaimReview(Record):
    claim_id: Identifier
    claim_sha256: Fingerprint
    verdict: Literal["supported", "unsupported", "uncertain"]
    reviewer: NonEmpty
    note: NonEmpty


class AdmissionDecision(Record):
    claim_id: Identifier
    status: Literal["admitted", "held"]
    reasons: tuple[str, ...]


class AdmissionReport(Record):
    batch_sha256: Fingerprint
    decisions: tuple[AdmissionDecision, ...]
    limitation: str = (
        "Admission requires a content-bound support review. It is not independent canon "
        "corroboration. Held claims remain inspectable outside the biological tree."
    )


def admit_claims(
    snapshot: SourceSnapshot, batch: ClaimBatch, reviews: tuple[ClaimReview, ...]
) -> AdmissionReport:
    """Check provenance and reviewed semantics; never infer support from a quote match alone."""
    if (batch.snapshot_id, batch.snapshot_sha256) != (snapshot.snapshot_id, snapshot.fingerprint):
        raise ValueError("Claims belong to a different source snapshot.")
    if len({r.claim_id for r in reviews}) != len(reviews) or not {r.claim_id for r in reviews} <= {
        c.claim_id for c in batch.claims
    }:
        raise ValueError("Reviews must uniquely identify claims in this batch.")
    identities = {c.character_id for c in batch.catalogue.characters}
    if snapshot.imported is not None:
        captured = {c.character_id: c for c in snapshot.imported.catalogue.characters}
        if any(captured.get(c.character_id) != c for c in batch.catalogue.characters):
            raise ValueError("Claim identities must match the captured reviewed catalogue.")
    passages = {p.evidence_id: p for p in snapshot.passages}
    checked = {r.claim_id: r for r in reviews}
    polarities: dict[tuple[str, str], set[str]] = {}
    parents: dict[str, set[str]] = {}
    roles: dict[tuple[str, str], set[str]] = {}
    for claim in batch.claims:
        if claim.relation == "biological_parent":
            polarities.setdefault((claim.parent_id, claim.child_id), set()).add(claim.polarity)
            if claim.polarity == "affirmed" and claim.certainty == "certain":
                parents.setdefault(claim.child_id, set()).add(claim.parent_id)
                roles.setdefault((claim.child_id, claim.parent_role), set()).add(claim.parent_id)
    decisions = []
    for claim in batch.claims:
        reasons = []
        if claim.parent_id == claim.child_id or not {claim.parent_id, claim.child_id} <= identities:
            reasons.append("identity")
        for evidence in claim.evidence:
            passage = passages.get(evidence.evidence_id)
            if (
                passage is None
                or not 0 <= evidence.start < evidence.end <= len(passage.text)
                or passage.text[evidence.start : evidence.end] != evidence.quote
            ):
                reasons.append("evidence_span")
                break
        review = checked.get(claim.claim_id)
        if (
            review is None
            or review.claim_sha256 != claim.fingerprint
            or review.verdict != "supported"
        ):
            reasons.append("support_review_required")
        if claim.relation != "biological_parent":
            reasons.append("non_biological")
        if claim.polarity != "affirmed":
            reasons.append("negated")
        if claim.certainty != "certain":
            reasons.append("uncertain")
        if (
            len(polarities.get((claim.parent_id, claim.child_id), set())) > 1
            or len(parents.get(claim.child_id, set())) > 2
            or (
                claim.parent_role != "parent"
                and len(roles.get((claim.child_id, claim.parent_role), set())) > 1
            )
        ):
            reasons.append("contradiction")
        decisions.append(
            AdmissionDecision(
                claim_id=claim.claim_id,
                status="held" if reasons else "admitted",
                reasons=tuple(reasons),
            )
        )
    candidates = {
        c.claim_id: c
        for c, d in zip(batch.claims, decisions, strict=True)
        if d.status == "admitted"
    }
    children: dict[str, set[str]] = {}
    for claim in candidates.values():
        children.setdefault(claim.parent_id, set()).add(claim.child_id)

    def reaches(start: str, target: str) -> bool:
        pending, visited = [start], set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current not in visited:
                visited.add(current)
                pending.extend(children.get(current, ()))
        return False

    for i, decision in enumerate(decisions):
        candidate = candidates.get(decision.claim_id)
        if candidate and reaches(candidate.child_id, candidate.parent_id):
            decisions[i] = AdmissionDecision(
                claim_id=candidate.claim_id, status="held", reasons=("cycle",)
            )
    return AdmissionReport(batch_sha256=batch.fingerprint, decisions=tuple(decisions))
