"""Orchestration diagnostics independent of strategy order and final semantic review."""

from pydantic import Field

from ask_phil.evidence import Record
from ask_phil.execution import ExecutionRecord
from ask_phil.investigation_records import InvestigationRecord
from ask_phil.investigation_tools import TOOL_ARGUMENTS, TOOL_CAPABILITIES, TextSearch


class InvestigationScores(Record):
    tool_attempts: int = Field(ge=0)
    eligible_attempts: int = Field(ge=0)
    declared_attempts: int = Field(ge=0)
    tool_eligibility: float | None
    valid_argument_attempts: int = Field(ge=0)
    argument_validity: float | None
    returned_results: int = Field(ge=0)
    ineligible_results: int = Field(ge=0)
    recovered_after_invalid_arguments: bool | None
    authority_preserved: bool
    stop_expected: bool
    within_limits: bool
    limitation: str = (
        "Tool diagnostics do not grade an exact call sequence or establish final factual "
        "support. Task completion, multi-fact context sufficiency and final semantic "
        "support require the separately frozen references and source review."
        " Limits here cover recorded calls, HTTP, context and spending; network deadline "
        "and cancellation behavior have separate integration evidence."
    )


def score_investigation(
    record: InvestigationRecord,
    execution: ExecutionRecord,
    *,
    expected_stops: tuple[str, ...],
) -> InvestigationScores:
    declared = eligible = valid = returned = ineligible = 0
    invalid_seen = recovered = False
    authority = True
    for step in record.steps:
        schema = TOOL_ARGUMENTS.get(step.tool)
        arguments_valid = False
        policy_eligible = TOOL_CAPABILITIES.get(step.tool) in execution.limits.capabilities
        if schema is not None:
            declared += 1
            eligible += policy_eligible
            try:
                query = schema.model_validate_json(step.arguments, strict=True)
                arguments_valid = (
                    not isinstance(query, TextSearch) or len(query.query.encode()) <= 1000
                )
            except ValueError:
                pass
            valid += arguments_valid
        completed_dispatch = step.status == "executed" or step.result is not None
        authority &= not completed_dispatch or (
            schema is not None and arguments_valid and policy_eligible
        )
        if step.status == "invalid_arguments":
            invalid_seen = True
        if step.result is not None:
            returned += 1
            ineligible += getattr(step.result, "status", None) == "ineligible"
            recovered |= invalid_seen and arguments_valid
    limits = execution.limits
    return InvestigationScores(
        tool_attempts=len(record.steps),
        eligible_attempts=eligible,
        declared_attempts=declared,
        tool_eligibility=eligible / len(record.steps) if record.steps else None,
        valid_argument_attempts=valid,
        argument_validity=valid / declared if declared else None,
        returned_results=returned,
        ineligible_results=ineligible,
        recovered_after_invalid_arguments=recovered if invalid_seen else None,
        authority_preserved=authority,
        stop_expected=record.stop_reason in expected_stops,
        within_limits=(
            execution.model_calls <= limits.model_calls
            and execution.tool_calls <= limits.tool_calls
            and execution.http_calls <= limits.http_calls
            and execution.reserved_usd <= limits.spend_usd
            and (execution.context_bytes or 0) <= limits.context_bytes
        ),
    )
