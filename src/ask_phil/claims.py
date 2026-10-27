"""Shared source and support-review obligations for every typed Claim admission."""

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol, Self

from pydantic import Field, model_validator

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
    verdict: Literal["supported", "unsupported", "uncertain", "disputed", "superseded"]
    reviewer: NonEmpty
    note: NonEmpty
    superseded_by: tuple[Identifier, ...] = Field(
        default=(), max_length=10, exclude_if=lambda value: not value
    )

    @model_validator(mode="after")
    def correction_targets(self) -> Self:
        if (self.verdict == "superseded") != bool(self.superseded_by):
            raise ValueError("A superseded Claim must identify its supported replacement Claims.")
        if self.claim_id in self.superseded_by or len(set(self.superseded_by)) != len(
            self.superseded_by
        ):
            raise ValueError("Correction targets must be distinct other Claims.")
        return self


class AdmissionDecision(Record):
    claim_id: Identifier
    status: Literal["admitted", "held"]
    reasons: tuple[str, ...]


def replacement_claim_ids(claim_id: str, reviews: Mapping[str, ClaimReview]) -> tuple[str, ...]:
    """Follow retained correction links without treating an intermediate account as current."""

    def visit(current: str, path: frozenset[str]) -> tuple[str, ...]:
        if current in path:
            raise ValueError("Corrections require acyclic, source-supported replacements.")
        review = reviews.get(current)
        if review is None or review.verdict != "superseded":
            return (current,)
        return tuple(
            dict.fromkeys(
                target
                for child in review.superseded_by
                for target in visit(child, path | {current})
            )
        )

    return visit(claim_id, frozenset())


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
        prior_reviews: Sequence[ClaimReview] = (),
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
        claims = {c.claim_id: c for c in (*batch.claims, *extra_claims)}
        self._superseded: set[str] = set()
        self._inherited: set[str] = set()
        prior = {r.claim_id: r for r in prior_reviews}
        self._replacements: dict[str, tuple[str, ...]] = {}
        for review in reviews:
            if review.verdict != "superseded":
                continue
            claim = claims[review.claim_id]
            old = prior.get(review.claim_id)
            if (
                old
                and old.verdict == "superseded"
                and (old.claim_sha256, old.superseded_by)
                == (review.claim_sha256, review.superseded_by)
            ):
                self._inherited.add(review.claim_id)
            targets = replacement_claim_ids(review.claim_id, self._reviews)
            if review.claim_sha256 != claim.fingerprint or any(
                target not in claims
                or (target_review := self._reviews.get(target)) is None
                or target_review.claim_sha256 != claims[target].fingerprint
                or (review.claim_id not in self._inherited and self.reasons(claims[target]))
                for target in targets
            ):
                raise ValueError(
                    "Corrections require content-bound, source-supported replacements."
                )
            self._superseded.add(review.claim_id)
            self._replacements[review.claim_id] = targets

    def superseded(self, claim_id: str) -> bool:
        """Only explicit, checked corrections remove earlier accounts from conflict checks."""
        return claim_id in self._superseded

    def validate_corrections(self, decisions: Sequence[AdmissionDecision]) -> None:
        """A support label cannot override domain safeguards on a corrective assertion."""
        by_id = {d.claim_id: d for d in decisions}
        for claim_id in self._superseded:
            if claim_id in self._inherited:
                continue
            for target in self._replacements[claim_id]:
                decision = by_id[target]
                if decision.status == "held" and not set(decision.reasons) <= {
                    "negated",
                    "non_biological",
                }:
                    raise ValueError("Correction replacement fails domain admission checks.")

    def review(self, claim_id: str) -> Review | None:
        """Retain the original review for additional typed obligations, including Crime."""
        return self._reviews.get(claim_id)

    def reasons(self, claim: _Claim) -> list[str]:
        reasons = []
        if not evidence_resolves(claim.evidence, self._passages):
            reasons.append("evidence_span")
        review = self.review(claim.claim_id)
        if (
            review is not None
            and review.claim_sha256 == claim.fingerprint
            and review.verdict in {"superseded", "disputed"}
        ):
            reasons.append(review.verdict)
        elif (
            review is None
            or review.claim_sha256 != claim.fingerprint
            or review.verdict != "supported"
        ):
            reasons.append("support_review_required")
        return reasons
