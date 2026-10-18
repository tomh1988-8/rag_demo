"""One bounded text-RAG execution, traced and durably associated with its final answer."""

import hashlib
import time
from pathlib import Path
from threading import BoundedSemaphore
from typing import Literal
from uuid import uuid4

import mlflow
from llama_index.core.llms import ChatMessage
from mlflow import MlflowClient
from mlflow.entities import MlflowExperimentLocation

from ask_phil.answers import (
    SYSTEM_PROMPT,
    AnswerReceipt,
    AnswerRecord,
    AskRequest,
    Citation,
    Draft,
    assemble_context,
    cite_answer,
    context_text,
)
from ask_phil.conversation import (
    ConversationReference,
    ReferenceTurn,
    TurnIdentity,
    resolve_reference,
)
from ask_phil.evidence import Passage
from ask_phil.execution import ExecutionBudget, ExecutionPolicies, ExecutionStopped
from ask_phil.identity import IdentityCatalogue
from ask_phil.models import ModelConfigurationError, ModelExecution, Models, TokenUsage
from ask_phil.responses import ResponseLedger
from ask_phil.retrieval import Retrieval, TextRetriever
from ask_phil.tracing import experiment_for


def application_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class AnswerService:
    def __init__(
        self,
        database_url: str,
        models: Models,
        tracking_uri: str,
        *,
        policies: ExecutionPolicies | None = None,
    ) -> None:
        self.policies = policies or ExecutionPolicies.from_environment()
        self._slots = {
            category: BoundedSemaphore(getattr(self.policies, category).concurrency)
            for category in ("serving", "offline_evaluation")
        }
        self.models = models
        if models.redact(models.settings.model_dump_json()) != models.settings.model_dump_json():
            raise ModelConfigurationError("Model settings contain unsafe credential text.")
        self.retriever = TextRetriever(
            database_url,
            models.embedding,
            models.settings.embedding_id,
            models.settings.embedding_dimensions,
        )
        self.ledger = ResponseLedger(database_url)
        # One configured MLflow backend per API process; experiments separate costs.
        mlflow.set_tracking_uri(tracking_uri)
        self.tracking = MlflowClient(tracking_uri=tracking_uri)

    def prepare(self, snapshot_id: str) -> str:
        self.models.verify()
        experiment_id = experiment_for(self.tracking, "indexing")
        with mlflow.start_span(
            "prepare_text_index", trace_destination=MlflowExperimentLocation(experiment_id)
        ) as span:
            span.set_inputs({"snapshot_id": snapshot_id})
            span.set_attributes(
                {
                    "expenditure_category": "indexing",
                    "model_settings": self.models.settings.model_dump(mode="json"),
                }
            )
            self.retriever.prepare(snapshot_id)
            span.set_outputs(
                {"index_ready": True, "embedding_id": self.models.settings.embedding_id}
            )
            trace_id = span.trace_id
        self.tracking.get_trace(trace_id, flush=True)
        return trace_id

    def ask(
        self,
        request: AskRequest,
        *,
        category: Literal["serving", "offline_evaluation"] = "serving",
        turn: TurnIdentity | None = None,
        history: tuple[ReferenceTurn, ...] = (),
        execution: ExecutionBudget | None = None,
    ) -> AnswerReceipt:
        budget = execution or ExecutionBudget(getattr(self.policies, category))
        request = request.model_copy(update={"question": self.models.redact(request.question)})
        with budget.activate():
            acquired = self._slots[category].acquire(blocking=False)
            if not acquired:
                budget.record_stop("concurrency_limit")
            try:
                return self._ask(request, category, turn, history, budget)
            finally:
                if acquired:
                    self._slots[category].release()

    def _ask(
        self,
        request: AskRequest,
        category: Literal["serving", "offline_evaluation"],
        turn: TurnIdentity | None,
        history: tuple[ReferenceTurn, ...],
        budget: ExecutionBudget,
    ) -> AnswerReceipt:
        started = time.perf_counter()
        pinned = self.retriever.pin(request.snapshot_id)
        publication = pinned.publication
        snapshot = pinned.snapshot
        snapshot_id = snapshot.snapshot_id
        if self.models.redact(snapshot.model_dump_json()) != snapshot.model_dump_json():
            raise ModelConfigurationError("Captured evidence contains unsafe credential text.")
        conversation = None
        question = request.question
        if turn:
            reference = resolve_reference(
                question,
                snapshot.imported.catalogue
                if snapshot.imported
                else IdentityCatalogue(characters=()),
                history,
            )
            conversation = ConversationReference(**turn.model_dump(), reference=reference)
            question = reference.question
        response_id = uuid4()
        experiment_id = experiment_for(self.tracking, category)
        with mlflow.start_span(
            "text_rag", trace_destination=MlflowExperimentLocation(experiment_id)
        ) as root:
            root.set_inputs(request.model_dump())
            if conversation:
                root.set_attribute("conversation", conversation.model_dump(mode="json"))
            if publication:
                root.set_attribute("publication", publication.reference.model_dump(mode="json"))
            root.set_attributes(
                {
                    "response_id": str(response_id),
                    "expenditure_category": category,
                    "model_settings": self.models.settings.model_dump(mode="json"),
                    "prompt": SYSTEM_PROMPT,
                    "baseline_version": "single-query-uncached-v2",
                    "usage_complete": False,
                    "usage_aggregate_scope": (
                        "Reported token counts only; incomplete usage is not a full-request total."
                    ),
                }
            )
            retrieved = Retrieval(
                snapshot=snapshot,
                hits=(),
                k=0,
                embedding_id=self.models.settings.embedding_id,
            )
            context: tuple[Passage, ...] = ()
            citations: tuple[Citation, ...] = ()
            execution = self.models.skipped_answer().model_copy(
                update={"usage": TokenUsage(input_tokens=0, output_tokens=0, embedding_tokens=0)}
            )
            failure = False
            clarification = conversation.reference.clarification if conversation else None
            try:
                budget.check()
                pinned.verify()
                self.models.verify()
                budget.check()
                if clarification:
                    draft = Draft(
                        answer=clarification,
                        status="clarification",
                        evidence_ids=(),
                        unanswered=("Which character is intended?",),
                        qualifications=(),
                    )
                    root.set_attribute("retrieval_skipped", "unresolved_reference")
                    root.set_attribute("answer_model_skipped", "unresolved_reference")
                else:
                    with mlflow.start_span("text_retrieval", span_type="RETRIEVER") as span:
                        span.set_inputs({"question": question, "k": 3})
                        retrieved = pinned.retrieve(question, k=3)
                        span.set_outputs(retrieved.model_dump(mode="json"))
                    execution = self.models.skipped_answer()
                    with mlflow.start_span("assembled_context") as span:
                        context = assemble_context(retrieved.hits, budget.limits.context_bytes)
                        span.set_outputs(
                            {
                                "passages": [p.model_dump() for p in context],
                                "byte_budget": budget.limits.context_bytes,
                            }
                        )
                    if not context:
                        draft = Draft(
                            answer=(
                                "I can't answer from the available captured context. "
                                "Missing evidence doesn't establish that an event didn't happen."
                            ),
                            evidence_ids=(),
                            status="insufficient_evidence",
                            qualifications=(),
                            unanswered=(
                                "The question cannot be answered from the available context.",
                            ),
                        )
                        root.set_attribute("answer_model_skipped", "empty_context")
                    else:
                        execution, draft = self._generate(question, retrieved, context)
                        if execution.failure_type is not None:
                            budget.stop(
                                execution.failure_type
                                if execution.failure_type
                                in {
                                    "malformed_output",
                                    "timeout",
                                    "cancelled",
                                    "endpoint_denied",
                                    "http_call_limit",
                                    "spend_limit",
                                    "model_call_limit",
                                }
                                else "provider_failure"
                            )
                        budget.check()
                        citations = cite_answer(draft, context, snapshot_id)
            except ExecutionStopped as exc:
                reason = str(exc)
                budget.record_stop(reason)
                if retrieved.k == 0 and budget.record().model_calls:
                    execution = execution.model_copy(
                        update={
                            "usage": TokenUsage(
                                input_tokens=0, output_tokens=0, embedding_tokens=None
                            )
                        }
                    )
                root.set_status("ERROR")
                failure = reason in {"provider_failure", "malformed_output"}
                draft = Draft(
                    answer=(
                        f"Execution stopped: {reason}. "
                        + (
                            "Captured excerpts: " + " ".join(p.text for p in context)
                            if context and not failure
                            else (
                                "I couldn't produce a usable, cited answer. Please try again later."
                            )
                        )
                        + " This limit does not establish that an event did not happen."
                    ),
                    status="partial" if context and not failure else "insufficient_evidence",
                    evidence_ids=tuple(p.evidence_id for p in context) if not failure else (),
                    unanswered=("The requested answer is incomplete because execution stopped.",),
                    qualifications=(),
                )
                citations = cite_answer(draft, context, snapshot_id)
            root.set_attribute("usage_complete", execution.usage_complete)
            root.set_attribute("execution", budget.record().model_dump(mode="json"))
            response = AnswerRecord(
                response_id=response_id,
                question=request.question,
                conversation=conversation,
                status="failed" if failure else draft.status,
                answer=draft.answer,
                unanswered=draft.unanswered,
                qualifications=draft.qualifications,
                citations=citations,
                snapshot_id=snapshot_id,
                snapshot_sha256=snapshot.fingerprint,
                publication=publication.reference if publication else None,
                source=snapshot.source,
                retrieved=retrieved.hits,
                context=context,
                retrieval_k=retrieved.k,
                baseline_version="single-query-uncached-v2",
                model_settings=self.models.settings,
                prompt_sha256=hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
                application_sha256=application_fingerprint(),
                trace_id=root.trace_id,
                execution=budget.record(),
                elapsed_ms=(time.perf_counter() - started) * 1000,
                usage=execution.usage,
                expenditure_category=category,
                provider_usage=execution.provider_usage,
                estimated_api_cost_usd=execution.estimated_api_cost_usd,
                cost_scope=execution.cost_scope,
                limitation=execution.limitation,
            )
            root.set_outputs(response.model_dump(mode="json"))
        # Trace finalization and deterministic receipt storage make the stop outcome inspectable.
        self.tracking.get_trace(response.trace_id, flush=True)
        return self.ledger.save(response)

    def _generate(
        self, question: str, retrieved: Retrieval, context: tuple[Passage, ...]
    ) -> tuple[ModelExecution, Draft]:
        with mlflow.start_span("answer_model", span_type="LLM") as span:
            messages = [
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(
                    role="user",
                    content=(
                        f"Question: {question}\n"
                        f"Snapshot provenance: {retrieved.snapshot.source.title} "
                        f"({retrieved.snapshot.source.support_status})\n"
                        f"Captured evidence: {context_text(context)}"
                    ),
                ),
            ]
            span.set_inputs([m.model_dump(mode="json") for m in messages])
            execution = self.models.generate_answer(messages, schema=Draft.model_json_schema())
            span.set_outputs({"content": execution.content})
            span.set_attributes(execution.trace_attributes)
            if execution.failure_type is not None:
                span.set_status("ERROR")
                span.set_attribute("failure_type", execution.failure_type)
                return execution, Draft(
                    answer="I couldn't produce a usable, cited answer. Please try again later.",
                    status="insufficient_evidence",
                    evidence_ids=(),
                    unanswered=(),
                    qualifications=(),
                )
            try:
                draft = Draft.model_validate_json(execution.content or "")
                cite_answer(draft, context, retrieved.snapshot.snapshot_id)
            except ValueError:
                span.set_status("ERROR")
                span.set_attribute("failure_type", "malformed_output")
                return execution.model_copy(update={"failure_type": "malformed_output"}), Draft(
                    answer="I couldn't produce a usable, cited answer. Please try again later.",
                    status="insufficient_evidence",
                    evidence_ids=(),
                    unanswered=(),
                    qualifications=(),
                )
            return execution, draft
