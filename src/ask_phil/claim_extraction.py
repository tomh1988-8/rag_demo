"""One retained Claim extraction outcome, including raw evidence and failed tracing."""

import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import mlflow
from mlflow import MlflowClient
from mlflow.entities import MlflowExperimentLocation
from pydantic import BaseModel, TypeAdapter

from ask_phil.answering import application_fingerprint
from ask_phil.event_evaluation import score_events
from ask_phil.event_extraction import EVENT_PROMPT, IncidentScope, extract_events
from ask_phil.evidence import Record, SourceSnapshot
from ask_phil.execution import ExecutionBudget, ExecutionLimits
from ask_phil.identity import IdentityCatalogue
from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile
from ask_phil.parentage import ClaimBatch, ExtractedClaims
from ask_phil.parentage_evaluation import score_extraction
from ask_phil.parentage_extraction import EXTRACTION_PROMPT, ClaimLLM, extract_parentage
from ask_phil.relationship_evaluation import score_relationships
from ask_phil.relationship_extraction import RELATIONSHIP_PROMPT, extract_relationships
from ask_phil.relationships import ExtractedRelationships, RelationshipBatch
from ask_phil.story_events import EventBatch, EventExtractionOutput, ExtractedEvents
from ask_phil.tracing import experiment_for


class ExtractionInputMismatch(ValueError):
    """Frozen source and reference identities do not match; no model work is allowed."""


@dataclass(frozen=True)
class _ExtractionSlice:
    name: str
    output_cls: type[BaseModel]
    prompt: str
    extract: Callable[
        [SourceSnapshot, IdentityCatalogue, ClaimLLM],
        tuple[ClaimBatch | RelationshipBatch | EventBatch, float],
    ]
    score: Callable[[str], Record]


def _slice(
    relationships: bool,
    snapshot: SourceSnapshot,
    reference: dict[str, Any],
    *,
    events: bool = False,
) -> _ExtractionSlice:
    if relationships and events:
        raise ValueError("Choose one extraction slice.")
    if events:
        expected_events = ExtractedEvents.model_validate(
            {
                "claims": reference["expected_claims"],
                "context_claims": reference.get("expected_context_claims", []),
            }
        )
        incidents = TypeAdapter(dict[str, IncidentScope]).validate_python(reference["incidents"])
        if set(incidents) != {p.evidence_id for p in snapshot.passages}:
            raise ExtractionInputMismatch("Incident scope must identify each captured passage.")
        return _ExtractionSlice(
            "story_event_extraction",
            EventExtractionOutput,
            EVENT_PROMPT,
            lambda s, c, llm: extract_events(s, c, llm, incidents),
            lambda raw: score_events(raw, expected_events, snapshot),
        )
    if relationships:
        expected_relationships = ExtractedRelationships.model_validate(
            {"claims": reference["expected_claims"]}
        )
        return _ExtractionSlice(
            "relationship_extraction",
            ExtractedRelationships,
            RELATIONSHIP_PROMPT,
            extract_relationships,
            lambda raw: score_relationships(
                raw, expected_relationships, snapshot, reference.get("alternatives")
            ),
        )
    expected_parentage = ExtractedClaims.model_validate({"claims": reference["expected_claims"]})
    return _ExtractionSlice(
        "parentage_extraction",
        ExtractedClaims,
        EXTRACTION_PROMPT,
        extract_parentage,
        lambda raw: score_extraction(raw, expected_parentage, snapshot),
    )


@dataclass(frozen=True)
class _FrozenInputs:
    snapshot_bytes: bytes
    reference_bytes: bytes
    snapshot: SourceSnapshot
    catalogue: IdentityCatalogue
    selected: _ExtractionSlice


def _load_inputs(
    snapshot_path: Path, reference_path: Path, relationships: bool, *, events: bool = False
) -> _FrozenInputs:
    snapshot_bytes = snapshot_path.read_bytes()
    reference_bytes = reference_path.read_bytes()
    snapshot = SourceSnapshot.model_validate_json(snapshot_bytes)
    reference = json.loads(reference_bytes)
    if reference["snapshot_sha256"] != snapshot.fingerprint:
        raise ExtractionInputMismatch("The frozen reference and source snapshot differ.")
    return _FrozenInputs(
        snapshot_bytes,
        reference_bytes,
        snapshot,
        IdentityCatalogue.model_validate(reference["catalogue"]),
        _slice(relationships, snapshot, reference, events=events),
    )


def validate_extraction_inputs(
    snapshot_path: Path, reference_path: Path, *, relationships: bool = False, events: bool = False
) -> None:
    """Allow command usage errors before credentials/setup; run always validates afresh."""
    _load_inputs(snapshot_path, reference_path, relationships, events=events)


class ClaimExtractionRun:
    def __init__(
        self,
        profile: OpenRouterProfile,
        key: str,
        client: httpx.Client,
        *,
        budget: Budget,
        tracking: MlflowClient,
    ) -> None:
        self._profile = profile
        self._key = key
        self._client = client
        self._budget = budget
        self._tracking = tracking

    def run(
        self,
        snapshot_path: Path,
        reference_path: Path,
        output: Path,
        *,
        relationships: bool = False,
        events: bool = False,
    ) -> dict[str, Any]:
        frozen = _load_inputs(snapshot_path, reference_path, relationships, events=events)
        snapshot, catalogue, selected = frozen.snapshot, frozen.catalogue, frozen.selected
        chat = OpenRouterChat(self._profile, self._key, self._budget, self._client)
        llm = ClaimLLM(chat, selected.output_cls)
        execution = ExecutionBudget(
            ExecutionLimits(model_calls=1, tool_calls=0, capabilities=(), http_calls=3)
        )
        record: dict[str, Any] = {
            "captured_at": datetime.now(UTC).isoformat(),
            "code_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "application_sha256": application_fingerprint(),
            "prompt_sha256": hashlib.sha256(selected.prompt.encode()).hexdigest(),
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "snapshot_file_sha256": hashlib.sha256(frozen.snapshot_bytes).hexdigest(),
            "reference_sha256": hashlib.sha256(frozen.reference_bytes).hexdigest(),
            "schema_sha256": hashlib.sha256(
                json.dumps(selected.output_cls.model_json_schema(), sort_keys=True).encode()
            ).hexdigest(),
            "profile": self._profile.model_dump(mode="json"),
            "expenditure_category": "offline_evaluation",
            "state": "running",
            "raw": None,
            "batch": None,
            "score": None,
            "usage": None,
            "execution": execution.record().model_dump(mode="json"),
            "elapsed_ms": None,
            "failure": None,
            "trace_id": None,
            "shared_ledger_usd": None,
            "unsettled_reservations": None,
            "limitation": "Agent-reviewed exposed labels; no held-out, human "
            "or independent canon acceptance.",
        }
        _save(output, record, initial=True)
        started = time.perf_counter()
        stage = "tracking"
        try:
            mlflow.set_tracking_uri(self._tracking.tracking_uri)
            experiment_id = experiment_for(self._tracking, "offline_evaluation")
            with (
                execution.activate(),
                mlflow.start_span(
                    selected.name, trace_destination=MlflowExperimentLocation(experiment_id)
                ) as span,
            ):
                record["trace_id"] = span.trace_id
                span.set_inputs(
                    {
                        "snapshot_sha256": snapshot.fingerprint,
                        "catalogue": catalogue.model_dump(mode="json"),
                        "passages": [p.model_dump(mode="json") for p in snapshot.passages],
                    }
                )
                _save(output, record)
                stage = "extraction"
                try:
                    batch, elapsed_ms = selected.extract(snapshot, catalogue, llm)
                    record.update(batch=batch.model_dump(mode="json"), elapsed_ms=elapsed_ms)
                except (ValueError, RuntimeError) as exc:
                    record.update(failure="extraction_failed", failure_type=type(exc).__name__)
                    span.set_status("ERROR")
                finally:
                    self._account(record, llm, chat, execution, started)
                record["score"] = selected.score(llm.raw or "").model_dump(mode="json")
                record["state"] = "failed" if record["failure"] else "complete"
                # Retain model evidence before any trace readback can fail.
                _save(output, record)
                stage = "tracking"
                span.set_outputs(record)
            if self._tracking.get_trace(record["trace_id"], flush=True) is None:
                raise RuntimeError("The extraction trace is unavailable.")
        except BaseException as exc:
            self._account(record, llm, chat, execution, started)
            if stage == "tracking":
                record["tracking_failure_type"] = type(exc).__name__
            record["failure"] = record["failure"] or f"{stage}_failed"
            record["state"] = "failed"
            _save(output, record)
            if not isinstance(exc, Exception):
                raise
        return record

    def _account(
        self,
        record: dict[str, Any],
        llm: ClaimLLM,
        chat: OpenRouterChat,
        execution: ExecutionBudget,
        started: float,
    ) -> None:
        record.update(
            raw=llm.raw,
            usage=chat.last_call.model_dump(mode="json") if chat.last_call else None,
            execution=execution.record().model_dump(mode="json"),
        )
        if record["elapsed_ms"] is None:
            record["elapsed_ms"] = (time.perf_counter() - started) * 1000
        try:
            spent, unsettled = self._budget.summary()
            record.update(shared_ledger_usd=spent, unsettled_reservations=unsettled)
        except Exception as exc:
            record.update(
                shared_ledger_usd=None,
                unsettled_reservations=None,
                accounting_failure_type=type(exc).__name__,
            )
            record["failure"] = record["failure"] or "accounting_failed"


def _save(output: Path, record: dict[str, Any], *, initial: bool = False) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    contents = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if initial:
        with output.open("x", encoding="utf-8") as destination:
            destination.write(contents)
            destination.flush()
            os.fsync(destination.fileno())
        return
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output.parent, delete=False
    ) as f:
        temporary = Path(f.name)
        try:
            f.write(contents)
            f.flush()
            os.fsync(f.fileno())
            os.replace(temporary, output)
        finally:
            temporary.unlink(missing_ok=True)
