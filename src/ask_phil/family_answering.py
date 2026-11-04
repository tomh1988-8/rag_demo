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
from ask_phil.graph_execution import GraphExecution, GraphResult
from ask_phil.graph_wording import GraphExplanation
from ask_phil.models import ModelExecution, TokenUsage
from ask_phil.publications import ActivePublication
from ask_phil.review_notes import (
    REVIEW_WORDING,
    ReviewedClaims,
    ReviewExplanation,
    ReviewNotice,
)
from ask_phil.security import require_credential_free


class FamilyAnswer:
    def __init__(
        self,
        database_url: str,
        snapshot_id: str | None,
        budget: ExecutionBudget,
        *,
        publication: ActivePublication | None = None,
    ) -> None:
        self.database_url = database_url
        self._graph = GraphExecution(
            database_url, snapshot_id, execution=budget, publication=publication
        )
        self.publication = self._graph.publication
        self.snapshot = self._graph.snapshot
        self._reviews = ReviewedClaims(database_url, self.snapshot)
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
        result: GraphResult | None = None
        assert request.graph is not None
        explanation = GraphExplanation.for_query(request.graph)
        wording = explanation.wording
        context: tuple[Passage, ...] = ()
        citations: tuple[Citation, ...] = ()
        notices: tuple[ReviewNotice, ...] = ()
        review = ReviewExplanation()
        try:
            budget.check()
            with mlflow.start_span(explanation.span_name, span_type="RETRIEVER") as span:
                span.set_inputs(request.graph.model_dump())
                result = self._graph.query(request.graph)
                span.set_outputs(result.model_dump(mode="json"))
            review = self._reviews.graph(result, budget.limits.context_bytes)
            context, notices = review.context, review.notices
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
            notices = ()
            root.set_status("ERROR")
        supported = explanation.supported(result)
        status: Literal["partial", "insufficient_evidence"] = (
            "partial" if supported else "insufficient_evidence"
        )
        answer = explanation.render(
            result, synthetic=review.synthetic, stop_reason=budget.record().stop_reason
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
        if notices:
            answer += "\n" + review.text + "\n"
            wording += REVIEW_WORDING
            status = "partial"
        return AnswerContent(
            conversation=conversation,
            status=status,
            answer=answer + explanation.limitation,
            unanswered=explanation.unanswered,
            citations=citations,
            context=context,
            review_notices=notices,
            graph=result,
            prompt_sha256=hashlib.sha256(wording.encode()).hexdigest(),
            accounting=ModelExecution(
                content=None,
                usage=TokenUsage(input_tokens=0, output_tokens=0, embedding_tokens=0),
                provider_usage=None,
                failure_type=None,
                estimated_api_cost_usd=0,
                cost_scope="No inference calls. Database and hosting costs are excluded.",
                limitation=explanation.limitation,
            ),
        )
