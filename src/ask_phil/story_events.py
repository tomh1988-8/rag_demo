"""Reviewed story events; participant roles retain each assertion's meaning."""

import hashlib
from typing import Any, Literal, Self

from pydantic import ConfigDict, Field, model_validator

from ask_phil.claims import AdmissionDecision, ClaimAdmission, ClaimEvidence, ClaimReview
from ask_phil.classified_facts import ContextClaim
from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record, SourceSnapshot
from ask_phil.identity import IdentityCatalogue

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
    "pregnancy",
    "death",
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
    "pregnant_person",
    "deceased",
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
    "pregnancy": ("pregnant_person", frozenset({"pregnant_person"})),
    "death": ("deceased", frozenset({"deceased"})),
}
EVENT_LIMITATION = (
    "Only admitted assertions about selected captured incidents are shown. An accusation, "
    "confession, charge, conviction, acquittal, imprisonment, release or court appearance "
    "alone establishes neither commission nor innocence. Only separately reviewed narrative "
    "support establishes commission. An empty legal history does not prove that a character "
    "committed no crime. Listing order is not chronology; unknown dates remain unknown. "
    "Source-supported does not mean independently cross-checked."
)
LIFE_EVENT_TYPES = ("pregnancy", "death")
LIFE_EVENT_LIMITATION = (
    "Only reviewed pregnancy and death assertions in selected captured passages are shown. "
    "Pregnancy does not establish unmentioned parentage; death does not establish a crime "
    "or an unmentioned witness. Themes and unclassified facts remain text-only and do not "
    "create shared events or relationships. Listing order is not chronology; unknown dates "
    "remain unknown, and a funeral date does not establish a death date. An empty result "
    "does not establish that an event never happened. Source-supported does not mean "
    "independently cross-checked."
)
CLASSIFICATION_LIMITATION = (
    "Themes describe subjects, not event types. A shared theme or co-appearance does not "
    "establish a character relationship or shared event. Unclassified facts have no checked "
    "graph category. Use the text route for supported themes and unclassified facts; "
    "graph absence does not establish that those facts are false."
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

    @property
    def assertion(self) -> tuple[object, ...]:
        """Source-anchored meaning, independently of generated claim/incident ID spelling."""
        return (
            self.event_type,
            tuple(sorted((p.character_id, p.role) for p in self.participants)),
            self.basis,
            self.account_status,
            self.polarity,
            self.certainty,
            self.story_time,
            self.time_precision,
            tuple(sorted({e.evidence_id for e in self.evidence})),
        )


def _require_classifications(schema: dict[str, Any]) -> None:
    # Newly requested structured output must emit both lists. Legacy retained
    # batches may still omit the previously unavailable text annotations.
    schema["required"] = list(dict.fromkeys([*schema.get("required", []), "context_claims"]))
    schema["properties"]["context_claims"].pop("default", None)


class ExtractedEvents(Record):
    claims: tuple[EventClaim, ...] = Field(max_length=100)
    context_claims: tuple[ContextClaim, ...] = Field(
        default=(), max_length=100, exclude_if=lambda value: not value
    )

    @model_validator(mode="after")
    def unique_claims(self) -> Self:
        claims: tuple[EventClaim | ContextClaim, ...] = (*self.claims, *self.context_claims)
        if len({c.claim_id for c in claims}) != len(claims):
            raise ValueError("Claim identifiers must be unique within an extraction.")
        return self


class EventExtractionOutput(ExtractedEvents):
    """Strict provider output keeps both lists explicit, independently of legacy API batches."""

    model_config = ConfigDict(json_schema_extra=_require_classifications)


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
    text_decisions: tuple[AdmissionDecision, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    limitation: str = EVENT_LIMITATION


def admit_events(
    snapshot: SourceSnapshot, batch: EventBatch, reviews: tuple[EventReview, ...]
) -> EventAdmission:
    admission = ClaimAdmission(snapshot, batch, reviews, extra_claims=batch.context_claims)
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
        review = admission.review(claim.claim_id)
        reasons = []
        participants = {(p.character_id, p.role) for p in claim.participants}
        if not {p.character_id for p in claim.participants} <= admission.character_ids:
            reasons.append("identity")
        required, allowed = EVENT_ROLES[claim.event_type]
        roles = {p.role for p in claim.participants}
        if (
            required not in roles
            or not roles <= allowed
            or len(participants) != len(claim.participants)
        ):
            reasons.append("participant_role")
        reasons.extend(admission.reasons(claim))
        if claim.event_type == "commission" and (
            claim.basis != "narrative" or review is None or not review.narrative_commission
        ):
            reasons.append("commission_support")
        expected_basis = (
            "narrative"
            if claim.event_type in {"commission", "pregnancy", "death"}
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
    text_decisions = []
    for fact in batch.context_claims:
        reasons = []
        if not set(fact.character_ids) <= admission.character_ids:
            reasons.append("identity")
        reasons.extend(admission.reasons(fact))
        text_decisions.append(
            AdmissionDecision(
                claim_id=fact.claim_id,
                status="held" if reasons else "admitted",
                reasons=tuple(reasons),
            )
        )
    return EventAdmission(
        batch_sha256=batch.fingerprint,
        decisions=tuple(decisions),
        text_decisions=tuple(text_decisions),
    )
