"""Known value errors cannot pass merely by retaining a claim ID and a valid locator."""

import json
import runpy
from copy import deepcopy
from pathlib import Path

import pytest

from ask_phil.evidence import SourceSnapshot


@pytest.mark.parametrize("wrong_guilt", [False, True])
def test_coverage_checks_legal_roles_independently_of_ids_and_locators(wrong_guilt: bool) -> None:
    assess = runpy.run_path("scripts/record_coverage.py")["assess"]
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/coverage/core-v1/janine-butcher-source.json").read_bytes()
    )
    claims = json.loads(Path("data/coverage/core-v1/janine-butcher-reference.json").read_bytes())[
        "expected_claims"
    ]
    reference = json.loads(Path("data/references/core-graph-questions-v1.json").read_bytes())
    reference["expected_claims"] = {c["claim_id"]: c for c in claims}
    actual = deepcopy(claims)
    if wrong_guilt:
        actual[1].update(event_type="commission", basis="narrative")
        actual[1]["participants"][0]["role"] = "perpetrator"
    answer = {"graph": {"status": "found", "claims": actual}, "answer": "Janine killed Laura."}
    score = assess(answer, snapshot, json.dumps(reference).encode(), case_id="janine-butcher")
    assert score["component_scores"]["result_correct"] is True
    assert score["component_scores"]["locators_resolve"] is True
    assert score["component_scores"]["values_correct"] is (not wrong_guilt)


def test_coverage_rejects_a_reversed_family_edge_with_the_expected_path() -> None:
    assess = runpy.run_path("scripts/record_coverage.py")["assess"]
    snapshot = SourceSnapshot.model_validate_json(
        Path("data/coverage/core-v1/peggy-mitchell-source.json").read_bytes()
    )
    reference = json.loads(Path("data/references/core-graph-questions-v1.json").read_bytes())
    expected = reference["expected_claims"]["ref-peggy-mitchell-1"]
    answer = {
        "graph": {
            "status": "found",
            "paths": [
                {
                    "characters": ["peggy-mitchell", "phil-mitchell"],
                    "edges": [
                        {
                            "parent_id": "phil-mitchell",
                            "child_id": "peggy-mitchell",
                            "claim_ids": ["ref-peggy-mitchell-1"],
                            "evidence": expected["evidence"],
                        }
                    ],
                }
            ],
        },
        "answer": "A reversed relationship.",
    }
    score = assess(answer, snapshot, json.dumps(reference).encode(), case_id="peggy-mitchell")
    assert score["component_scores"]["result_correct"] is True
    assert score["component_scores"]["values_correct"] is False
