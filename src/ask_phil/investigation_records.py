"""Inspectable observations from the single, bounded investigator."""

from typing import Literal

from pydantic import Field

from ask_phil.classified_facts import ContextClaim
from ask_phil.evidence import Fingerprint, Identifier, Passage, Record
from ask_phil.graph_execution import GraphResult
from ask_phil.models import ModelExecution
from ask_phil.retrieval import RetrievedPassage
from ask_phil.review_notes import ReviewNotice


class CoveragePart(Record):
    part: str = Field(min_length=1, max_length=300)
    evidence_ids: tuple[Identifier, ...] = Field(max_length=3)
    resolved: bool


class TextFinding(Record):
    hits: tuple[RetrievedPassage, ...]
    context_claims: tuple[ContextClaim, ...] = ()
    review_notices: tuple[ReviewNotice, ...] = ()


class InvestigationStep(Record):
    tool: str = Field(max_length=80)
    arguments: str = Field(max_length=2000)
    status: Literal["executed", "invalid_arguments", "denied_tool", "repeated_call", "stopped"]
    result: TextFinding | GraphResult | None = None
    context_ids: tuple[Identifier, ...] = ()
    elapsed_ms: float = Field(ge=0)


class InvestigationRecord(Record):
    version: Literal["bounded-investigator-v1"] = "bounded-investigator-v1"
    tool_contract_version: Literal["captured-read-tools-v1"] = "captured-read-tools-v1"
    tool_contract_sha256: Fingerprint
    coverage: tuple[CoveragePart, ...]
    steps: tuple[InvestigationStep, ...]
    model_executions: tuple[ModelExecution, ...]
    embedding_tokens: tuple[int | None, ...]
    stop_reason: str
    context_bytes: int = Field(ge=0)
    context: tuple[Passage, ...]
