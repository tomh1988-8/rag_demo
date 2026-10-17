"""One bounded text-RAG execution, traced and durably associated with its final answer."""

import hashlib
import time
from pathlib import Path
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
from ask_phil.models import Models
from ask_phil.passage_context import CONTEXT_BYTE_BUDGET
from ask_phil.publications import PublicationStore
from ask_phil.responses import ResponseLedger
from ask_phil.retrieval import IndexNotReady, TextRetriever


def application_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class AnswerService:
    def __init__(self, database_url: str, models: Models, tracking_uri: str) -> None:
        self.models = models
        self.publications = PublicationStore(database_url)
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

    def _experiment(self, category: str) -> str:
        name = f"ask-phil-{category}"
        experiment = self.tracking.get_experiment_by_name(name)
        return (
            experiment.experiment_id
            if experiment
            else self.tracking.create_experiment(
                name, artifact_location=str(Path("artifacts/mlflow").resolve().as_uri())
            )
        )

    def prepare(self, snapshot_id: str) -> str:
        self.models.verify()
        experiment_id = self._experiment("indexing")
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
        self, request: AskRequest, *, category: Literal["serving", "offline_evaluation"] = "serving"
    ) -> AnswerReceipt:
        started = time.perf_counter()
        publication = self.publications.pin(request.snapshot_id)
        snapshot_id = publication.manifest.snapshot_id if publication else request.snapshot_id
        if snapshot_id is None:
            raise IndexNotReady("Publish a usable source/index snapshot before answering.")
        if publication and self.retriever.manifest(snapshot_id) != publication.manifest.index:
            raise IndexNotReady("The configured retrieval index differs from the publication.")
        self.models.verify()
        response_id = uuid4()
        experiment_id = self._experiment(category)
        with mlflow.start_span(
            "text_rag", trace_destination=MlflowExperimentLocation(experiment_id)
        ) as root:
            root.set_inputs(request.model_dump())
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
            with mlflow.start_span("text_retrieval", span_type="RETRIEVER") as span:
                span.set_inputs({"question": request.question, "k": 3})
                retrieved = self.retriever.retrieve(snapshot_id, request.question, k=3)
                span.set_outputs(retrieved.model_dump(mode="json"))
            with mlflow.start_span("assembled_context") as span:
                context = assemble_context(retrieved.hits)
                span.set_outputs(
                    {
                        "passages": [p.model_dump() for p in context],
                        "byte_budget": CONTEXT_BYTE_BUDGET,
                    }
                )
            failure = False
            citations: tuple[Citation, ...] = ()
            if not context:
                execution = self.models.skipped_answer()
                draft = Draft(
                    answer=(
                        "I can't answer from the available captured context. "
                        "Missing evidence doesn't establish that an event didn't happen."
                    ),
                    evidence_ids=(),
                    status="insufficient_evidence",
                    qualifications=(),
                    unanswered=("The question cannot be answered from the available context.",),
                )
                root.set_attribute("answer_model_skipped", "empty_context")
            else:
                with mlflow.start_span("answer_model", span_type="LLM") as span:
                    messages = [
                        ChatMessage(role="system", content=SYSTEM_PROMPT),
                        ChatMessage(
                            role="user",
                            content=(
                                f"Question: {request.question}\n"
                                f"Snapshot provenance: {retrieved.snapshot.source.title} "
                                f"({retrieved.snapshot.source.support_status})\n"
                                f"Captured evidence: {context_text(context)}"
                            ),
                        ),
                    ]
                    span.set_inputs([m.model_dump(mode="json") for m in messages])
                    execution = self.models.generate_answer(
                        messages, schema=Draft.model_json_schema()
                    )
                    span.set_outputs({"content": execution.content})
                    span.set_attributes(execution.trace_attributes)
                    validated: Draft | None = None
                    failure_type = execution.failure_type
                    if failure_type is None:
                        try:
                            candidate = Draft.model_validate_json(execution.content or "")
                            citations = cite_answer(candidate, context, snapshot_id)
                            validated = candidate
                        except ValueError as exc:
                            failure_type = type(exc).__name__
                    if validated is None:
                        failure = True
                        span.set_status("ERROR")
                        span.set_attributes({"failure_type": failure_type})
                        root.set_status("ERROR")
                        draft = Draft(
                            answer=(
                                "I couldn't produce a usable, cited answer. Please try again later."
                            ),
                            status="insufficient_evidence",
                            evidence_ids=(),
                            unanswered=(),
                            qualifications=(),
                        )
                    else:
                        draft = validated
            root.set_attribute("usage_complete", execution.usage_complete)
            response = AnswerRecord(
                response_id=response_id,
                question=request.question,
                status="failed" if failure else draft.status,
                answer=draft.answer,
                unanswered=draft.unanswered,
                qualifications=draft.qualifications,
                citations=citations,
                snapshot_id=snapshot_id,
                snapshot_sha256=retrieved.snapshot.fingerprint,
                publication=publication.reference if publication else None,
                source=retrieved.snapshot.source,
                retrieved=retrieved.hits,
                context=context,
                retrieval_k=3,
                baseline_version="single-query-uncached-v2",
                model_settings=self.models.settings,
                prompt_sha256=hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
                application_sha256=application_fingerprint(),
                trace_id=root.trace_id,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                usage=execution.usage,
                expenditure_category=category,
                provider_usage=execution.provider_usage,
                estimated_api_cost_usd=execution.estimated_api_cost_usd,
                cost_scope=execution.cost_scope,
                limitation=execution.limitation,
            )
            root.set_outputs(response.model_dump(mode="json"))
        # A returned reference must resolve to a completed trace, not just an allocated ID.
        self.tracking.get_trace(response.trace_id, flush=True)
        return self.ledger.save(response)
