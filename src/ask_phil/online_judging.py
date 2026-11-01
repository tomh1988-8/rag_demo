"""Calibrated, context-only online judge admission and configuration."""

import json
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, StrictBool

from ask_phil.evaluation import document_fingerprint
from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record
from ask_phil.execution import ExecutionRecord
from ask_phil.reference_data import reference_directory
from ask_phil.semantic_judge import (
    SUPPORT_RUBRIC_SHA256,
    JudgeObservation,
    SupportAssessment,
    SupportDataset,
    SupportInput,
    SupportJudge,
    calibration_report,
)


class StoredSupportResult(Record):
    result_key: Fingerprint
    origin_job_id: UUID
    status: Literal["reserved", "disabled", "pending", "completed", "failed", "skipped"]
    assessment: SupportAssessment | None = None
    execution: ExecutionRecord | None = None
    calls: int = 1
    reserved_usd: float
    cost_usd: float | None = None


def checked_calibration(judge: SupportJudge, path: Path) -> str:
    """Recompute the saved calibration; do not trust an editable enable flag alone."""
    document = json.loads(path.read_bytes())
    references = SupportDataset.model_validate_json(
        (reference_directory() / "support-judge-v1.json").read_bytes()
    )
    observations = tuple(
        JudgeObservation.model_validate(c["observation"])
        for c in document["cases"]
        if c["state"] == "complete"
    )
    report = calibration_report(references, observations)
    if (
        document.get("state") != "complete"
        or report != document.get("calibration")
        or report["eligible_to_enable"] is not True
        or report["judge_settings_sha256"]
        != document_fingerprint(judge.chat.profile.model_dump(mode="json"))
    ):
        raise ValueError("Online judge requires matching successful human-reviewed calibration.")
    return document_fingerprint(document)


class ScopedSupportControl(Record):
    case_id: Identifier
    supplied: SupportInput
    snapshot_sha256: Fingerprint
    expected_supported: StrictBool
    review_note: NonEmpty


class ExcludedSupportCase(Record):
    case_id: Identifier
    input_sha256: Fingerprint | None
    disposition: str


class OnlineJudgeScope(Record):
    scope_id: Identifier
    reviewer: NonEmpty
    reviewer_type: str
    human_reviewed: StrictBool
    limitation: NonEmpty
    calibration_sha256: Fingerprint
    judge_settings_sha256: Fingerprint
    rubric_sha256: Fingerprint
    controls: tuple[ScopedSupportControl, ...] = Field(min_length=2)
    exclusions: tuple[ExcludedSupportCase, ...] = Field(min_length=1)

    @property
    def fingerprint(self) -> str:
        return document_fingerprint(self.model_dump(mode="json"))

    def admits(self, supplied: SupportInput, snapshot_sha256: str) -> bool:
        fingerprint = document_fingerprint(supplied.model_dump(mode="json"))
        return any(
            control.snapshot_sha256 == snapshot_sha256
            and document_fingerprint(control.supplied.model_dump(mode="json")) == fingerprint
            for control in self.controls
        )


def checked_scope(
    judge: SupportJudge, calibration_sha256: str, path: Path | None
) -> OnlineJudgeScope:
    scope = OnlineJudgeScope.model_validate_json(
        (path or reference_directory() / "online-support-scope-v1.json").read_bytes()
    )
    if (
        scope.calibration_sha256 != calibration_sha256
        or scope.judge_settings_sha256
        != document_fingerprint(judge.chat.profile.model_dump(mode="json"))
        or scope.rubric_sha256 != SUPPORT_RUBRIC_SHA256
        or {control.expected_supported for control in scope.controls} != {True, False}
        or any(case.disposition != "unresolved_excluded" for case in scope.exclusions)
    ):
        raise ValueError(
            "Online judge scope differs from its reviewed calibration and admission controls."
        )
    return scope
