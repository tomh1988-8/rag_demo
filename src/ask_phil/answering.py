"""One answer lifecycle for text and Family tree execution, tracing and retained receipts."""

import hashlib
import time
from pathlib import Path
from threading import BoundedSemaphore, Lock
from typing import Literal
from uuid import uuid4

import mlflow
from mlflow import MlflowClient
from mlflow.entities import MlflowExperimentLocation

from ask_phil.answers import AnswerReceipt, AnswerRecord, AskRequest
from ask_phil.conversation import ReferenceTurn, TurnIdentity
from ask_phil.execution import ExecutionBudget, ExecutionPolicies
from ask_phil.family_answering import FamilyAnswer
from ask_phil.models import ModelConfigurationError, Models
from ask_phil.responses import ResponseLedger
from ask_phil.retrieval import TextRetriever
from ask_phil.text_answering import TextAnswer
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
        models: Models | None,
        tracking_uri: str,
        *,
        policies: ExecutionPolicies | None = None,
    ) -> None:
        self.database_url = database_url
        self.policies = policies or ExecutionPolicies.from_environment()
        self._slots = {
            category: BoundedSemaphore(getattr(self.policies, category).concurrency)
            for category in ("serving", "offline_evaluation")
        }
        self._models = models
        self._retriever: TextRetriever | None = None
        self._model_lock = Lock()
        self.ledger = ResponseLedger(database_url)
        # One configured MLflow backend per process; experiments separate costs.
        mlflow.set_tracking_uri(tracking_uri)
        self.tracking = MlflowClient(tracking_uri=tracking_uri)

    def _text_resources(self) -> tuple[Models, TextRetriever]:
        with self._model_lock:
            models = self._models if self._models is not None else Models.from_environment()
            if self._retriever is None:
                if (
                    models.redact(models.settings.model_dump_json())
                    != models.settings.model_dump_json()
                ):
                    raise ModelConfigurationError("Model settings contain unsafe credential text.")
                self._retriever = TextRetriever(
                    self.database_url,
                    models.embedding,
                    models.settings.embedding_id,
                    models.settings.embedding_dimensions,
                )
                self._models = models
            return models, self._retriever

    def prepare(self, snapshot_id: str) -> str:
        models, retriever = self._text_resources()
        models.verify()
        experiment_id = experiment_for(self.tracking, "indexing")
        with mlflow.start_span(
            "prepare_text_index", trace_destination=MlflowExperimentLocation(experiment_id)
        ) as span:
            span.set_inputs({"snapshot_id": snapshot_id})
            span.set_attributes(
                {
                    "expenditure_category": "indexing",
                    "model_settings": models.settings.model_dump(mode="json"),
                }
            )
            retriever.prepare(snapshot_id)
            span.set_outputs({"index_ready": True, "embedding_id": models.settings.embedding_id})
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
        route: TextAnswer | FamilyAnswer
        if request.route == "graph":
            route = FamilyAnswer(self.database_url, request.snapshot_id, budget)
        else:
            models, retriever = self._text_resources()
            request = request.model_copy(update={"question": models.redact(request.question)})
            route = TextAnswer(models, retriever.pin(request.snapshot_id))
        response_id = uuid4()
        experiment_id = experiment_for(self.tracking, category)
        with mlflow.start_span(
            request.route, trace_destination=MlflowExperimentLocation(experiment_id)
        ) as root:
            root.set_inputs(request.model_dump(mode="json"))
            root.set_attributes(
                {
                    "response_id": str(response_id),
                    "expenditure_category": category,
                    "route_override": request.route == "graph",
                }
            )
            if route.publication:
                root.set_attribute(
                    "publication", route.publication.reference.model_dump(mode="json")
                )
            content = route.answer(request, turn, history, budget, root)
            if content.conversation:
                root.set_attribute("conversation", content.conversation.model_dump(mode="json"))
            root.set_attributes(
                {
                    "usage_complete": content.accounting.usage_complete,
                    "execution": budget.record().model_dump(mode="json"),
                }
            )
            response = AnswerRecord(
                response_id=response_id,
                question=request.question,
                conversation=content.conversation,
                status=content.status,
                answer=content.answer,
                unanswered=content.unanswered,
                qualifications=content.qualifications,
                citations=content.citations,
                snapshot_id=route.snapshot.snapshot_id,
                snapshot_sha256=route.snapshot.fingerprint,
                publication=route.publication.reference if route.publication else None,
                source=route.snapshot.source,
                retrieved=content.retrieved,
                context=content.context,
                context_claims=content.context_claims,
                review_notices=content.review_notices,
                retrieval_k=content.retrieval_k,
                route=request.route,
                route_override=request.route == "graph",
                graph=content.graph,
                baseline_version=content.baseline_version,
                model_settings=content.model_settings,
                prompt_sha256=content.prompt_sha256,
                application_sha256=application_fingerprint(),
                trace_id=root.trace_id,
                execution=budget.record(),
                elapsed_ms=(time.perf_counter() - started) * 1000,
                usage=content.accounting.usage,
                expenditure_category=category,
                provider_usage=content.accounting.provider_usage,
                estimated_api_cost_usd=content.accounting.estimated_api_cost_usd,
                cost_scope=content.accounting.cost_scope,
                limitation=content.accounting.limitation,
            )
            root.set_outputs(response.model_dump(mode="json"))
        # Complete the trace before storing and returning the same immutable outcome.
        self.tracking.get_trace(response.trace_id, flush=True)
        return self.ledger.save(response)
