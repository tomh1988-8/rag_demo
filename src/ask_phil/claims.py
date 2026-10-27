"""Shared source and support-review obligations for every typed Claim admission."""

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol

from pydantic import Field

from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Passage, Record, SourceSnapshot
from ask_phil.identity import IdentityCatalogue


class ClaimEvidence(Record):
    evidence_id: Identifier
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: NonEmpty


def evidence_resolves(evidence: tuple[ClaimEvidence, ...], passages: Mapping[str, Passage]) -> bool:
    """Resolve exact Unicode source spans; quote equality alone does not establish support."""
    return all(
        (passage := passages.get(span.evidence_id)) is not None
        and 0 <= span.start < span.end <= len(passage.text)
        and passage.text[span.start : span.end] == span.quote
        for span in evidence
    )


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


class _Claim(Protocol):
    @property
    def claim_id(self) -> str: ...

    @property
    def evidence(self) -> tuple[ClaimEvidence, ...]: ...

    @property
    def fingerprint(self) -> str: ...


class _Batch(Protocol):
    @property
    def snapshot_id(self) -> str: ...

    @property
    def snapshot_sha256(self) -> str: ...

    @property
    def catalogue(self) -> IdentityCatalogue: ...

    @property
    def claims(self) -> Sequence[_Claim]: ...


class ClaimAdmission[Review: ClaimReview]:
    """Bind a batch to its source once, then check each Claim's evidence and review.

    Typed admission owns identity roles and semantic rules. Extra Claims share
    the same review namespace, even when they are kept outside graph adjacency.
    """

    def __init__(
        self,
        snapshot: SourceSnapshot,
        batch: _Batch,
        reviews: Sequence[Review],
        *,
        extra_claims: Sequence[_Claim] = (),
    ) -> None:
        if (batch.snapshot_id, batch.snapshot_sha256) != (
            snapshot.snapshot_id,
            snapshot.fingerprint,
        ):
            raise ValueError("Claims belong to a different source snapshot.")
        claim_ids = {c.claim_id for c in (*batch.claims, *extra_claims)}
        if (
            len({r.claim_id for r in reviews}) != len(reviews)
            or not {r.claim_id for r in reviews} <= claim_ids
        ):
            raise ValueError("Reviews must uniquely identify claims in this batch.")
        if snapshot.imported is not None:
            captured = {c.character_id: c for c in snapshot.imported.catalogue.characters}
            if any(captured.get(c.character_id) != c for c in batch.catalogue.characters):
                raise ValueError("Claim identities must match the captured reviewed catalogue.")
        self.character_ids = frozenset(c.character_id for c in batch.catalogue.characters)
        self._passages = {p.evidence_id: p for p in snapshot.passages}
        self._reviews = {r.claim_id: r for r in reviews}

    def review(self, claim_id: str) -> Review | None:
        """Retain the original review for additional typed obligations, including Crime."""
        return self._reviews.get(claim_id)

    def reasons(self, claim: _Claim) -> list[str]:
        reasons = []
        if not evidence_resolves(claim.evidence, self._passages):
            reasons.append("evidence_span")
        review = self.review(claim.claim_id)
        if (
            review is None
            or review.claim_sha256 != claim.fingerprint
            or review.verdict != "supported"
        ):
            reasons.append("support_review_required")
        return reasons
