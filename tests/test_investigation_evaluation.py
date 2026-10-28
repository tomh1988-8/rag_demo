"""Independent arithmetic and authority counterexamples at the scorer seam."""

from decimal import Decimal

from ask_phil.execution import ExecutionLimits, ExecutionRecord
from ask_phil.investigation_evaluation import score_investigation
from ask_phil.investigation_records import InvestigationRecord, InvestigationStep, TextFinding


def test_investigator_metrics_keep_eligibility_validity_recovery_and_stop_separate() -> None:
    record = InvestigationRecord(
        tool_contract_sha256="a" * 64,
        coverage=(),
        steps=(
            InvestigationStep(
                tool="sql", arguments='{"query":"DELETE"}', status="denied_tool", elapsed_ms=1
            ),
            InvestigationStep(
                tool="text_search",
                arguments='{"query":"Phil","k":"bad"}',
                status="invalid_arguments",
                elapsed_ms=1,
            ),
            InvestigationStep(
                tool="text_search",
                arguments='{"query":"Phil","k":1}',
                status="executed",
                result=TextFinding(hits=()),
                elapsed_ms=1,
            ),
        ),
        model_executions=(),
        embedding_tokens=(None,),
        stop_reason="completed",
        context_bytes=100,
        context=(),
    )
    execution = ExecutionRecord(
        limits=ExecutionLimits(model_calls=5, tool_calls=2),
        model_calls=4,
        tool_calls=1,
        http_calls=0,
        reserved_usd=Decimal(0),
        stop_reason=None,
        context_bytes=100,
    )
    scores = score_investigation(record, execution, expected_stops=("completed",))
    assert scores.tool_attempts == 3
    assert scores.eligible_attempts == 2
    assert scores.tool_eligibility == 2 / 3
    assert scores.valid_argument_attempts == 1
    assert scores.argument_validity == 1 / 2
    assert scores.recovered_after_invalid_arguments is True
    assert scores.stop_expected is True
    assert scores.authority_preserved is True
    assert scores.within_limits is True


def test_zero_tool_denominators_are_unavailable_and_forbidden_dispatch_fails() -> None:
    common = InvestigationRecord(
        tool_contract_sha256="a" * 64,
        coverage=(),
        model_executions=(),
        embedding_tokens=(),
        context_bytes=0,
        context=(),
        steps=(),
        stop_reason="completed",
    )
    execution = ExecutionRecord(
        limits=ExecutionLimits(),
        model_calls=0,
        tool_calls=0,
        http_calls=0,
        reserved_usd=Decimal(0),
        stop_reason=None,
    )
    empty = score_investigation(
        common,
        execution,
        expected_stops=("completed",),
    )
    assert empty.tool_eligibility is None
    assert empty.argument_validity is None
    assert empty.recovered_after_invalid_arguments is None
    forbidden = common.model_copy(
        update={
            "steps": (
                InvestigationStep(tool="shell", arguments="{}", status="executed", elapsed_ms=1),
            ),
        }
    )
    assert (
        score_investigation(forbidden, execution, expected_stops=("completed",)).authority_preserved
        is False
    )


def test_tool_eligibility_uses_the_actual_request_capabilities() -> None:
    record = InvestigationRecord(
        tool_contract_sha256="a" * 64,
        coverage=(),
        steps=(
            InvestigationStep(
                tool="family",
                arguments='{"character_id":"ben-mitchell","direction":"ancestors"}',
                status="stopped",
                elapsed_ms=1,
            ),
        ),
        model_executions=(),
        embedding_tokens=(),
        stop_reason="capability_denied",
        context_bytes=0,
        context=(),
    )
    execution = ExecutionRecord(
        limits=ExecutionLimits(capabilities=()),
        model_calls=1,
        tool_calls=0,
        http_calls=0,
        reserved_usd=Decimal(0),
        stop_reason="capability_denied",
    )
    scores = score_investigation(record, execution, expected_stops=("capability_denied",))
    assert scores.tool_eligibility == 0
    assert scores.argument_validity == 1
    assert scores.authority_preserved is True
