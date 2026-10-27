"""Text evidence and wording inside the shared answer execution lifecycle."""

import hashlib

import mlflow
from llama_index.core.llms import ChatMessage
from mlflow.entities import LiveSpan

from ask_phil.answers import (
    SYSTEM_PROMPT,
    AnswerContent,
    AskRequest,
    Citation,
    Draft,
    assemble_context,
    cite_answer,
    context_text,
)
from ask_phil.classified_facts import context_for
from ask_phil.conversation import (
    ConversationReference,
    ReferenceTurn,
    TurnIdentity,
    resolve_reference,
)
from ask_phil.evidence import Passage
from ask_phil.execution import ExecutionBudget, ExecutionStopped
from ask_phil.identity import IdentityCatalogue
from ask_phil.models import ModelConfigurationError, ModelExecution, Models, TokenUsage
from ask_phil.retrieval import PinnedText, Retrieval
from ask_phil.review_notes import (
    REVIEW_WORDING,
    ReviewExplanation,
    ReviewNotice,
    prepare_text_review,
)


class TextAnswer:
    def __init__(self, models: Models, pinned: PinnedText) -> None:
        self.models = models
        self.pinned = pinned
        self.snapshot = pinned.snapshot
        self.publication = pinned.publication
        if models.redact(self.snapshot.model_dump_json()) != self.snapshot.model_dump_json():
            raise ModelConfigurationError("Captured evidence contains unsafe credential text.")

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
        root.set_attributes(
            {
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
        notices: tuple[ReviewNotice, ...] = ()
        review = ReviewExplanation()
        clarification = conversation.reference.clarification if conversation else None
        try:
            budget.check()
            self.pinned.verify()
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
                    retrieved = self.pinned.retrieve(question, k=3)
                    span.set_outputs(retrieved.model_dump(mode="json"))
                execution = self.models.skipped_answer()
                with mlflow.start_span("assembled_context") as span:
                    context = assemble_context(
                        retrieved.hits,
                        budget.limits.context_bytes,
                        context_claims=retrieved.context_claims,
                    )
                    if retrieved.review_notices:
                        review = prepare_text_review(
                            snapshot, retrieved.review_notices, budget.limits.context_bytes
                        )
                        context = review.context
                    span.set_outputs(
                        {
                            "passages": [p.model_dump() for p in context],
                            "byte_budget": budget.limits.context_bytes,
                            "context_claims": [
                                c.model_dump()
                                for c in context_for(
                                    retrieved.context_claims, (p.evidence_id for p in context)
                                )
                            ],
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
                        unanswered=("The question cannot be answered from the available context.",),
                    )
                    root.set_attribute("answer_model_skipped", "empty_context")
                elif retrieved.review_notices:
                    notices = review.notices
                    draft = Draft(
                        answer="Right, listen. " + review.text,
                        status="partial",
                        evidence_ids=tuple(p.evidence_id for p in context),
                        unanswered=(
                            "Coverage beyond these reviewed source accounts remains unresolved.",
                        ),
                        qualifications=(),
                    )
                    citations = cite_answer(draft, context, snapshot_id)
                    root.set_attributes(
                        {
                            "answer_model_skipped": "reviewed_interpretation",
                            "prompt": REVIEW_WORDING,
                        }
                    )
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
                        "usage": TokenUsage(input_tokens=0, output_tokens=0, embedding_tokens=None)
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
                        else ("I couldn't produce a usable, cited answer. Please try again later.")
                    )
                    + " This limit does not establish that an event did not happen."
                ),
                status="partial" if context and not failure else "insufficient_evidence",
                evidence_ids=tuple(p.evidence_id for p in context) if not failure else (),
                unanswered=("The requested answer is incomplete because execution stopped.",),
                qualifications=(),
            )
            citations = cite_answer(draft, context, snapshot_id)
        classifications = context_for(retrieved.context_claims, (c.evidence_id for c in citations))
        answer = draft.answer
        if classifications:
            answer += "\n" + "\n".join(dict.fromkeys(c.qualification for c in classifications))
        return AnswerContent(
            conversation=conversation,
            status="failed" if failure else draft.status,
            answer=answer,
            context_claims=classifications,
            review_notices=notices,
            unanswered=draft.unanswered,
            qualifications=draft.qualifications,
            citations=citations,
            context=context,
            retrieved=retrieved.hits,
            retrieval_k=retrieved.k,
            baseline_version="single-query-uncached-v2",
            model_settings=self.models.settings,
            prompt_sha256=hashlib.sha256(
                (REVIEW_WORDING if notices else SYSTEM_PROMPT).encode()
            ).hexdigest(),
            accounting=execution,
        )

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
                        f"Captured evidence: {context_text(context, retrieved.context_claims)}"
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
