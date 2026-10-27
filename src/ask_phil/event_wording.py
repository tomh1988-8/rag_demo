"""Factual crime/justice wording, without inferring guilt from a legal account."""

from ask_phil.event_graph import EventResult

EVENT_WORDING = (
    "crime-justice-v1: stage-specific roles; explicit false accounts; no guilt inference"
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
        + "Captured crime and justice history:\n"
        + "\n".join(entries)
        + "\n"
    )
