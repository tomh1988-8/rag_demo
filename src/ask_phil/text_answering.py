"""Text evidence and wording inside the shared answer execution lifecycle."""

import hashlib
from typing import Literal

import mlflow
from llama_index.core.llms import ChatMessage
from mlflow.entities import LiveSpan

from ask_phil.answers import (
    SYSTEM_PROMPT,
    AnswerContent,
    AskRequest,
    Citation,
    Draft,
    cite_answer,
    context_text,
    stopped_answer,
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
from ask_phil.models import ModelConfigurationError, ModelExecution, Models
from ask_phil.retrieval import PinnedText, Retrieval
from ask_phil.review_notes import (
    REVIEW_WORDING,
    ReviewNotice,
    TextReview,
)
from ask_phil.text_retrieval import ConventionalText, TextPolicy


class TextAnswer:
    def __init__(self, models: Models, pinned: PinnedText, policy: TextPolicy) -> None:
        self.models = models
        self.pinned = pinned
        self.snapshot = pinned.snapshot
        self.publication = pinned.publication
        self.policy = policy
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
        with self.models.accounting() as accounting:
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
            pipeline = ConventionalText(
                self.pinned, self.models, self.policy, request.question, question
            )
            citations: tuple[Citation, ...] = ()
            failure = False
            stopped = False
            notices: tuple[ReviewNotice, ...] = ()
            review: TextReview | None = None
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
                    selection = pipeline.retrieve(budget)
                    retrieved, context = selection.retrieved, selection.context
                    review = selection.review
                    with mlflow.start_span("assembled_context") as span:
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
                    if review is not None:
                        draft, citations, notices = review.draft, review.citations, review.notices
                        root.set_attributes(
                            {
                                "answer_model_skipped": "reviewed_interpretation",
                                "prompt": REVIEW_WORDING,
                            }
                        )
                    elif not context:
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
                if pipeline.selection is not None:
                    retrieved, context = pipeline.selection.retrieved, pipeline.selection.context
                    review = pipeline.selection.review
                reason = str(exc)
                budget.record_stop(reason)
                root.set_status("ERROR")
                failure = reason in {"provider_failure", "malformed_output"}
                stopped = True
                if review is not None:
                    draft, citations, notices = review.draft, review.citations, review.notices
                else:
                    draft = stopped_answer(
                        reason,
                        () if failure else context,
                        context_claims=retrieved.context_claims,
                        synthetic=any(
                            (p.source or snapshot.source).support_status == "synthetic_fixture"
                            for p in context
                        ),
                    )
                    citations = cite_answer(draft, context, snapshot_id)
            classifications = context_for(
                retrieved.context_claims, (c.evidence_id for c in citations)
            )
            answer = draft.answer
            if classifications and not stopped and review is None:
                answer += "\n" + "\n".join(dict.fromkeys(c.qualification for c in classifications))
            record = pipeline.record.with_final_context(
                context, retrieved.context_claims
            ).model_copy(
                update={
                    "model_executions": accounting.executions,
                    "embedding_tokens": accounting.embedding_tokens,
                }
            )
            version: Literal["single-query-uncached-v2", "bounded-text-v1"] = (
                "single-query-uncached-v2" if self.policy.mode == "baseline" else "bounded-text-v1"
            )
            root.set_attributes(
                {"text_pipeline": record.model_dump(mode="json"), "baseline_version": version}
            )
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
                baseline_version=version,
                text_pipeline=record,
                model_settings=self.models.settings,
                prompt_sha256=hashlib.sha256(
                    (REVIEW_WORDING if review is not None else SYSTEM_PROMPT).encode()
                ).hexdigest(),
                accounting=accounting.summary(),
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
