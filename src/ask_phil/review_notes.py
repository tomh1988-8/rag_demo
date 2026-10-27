"""Qualified, deterministic explanations of retained review outcomes."""

from dataclasses import dataclass
from typing import Literal

from ask_phil.claim_projections import EventAudit
from ask_phil.claims import evidence_resolves, replacement_claim_ids
from ask_phil.classified_facts import ContextClaim
from ask_phil.event_graph import EventResult
from ask_phil.evidence import Identifier, Passage, Record, SourceSnapshot
from ask_phil.execution import ExecutionStopped
from ask_phil.family_graph import FamilyResult
from ask_phil.parentage import ParentageClaim
from ask_phil.passage_context import context_text
from ask_phil.relationship_graph import RelationshipResult
from ask_phil.relationships import RelationshipClaim
from ask_phil.story_events import EventClaim

type ReviewedClaim = ParentageClaim | RelationshipClaim | EventClaim | ContextClaim
REVIEW_WORDING = (
    "reviewed-interpretations-v1: source accounts, explicit outcomes and retained rationale"
)


class ReviewNotice(Record):
    family: Literal["family", "relationship", "event"]
    claim_id: Identifier
    character_ids: tuple[Identifier, ...]
    evidence_ids: tuple[Identifier, ...]
    explanation: str
    group_id: str
    related_group_ids: tuple[str, ...] = ()
    disputed: bool = False
    reviewer: str | None = None
    rationale: str | None = None


def _review_group(claim: ReviewedClaim) -> str:
    if isinstance(claim, ParentageClaim):
        return "parentage:" + claim.child_id
    if isinstance(claim, RelationshipClaim):
        return "relationship:" + claim.episode_id
    if isinstance(claim, EventClaim):
        return "event:" + claim.event_id
    return claim.kind + ":" + ",".join(sorted(claim.character_ids))


def _complete_review_groups(
    notices: tuple[ReviewNotice, ...], selected: tuple[ReviewNotice, ...]
) -> tuple[ReviewNotice, ...]:
    """Keep connected correction and competing-account groups together."""
    groups = {g for n in selected for g in (n.group_id, *n.related_group_ids)}
    while True:
        complete = tuple(
            n for n in notices if groups.intersection((n.group_id, *n.related_group_ids))
        )
        expanded = groups | {g for n in complete for g in (n.group_id, *n.related_group_ids)}
        if expanded == groups:
            return complete
        groups = expanded


def _character_ids(claim: ReviewedClaim) -> tuple[str, ...]:
    if isinstance(claim, ParentageClaim):
        return claim.parent_id, claim.child_id
    if isinstance(claim, RelationshipClaim):
        return claim.subject_id, claim.object_id
    if isinstance(claim, EventClaim):
        return tuple(p.character_id for p in claim.participants)
    return claim.character_ids


def _describe_account(claim: ReviewedClaim, names: dict[str, str]) -> str:
    if isinstance(claim, ContextClaim):
        return claim.qualification
    timing = (
        "story date unknown"
        if claim.time_precision == "unknown"
        else f"{claim.story_time} ({claim.time_precision})"
    )
    if isinstance(claim, ParentageClaim):
        account = (
            f"{names.get(claim.parent_id, claim.parent_id)} as "
            f"{names.get(claim.child_id, claim.child_id)}'s "
            f"{claim.relation.removesuffix('_parent').replace('_', ' ')} {claim.parent_role}"
        )
    elif isinstance(claim, RelationshipClaim):
        account = (
            f"{names.get(claim.subject_id, claim.subject_id)} and "
            f"{names.get(claim.object_id, claim.object_id)}: {claim.relation.replace('_', ' ')}; "
            f"status {claim.status}; episode {claim.episode_id}"
        )
    else:
        account = f"{claim.event_label}: {claim.event_type}; " + "; ".join(
            f"{names.get(p.character_id, p.character_id)} ({p.role.replace('_', ' ')})"
            for p in claim.participants
        )
        account += f"; {claim.basis.replace('_', ' ')}; {claim.account_status.replace('_', ' ')}"
    qualification = ""
    if claim.polarity == "negated":
        qualification += "; explicitly negated"
    if claim.certainty == "uncertain":
        qualification += "; uncertain"
    return f"{account}{qualification}; {timing}"


def _render_notices(notices: tuple[ReviewNotice, ...], *, synthetic: bool) -> str:
    label = "Synthetic review example, not EastEnders canon. " if synthetic else ""
    rationales = tuple(
        dict.fromkeys(
            f"Review rationale ({n.reviewer}): {n.rationale}" for n in notices if n.rationale
        )
    )
    return (
        label
        + "\n".join(dict.fromkeys(n.explanation for n in notices))
        + ("\n" + "\n".join(rationales) if rationales else "")
        + "\nThis is source review, not independent corroboration. "
        "Coverage outside these reviewed accounts remains unknown."
    )


@dataclass(frozen=True)
class ReviewExplanation:
    """An indivisible explanation and the complete captured evidence it can cite."""

    notices: tuple[ReviewNotice, ...] = ()
    context: tuple[Passage, ...] = ()
    text: str = ""
    synthetic: bool = False


def _explanation(
    snapshot: SourceSnapshot, notices: tuple[ReviewNotice, ...], evidence_ids: set[str]
) -> ReviewExplanation | None:
    context = tuple(p for p in snapshot.passages if p.evidence_id in evidence_ids)
    if len(context) != len(evidence_ids):
        return None
    synthetic = any(
        (p.source or snapshot.source).support_status == "synthetic_fixture" for p in context
    )
    return ReviewExplanation(
        notices=notices,
        context=context,
        text=_render_notices(notices, synthetic=synthetic) if notices else "",
        synthetic=synthetic,
    )


def _wording_bytes(snapshot: SourceSnapshot, explanation: ReviewExplanation) -> int:
    if not explanation.notices:
        return 0
    # Existing budgets use the snapshot's qualification; final wording also considers
    # passage-specific provenance. Preserve that distinction for mixed-source captures.
    synthetic = snapshot.source.support_status == "synthetic_fixture"
    text = (
        explanation.text
        if synthetic == explanation.synthetic
        else _render_notices(explanation.notices, synthetic=synthetic)
    )
    return len(text.encode())


def retrieved_review_notices(
    database_url: str, snapshot_id: str, evidence_ids: set[str]
) -> tuple[ReviewNotice, ...]:
    """A retrieved predecessor brings every connected correction and competing account."""
    notices = review_notices(database_url, snapshot_id)
    return _complete_review_groups(
        notices, tuple(n for n in notices if evidence_ids.intersection(n.evidence_ids))
    )


def prepare_text_review(
    snapshot: SourceSnapshot, notices: tuple[ReviewNotice, ...], byte_budget: int
) -> ReviewExplanation:
    """Keep every reviewed account within the existing text citation and byte limits."""
    explanation = _explanation(snapshot, notices, {eid for n in notices for eid in n.evidence_ids})
    if (
        explanation is None
        or len(explanation.context) > 3
        or len(context_text(explanation.context).encode()) + _wording_bytes(snapshot, explanation)
        > byte_budget
    ):
        return ReviewExplanation()
    return explanation


def prepare_graph_review(
    database_url: str,
    snapshot: SourceSnapshot,
    result: FamilyResult | RelationshipResult | EventResult,
    byte_budget: int,
) -> ReviewExplanation:
    """Complete the graph's evidence and relevant review groups, or stop without an excerpt."""
    family = (
        "event"
        if isinstance(result, EventResult)
        else "relationship"
        if isinstance(result, RelationshipResult)
        else "family"
    )
    notices: tuple[ReviewNotice, ...] = ()
    if result.status not in {"unknown_character", "ineligible", "unavailable"}:
        all_notices = review_notices(database_url, snapshot.snapshot_id)
        notices = _complete_review_groups(
            all_notices,
            tuple(
                n
                for n in all_notices
                if n.family == family and result.query.character_id in n.character_ids
            ),
        )
    evidence_ids = (
        {e.evidence_id for c in result.claims for e in c.evidence}
        if isinstance(result, RelationshipResult | EventResult)
        else {e.evidence_id for p in result.paths for edge in p.edges for e in edge.evidence}
    )
    evidence_ids.update(eid for n in notices for eid in n.evidence_ids)
    explanation = _explanation(snapshot, notices, evidence_ids)
    if explanation is None:
        raise ExecutionStopped("malformed_output")
    if (
        sum(len(p.text.encode()) for p in explanation.context)
        + _wording_bytes(snapshot, explanation)
        > byte_budget
    ):
        raise ExecutionStopped("context_limit")
    return explanation


def review_notices(database_url: str, snapshot_id: str) -> tuple[ReviewNotice, ...]:
    """Only review revisions change serving interpretation; legacy snapshots retain behavior."""
    from ask_phil.knowledge_review import inspect_reviews, review_revision

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
            explanation = f"{label}: {_describe_account(claim, names)}."
            for target in targets:
                target_decision = next(d for d in decisions if d.claim_id == target.claim_id)
                current = (
                    "Current replacement source account"
                    if target_decision.status == "admitted"
                    or set(target_decision.reasons) <= {"non_biological", "negated"}
                    else "Current replacement remains held"
                )
                explanation += f" {current}: {_describe_account(target, names)}."
            if not review:
                explanation += " A content-bound support review is still required."
            explanation += (
                " Source passages: " + ", ".join(dict.fromkeys(e.evidence_id for e in spans)) + "."
            )
            notices.append(
                ReviewNotice(
                    family=kind,
                    claim_id=claim.claim_id,
                    character_ids=tuple(sorted({i for c in accounts for i in _character_ids(c)})),
                    evidence_ids=tuple(dict.fromkeys(e.evidence_id for e in spans)),
                    explanation=explanation,
                    group_id=_review_group(claim),
                    related_group_ids=tuple(sorted({_review_group(c) for c in targets})),
                    disputed=disputed,
                    reviewer=review.reviewer if review else None,
                    rationale=review.note if review else None,
                )
            )
    return tuple(notices)
