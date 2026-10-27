"""Factual event wording preserves reviewed roles, source timing and account distinctions."""

from ask_phil.event_graph import EventResult

EVENT_WORDING = (
    "story-events-v2: stage-specific roles; no inferred guilt, parentage, presence or dates"
)
ROLE_WORDING = {
    "perpetrator": "committed the act described in this incident",
    "victim": "was the victim",
    "accused": "was accused",
    "arrested": "was arrested",
    "defendant": "was a defendant at trial",
    "convicted": "was convicted",
    "acquitted": "was acquitted",
    "prisoner": "was imprisoned",
    "released": "was released",
    "confessor": "confessed",
    "witness": "was a witness",
    "accuser": "made the accusation",
    "pregnant_person": "was pregnant",
    "deceased": "died",
}


def render_events(result: EventResult, *, synthetic: bool = False) -> str:
    entries = []
    seen = set()
    for claim in result.claims:
        key = (claim.event_id, claim.assertion)
        if key in seen:
            continue
        seen.add(key)
        participants = []
        for person in claim.participants:
            name = result.names[person.character_id]
            wording = ROLE_WORDING[person.role]
            if person.character_id == "phil-mitchell":
                name = "I"
            participants.append(f"{name} {wording}")
        timing = (
            "story date unknown"
            if claim.time_precision == "unknown"
            else f"story timing {claim.story_time} ({claim.time_precision})"
        )
        account = (
            f" The captured narrative identifies this {claim.event_type} as false."
            if claim.account_status == "explicitly_false"
            else ""
        )
        support = (
            " Separately reviewed narrative supports commission."
            if claim.event_type == "commission"
            else ""
        )
        entries.append(
            f"{claim.event_label} — {claim.event_type}: "
            + "; ".join(participants)
            + f"; {timing}.{account}{support}"
        )
    label = "Synthetic example, not EastEnders canon. " if synthetic else ""
    return (
        "Right, listen. "
        + label
        + f"Captured {result.query.subject}:\n"
        + "\n".join(entries)
        + "\n"
    )
