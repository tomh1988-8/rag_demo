"""Automatic routes inside the existing single-response lifecycle."""

import time
from collections.abc import Callable
from dataclasses import replace
from threading import BoundedSemaphore

from mlflow.entities import LiveSpan

from ask_phil.answers import AnswerContent, AskRequest
from ask_phil.conversation import (
    ConversationReference,
    ReferenceTurn,
    TurnIdentity,
    resolve_snapshot_reference,
)
from ask_phil.execution import ExecutionBudget
from ask_phil.family_answering import FamilyAnswer
from ask_phil.graph_execution import GraphExecution
from ask_phil.investigation import Investigation
from ask_phil.models import ModelExecution, Models
from ask_phil.retrieval import PinnedText, TextRetriever
from ask_phil.routing import (
    Route,
    RoutingCheck,
    RoutingPolicy,
    RoutingRecord,
    RoutingRules,
    RoutingStage,
)
from ask_phil.text_answering import TextAnswer
from ask_phil.text_retrieval import TextPolicy


class AutomaticAnswer:
    def __init__(
        self,
        database_url: str,
        snapshot_id: str | None,
        budget: ExecutionBudget,
        resources: Callable[[], tuple[Models, TextRetriever]],
        text_policy: TextPolicy,
        investigation_slot: BoundedSemaphore,
    ) -> None:
        self.database_url = database_url
        graph = GraphExecution(database_url, snapshot_id, execution=budget)
        self.snapshot = graph.snapshot
        self.publication = graph.publication
        self.resources = resources
        self.text_policy = text_policy
        self.investigation_slot = investigation_slot
        self.policy = RoutingPolicy.from_environment()

    def answer(
        self,
        request: AskRequest,
        turn: TurnIdentity | None,
        history: tuple[ReferenceTurn, ...],
        budget: ExecutionBudget,
        root: LiveSpan,
    ) -> AnswerContent:
        selection_started = time.perf_counter()
        rules = RoutingRules.load(self.database_url, self.snapshot, budget.limits)
        reference = resolve_snapshot_reference(
            request.question, self.snapshot, history, legacy_catalogue=rules.catalogue
        )
        eligibility = rules.eligibility(reference.question) if not reference.clarification else None
        selection_elapsed_ms = (time.perf_counter() - selection_started) * 1000
        check_elapsed_ms = None
        stages: list[RoutingStage] = []
        checks: list[RoutingCheck] = []
        route: Route
        started = time.perf_counter()
        before = budget.record()
        if eligibility and eligibility.eligible:
            graph_request = request.model_copy(
                update={"route": "graph", "graph": eligibility.query}
            )
            content = FamilyAnswer(
                self.database_url, self.snapshot.snapshot_id, budget, publication=self.publication
            ).answer(graph_request, turn, history, budget, root)
            route = "graph"
        else:
            models, retriever = self.resources()
            pinned = PinnedText(retriever, self.snapshot, self.publication)
            content = TextAnswer(models, pinned, self.text_policy, reference=reference).answer(
                request, turn, history, budget, root
            )
            route = "text_rag"
        stages.append(
            RoutingStage(
                route=route,
                status=content.status,
                elapsed_ms=(time.perf_counter() - started) * 1000,
                execution_before=before,
                execution_after=budget.record(),
                accounting=content.accounting,
                graph=content.graph,
            )
        )
        checks.append(
            RoutingCheck(
                kind="selection",
                reason="eligible_graph"
                if route == "graph"
                else eligibility.reason
                if eligibility
                else "unresolved_reference",
            )
        )
        if route == "text_rag" and eligibility and not eligibility.eligible:
            checks.append(RoutingCheck(kind="fallback", reason="text_fallback"))
        if route == "graph" and not content.citations and not budget.record().stop_reason:
            checks.append(RoutingCheck(kind="fallback", reason="graph_evidence_gap"))
            models, retriever = self.resources()
            pinned = PinnedText(retriever, self.snapshot, self.publication)
            before = budget.record()
            started = time.perf_counter()
            content = TextAnswer(models, pinned, self.text_policy, reference=reference).answer(
                request, turn, history, budget, root
            )
            stages.append(
                RoutingStage(
                    route="text_rag",
                    status=content.status,
                    elapsed_ms=(time.perf_counter() - started) * 1000,
                    execution_before=before,
                    execution_after=budget.record(),
                    accounting=content.accounting,
                )
            )
            content = replace(
                content, accounting=ModelExecution.combine([s.accounting for s in stages])
            )
            route = "text_rag"
        stop_reason = budget.record().stop_reason or "completed"
        if route == "text_rag":
            check_started = time.perf_counter()
            reason = self.policy.escalation(
                status=content.status,
                reviewed=bool(content.review_notices),
                additional_evidence=rules.additional_evidence(
                    reference.question, content.unanswered, content.context, self.snapshot
                ),
                published=self.publication is not None,
                budget=budget,
            )
            check_elapsed_ms = (time.perf_counter() - check_started) * 1000
            checks.append(
                RoutingCheck(
                    kind="evidence",
                    reason=reason,
                    evidence_ids=tuple(c.evidence_id for c in content.citations),
                )
            )
            stop_reason = budget.record().stop_reason or reason
            if reason == "investigate_evidence_gap":
                acquired = self.investigation_slot.acquire(blocking=False)
                if acquired:
                    try:
                        before = budget.record()
                        started = time.perf_counter()
                        investigated = Investigation(
                            self.database_url, models, pinned, reference=reference
                        ).answer(request, turn, history, budget, root, initial=content)
                        stages.append(
                            RoutingStage(
                                route="investigation",
                                status=investigated.status,
                                elapsed_ms=(time.perf_counter() - started) * 1000,
                                execution_before=before,
                                execution_after=budget.record(),
                                accounting=investigated.accounting,
                            )
                        )
                        retain_prior = (
                            bool(content.citations)
                            and not investigated.review_notices
                            and (
                                budget.record().stop_reason is not None
                                or investigated.status
                                in {"failed", "insufficient_evidence", "clarification"}
                                or not {c.evidence_id for c in content.citations}
                                <= {c.evidence_id for c in investigated.citations}
                            )
                        )
                        content = replace(
                            content if retain_prior else investigated,
                            investigation=investigated.investigation,
                            text_pipeline=content.text_pipeline,
                            accounting=ModelExecution.combine([s.accounting for s in stages]),
                        )
                        route = "text_rag" if retain_prior else "investigation"
                        stop_reason = budget.record().stop_reason or "completed"
                        checks.append(
                            RoutingCheck(kind="escalation", reason="investigation_executed")
                        )
                        if retain_prior:
                            checks.append(
                                RoutingCheck(kind="fallback", reason="retained_prior_support")
                            )
                    finally:
                        self.investigation_slot.release()
                else:
                    checks.append(
                        RoutingCheck(kind="escalation", reason="investigation_concurrency_limit")
                    )
                    stop_reason = "investigation_concurrency_limit"
        else:
            checks.append(
                RoutingCheck(
                    kind="evidence",
                    reason="qualified_graph_coverage",
                    evidence_ids=tuple(c.evidence_id for c in content.citations),
                )
            )
        if turn and route == "graph":
            content = replace(
                content,
                conversation=ConversationReference(**turn.model_dump(), reference=reference),
            )
        return replace(
            content,
            routing=RoutingRecord(
                requested_route="auto",
                selection="automatic",
                final_route=route,
                eligibility=eligibility,
                stages=tuple(stages),
                checks=tuple(checks),
                stop_reason=stop_reason,
                policy=self.policy,
                selection_elapsed_ms=selection_elapsed_ms,
                evidence_check_elapsed_ms=check_elapsed_ms,
            ),
        )
