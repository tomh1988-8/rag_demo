"""Family tree evidence and deterministic wording; inference is never required."""

import hashlib
from typing import Literal

import mlflow
import psycopg
from mlflow.entities import LiveSpan

from ask_phil.answers import AnswerContent, AskRequest, Citation
from ask_phil.conversation import (
    ConversationReference,
    ReferenceResolution,
    ReferenceTurn,
    TurnIdentity,
)
from ask_phil.evidence import Passage
from ask_phil.execution import ExecutionBudget, ExecutionStopped
from ask_phil.family_graph import GRAPH_LIMITATION, FamilyGraph, FamilyResult
from ask_phil.models import ModelExecution, TokenUsage
from ask_phil.publications import PublicationStore
from ask_phil.relationship_graph import RelationshipGraph, RelationshipQuery, RelationshipResult
from ask_phil.relationships import HISTORY_LIMITATION
from ask_phil.security import require_credential_free
from ask_phil.storage import EvidenceStore

GRAPH_WORDING = "biological-paths-v1: explicit typed query; bounded captured relationships only"
HISTORY_WORDING = (
    "relationship-history-v1: reviewed assertions; distinct episodes; explicit order only"
)


def render_history(result: RelationshipResult) -> str:
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
    positions = {c.claim_id: i for i, c in enumerate(result.claims, 1)}
    entries = []
    for claim in result.claims:
        timing = (
            "story date unknown"
            if claim.time_precision == "unknown"
            else (f"story timing {claim.story_time} ({claim.time_precision})")
        )
        previous = positions.get(claim.after_claim_id or "")
        ordering = f" Follows entry {previous}." if previous else ""
        entries.append(
            f"{positions[claim.claim_id]}. {result.names[claim.subject_id]} "
            f"{verbs[claim.relation]} {result.names[claim.object_id]}; {timing}; "
            f"status {claim.status} in the captured account.{ordering}"
        )
    return "Right, listen. Captured relationship history:\n" + "\n".join(entries) + "\n"


class FamilyAnswer:
    def __init__(self, database_url: str, snapshot_id: str | None) -> None:
        self.database_url = database_url
        self.publication = PublicationStore(database_url).pin(snapshot_id)
        selected = snapshot_id or (
            self.publication.manifest.snapshot_id if self.publication else ""
        )
        self.snapshot = EvidenceStore(database_url).snapshot(selected)
        require_credential_free(self.snapshot.model_dump_json())

    def answer(
        self,
        request: AskRequest,
        turn: TurnIdentity | None,
        history: tuple[ReferenceTurn, ...],
        budget: ExecutionBudget,
        root: LiveSpan,
    ) -> AnswerContent:
        snapshot = self.snapshot
        snapshot_id = snapshot.snapshot_id
        result: FamilyResult | RelationshipResult | None = None
        is_history = isinstance(request.graph, RelationshipQuery)
        limitation = HISTORY_LIMITATION if is_history else GRAPH_LIMITATION
        context: tuple[Passage, ...] = ()
        citations: tuple[Citation, ...] = ()
        try:
            budget.check()
            assert request.graph is not None
            with mlflow.start_span(
                "relationship_history" if is_history else "family_graph", span_type="RETRIEVER"
            ) as span:
                span.set_inputs(request.graph.model_dump())
                if isinstance(request.graph, RelationshipQuery):
                    result = RelationshipGraph(self.database_url).query(snapshot_id, request.graph)
                else:
                    result = FamilyGraph(self.database_url).query(snapshot_id, request.graph)
                span.set_outputs(result.model_dump(mode="json"))
            ids = (
                {e.evidence_id for c in result.claims for e in c.evidence}
                if isinstance(result, RelationshipResult)
                else {
                    e.evidence_id for p in result.paths for edge in p.edges for e in edge.evidence
                }
            )
            context = tuple(p for p in snapshot.passages if p.evidence_id in ids)
            if len(context) != len(ids):
                budget.stop("malformed_output")
            if sum(len(p.text.encode()) for p in context) > budget.limits.context_bytes:
                budget.stop("context_limit")
            citations = tuple(
                Citation(
                    **p.model_dump(),
                    resolve_path=f"/v1/snapshots/{snapshot_id}/evidence/{p.evidence_id}",
                )
                for p in context
            )
            budget.check()
        except (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable):
            budget.record_stop("timeout")
        except ExecutionStopped as exc:
            budget.record_stop(str(exc))
        if budget.record().stop_reason:
            result, context, citations = None, (), ()
            root.set_status("ERROR")
        supported = bool(
            result and (result.claims if isinstance(result, RelationshipResult) else result.paths)
        )
        status: Literal["partial", "insufficient_evidence"] = (
            "partial" if supported else "insufficient_evidence"
        )
        if isinstance(result, RelationshipResult) and result.claims:
            answer = render_history(result)
        elif isinstance(result, FamilyResult) and result.paths:
            paths = "; ".join(
                " → ".join(result.names[c] for c in p.characters) for p in result.paths
            )
            answer = f"Right, listen. Captured biological {result.query.direction} paths: {paths}. "
        else:
            reason = budget.record().stop_reason or (result.status if result else "unavailable")
            subject = "relationship history" if is_history else "biological paths"
            answer = f"I can't establish the requested {subject} from this graph ({reason}). "
        conversation = (
            ConversationReference(
                **turn.model_dump(),
                reference=ReferenceResolution(
                    question=request.question,
                    character_ids=(request.graph.character_id,)
                    if result and request.graph and request.graph.character_id in result.names
                    else (),
                    followup_requires_name=True,
                ),
            )
            if turn
            else None
        )
        return AnswerContent(
            conversation=conversation,
            status=status,
            answer=answer + limitation,
            unanswered=("Relationship coverage outside the reviewed spans and query bounds.",)
            if is_history
            else ("Family coverage outside the reviewed spans and traversal bounds.",),
            citations=citations,
            context=context,
            graph=result,
            prompt_sha256=hashlib.sha256(
                (HISTORY_WORDING if is_history else GRAPH_WORDING).encode()
            ).hexdigest(),
            accounting=ModelExecution(
                content=None,
                usage=TokenUsage(input_tokens=0, output_tokens=0, embedding_tokens=0),
                provider_usage=None,
                failure_type=None,
                estimated_api_cost_usd=0,
                cost_scope="No inference calls. Database and hosting costs are excluded.",
                limitation=limitation,
            ),
        )
