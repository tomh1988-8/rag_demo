import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ask_phil.evidence import SourceSnapshot


def test_changed_passage_cannot_keep_the_original_evidence_fingerprint() -> None:
    fixture = json.loads(Path("data/seed/phil-arrival-v1.json").read_text())
    fixture["passages"][0]["text"] = "A changed source passage."

    with pytest.raises(ValidationError, match="passage fingerprint"):
        SourceSnapshot.model_validate(fixture)


@pytest.mark.parametrize(
    "field,value",
    [
        ("captured_at", "2026-09-23T14:18:05"),
        ("scope", "spin_off"),
        ("support_status", "cross_checked"),
    ],
)
def test_seed_cannot_claim_unrecorded_provenance(field: str, value: str) -> None:
    fixture = json.loads(Path("data/seed/phil-arrival-v1.json").read_text())
    fixture["source"][field] = value
    with pytest.raises(ValidationError):
        SourceSnapshot.model_validate(fixture)


def test_citation_span_cannot_extend_beyond_retained_text() -> None:
    fixture = json.loads(Path("data/seed/phil-arrival-v1.json").read_text())
    fixture["passages"][0]["end"] = 999
    with pytest.raises(ValidationError, match="span"):
        SourceSnapshot.model_validate(fixture)
