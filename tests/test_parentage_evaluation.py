import json
from pathlib import Path

from ask_phil.evidence import SourceSnapshot
from ask_phil.parentage import ExtractedClaims
from ask_phil.parentage_evaluation import score_extraction


def test_schema_value_direction_and_evidence_support_are_measured_separately() -> None:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    reference = json.loads(Path("data/references/parentage-v1.json").read_text())
    expected = ExtractedClaims.model_validate({"claims": reference["expected_claims"]})
    wrong_direction = {
        **reference["expected_claims"][0],
        "parent_id": "ben-mitchell",
        "child_id": "phil-mitchell",
    }
    score = score_extraction(json.dumps({"claims": [wrong_direction]}), expected, snapshot)
    assert score.schema_valid
    assert score.predicted == 1
    assert score.true_positive == 0
    assert score.resolvable_spans == 1
    assert score.grounded == 0
    assert score.precision == 0
    assert score.recall == 0
    assert score.f1 == 0


def test_unreviewed_partial_quotes_do_not_gain_grounding_from_correct_values() -> None:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    reference = json.loads(Path("data/references/parentage-v1.json").read_text())
    expected = ExtractedClaims.model_validate({"claims": reference["expected_claims"]})
    value = {
        **reference["expected_claims"][0],
        "evidence": [{"evidence_id": "family-ben-birth", "start": 0, "end": 3, "quote": "Ben"}],
    }
    score = score_extraction(json.dumps({"claims": [value]}), expected, snapshot)
    assert score.true_positive == 1
    assert score.resolvable_spans == 1
    assert score.grounded == 0


def test_malformed_schema_has_no_fabricated_value_scores() -> None:
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/seed/family-pilot-v1.json").read_text()
    )
    expected = ExtractedClaims(claims=())
    score = score_extraction('{"claims":[{"parent":"Phil"}]}', expected, snapshot)
    assert not score.schema_valid
    assert score.precision is None
    assert score.recall is None
