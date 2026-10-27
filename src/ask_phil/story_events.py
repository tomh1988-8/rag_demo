"""Reviewed crime and justice assertions; legal stages never establish commission."""

import hashlib
from typing import Literal, Self

from pydantic import Field, model_validator

from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record, SourceSnapshot
from ask_phil.identity import IdentityCatalogue
from ask_phil.parentage import AdmissionDecision, ClaimEvidence, ClaimReview, evidence_resolves

EventType = Literal[
    "commission",
    "accusation",
    "arrest",
    "charge",
    "trial",
    "conviction",
    "acquittal",
    "imprisonment",
    "release",
    "confession",
]
ParticipantRole = Literal[
    "perpetrator",
    "victim",
    "accused",
    "arrested",
    "defendant",
    "convicted",
    "acquitted",
    "prisoner",
    "released",
    "confessor",
    "witness",
    "accuser",
]
EVENT_ROLES: dict[str, tuple[str, frozenset[str]]] = {
    "commission": ("perpetrator", frozenset({"perpetrator", "victim"})),
    "accusation": ("accused", frozenset({"accused", "accuser"})),
    "arrest": ("arrested", frozenset({"arrested"})),
    "charge": ("accused", frozenset({"accused"})),
    "trial": ("defendant", frozenset({"defendant", "witness"})),
    "conviction": ("convicted", frozenset({"convicted"})),
    "acquittal": ("acquitted", frozenset({"acquitted"})),
    "imprisonment": ("prisoner", frozenset({"prisoner"})),
    "release": ("released", frozenset({"released"})),
    "confession": ("confessor", frozenset({"confessor"})),
}
EVENT_LIMITATION = (
    "Only admitted assertions about selected captured incidents are shown. An accusation, "
    "confession, charge, conviction, acquittal, imprisonment, release or court appearance "
    "alone establishes neither commission nor innocence. Only separately reviewed narrative "
    "support establishes commission. An empty legal history does not prove that a character "
    "committed no crime. Listing order is not chronology; unknown dates remain unknown. "
    "Source-supported does not mean independently cross-checked."
)


class EventParticipant(Record):
    character_id: Identifier
    role: ParticipantRole


class EventClaim(Record):
    claim_id: Identifier
    event_id: Identifier
    event_label: NonEmpty
    event_type: EventType
    basis: Literal["narrative", "allegation", "confession", "legal_outcome"]
    participants: tuple[EventParticipant, ...] = Field(min_length=1, max_length=8)
    account_status: Literal["as_reported", "explicitly_false"]
    polarity: Literal["affirmed", "negated"]
    certainty: Literal["certain", "uncertain"]
    story_time: NonEmpty
    time_precision: Literal["exact", "approximate", "relative", "unknown"]
    evidence: tuple[ClaimEvidence, ...] = Field(min_length=1, max_length=4)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ExtractedEvents(Record):
    claims: tuple[EventClaim, ...] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_claims(self) -> Self:
        if len({c.claim_id for c in self.claims}) != len(self.claims):
            raise ValueError("Claim identifiers must be unique within an extraction.")
        return self


class EventBatch(ExtractedEvents):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    catalogue: IdentityCatalogue
    extractor: NonEmpty

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class EventReview(ClaimReview):
    narrative_commission: bool = False


class EventAdmission(Record):
    batch_sha256: Fingerprint
    decisions: tuple[AdmissionDecision, ...]
    limitation: str = EVENT_LIMITATION


def admit_events(
    snapshot: SourceSnapshot, batch: EventBatch, reviews: tuple[EventReview, ...]
) -> EventAdmission:
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
    labels: dict[str, set[str]] = {}
    accounts: dict[tuple[object, ...], set[tuple[str, str]]] = {}
    for claim in batch.claims:
        labels.setdefault(claim.event_id, set()).add(claim.event_label)
        key = (
            claim.event_id,
            claim.event_type,
            tuple(sorted((p.character_id, p.role) for p in claim.participants)),
            claim.story_time,
            claim.time_precision,
        )
        accounts.setdefault(key, set()).add((claim.polarity, claim.account_status))
    decisions = []
    for claim in batch.claims:
        review = checked.get(claim.claim_id)
        reasons = []
        participants = {(p.character_id, p.role) for p in claim.participants}
        if not {p.character_id for p in claim.participants} <= identities:
            reasons.append("identity")
        required, allowed = EVENT_ROLES[claim.event_type]
        roles = {p.role for p in claim.participants}
        if (
            required not in roles
            or not roles <= allowed
            or len(participants) != len(claim.participants)
        ):
            reasons.append("participant_role")
        if not evidence_resolves(claim.evidence, passages):
            reasons.append("evidence_span")
        if (
            review is None
            or review.claim_sha256 != claim.fingerprint
            or review.verdict != "supported"
        ):
            reasons.append("support_review_required")
        if claim.event_type == "commission" and (
            claim.basis != "narrative" or review is None or not review.narrative_commission
        ):
            reasons.append("commission_support")
        expected_basis = (
            "narrative"
            if claim.event_type == "commission"
            else "allegation"
            if claim.event_type == "accusation"
            else "confession"
            if claim.event_type == "confession"
            else "legal_outcome"
        )
        if claim.basis != expected_basis:
            reasons.append("account_basis")
        if claim.account_status == "explicitly_false" and claim.event_type not in {
            "accusation",
            "confession",
        }:
            reasons.append("false_account")
        if claim.polarity != "affirmed":
            reasons.append("negated")
        if claim.certainty != "certain":
            reasons.append("uncertain")
        if (claim.time_precision == "unknown") != (claim.story_time == "unknown"):
            reasons.append("timing")
        key = (
            claim.event_id,
            claim.event_type,
            tuple(sorted(participants)),
            claim.story_time,
            claim.time_precision,
        )
        if len(accounts[key]) > 1:
            reasons.append("contradiction")
        if len(labels[claim.event_id]) > 1:
            reasons.append("event_collision")
        decisions.append(
            AdmissionDecision(
                claim_id=claim.claim_id,
                status="held" if reasons else "admitted",
                reasons=tuple(reasons),
            )
        )
    return EventAdmission(batch_sha256=batch.fingerprint, decisions=tuple(decisions))
