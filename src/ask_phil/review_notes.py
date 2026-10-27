"""Qualified, deterministic explanations of retained review outcomes."""

from typing import Literal

from ask_phil.classified_facts import ContextClaim
from ask_phil.evidence import Identifier, Passage, Record, SourceSnapshot
from ask_phil.parentage import ParentageClaim
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


def review_group(claim: ReviewedClaim) -> str:
    if isinstance(claim, ParentageClaim):
        return "parentage:" + claim.child_id
    if isinstance(claim, RelationshipClaim):
        return "relationship:" + claim.episode_id
    if isinstance(claim, EventClaim):
        return "event:" + claim.event_id
    return claim.kind + ":" + ",".join(sorted(claim.character_ids))


def complete_review_groups(
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


def character_ids(claim: ReviewedClaim) -> tuple[str, ...]:
    if isinstance(claim, ParentageClaim):
        return claim.parent_id, claim.child_id
    if isinstance(claim, RelationshipClaim):
        return claim.subject_id, claim.object_id
    if isinstance(claim, EventClaim):
        return tuple(p.character_id for p in claim.participants)
    return claim.character_ids


def describe_account(claim: ReviewedClaim, names: dict[str, str]) -> str:
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


def render_notices(notices: tuple[ReviewNotice, ...], *, synthetic: bool) -> str:
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


def review_context(
    snapshot: SourceSnapshot, notices: tuple[ReviewNotice, ...], byte_budget: int
) -> tuple[Passage, ...]:
    """A review explanation is indivisible: include all its source accounts or abstain."""
    from ask_phil.passage_context import context_text

    ids = {eid for n in notices for eid in n.evidence_ids}
    context = tuple(p for p in snapshot.passages if p.evidence_id in ids)
    payload = (
        context_text(context).encode()
        + render_notices(
            notices, synthetic=snapshot.source.support_status == "synthetic_fixture"
        ).encode()
    )
    if len(context) != len(ids) or len(payload) > byte_budget:
        return ()
    return context
