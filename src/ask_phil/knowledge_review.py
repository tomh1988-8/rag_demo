"""Maintainer-only review revisions, retaining prior Claims and publishing one usable version."""

import hashlib
from typing import Literal, Self
from uuid import uuid4

import psycopg
from llama_index.core.base.embeddings.base import BaseEmbedding
from psycopg.types.json import Jsonb
from pydantic import Field, model_validator

from ask_phil.claim_projections import EventAudit, FamilyAudit, GraphVersions, RelationshipAudit
from ask_phil.claims import ClaimReview, evidence_resolves, replacement_claim_ids
from ask_phil.classified_facts import ContextClaim
from ask_phil.event_graph import EventGraph
from ask_phil.evidence import Fingerprint, Identifier, Passage, Record
from ask_phil.execution import read_options
from ask_phil.family_graph import FamilyGraph
from ask_phil.ingestion import source_input_fingerprint
from ask_phil.parentage import ParentageClaim, admit_claims
from ask_phil.publications import PublicationNotFound, PublicationStore, RefreshRun
from ask_phil.refresh_journal import refresh_journal
from ask_phil.relationship_graph import RelationshipGraph
from ask_phil.relationships import RelationshipClaim, admit_relationships
from ask_phil.retrieval import TextRetriever
from ask_phil.review_notes import (
    ReviewedClaim,
    ReviewNotice,
    character_ids,
    describe_account,
    review_group,
)
from ask_phil.security import require_credential_free
from ask_phil.source_records import SourceBatch
from ask_phil.storage import EvidenceStore, SnapshotConflict
from ask_phil.story_events import EventClaim, EventReview, admit_events


class ReviewRequest(Record):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    graphs: GraphVersions
    family_reviews: tuple[ClaimReview, ...] = Field(default=(), max_length=100)
    relationship_reviews: tuple[ClaimReview, ...] = Field(default=(), max_length=100)
    event_reviews: tuple[EventReview, ...] = Field(default=(), max_length=200)
    new_family_claims: tuple[ParentageClaim, ...] = Field(default=(), max_length=100)
    new_relationship_claims: tuple[RelationshipClaim, ...] = Field(default=(), max_length=100)
    new_event_claims: tuple[EventClaim, ...] = Field(default=(), max_length=100)
    new_context_claims: tuple[ContextClaim, ...] = Field(default=(), max_length=100)

    @model_validator(mode="after")
    def explicit_changes(self) -> Self:
        groups = (self.family_reviews, self.relationship_reviews, self.event_reviews)
        if not any(groups):
            raise ValueError("A review revision needs at least one explicit outcome and rationale.")
        if any(len({r.claim_id for r in group}) != len(group) for group in groups):
            raise ValueError("Each Claim can have only one outcome per review revision.")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()


class ReviewRevision(Record):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    request: ReviewRequest


class ReviewInspection(Record):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    graphs: GraphVersions
    family: FamilyAudit | None
    relationship: RelationshipAudit | None
    event: EventAudit | None
    evidence: tuple[Passage, ...]
    history: tuple[ReviewRevision, ...]
    limitation: str = (
        "Reviews record source support and interpretation, not independent corroboration. "
        "Earlier snapshots retain original reviews, Claims and evidence."
    )


def review_revision(database_url: str, snapshot_id: str) -> ReviewRevision | None:
    with psycopg.connect(database_url, connect_timeout=5, options=read_options()) as conn:
        if conn.execute("SELECT to_regclass('review_revisions')").fetchone() == (None,):
            return None
        row = conn.execute(
            "SELECT document FROM review_revisions WHERE snapshot_id=%s", (snapshot_id,)
        ).fetchone()
    return ReviewRevision.model_validate(row[0]) if row else None


def inspect_reviews(database_url: str, snapshot_id: str) -> ReviewInspection:
    snapshot = EvidenceStore(database_url).snapshot(snapshot_id)
    family = FamilyGraph(database_url).audit(snapshot_id)
    relationship = RelationshipGraph(database_url).audit(snapshot_id)
    event = EventGraph(database_url).audit(snapshot_id)
    evidence_ids = {
        span.evidence_id
        for audit in (family, relationship, event)
        if audit is not None
        for claim in audit.batch.claims
        for span in claim.evidence
    }
    if event:
        evidence_ids.update(e.evidence_id for c in event.batch.context_claims for e in c.evidence)
    history: list[ReviewRevision] = []
    selected = snapshot_id
    while revision := review_revision(database_url, selected):
        if len(history) >= 100 or any(r.snapshot_id == selected for r in history):
            raise ValueError(
                "Review history is cyclic or exceeds the 100-revision inspection bound."
            )
        history.append(revision)
        selected = revision.request.snapshot_id
    return ReviewInspection(
        snapshot_id=snapshot_id,
        snapshot_sha256=snapshot.fingerprint,
        graphs=GraphVersions(
            family=family.graph_sha256 if family else None,
            relationship=relationship.graph_sha256 if relationship else None,
            event=event.graph_sha256 if event else None,
        ),
        family=family,
        relationship=relationship,
        event=event,
        evidence=tuple(p for p in snapshot.passages if p.evidence_id in evidence_ids),
        history=tuple(reversed(history)),
    )


def review_notices(database_url: str, snapshot_id: str) -> tuple[ReviewNotice, ...]:
    """Only review revisions change serving interpretation; legacy snapshots retain behavior."""
    if review_revision(database_url, snapshot_id) is None:
        return ()
    inspection = inspect_reviews(database_url, snapshot_id)
    passages = {p.evidence_id: p for p in inspection.evidence}
    notices = []
    kinds: tuple[Literal["family", "relationship", "event"], ...] = (
        "family",
        "relationship",
        "event",
    )
    for kind, audit in zip(
        kinds, (inspection.family, inspection.relationship, inspection.event), strict=True
    ):
        if audit is None:
            continue
        claims: dict[str, ReviewedClaim] = {c.claim_id: c for c in audit.batch.claims}
        decisions = list(audit.admission.decisions)
        if isinstance(audit, EventAudit):
            claims.update({c.claim_id: c for c in audit.batch.context_claims})
            decisions.extend(audit.admission.text_decisions)
        names = {c.character_id: c.name for c in audit.batch.catalogue.characters}
        reviews = {r.claim_id: r for r in audit.reviews}
        for decision in decisions:
            if decision.status != "held" or set(decision.reasons) <= {"non_biological", "negated"}:
                continue
            claim = claims[decision.claim_id]
            review = reviews.get(claim.claim_id)
            disputed = (
                bool(review and review.verdict == "disputed") or "contradiction" in decision.reasons
            )
            targets = (
                tuple(claims[cid] for cid in replacement_claim_ids(claim.claim_id, reviews))
                if review and review.verdict == "superseded"
                else ()
            )
            accounts = (claim, *targets)
            spans = tuple(
                e for c in accounts for e in c.evidence if evidence_resolves((e,), passages)
            )
            if not spans:
                continue
            if review and review.verdict == "superseded":
                label = "Superseded claim (not current)"
            elif disputed:
                label = "Unresolved source disagreement (no established connection)"
            else:
                label = "Held claim (not established)"
            explanation = f"{label}: {describe_account(claim, names)}."
            for target in targets:
                target_decision = next(d for d in decisions if d.claim_id == target.claim_id)
                current = (
                    "Current replacement source account"
                    if target_decision.status == "admitted"
                    or set(target_decision.reasons) <= {"non_biological", "negated"}
                    else "Current replacement remains held"
                )
                explanation += f" {current}: {describe_account(target, names)}."
            if not review:
                explanation += " A content-bound support review is still required."
            explanation += (
                " Source passages: " + ", ".join(dict.fromkeys(e.evidence_id for e in spans)) + "."
            )
            notices.append(
                ReviewNotice(
                    family=kind,
                    claim_id=claim.claim_id,
                    character_ids=tuple(sorted({i for c in accounts for i in character_ids(c)})),
                    evidence_ids=tuple(dict.fromkeys(e.evidence_id for e in spans)),
                    explanation=explanation,
                    group_id=review_group(claim),
                    related_group_ids=tuple(sorted({review_group(c) for c in targets})),
                    disputed=disputed,
                    reviewer=review.reviewer if review else None,
                    rationale=review.note if review else None,
                )
            )
    return tuple(notices)


def _reviews[R: ClaimReview](
    existing: tuple[R, ...], changes: tuple[R, ...], fingerprints: dict[str, str]
) -> tuple[R, ...]:
    if any(fingerprints.get(r.claim_id) != r.claim_sha256 for r in changes):
        raise ValueError(
            "A review must identify the exact retained Claim content in this projection."
        )
    merged = {r.claim_id: r for r in existing}
    merged.update({r.claim_id: r for r in changes})
    return tuple(merged[key] for key in sorted(merged))


def _extend_batch[B: Record](
    batch: B, field: str, additions: tuple[ReviewedClaim, ...], reviews: tuple[ClaimReview, ...]
) -> B:
    document = batch.model_dump(mode="json")
    previous = {c["claim_id"] for c in document[field]}
    added = {c.claim_id for c in additions}
    if previous.intersection(added) or len(added) != len(additions):
        raise ValueError("New Claims must have distinct IDs; existing raw Claims cannot be edited.")
    if not added <= {r.claim_id for r in reviews}:
        raise ValueError("Every new Claim requires an explicit review outcome.")
    document[field].extend(c.model_dump(mode="json") for c in additions)
    return batch.model_validate(document)


class KnowledgeReview:
    def __init__(
        self, database_url: str, embedding: BaseEmbedding, embedding_id: str, dimensions: int
    ) -> None:
        self.database_url = database_url
        self.publications = PublicationStore(database_url)
        self.retriever = TextRetriever(database_url, embedding, embedding_id, dimensions)

    def inspect(self, snapshot_id: str) -> ReviewInspection:
        return inspect_reviews(self.database_url, snapshot_id)

    def apply(self, request: ReviewRequest) -> RefreshRun:
        """Stage immutable artifacts and switch the shared publication pointer only when ready."""
        require_credential_free(request.model_dump_json())
        with refresh_journal(self.publications, uuid4(), action="review") as journal:
            before = self.inspect(request.snapshot_id)
            if (before.snapshot_sha256, before.graphs) != (request.snapshot_sha256, request.graphs):
                raise ValueError("The review input differs from the inspected source or Claims.")
            if len(before.history) >= 100:
                raise ValueError("The review history has reached its inspection bound.")
            original = EvidenceStore(self.database_url).snapshot(request.snapshot_id)
            snapshot = original.model_copy(update={"snapshot_id": "review-" + request.fingerprint})
            try:
                active = self.publications.active()
            except PublicationNotFound:
                active = None
            if active and active.manifest.snapshot_id not in {
                request.snapshot_id,
                snapshot.snapshot_id,
            }:
                raise ValueError("The active version changed; inspect it before reviewing again.")
            bindings = {
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_sha256": snapshot.fingerprint,
            }
            family = before.family
            relationship = before.relationship
            event = before.event
            for audit, changes in (
                (family, bool(request.family_reviews or request.new_family_claims)),
                (
                    relationship,
                    bool(request.relationship_reviews or request.new_relationship_claims),
                ),
                (
                    event,
                    bool(
                        request.event_reviews
                        or request.new_event_claims
                        or request.new_context_claims
                    ),
                ),
            ):
                if changes and audit is None:
                    raise ValueError("Review requires an existing retained Claim projection.")
            if family:
                family = family.model_copy(
                    update={
                        "batch": _extend_batch(
                            family.batch,
                            "claims",
                            request.new_family_claims,
                            request.family_reviews,
                        )
                    }
                )
            if relationship:
                relationship = relationship.model_copy(
                    update={
                        "batch": _extend_batch(
                            relationship.batch,
                            "claims",
                            request.new_relationship_claims,
                            request.relationship_reviews,
                        )
                    }
                )
            if event:
                expanded = _extend_batch(
                    event.batch, "claims", request.new_event_claims, request.event_reviews
                )
                event = event.model_copy(
                    update={
                        "batch": _extend_batch(
                            expanded,
                            "context_claims",
                            request.new_context_claims,
                            request.event_reviews,
                        )
                    }
                )
            family_reviews = (
                _reviews(
                    family.reviews,
                    request.family_reviews,
                    {c.claim_id: c.fingerprint for c in family.batch.claims},
                )
                if family
                else ()
            )
            relationship_reviews = (
                _reviews(
                    relationship.reviews,
                    request.relationship_reviews,
                    {c.claim_id: c.fingerprint for c in relationship.batch.claims},
                )
                if relationship
                else ()
            )
            event_reviews = (
                _reviews(
                    event.reviews,
                    request.event_reviews,
                    {c.claim_id: c.fingerprint for c in event.batch.claims}
                    | {c.claim_id: c.fingerprint for c in event.batch.context_claims},
                )
                if event
                else ()
            )
            # Validate every family before staging any projection. Earlier raw Claims stay intact.
            if family:
                admit_claims(
                    snapshot,
                    family.batch.model_copy(update=bindings),
                    family_reviews,
                    prior_reviews=family.reviews,
                )
            if relationship:
                admit_relationships(
                    snapshot,
                    relationship.batch.model_copy(update=bindings),
                    relationship_reviews,
                    prior_reviews=relationship.reviews,
                )
            if event:
                admit_events(
                    snapshot,
                    event.batch.model_copy(update=bindings),
                    event_reviews,
                    prior_reviews=event.reviews,
                )
            source_input = (
                source_input_fingerprint(
                    SourceBatch(
                        format_version=original.imported.format_version,
                        catalogue=original.imported.catalogue,
                        policies=original.imported.policies,
                        captures=original.imported.captures,
                    )
                )
                if original.imported
                else original.fingerprint
            )
            journal.stage_review(snapshot, source_input)
            revision = ReviewRevision(
                snapshot_id=snapshot.snapshot_id,
                snapshot_sha256=snapshot.fingerprint,
                request=request,
            )
            self._retain(revision)
            if family:
                FamilyGraph(self.database_url).install(
                    family.batch.model_copy(update=bindings), family_reviews
                )
            if relationship:
                RelationshipGraph(self.database_url).install(
                    relationship.batch.model_copy(update=bindings), relationship_reviews
                )
            if event:
                EventGraph(self.database_url).install(
                    event.batch.model_copy(update=bindings), event_reviews
                )
            index = journal.prepare(snapshot, self.retriever)
            return journal.publish(snapshot, index)

    def _retain(self, revision: ReviewRevision) -> None:
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS review_revisions (
                snapshot_id text PRIMARY KEY REFERENCES source_snapshots(snapshot_id),
                document jsonb NOT NULL)""")
            conn.execute(
                "INSERT INTO review_revisions VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (revision.snapshot_id, Jsonb(revision.model_dump(mode="json"))),
            )
            row = conn.execute(
                "SELECT document FROM review_revisions WHERE snapshot_id=%s",
                (revision.snapshot_id,),
            ).fetchone()
            if row is None or ReviewRevision.model_validate(row[0]) != revision:
                raise SnapshotConflict("Review revisions are immutable.")
