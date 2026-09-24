"""Exercise the evaluation CLI's public lineage guard without calling a model."""

import json
import subprocess
import sys
from pathlib import Path


def test_evaluation_cli_rejects_a_review_of_a_different_response(tmp_path: Path) -> None:
    capture = tmp_path / "capture.json"
    reviews = tmp_path / "reviews.json"
    output = tmp_path / "scores.json"
    capture.write_text(
        json.dumps(
            {
                "state": "complete",
                "cases": [
                    {
                        "reference": {"case_id": "changed", "required_facts": ["A fact"]},
                        "response": {"answer": "A changed answer"},
                    }
                ],
            }
        )
    )
    reviews.write_text(
        json.dumps(
            {
                "reviews": [
                    {
                        "case_id": "changed",
                        "response_sha256": "a" * 64,
                        "reference_sha256": "b" * 64,
                        "reviewer": "Synthetic stale review",
                        "rationale": "Labels belong to a different output.",
                        "claims": [],
                        "required_facts": [{"fact": "A fact", "covered": True}],
                        "answerability": True,
                    }
                ]
            }
        )
    )
    result = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_answer_policy.py",
            "score",
            "--capture",
            str(capture),
            "--reviews",
            str(reviews),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "Stale review" in result.stderr
    assert not output.exists()
