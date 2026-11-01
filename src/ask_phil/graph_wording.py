"""Typed graph explanation metadata and wording shared by direct answers and investigation."""

from dataclasses import dataclass
from typing import Self

from ask_phil.connection_graph import CONNECTION_LIMITATION, ConnectionQuery, ConnectionResult
from ask_phil.connection_wording import CONNECTION_WORDING, render_connections
from ask_phil.event_graph import EventQuery, EventResult
from ask_phil.event_wording import EVENT_WORDING, render_events
from ask_phil.family_graph import GRAPH_LIMITATION, FamilyResult
from ask_phil.graph_execution import GraphQuery, GraphResult
from ask_phil.relationship_graph import RelationshipQuery, RelationshipResult
from ask_phil.relationships import HISTORY_LIMITATION, RelationshipClaim

GRAPH_WORDING = "biological-paths-v1: explicit typed query; bounded captured relationships only"
HISTORY_WORDING = (
    "relationship-history-v1: reviewed assertions; distinct episodes; explicit order; "
    "synthetic labels; same-episode evidence grouping"
)


def render_history(result: RelationshipResult, *, synthetic: bool = False) -> str:
    verbs = {
        "biological_parent": "was identified as a biological parent of",
        "adoptive_parent": "was identified as an adoptive parent of",
        "step_parent": "was identified as a step-parent of",
        "ward": "was identified as guardian of the ward",
        "marriage": "married",
        "remarriage": "remarried",
        "separation": "separated from",
        "divorce": "divorced",
        "reconciliation": "reconciled with",
        "affair": "had an affair with",
        "partnership": "had a partnership with",
    }
    groups: dict[tuple[object, ...], list[RelationshipClaim]] = {}
    for claim in result.claims:
        groups.setdefault((claim.episode_id, claim.assertion, claim.status), []).append(claim)
    positions = {
        claim.claim_id: position
        for position, group in enumerate(groups.values(), 1)
        for claim in group
    }
    entries = []
    for group in groups.values():
        claim = group[0]
        timing = (
            "story date unknown"
            if claim.time_precision == "unknown"
            else (f"story timing {claim.story_time} ({claim.time_precision})")
        )
        previous = sorted(
            {
                positions[c.after_claim_id]
                for c in group
                if c.after_claim_id in positions
                and positions[c.after_claim_id] != positions[claim.claim_id]
            }
        )
        ordering = (
            (
                " Follows "
                + ("entry " if len(previous) == 1 else "entries ")
                + ", ".join(map(str, previous))
                + "."
            )
            if previous
            else ""
        )
        entries.append(
            f"{positions[claim.claim_id]}. {result.names[claim.subject_id]} "
            f"{verbs[claim.relation]} {result.names[claim.object_id]}; {timing}; "
            f"status {claim.status} in the captured account.{ordering}"
        )
    label = "Synthetic example, not EastEnders canon. " if synthetic else ""
    return (
        "Right, listen. " + label + "Captured relationship history:\n" + "\n".join(entries) + "\n"
    )


@dataclass(frozen=True)
class GraphExplanation:
    span_name: str
    subject: str
    limitation: str
    wording: str
    unanswered: tuple[str, ...]

    @classmethod
    def for_query(cls, query: GraphQuery) -> Self:
        if isinstance(query, ConnectionQuery):
            return cls(
                "connection_graph",
                "character connections",
                CONNECTION_LIMITATION,
                CONNECTION_WORDING,
                ("Connection coverage outside the reviewed graph and traversal bounds.",),
            )
        if isinstance(query, EventQuery):
            return cls(
                query.kind,
                query.subject,
                query.limitation,
                EVENT_WORDING,
                (
                    f"{query.subject.capitalize()} outside the reviewed assertions "
                    "and query bounds.",
                ),
            )
        if isinstance(query, RelationshipQuery):
            return cls(
                "relationship_history",
                "relationship history",
                HISTORY_LIMITATION,
                HISTORY_WORDING,
                ("Relationship coverage outside the reviewed spans and query bounds.",),
            )
        return cls(
            "family_graph",
            "biological paths",
            GRAPH_LIMITATION,
            GRAPH_WORDING,
            ("Family coverage outside the reviewed spans and traversal bounds.",),
        )

    @staticmethod
    def supported(result: GraphResult | None) -> bool:
        return bool(
            result
            and (
                result.claims
                if isinstance(result, RelationshipResult | EventResult)
                else result.paths
            )
        )

    def render(
        self,
        result: GraphResult | None,
        *,
        synthetic: bool = False,
        investigation: bool = False,
        stop_reason: str | None = None,
    ) -> str:
        """Keep direct-answer prose distinct from findings offered to the investigator."""
        if not investigation and not self.supported(result):
            reason = stop_reason or (result.status if result else "unavailable")
            return f"I can't establish the requested {self.subject} from this graph ({reason}). "
        if isinstance(result, ConnectionResult):
            return render_connections(result, synthetic=synthetic)
        if isinstance(result, EventResult):
            return render_events(result, synthetic=synthetic)
        if isinstance(result, RelationshipResult):
            return render_history(result, synthetic=synthetic)
        if isinstance(result, FamilyResult):
            if investigation:
                return "; ".join(
                    f"{result.names[e.parent_id]} is a biological parent "
                    f"of {result.names[e.child_id]}"
                    for p in result.paths
                    for e in p.edges
                )
            paths = "; ".join(
                " → ".join(result.names[c] for c in p.characters) for p in result.paths
            )
            return f"Right, listen. Captured biological {result.query.direction} paths: {paths}. "
        raise ValueError("Investigation findings require a graph result.")
