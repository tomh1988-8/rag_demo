"""Conservative public routing rules: typed capabilities, coverage and remaining authority."""

import hashlib
import os
import re
from pathlib import Path
from typing import Literal

from pydantic import Field

from ask_phil.connection_graph import ConnectionQuery
from ask_phil.event_graph import EventGraph, EventQuery
from ask_phil.evidence import Identifier, Passage, Record, SourceSnapshot
from ask_phil.execution import ExecutionBudget, ExecutionLimits, ExecutionRecord
from ask_phil.family_graph import FamilyGraph, FamilyQuery
from ask_phil.graph_execution import GraphQuery, GraphResult
from ask_phil.identity import IdentityCatalogue
from ask_phil.models import ModelExecution
from ask_phil.relationship_graph import RelationshipGraph, RelationshipQuery
from ask_phil.story_events import LIFE_EVENT_TYPES

type Route = Literal["text_rag", "graph", "investigation"]


class RoutingPolicy(Record):
    version: Literal["evidence-routing-v1"] = "evidence-routing-v1"
    escalation_enabled: bool = True
    minimum_remaining_seconds: float = Field(default=3, ge=0, le=60, allow_inf_nan=False)

    @classmethod
    def from_environment(cls) -> "RoutingPolicy":
        path = os.environ.get("ASK_PHIL_ROUTING_POLICY")
        if path is None:
            return cls()
        try:
            return cls.model_validate_json(Path(path).read_bytes())
        except (OSError, ValueError):
            raise ValueError("Routing policy could not be loaded.") from None

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()

    def escalation(
        self,
        *,
        status: str,
        reviewed: bool,
        additional_evidence: bool,
        published: bool,
        budget: ExecutionBudget,
    ) -> str:
        """Return an externally inspectable reason; this never increases request authority."""
        if status == "answered":
            return "sufficient_text_evidence"
        if status == "clarification":
            return "unresolved_reference"
        if reviewed:
            return "reviewed_interpretation"
        if budget.record().stop_reason or status == "failed":
            return "request_stopped"
        if not self.escalation_enabled:
            return "escalation_disabled"
        if not published:
            return "investigation_unavailable"
        if not additional_evidence:
            return "no_additional_evidence"
        record = budget.record()
        if (
            budget.limits.model_calls - record.model_calls < 3
            or budget.limits.tool_calls - record.tool_calls < 1
            or budget.limits.http_calls - record.http_calls < 4
            or budget.remaining_seconds < self.minimum_remaining_seconds
            or record.reserved_usd >= budget.limits.spend_usd
            or not budget.limits.capabilities
        ):
            return "no_escalation_budget"
        return "investigate_evidence_gap"


class RoutingCheck(Record):
    kind: Literal["selection", "evidence", "fallback", "escalation"]
    reason: str
    evidence_ids: tuple[Identifier, ...] = ()


class RoutingStage(Record):
    route: Route
    status: str
    elapsed_ms: float
    execution_before: ExecutionRecord
    execution_after: ExecutionRecord
    accounting: ModelExecution
    graph: GraphResult | None = Field(default=None, exclude_if=lambda v: v is None)


class RoutingRecord(Record):
    version: Literal["evidence-routing-v1"] = "evidence-routing-v1"
    requested_route: Literal["auto", "text_rag", "graph", "investigation"]
    selection: Literal["automatic", "override"]
    final_route: Route
    eligibility: "Eligibility | None" = None
    checks: tuple[RoutingCheck, ...] = ()
    stages: tuple[RoutingStage, ...]
    stop_reason: str
    policy: RoutingPolicy = RoutingPolicy()
    selection_elapsed_ms: float | None = None
    evidence_check_elapsed_ms: float | None = None


class CoveredEvent(Record):
    kind: Literal["crime_history", "life_events"]
    event_id: Identifier
    character_ids: tuple[Identifier, ...]


class GraphCoverage(Record):
    family_edges: tuple[tuple[Identifier, Identifier], ...] = ()
    relationship_pairs: tuple[tuple[Identifier, Identifier], ...] = ()
    events: tuple[CoveredEvent, ...] = ()


class Eligibility(Record):
    eligible: bool
    reason: str
    query: GraphQuery | None = None


class RoutingRules:
    def __init__(
        self,
        catalogue: IdentityCatalogue,
        coverage: GraphCoverage,
        capabilities: tuple[str, ...] = ExecutionLimits().capabilities,
    ) -> None:
        self.catalogue = catalogue
        self.coverage = coverage
        self.capabilities = capabilities

    def additional_evidence(
        self,
        question: str,
        unanswered: tuple[str, ...],
        context: tuple[Passage, ...],
        snapshot: SourceSnapshot,
    ) -> bool:
        """Require unexamined captured material and a topic or admitted character link."""
        outside = tuple(
            p
            for p in snapshot.passages
            if not any(
                p.start >= c.start
                and p.end <= c.end
                and p.source == c.source
                and (p.location.source_id if p.location else None)
                == (c.location.source_id if c.location else None)
                for c in context
            )
        )
        if not outside:
            return False
        from ask_phil.conversation import resolve_reference

        reference = resolve_reference(question, self.catalogue, ())
        linked = {
            c
            for pair in (*self.coverage.family_edges, *self.coverage.relationship_pairs)
            for c in pair
        }
        linked.update(c for e in self.coverage.events for c in e.character_ids)
        graph_topics = {
            "biological",
            "parents",
            "parent",
            "mother",
            "father",
            "grandmother",
            "grandfather",
            "ancestry",
            "ancestors",
            "descendants",
            "children",
            "relationship",
            "relationships",
            "married",
            "marriage",
            "divorce",
            "pregnant",
            "pregnancy",
            "death",
            "died",
            "killed",
            "crime",
            "justice",
            "arrested",
            "convicted",
            "connected",
            "connection",
        }
        requested = set(re.findall(r"\b[a-z]+\b", " ".join((question, *unanswered)).casefold()))
        if (
            not reference.clarification
            and set(reference.character_ids) & linked
            and requested & graph_topics
        ):
            return True
        stopwords = {
            "what",
            "when",
            "where",
            "which",
            "does",
            "have",
            "that",
            "this",
            "from",
            "about",
            "their",
            "there",
            "with",
            "were",
            "explain",
            "captured",
            "evidence",
            "question",
            "unresolved",
            "biological",
        }
        names = {
            word.casefold()
            for c in self.catalogue.characters
            for name in (c.name, *c.aliases)
            for word in name.split()
        }
        topics = (
            set(re.findall(r"\b[a-z]{4,}\b", " ".join((question, *unanswered)).casefold()))
            - stopwords
            - names
        )
        return any(topics & set(re.findall(r"\b[a-z]{4,}\b", p.text.casefold())) for p in outside)

    @classmethod
    def load(
        cls, database_url: str, snapshot: SourceSnapshot, limits: ExecutionLimits
    ) -> "RoutingRules":
        """Inspect admitted claims, never raw extraction counts or roster membership."""
        family = FamilyGraph(database_url).audit(snapshot.snapshot_id)
        relationships = RelationshipGraph(database_url).audit(snapshot.snapshot_id)
        events = EventGraph(database_url).audit(snapshot.snapshot_id)
        characters = (
            {c.character_id: c for c in snapshot.imported.catalogue.characters}
            if snapshot.imported
            else {}
        )
        for audit in (family, relationships, events):
            if audit is not None:
                if audit.batch.snapshot_sha256 != snapshot.fingerprint:
                    raise ValueError("Routing coverage differs from the captured source.")
                for character in audit.batch.catalogue.characters:
                    characters.setdefault(character.character_id, character)
        family_ids = (
            {d.claim_id for d in family.admission.decisions if d.status == "admitted"}
            if family
            else set()
        )
        relationship_ids = (
            {d.claim_id for d in relationships.admission.decisions if d.status == "admitted"}
            if relationships
            else set()
        )
        event_ids = (
            {d.claim_id for d in events.admission.decisions if d.status == "admitted"}
            if events
            else set()
        )
        coverage = GraphCoverage(
            family_edges=tuple(
                (c.parent_id, c.child_id) for c in family.batch.claims if c.claim_id in family_ids
            )
            if family
            else (),
            relationship_pairs=tuple(
                (c.subject_id, c.object_id)
                for c in relationships.batch.claims
                if c.claim_id in relationship_ids
            )
            if relationships
            else (),
            events=tuple(
                CoveredEvent(
                    kind="life_events" if c.event_type in LIFE_EVENT_TYPES else "crime_history",
                    event_id=c.event_id,
                    character_ids=tuple(p.character_id for p in c.participants),
                )
                for c in events.batch.claims
                if c.claim_id in event_ids
            )
            if events
            else (),
        )
        return cls(
            IdentityCatalogue(characters=tuple(characters.values())), coverage, limits.capabilities
        )

    def eligibility(self, question: str, *, query: GraphQuery | None = None) -> Eligibility:
        if query is None:
            proposal = self._propose(question)
            if isinstance(proposal, str):
                return Eligibility(eligible=False, reason=proposal)
            query = proposal
        capability = (
            "connection_graph"
            if isinstance(query, ConnectionQuery)
            else "event_graph"
            if isinstance(query, EventQuery)
            else "family_graph"
        )
        if capability not in self.capabilities:
            return Eligibility(eligible=False, reason="capability_denied", query=query)
        covered = False
        if isinstance(query, FamilyQuery):
            covered = any(
                query.character_id == (child if query.direction == "ancestors" else parent)
                for parent, child in self.coverage.family_edges
            )
        elif isinstance(query, RelationshipQuery):
            covered = any(
                query.character_id in pair
                and (query.partner_id is None or query.partner_id in pair)
                for pair in self.coverage.relationship_pairs
            )
        elif isinstance(query, EventQuery):
            if not query.event_types:
                return Eligibility(eligible=False, reason="unsupported_graph_family", query=query)
            covered = any(
                query.kind == event.kind
                and query.character_id in event.character_ids
                and (query.participant_id is None or query.participant_id in event.character_ids)
                and (query.event_id is None or query.event_id == event.event_id)
                for event in self.coverage.events
            )
        else:
            endpoints = {
                c
                for pair in (*self.coverage.family_edges, *self.coverage.relationship_pairs)
                for c in pair
            } | {c for e in self.coverage.events for c in e.character_ids}
            covered = {query.character_id, query.target_id} <= endpoints
        return Eligibility(
            eligible=covered,
            reason="admitted_coverage" if covered else "no_admitted_coverage",
            query=query,
        )

    def _propose(self, question: str) -> GraphQuery | str:
        question = question.strip().rstrip("?.!")
        connection = re.fullmatch(r"how are (.+?) and (.+?) connected", question, re.IGNORECASE)
        if connection:
            first, second = (self.catalogue.resolve(connection[i]) for i in (1, 2))
            if first.status != "resolved" or second.status != "resolved":
                return "unresolved_character"
            if first.character_ids == second.character_ids:
                return "invalid_participants"
            return ConnectionQuery(
                kind="connection",
                character_id=first.character_ids[0],
                target_id=second.character_ids[0],
            )
        event = re.fullmatch(
            r"(?:show|explain|describe|list) (.+?)['’]s "
            r"(crime and justice history|crime history|criminal justice history|"
            r"pregnancy and death history)",
            question,
            re.IGNORECASE,
        )
        if event:
            subject = self.catalogue.resolve(event[1])
            if subject.status != "resolved":
                return "unresolved_character"
            return EventQuery(
                kind="life_events"
                if event[2].casefold() == "pregnancy and death history"
                else "crime_history",
                character_id=subject.character_ids[0],
            )
        relationship = re.fullmatch(
            r"(?:show|explain|describe|list) (?:the )?relationship history "
            r"(?:between|of|for) (.+?)(?: and (.+))?",
            question,
            re.IGNORECASE,
        )
        if relationship:
            subject = self.catalogue.resolve(relationship[1])
            partner = self.catalogue.resolve(relationship[2]) if relationship[2] else None
            if subject.status != "resolved" or (partner and partner.status != "resolved"):
                return "unresolved_character"
            character_id = subject.character_ids[0]
            partner_id = partner.character_ids[0] if partner else None
            if partner_id == character_id:
                return "invalid_participants"
            return RelationshipQuery(
                kind="relationship_history", character_id=character_id, partner_id=partner_id
            )
        match = re.fullmatch(
            r"who are (.+?)['’]s biological (parents|children|ancestors|descendants)",
            question,
            re.IGNORECASE,
        )
        if not match:
            return "unsupported_question"
        identity = self.catalogue.resolve(match[1])
        if identity.status != "resolved":
            return "unresolved_character"
        direction: Literal["ancestors", "descendants"] = (
            "ancestors" if match[2].casefold() in {"parents", "ancestors"} else "descendants"
        )
        return FamilyQuery(
            character_id=identity.character_ids[0],
            direction=direction,
            max_depth=1 if match[2].casefold() in {"parents", "children"} else 3,
        )
