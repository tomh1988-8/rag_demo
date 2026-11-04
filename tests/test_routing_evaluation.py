"""A matching route label cannot replace supported task completion."""

from uuid import UUID

from ask_phil.answers import AnswerRecord
from ask_phil.evaluation import QualityReview, score_answer_review
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionBudget, ExecutionLimits
from ask_phil.models import TokenUsage
from ask_phil.routing import RoutingRecord
from ask_phil.routing_evaluation import score_routing


def test_multiple_routes_can_succeed_and_label_agreement_does_not_repair_bad_answers(
    seed: SourceSnapshot,
) -> None:
    routing = RoutingRecord(
        requested_route="auto",
        selection="automatic",
        final_route="graph",
        stages=(),
        stop_reason="completed",
    )
    answer = AnswerRecord(
        response_id=UUID(int=18),
        question="An unsupported question?",
        status="insufficient_evidence",
        answer="The captured evidence cannot answer this.",
        citations=(),
        snapshot_id=seed.snapshot_id,
        snapshot_sha256=seed.fingerprint,
        source=seed.source,
        retrieved=(),
        context=(),
        retrieval_k=0,
        model_settings=None,
        prompt_sha256="a" * 64,
        application_sha256="b" * 64,
        trace_id="review-example",
        elapsed_ms=1,
        usage=TokenUsage(),
        expenditure_category="serving",
        route="graph",
        routing=routing,
        execution=ExecutionBudget(ExecutionLimits()).record(),
    )
    review = QualityReview(
        case_id="unsupported",
        response_sha256="a" * 64,
        reference_sha256="b" * 64,
        reviewer="independent source example",
        rationale="Known outcome counterexample.",
        claims=(),
        required_facts=(),
        answerability=False,
        relevance=True,
    )
    failed = score_routing(
        answer,
        graph_eligible=False,
        allowed_routes=("graph", "text_rag"),
        quality=score_answer_review(review),
    )
    assert failed.route_allowed
    assert failed.task_success is False
    text = answer.model_copy(
        update={
            "route": "text_rag",
            "routing": routing.model_copy(update={"final_route": "text_rag"}),
        }
    )
    success = score_routing(
        text,
        graph_eligible=False,
        allowed_routes=("graph", "text_rag"),
        quality=score_answer_review(review.model_copy(update={"answerability": True})),
    )
    assert success.route_allowed
    assert success.task_success is True
    assert not success.usage_complete
