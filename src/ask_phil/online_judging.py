"""Calibrated, context-only online judge admission and configuration."""

import json
from pathlib import Path

from ask_phil.evaluation import document_fingerprint
from ask_phil.semantic_judge import (
    JudgeObservation,
    SupportDataset,
    SupportJudge,
    calibration_report,
)


def checked_calibration(judge: SupportJudge, path: Path) -> str:
    """Recompute the saved calibration; do not trust an editable enable flag alone."""
    document = json.loads(path.read_bytes())
    references = SupportDataset.model_validate_json(
        Path("data/references/support-judge-v1.json").read_bytes()
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
