"""Independent reference checks; resolvable evidence does not establish a step's meaning."""

from typing import Literal

from pydantic import Field

from ask_phil.claims import evidence_resolves
from ask_phil.classified_facts import ContextClaim
from ask_phil.connection_graph import (
    BiologicalStep,
    ConnectionMeaning,
    ConnectionQuery,
    ConnectionResult,
    RelationshipStep,
)
from ask_phil.evidence import Fingerprint, Identifier, Record, SourceSnapshot
from ask_phil.identity import IdentityCatalogue
from ask_phil.parentage import ParentageClaim
from ask_phil.relationships import RelationshipClaim
from ask_phil.story_events import EventClaim


class ConnectionCase(Record):
    case_id: Identifier
    category: str
    character_id: Identifier
    target_id: Identifier
    max_depth: int
    status: Literal["found", "empty", "unknown_character"]
    acceptable_paths: tuple[tuple[Identifier, ...], ...]
    require_all_alternatives: bool = False
    required_claims: tuple[Identifier, ...] = ()
    derived_meaning: ConnectionMeaning | None = None
    forbidden_meanings: tuple[ConnectionMeaning, ...] = ()
    forbidden_text: tuple[str, ...] = ()

    @property
    def query(self) -> ConnectionQuery:
        return ConnectionQuery(
            kind="connection",
            character_id=self.character_id,
            target_id=self.target_id,
            max_depth=self.max_depth,
        )


class ConnectionReference(Record):
    version: Literal[1]
    split: Literal["exposed_development"]
    synthetic: bool
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    catalogue: IdentityCatalogue
    origins: dict[str, Fingerprint]
    family_claims: tuple[ParentageClaim, ...]
    relationship_claims: tuple[RelationshipClaim, ...]
    event_claims: tuple[EventClaim, ...]
    context_claims: tuple[ContextClaim, ...]
    cases: tuple[ConnectionCase, ...]
    review_note: str


class ConnectionScores(Record):
    result_correct: bool
    step_meanings_correct: bool
    provenance_resolves: bool
    steps_scored: int = Field(ge=0)
    evidence_spans_scored: int = Field(ge=0)
    limitation: str = (
        "Exposed reviewed reference comparison; final answer support is assessed separately. "
        "Resolvable locators do not independently corroborate claims or establish canon accuracy."
    )


def score_connection(
    result: ConnectionResult,
    case: ConnectionCase,
    reference: ConnectionReference,
    snapshot: SourceSnapshot,
) -> ConnectionScores:
    if (reference.snapshot_id, reference.snapshot_sha256) != (
        snapshot.snapshot_id,
        snapshot.fingerprint,
    ):
        raise ValueError("The reference must describe the exact evaluated source snapshot.")
    actual = {p.characters for p in result.paths}
    allowed = set(case.acceptable_paths)
    correct = (
        result.query == case.query
        and result.snapshot_id == snapshot.snapshot_id
        and result.snapshot_sha256 == snapshot.fingerprint
        and result.status == case.status
        and actual <= allowed
        and (bool(actual) if case.status == "found" else not actual)
        and (not case.require_all_alternatives or actual == allowed)
    )
    families = {c.claim_id: c for c in reference.family_claims}
    relationships = {c.claim_id: c for c in reference.relationship_claims}
    events = {c.claim_id: c for c in reference.event_claims}
    meanings = True
    present_claims: set[str] = set()
    steps = [s for p in result.paths for s in p.steps]
    for step in steps:
        if isinstance(step, BiologicalStep):
            expected = [families.get(cid) for cid in step.edge.claim_ids]
            meanings &= all(
                c is not None
                and c.relation == "biological_parent"
                and (c.parent_id, c.child_id) == (step.edge.parent_id, step.edge.child_id)
                for c in expected
            )
            meanings &= step.evidence == tuple(e for c in expected if c for e in c.evidence)
            present_claims.update(step.edge.claim_ids)
        elif isinstance(step, RelationshipStep):
            meanings &= relationships.get(step.claim.claim_id) == step.claim
            present_claims.add(step.claim.claim_id)
        else:
            meanings &= all(events.get(c.claim_id) == c for c in step.claims)
            present_claims.update(c.claim_id for c in step.claims)
    meanings &= set(case.required_claims) <= present_claims
    meanings &= all(
        p.meaning not in case.forbidden_meanings
        and (case.derived_meaning is None or p.meaning == case.derived_meaning)
        for p in result.paths
    )
    evidence = tuple(e for s in steps for e in s.evidence)
    return ConnectionScores(
        result_correct=correct,
        step_meanings_correct=meanings,
        provenance_resolves=evidence_resolves(
            evidence, {p.evidence_id: p for p in snapshot.passages}
        ),
        steps_scored=len(steps),
        evidence_spans_scored=len(evidence),
    )
