"""Declared read tools, one pinned publication and bounded evidence accumulation."""

import hashlib
import json
import time
from functools import cached_property
from typing import Annotated, Any

import mlflow
from pydantic import Field, StringConstraints

from ask_phil.classified_facts import ContextClaim
from ask_phil.connection_graph import ConnectionQuery, ConnectionResult
from ask_phil.connection_wording import render_connections
from ask_phil.event_graph import EventQuery, EventResult
from ask_phil.event_wording import render_events
from ask_phil.evidence import Passage, Record
from ask_phil.execution import ExecutionBudget, ExecutionStopped
from ask_phil.family_answering import render_history
from ask_phil.family_graph import FamilyQuery
from ask_phil.graph_execution import GraphExecution, GraphResult
from ask_phil.investigation_records import InvestigationStep, TextFinding
from ask_phil.passage_context import context_text
from ask_phil.relationship_graph import RelationshipQuery, RelationshipResult
from ask_phil.retrieval import IndexNotReady, PinnedText
from ask_phil.review_notes import ReviewNotice, prepare_graph_review, prepare_text_review

TOOL_CONTRACT = """captured-read-tools-v1. Arguments are a JSON-encoded object string.
text_search: {query: string (1..500 characters, <=1000 UTF-8 bytes), k: integer 1..3}.
family: {character_id: ID, direction: ancestors|descendants, max_depth: 1..6,
max_paths: 1..50}. Only admitted biological parentage.
relationships: {kind: relationship_history, character_id: ID, partner_id?: ID|null,
max_events: 1..50}. Historical, adoptive and step ties remain distinct.
events: {kind: crime_history|life_events|theme|unclassified, character_id: ID,
participant_id?: ID|null, event_id?: ID|null, max_events: 1..20}.
connections: {kind: connection, character_id: ID, target_id: different ID,
max_depth: 1..6, max_paths: 1..20, max_expansions: 1..5000}.
IDs are reviewed character IDs, e.g. phil-mitchell; character and performer differ.
Omitted bounds use the typed tool defaults. Prefer small bounds for a small context.
All tools read the same captured publication. Empty/truncated/unavailable results
are coverage limits, not proof of absence. Graph paths preserve roles and direction;
themes, co-appearance, adoption and false accounts cannot create biological ancestry
or guilt. Source-supported does not mean independently cross-checked.
No SQL, shell, source mutation, ingestion or live-web access exists.
"""


class TextSearch(Record):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    k: int = Field(default=3, ge=1, le=3, strict=True)


TOOL_ARGUMENTS: dict[str, type[Record]] = {
    "text_search": TextSearch,
    "family": FamilyQuery,
    "relationships": RelationshipQuery,
    "events": EventQuery,
    "connections": ConnectionQuery,
}
TOOL_CAPABILITIES = {
    "text_search": "text_retrieval",
    "family": "family_graph",
    "relationships": "family_graph",
    "events": "event_graph",
    "connections": "connection_graph",
}
TOOL_CONTRACT_SHA256 = hashlib.sha256(
    json.dumps(
        {
            "description": TOOL_CONTRACT,
            "schemas": {k: v.model_json_schema() for k, v in TOOL_ARGUMENTS.items()},
            "capabilities": TOOL_CAPABILITIES,
        },
        sort_keys=True,
    ).encode()
).hexdigest()


class InvestigationTools:
    def __init__(self, database_url: str, pinned: PinnedText, budget: ExecutionBudget) -> None:
        self._database_url = database_url
        self._pinned = pinned
        self._budget = budget
        self.context: tuple[Passage, ...] = ()
        self.steps: list[InvestigationStep] = []
        self.context_claims: tuple[ContextClaim, ...] = ()
        self.review_notices: tuple[ReviewNotice, ...] = ()
        self._graph_findings: list[dict[str, Any]] = []
        self._seen: set[str] = set()

    @cached_property
    def _graph(self) -> GraphExecution:
        return GraphExecution(
            self._database_url,
            self._pinned.snapshot.snapshot_id,
            execution=self._budget,
            publication=self._pinned.publication,
        )

    def model_context(self) -> dict[str, Any]:
        return self._context(
            self.context, self.context_claims, self.review_notices, self._graph_findings
        )

    @property
    def context_bytes(self) -> int:
        return len(
            json.dumps(self.model_context(), ensure_ascii=False, separators=(",", ":")).encode()
        )

    def _context(
        self,
        passages: tuple[Passage, ...],
        classifications: tuple[ContextClaim, ...],
        notices: tuple[ReviewNotice, ...],
        graphs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "passages": json.loads(context_text(passages, classifications)),
            "graph_findings": graphs,
            "review_notices": [n.explanation for n in notices],
            "attempts": [
                {"tool": s.tool, "arguments": s.arguments, "status": s.status} for s in self.steps
            ],
        }

    def execute(self, tool: str, arguments: str) -> None:
        """Validate before dispatch; retain the outcome even if it cannot enter context."""
        started = time.perf_counter()
        record = InvestigationStep(tool=tool, arguments=arguments, status="stopped", elapsed_ms=0)
        schema = TOOL_ARGUMENTS.get(tool)
        if schema is None:
            self.steps.append(record.model_copy(update={"status": "denied_tool"}))
            self._budget.stop("capability_denied")
        try:
            # JSON input must satisfy the actual public query contract, including extra fields.
            query = schema.model_validate_json(arguments, strict=True)
            if isinstance(query, TextSearch) and len(query.query.encode()) > 1000:
                raise ValueError("Query input limit")
        except ValueError:
            self.steps.append(record.model_copy(update={"status": "invalid_arguments"}))
            return
        identity = tool + ":" + query.model_dump_json()
        if identity in self._seen:
            self.steps.append(record.model_copy(update={"status": "repeated_call"}))
            self._budget.stop("repeated_call")
        self._seen.add(identity)
        with mlflow.start_span(tool, span_type="RETRIEVER") as span:
            span.set_inputs(query.model_dump(mode="json"))
            finding: TextFinding | GraphResult | None = None
            try:
                self._budget.check()
                passages: tuple[Passage, ...]
                classifications: tuple[ContextClaim, ...] = ()
                notices: tuple[ReviewNotice, ...] = ()
                graphs = list(self._graph_findings)
                if isinstance(query, TextSearch):
                    result = self._pinned.retrieve(query.query, k=query.k)
                    finding = TextFinding(
                        hits=result.hits,
                        context_claims=result.context_claims,
                        review_notices=result.review_notices,
                    )
                    passages = tuple(h.passage for h in result.hits)
                    classifications = result.context_claims
                    notices = result.review_notices
                    if notices:
                        review = prepare_text_review(
                            self._pinned.snapshot, notices, self._budget.limits.context_bytes
                        )
                        if not review.context:
                            self._budget.stop("context_limit")
                        passages = review.context
                else:
                    if not isinstance(
                        query, FamilyQuery | RelationshipQuery | EventQuery | ConnectionQuery
                    ):
                        raise ValueError("Unknown query type")
                    finding = self._graph.query(query)
                    if finding.snapshot_sha256 != self._pinned.snapshot.fingerprint:
                        raise ValueError("Incompatible graph source")
                    review = prepare_graph_review(
                        self._database_url,
                        self._pinned.snapshot,
                        finding,
                        self._budget.limits.context_bytes,
                    )
                    passages = review.context
                    notices = review.notices
                    if isinstance(finding, ConnectionResult):
                        description = render_connections(finding, synthetic=review.synthetic)
                    elif isinstance(finding, EventResult):
                        description = render_events(finding, synthetic=review.synthetic)
                    elif isinstance(finding, RelationshipResult):
                        description = render_history(finding, synthetic=review.synthetic)
                    else:
                        description = "; ".join(
                            f"{finding.names[e.parent_id]} is a biological parent "
                            f"of {finding.names[e.child_id]}"
                            for p in finding.paths
                            for e in p.edges
                        )
                    graphs.append({"tool": tool, "status": finding.status, "findings": description})
                span.set_outputs(finding.model_dump(mode="json"))
                record = record.model_copy(update={"status": "executed", "result": finding})
                available = {p.evidence_id: p for p in self.context}
                available.update({p.evidence_id: p for p in passages})
                candidate = tuple(available.values())
                all_classifications = tuple(
                    {c.claim_id: c for c in (*self.context_claims, *classifications)}.values()
                )
                all_notices = tuple(
                    {(n.family, n.claim_id): n for n in (*self.review_notices, *notices)}.values()
                )
                payload = self._context(candidate, all_classifications, all_notices, graphs)
                payload["attempts"].append(
                    {"tool": tool, "arguments": arguments, "status": "executed"}
                )
                self._budget.context(
                    len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
                )
                self.context = candidate
                self.context_claims = all_classifications
                self.review_notices = all_notices
                self._graph_findings = graphs
                record = record.model_copy(
                    update={"context_ids": tuple(p.evidence_id for p in self.context)}
                )
            except (ValueError, IndexNotReady):
                span.set_status("ERROR")
                self._budget.stop("incompatible_snapshot")
            except ExecutionStopped:
                span.set_status("ERROR")
                raise
            finally:
                if finding is not None:
                    span.set_outputs(finding.model_dump(mode="json"))
                self.steps.append(
                    record.model_copy(
                        update={
                            "result": finding,
                            "elapsed_ms": (time.perf_counter() - started) * 1000,
                        }
                    )
                )
