"""Model decisions within a finite captured-text investigation."""

import hashlib
import json
from typing import Annotated, Literal

import mlflow
import psycopg
from llama_index.core.llms import ChatMessage
from mlflow.entities import LiveSpan
from pydantic import Field

from ask_phil.answers import (
    SYSTEM_PROMPT,
    AnswerContent,
    AskRequest,
    Draft,
    cite_answer,
    stopped_answer,
)
from ask_phil.classified_facts import context_for
from ask_phil.conversation import (
    ConversationReference,
    ReferenceTurn,
    TurnIdentity,
    resolve_reference,
)
from ask_phil.evidence import Passage, Record
from ask_phil.execution import ExecutionBudget, ExecutionStopped
from ask_phil.identity import IdentityCatalogue
from ask_phil.investigation_records import CoveragePart, InvestigationRecord, TextFinding
from ask_phil.investigation_tools import (
    TOOL_CONTRACT,
    TOOL_CONTRACT_SHA256,
    InvestigationTools,
)
from ask_phil.models import ModelConfigurationError, ModelExecution, Models, TokenUsage
from ask_phil.retrieval import IndexNotReady, PinnedText
from ask_phil.review_notes import ReviewNotice, prepare_text_review

INVESTIGATOR_PROMPT = (
    """Single bounded investigator, version bounded-investigator-v1.
Return a coverage list and exactly one action. First identify EVERY requested part;
keep the same part texts on later decisions. A part is resolved only when the supplied
context supports it; list its evidence_ids. No context means no resolved parts.
Choose action {kind: tool, tool: a declared tool name, arguments: JSON-encoded object string}
to gather evidence, or {kind: finish, draft: the five-field answer object} to finish.
Assess combined sufficiency: one relevant passage need not answer all requested facts.
Use only declared tools. Arguments cannot change snapshot, limits or authority.
Repeated identical calls cannot add evidence. Repair invalid arguments only when the
remaining budget allows it. Stop with partial/insufficient evidence when necessary.
The coverage assessment is an explicit evidence judgment, not hidden reasoning.
Do not narrate imagined searches. The application records the tools actually executed.
The final draft must follow these answer rules:
"""
    + SYSTEM_PROMPT
)


class ToolAction(Record):
    kind: Literal["tool"]
    tool: str = Field(min_length=1, max_length=80)
    arguments: str = Field(max_length=2000)


class FinishAction(Record):
    kind: Literal["finish"]
    draft: Draft


class InvestigationDecision(Record):
    coverage: tuple[CoveragePart, ...] = Field(min_length=1, max_length=5)
    action: Annotated[ToolAction | FinishAction, Field(discriminator="kind")]


def _sum_known[T: (int, float)](values: list[T | None]) -> T | None:
    return None if any(v is None for v in values) else sum(v for v in values if v is not None)


def _validate_coverage(
    proposed: tuple[CoveragePart, ...],
    previous: tuple[CoveragePart, ...],
    context: tuple[Passage, ...],
) -> None:
    parts = tuple(c.part for c in proposed)
    if len(set(parts)) != len(parts) or (previous and parts != tuple(c.part for c in previous)):
        raise ValueError("Requested parts must remain distinct and stable.")
    available = {p.evidence_id for p in context}
    if any(
        (c.resolved and not c.evidence_ids)
        or len(set(c.evidence_ids)) != len(c.evidence_ids)
        or not set(c.evidence_ids) <= available
        for c in proposed
    ):
        raise ValueError("Coverage must refer to available evidence.")


def _qualified_draft(draft: Draft, coverage: tuple[CoveragePart, ...]) -> Draft:
    resolved_ids = {eid for c in coverage if c.resolved for eid in c.evidence_ids}
    if not resolved_ids <= set(draft.evidence_ids):
        raise ValueError("Final citations must include the assessed support.")
    unresolved = tuple(c.part for c in coverage if not c.resolved)
    if draft.status in {"answered", "partial"} and unresolved:
        return Draft(
            **{
                **draft.model_dump(),
                "status": "partial",
                "unanswered": unresolved,
                "answer": draft.answer + " Unresolved: " + " ".join(unresolved),
            }
        )
    return draft


class Investigation:
    def __init__(self, database_url: str, models: Models, pinned: PinnedText) -> None:
        if pinned.publication is None:
            raise IndexNotReady("Investigation requires a published source/index/graph snapshot.")
        self.models = models
        self.database_url = database_url
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
        question = request.question
        conversation = None
        if turn:
            reference = resolve_reference(
                question,
                self.snapshot.imported.catalogue
                if self.snapshot.imported
                else IdentityCatalogue(characters=()),
                history,
            )
            conversation = ConversationReference(**turn.model_dump(), reference=reference)
            question = reference.question
        root.set_attributes({"prompt": INVESTIGATOR_PROMPT, "tool_contract": TOOL_CONTRACT})
        tools = InvestigationTools(self.database_url, self.models, self.pinned, budget)
        coverage: tuple[CoveragePart, ...] = ()
        calls: list[ModelExecution] = []
        draft: Draft | None = None
        stop_reason = "completed"
        stopped = False
        try:
            budget.check()
            self.pinned.verify()
            self.models.verify()
            budget.check()
            if conversation and conversation.reference.clarification:
                draft = Draft(
                    answer=conversation.reference.clarification,
                    status="clarification",
                    evidence_ids=(),
                    unanswered=("Which character is intended?",),
                    qualifications=(),
                )
            while draft is None:
                budget.check()
                budget.context(tools.context_bytes)
                with mlflow.start_span("investigator_decision", span_type="LLM") as span:
                    messages = [
                        ChatMessage(role="system", content=INVESTIGATOR_PROMPT + TOOL_CONTRACT),
                        ChatMessage(
                            role="user",
                            content=json.dumps(
                                {
                                    "question": question,
                                    "source": self.snapshot.source.title,
                                    "support_status": self.snapshot.source.support_status,
                                    "coverage": [p.model_dump() for p in coverage],
                                    "context": tools.model_context(),
                                    "remaining": {
                                        "model_calls": budget.limits.model_calls
                                        - budget.record().model_calls,
                                        "tool_calls": budget.limits.tool_calls
                                        - budget.record().tool_calls,
                                    },
                                },
                                ensure_ascii=False,
                            ),
                        ),
                    ]
                    span.set_inputs([m.model_dump(mode="json") for m in messages])
                    execution = self.models.generate_answer(
                        messages, schema=InvestigationDecision.model_json_schema()
                    )
                    execution = execution.model_copy(
                        update={"usage": execution.usage.model_copy(update={"embedding_tokens": 0})}
                    )
                    calls.append(execution)
                    span.set_outputs({"content": execution.content})
                    span.set_attributes(execution.trace_attributes)
                    if execution.failure_type:
                        budget.stop(
                            execution.failure_type
                            if execution.failure_type
                            in {
                                "malformed_output",
                                "timeout",
                                "cancelled",
                                "endpoint_denied",
                                "input_limit",
                                "http_call_limit",
                                "spend_limit",
                                "model_call_limit",
                            }
                            else "provider_failure"
                        )
                    budget.check()
                    try:
                        choice = InvestigationDecision.model_validate_json(execution.content or "")
                    except ValueError:
                        budget.stop("malformed_output")
                _validate_coverage(choice.coverage, coverage, tools.context)
                coverage = choice.coverage
                if isinstance(choice.action, FinishAction):
                    draft = _qualified_draft(choice.action.draft, coverage)
                    cite_answer(draft, tools.context, self.snapshot.snapshot_id)
                    continue
                action = choice.action
                tools.execute(action.tool, action.arguments)
        except (
            ExecutionStopped,
            ValueError,
            psycopg.errors.QueryCanceled,
            psycopg.errors.LockNotAvailable,
        ) as exc:
            stop_reason = (
                str(exc)
                if isinstance(exc, ExecutionStopped)
                else "timeout"
                if isinstance(exc, psycopg.errors.QueryCanceled | psycopg.errors.LockNotAvailable)
                else "malformed_output"
            )
            budget.record_stop(stop_reason)
            root.set_status("ERROR")
            stopped = True
            resolved = {eid for c in coverage if c.resolved for eid in c.evidence_ids}
            excerpts = tuple(p for p in tools.context if p.evidence_id in resolved)[:3]
            draft = stopped_answer(
                stop_reason,
                excerpts,
                unanswered=tuple(c.part for c in coverage if not c.resolved),
                context_claims=tools.context_claims,
                synthetic=any(
                    (p.source or self.snapshot.source).support_status == "synthetic_fixture"
                    for p in tools.context
                ),
            )
        assert draft is not None
        notices: tuple[ReviewNotice, ...] = ()
        if tools.review_notices:
            stopped = False
            review = prepare_text_review(
                self.snapshot, tools.review_notices, budget.limits.context_bytes
            )
            # Preserve the reviewed interpretation even if a model repeats a predecessor.
            if review.context and len(review.text) <= 1400:
                notices = review.notices
                draft = Draft(
                    answer="Right, listen. " + review.text,
                    status="partial",
                    evidence_ids=tuple(p.evidence_id for p in review.context),
                    unanswered=("Coverage beyond these reviewed accounts remains unresolved.",),
                    qualifications=(),
                )
                coverage = tuple(
                    c.model_copy(update={"resolved": False, "evidence_ids": ()}) for c in coverage
                )
                if stop_reason == "completed":
                    stop_reason = "reviewed_interpretation"
            else:
                budget.record_stop("context_limit")
                stop_reason = budget.record().stop_reason or "context_limit"
                draft = Draft(
                    answer=(
                        "The reviewed accounts cannot be safely assembled within "
                        "this request's context limit."
                    ),
                    status="insufficient_evidence",
                    evidence_ids=(),
                    qualifications=(),
                    unanswered=("The reviewed interpretation remains unresolved.",),
                )
        classifications = context_for(tools.context_claims, draft.evidence_ids)
        answer = draft.answer
        if classifications and not stopped:
            answer += "\n" + "\n".join(dict.fromkeys(c.qualification for c in classifications))
        if not stopped and any(
            (p.source or self.snapshot.source).support_status == "synthetic_fixture"
            for p in tools.context
        ):
            answer = "Synthetic example, not EastEnders canon. " + answer
        accounting = self.models.skipped_answer().model_copy(
            update={
                "usage": TokenUsage(
                    input_tokens=_sum_known([c.usage.input_tokens for c in calls]),
                    output_tokens=_sum_known([c.usage.output_tokens for c in calls]),
                    embedding_tokens=_sum_known(tools.embeddings),
                ),
                "estimated_api_cost_usd": _sum_known([c.estimated_api_cost_usd for c in calls]),
                "cost_scope": "All investigator decisions and query embeddings; "
                + self.models.skipped_answer().cost_scope,
            }
        )
        return AnswerContent(
            conversation=conversation,
            status=draft.status,
            answer=answer,
            unanswered=draft.unanswered,
            qualifications=draft.qualifications,
            citations=cite_answer(draft, tools.context, self.snapshot.snapshot_id),
            context=tools.context,
            review_notices=notices,
            context_claims=classifications,
            retrieved=tuple(
                h for s in tools.steps if isinstance(s.result, TextFinding) for h in s.result.hits
            ),
            retrieval_k=max(
                (len(s.result.hits) for s in tools.steps if isinstance(s.result, TextFinding)),
                default=0,
            ),
            model_settings=self.models.settings,
            baseline_version="bounded-investigator-v1",
            prompt_sha256=hashlib.sha256(INVESTIGATOR_PROMPT.encode()).hexdigest(),
            accounting=accounting,
            investigation=InvestigationRecord(
                tool_contract_sha256=TOOL_CONTRACT_SHA256,
                coverage=coverage,
                steps=tuple(tools.steps),
                model_executions=tuple(calls),
                embedding_tokens=tuple(tools.embeddings),
                stop_reason=stop_reason,
                context_bytes=budget.record().context_bytes or 0,
                context=tools.context,
            ),
        )
