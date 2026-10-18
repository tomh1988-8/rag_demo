"""Explicit graph answers: supported SQL paths, deterministic wording, no model calls."""

import hashlib
import time
from threading import BoundedSemaphore
from typing import Literal
from uuid import uuid4

import mlflow
import psycopg
from mlflow import MlflowClient
from mlflow.entities import MlflowExperimentLocation

from ask_phil.answering import application_fingerprint
from ask_phil.answers import AnswerReceipt, AnswerRecord, AskRequest, Citation
from ask_phil.conversation import ConversationReference, ReferenceResolution, TurnIdentity
from ask_phil.evidence import Passage
from ask_phil.execution import ExecutionBudget, ExecutionPolicies, ExecutionStopped
from ask_phil.family_graph import GRAPH_LIMITATION, FamilyGraph, FamilyResult
from ask_phil.models import TokenUsage
from ask_phil.publications import PublicationStore
from ask_phil.responses import ResponseLedger
from ask_phil.security import require_credential_free
from ask_phil.storage import EvidenceStore
from ask_phil.tracing import experiment_for

GRAPH_WORDING = "biological-paths-v1: explicit typed query; bounded captured relationships only"


class FamilyAnswerService:
    def __init__(self, database_url: str, tracking_uri: str, policies: ExecutionPolicies) -> None:
        self.database_url = database_url
        self.policies = policies
        self._slots = {
            category: BoundedSemaphore(getattr(policies, category).concurrency)
            for category in ("serving", "offline_evaluation")
        }
        mlflow.set_tracking_uri(tracking_uri)
        self.tracking = MlflowClient(tracking_uri=tracking_uri)

    def ask(
        self,
        request: AskRequest,
        *,
        turn: TurnIdentity | None = None,
        category: Literal["serving", "offline_evaluation"] = "serving",
        execution: ExecutionBudget | None = None,
    ) -> AnswerReceipt:
        if request.route != "graph" or request.graph is None:
            raise ValueError("An explicit typed family query is required.")
        budget = execution or ExecutionBudget(getattr(self.policies, category))
        with budget.activate():
            acquired = self._slots[category].acquire(blocking=False)
            if not acquired:
                budget.record_stop("concurrency_limit")
            try:
                return self._ask(request, turn, category, budget)
            finally:
                if acquired:
                    self._slots[category].release()

    def _ask(
        self,
        request: AskRequest,
        turn: TurnIdentity | None,
        category: Literal["serving", "offline_evaluation"],
        budget: ExecutionBudget,
    ) -> AnswerReceipt:
        started = time.perf_counter()
        publication = PublicationStore(self.database_url).pin(request.snapshot_id)
        snapshot_id = request.snapshot_id or (
            publication.manifest.snapshot_id if publication else ""
        )
        snapshot = EvidenceStore(self.database_url).snapshot(snapshot_id)
        require_credential_free(snapshot.model_dump_json())
        experiment_id = experiment_for(self.tracking, category)
        result: FamilyResult | None = None
        context: tuple[Passage, ...] = ()
        citations: tuple[Citation, ...] = ()
        with mlflow.start_span(
            "graph", trace_destination=MlflowExperimentLocation(experiment_id)
        ) as root:
            root.set_inputs(request.model_dump(mode="json"))
            try:
                budget.check()
                assert request.graph is not None
                with mlflow.start_span("family_graph", span_type="RETRIEVER") as span:
                    span.set_inputs(request.graph.model_dump())
                    result = FamilyGraph(self.database_url).query(snapshot_id, request.graph)
                    span.set_outputs(result.model_dump(mode="json"))
                ids = {
                    e.evidence_id for p in result.paths for edge in p.edges for e in edge.evidence
                }
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
            status: Literal["partial", "insufficient_evidence"] = (
                "partial" if result and result.paths else "insufficient_evidence"
            )
            if result and result.paths:
                paths = "; ".join(
                    " → ".join(result.names[c] for c in p.characters) for p in result.paths
                )
                answer = (
                    f"Right, listen. Captured biological {result.query.direction} paths: {paths}. "
                )
            else:
                reason = budget.record().stop_reason or (result.status if result else "unavailable")
                answer = (
                    f"I can't establish the requested biological paths from this graph ({reason}). "
                )
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
            response = AnswerRecord(
                response_id=uuid4(),
                question=request.question,
                conversation=conversation,
                status=status,
                answer=answer + GRAPH_LIMITATION,
                unanswered=("Family coverage outside the reviewed spans and traversal bounds.",),
                citations=citations,
                snapshot_id=snapshot_id,
                snapshot_sha256=snapshot.fingerprint,
                publication=publication.reference if publication else None,
                source=snapshot.source,
                retrieved=(),
                context=context,
                retrieval_k=0,
                route="graph",
                route_override=True,
                graph=result,
                model_settings=None,
                prompt_sha256=hashlib.sha256(GRAPH_WORDING.encode()).hexdigest(),
                application_sha256=application_fingerprint(),
                trace_id=root.trace_id,
                execution=budget.record(),
                elapsed_ms=(time.perf_counter() - started) * 1000,
                usage=TokenUsage(input_tokens=0, output_tokens=0, embedding_tokens=0),
                expenditure_category=category,
                estimated_api_cost_usd=0,
                cost_scope="No inference calls. Database and hosting costs are excluded.",
                limitation=GRAPH_LIMITATION,
            )
            root.set_attributes(
                {
                    "route_override": True,
                    "expenditure_category": category,
                    "execution": budget.record().model_dump(mode="json"),
                }
            )
            root.set_outputs(response.model_dump(mode="json"))
        self.tracking.get_trace(response.trace_id, flush=True)
        return ResponseLedger(self.database_url).save(response)
