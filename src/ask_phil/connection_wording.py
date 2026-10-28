"""Connection wording is determined by typed steps, never generated graph proximity."""

from ask_phil.connection_graph import (
    BiologicalStep,
    ConnectionResult,
    RelationshipStep,
)
from ask_phil.event_graph import EventQuery, EventResult
from ask_phil.event_wording import render_events
from ask_phil.story_events import LIFE_EVENT_TYPES

CONNECTION_WORDING = (
    "connections-v1: explicit typed paths; role-preserving steps; biological-only derivations"
)


def render_connections(result: ConnectionResult, *, synthetic: bool = False) -> str:
    entries = []
    for index, path in enumerate(result.paths, 1):
        names = " → ".join(result.names[c] for c in path.characters)
        meaning = (
            f" Derived meaning: {path.meaning.replace('_', ' ')} from the first to last character."
            if path.meaning != "connection"
            else ""
        )
        entries.append(f"{index}. {names}.{meaning}")
        for position, step in enumerate(path.steps, 1):
            if isinstance(step, BiologicalStep):
                text = (
                    f"{result.names[step.edge.parent_id]} is a biological parent of "
                    f"{result.names[step.edge.child_id]}; traversed {step.direction}."
                )
            elif isinstance(step, RelationshipStep):
                claim = step.claim
                text = (
                    f"{result.names[claim.subject_id]} → {result.names[claim.object_id]}: "
                    f"{claim.relation.replace('_', ' ')}; captured status {claim.status}; "
                    f"story timing {claim.story_time} ({claim.time_precision}); "
                    f"traversed {step.direction}."
                )
            else:
                events = EventResult(
                    snapshot_id=result.snapshot_id,
                    snapshot_sha256=result.snapshot_sha256,
                    query=EventQuery(
                        kind="life_events"
                        if all(c.event_type in LIFE_EVENT_TYPES for c in step.claims)
                        else "crime_history",
                        character_id=step.from_id,
                        participant_id=step.to_id,
                    ),
                    status="found",
                    claims=step.claims,
                    names=result.names,
                )
                text = (
                    f"Shared incident {step.event_id}; each character retains their stated roles. "
                    + render_events(events).removeprefix("Right, listen. ").rstrip()
                )
            evidence = ", ".join(sorted({e.evidence_id for e in step.evidence}))
            entries.append(f"Step {position}: {text} [{evidence}]")
    label = "Synthetic example, not EastEnders canon. " if synthetic else ""
    if result.status == "truncated":
        entries.append("Search or result limit reached; further paths may be omitted.")
    return "Right, listen. " + label + "Captured connection paths:\n" + "\n".join(entries) + "\n"
