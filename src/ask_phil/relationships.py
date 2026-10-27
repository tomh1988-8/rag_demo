"""Reviewed relationship assertions, episode identity and supported partial ordering."""

import hashlib
from typing import Literal, Self

from pydantic import Field, model_validator

from ask_phil.claims import AdmissionDecision, ClaimAdmission, ClaimEvidence, ClaimReview
from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record, SourceSnapshot
from ask_phil.identity import IdentityCatalogue

Relation = Literal[
    "biological_parent",
    "adoptive_parent",
    "step_parent",
    "ward",
    "marriage",
    "separation",
    "divorce",
    "reconciliation",
    "remarriage",
    "affair",
    "partnership",
]
DIRECTED_RELATIONS = frozenset({"biological_parent", "adoptive_parent", "step_parent", "ward"})
HISTORY_LIMITATION = (
    "Only admitted assertions from selected reviewed spans are shown. Social ties never "
    "establish biological ancestry. Status is as reported in the captured account, not a "
    "claim about the present. Only explicit after links establish ordering; otherwise "
    "listing order is not chronology. Missing history does not prove a relationship never "
    "existed. Source-supported does not mean independently cross-checked."
)


class RelationshipClaim(Record):
    claim_id: Identifier
    subject_id: Identifier
    object_id: Identifier
    relation: Relation
    episode_id: Identifier
    status: Literal["current", "former", "unknown"]
    polarity: Literal["affirmed", "negated"]
    certainty: Literal["certain", "uncertain"]
    story_time: NonEmpty
    time_precision: Literal["exact", "approximate", "relative", "unknown"]
    after_claim_id: Identifier | None
    evidence: tuple[ClaimEvidence, ...] = Field(min_length=1, max_length=4)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()

    @property
    def participants(self) -> tuple[str, str]:
        if self.relation in DIRECTED_RELATIONS:
            return self.subject_id, self.object_id
        first, second = sorted((self.subject_id, self.object_id))
        return first, second

    @property
    def assertion(self) -> tuple[object, ...]:
        return (
            self.participants,
            self.relation,
            self.story_time,
            self.time_precision,
        )


class ExtractedRelationships(Record):
    claims: tuple[RelationshipClaim, ...] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_claims(self) -> Self:
        if len({c.claim_id for c in self.claims}) != len(self.claims):
            raise ValueError("Claim identifiers must be unique within an extraction.")
        return self


class RelationshipBatch(ExtractedRelationships):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    catalogue: IdentityCatalogue
    extractor: NonEmpty

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class RelationshipAdmission(Record):
    batch_sha256: Fingerprint
    decisions: tuple[AdmissionDecision, ...]
    limitation: str = HISTORY_LIMITATION


def admit_relationships(
    snapshot: SourceSnapshot, batch: RelationshipBatch, reviews: tuple[ClaimReview, ...]
) -> RelationshipAdmission:
    """Review exact content, preserving unadmitted claims independently of the projection."""
    admission = ClaimAdmission(snapshot, batch, reviews)
    claims_by_id = {c.claim_id: c for c in batch.claims}
    episodes: dict[str, list[RelationshipClaim]] = {}
    polarities: dict[tuple[object, ...], set[str]] = {}
    for claim in batch.claims:
        episodes.setdefault(claim.episode_id, []).append(claim)
        polarities.setdefault(claim.assertion, set()).add(claim.polarity)
    collided = {
        episode
        for episode, claims in episodes.items()
        if len(
            {
                (c.participants, c.relation if c.relation in DIRECTED_RELATIONS else "romantic")
                for c in claims
            }
        )
        > 1
        or len(
            {
                (c.relation, c.story_time, c.time_precision)
                for c in claims
                if c.relation in {"marriage", "remarriage"}
            }
        )
        > 1
    }
    decisions = []
    for claim in batch.claims:
        reasons = []
        if (
            claim.subject_id == claim.object_id
            or not {claim.subject_id, claim.object_id} <= admission.character_ids
        ):
            reasons.append("identity")
        reasons.extend(admission.reasons(claim))
        if claim.polarity != "affirmed":
            reasons.append("negated")
        if claim.certainty != "certain":
            reasons.append("uncertain")
        if claim.relation == "divorce" and claim.status == "current":
            reasons.append("status")
        if len(polarities[claim.assertion]) > 1:
            reasons.append("contradiction")
        if claim.episode_id in collided:
            reasons.append("episode_collision")
        if (claim.time_precision == "unknown") != (claim.story_time == "unknown"):
            reasons.append("timing")
        previous = claims_by_id.get(claim.after_claim_id or "")
        if claim.after_claim_id is not None and (
            previous is None or previous.participants != claim.participants
        ):
            reasons.append("ordering")
        decisions.append(
            AdmissionDecision(
                claim_id=claim.claim_id,
                status="held" if reasons else "admitted",
                reasons=tuple(reasons),
            )
        )
    statuses = {d.claim_id: d.status for d in decisions}
    for index, decision in enumerate(decisions):
        if decision.status == "held":
            continue
        visited = {decision.claim_id}
        previous_id = claims_by_id[decision.claim_id].after_claim_id
        while previous_id is not None:
            if previous_id in visited or statuses.get(previous_id) != "admitted":
                decisions[index] = AdmissionDecision(
                    claim_id=decision.claim_id, status="held", reasons=("ordering",)
                )
                break
            visited.add(previous_id)
            previous_id = claims_by_id[previous_id].after_claim_id
    return RelationshipAdmission(batch_sha256=batch.fingerprint, decisions=tuple(decisions))
