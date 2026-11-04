"""Route diagnostics and source-reviewed task success are independent measurements."""

from ask_phil.answers import AnswerRecord
from ask_phil.evaluation import AnswerQuality
from ask_phil.evidence import Record
from ask_phil.routing import Route


class RoutingScores(Record):
    eligibility_correct: bool | None
    route_allowed: bool
    task_success: bool | None
    within_limits: bool | None
    usage_complete: bool
    serving_cost_usd: float | None
    known_stage_cost_usd: float
    missing_stage_costs: int
    limitation: str = (
        "Route labels do not establish task success. Quality uses separately bound source "
        "reviews, including abstention and all required facts. Stage costs cover every "
        "executed stage; unknown usage is not zero. Infrastructure cost is unmeasured."
    )


def score_routing(
    answer: AnswerRecord,
    *,
    graph_eligible: bool,
    allowed_routes: tuple[Route, ...],
    quality: AnswerQuality | None = None,
) -> RoutingScores:
    """The capture review boundary must bind quality to this exact response/reference."""
    routing = answer.routing
    eligibility = routing.eligibility if routing else None
    execution = answer.execution
    task_success = None
    if quality is not None:
        metrics = (
            quality.correctness,
            quality.groundedness,
            quality.completeness,
            quality.citation_support,
            quality.answerability,
            quality.relevance,
        )
        if (
            not any(m.unassessed for m in metrics)
            and quality.answerability.assessed
            and quality.relevance.assessed
        ):
            task_success = not quality.critical_failures and all(
                m.passed == m.assessed for m in metrics
            )
    costs = [s.accounting.estimated_api_cost_usd for s in routing.stages] if routing else []
    return RoutingScores(
        eligibility_correct=(eligibility.eligible == graph_eligible) if eligibility else None,
        route_allowed=answer.route in allowed_routes,
        task_success=task_success,
        within_limits=(
            execution.model_calls <= execution.limits.model_calls
            and execution.tool_calls <= execution.limits.tool_calls
            and execution.http_calls <= execution.limits.http_calls
            and execution.reserved_usd <= execution.limits.spend_usd
            and (execution.context_bytes or 0) <= execution.limits.context_bytes
        )
        if execution
        else None,
        usage_complete=all(v is not None for v in answer.usage.model_dump().values()),
        serving_cost_usd=answer.estimated_api_cost_usd,
        known_stage_cost_usd=sum(c for c in costs if c is not None),
        missing_stage_costs=sum(c is None for c in costs),
    )
