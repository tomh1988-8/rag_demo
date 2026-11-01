"""Source-checked report review and regression promotion at the evaluation seam."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from test_answers_api import models as models
from test_feedback_api import feedback_client as feedback_client
from test_feedback_api import feedback_clock as feedback_clock

from ask_phil.evaluation import document_fingerprint
from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.online_evaluation import OnlinePolicy
from ask_phil.online_workflow import OnlineEvaluation


@pytest.mark.parametrize(
    "models",
    [
        {
            "draft": {
                "answer": "I arrived in February 1991.",
                "evidence_ids": ["phil-arrival-001"],
            }
        }
    ],
    indirect=True,
)
@pytest.mark.parametrize("contamination", ["none", "group", "question", "evidence", "derivative"])
def test_checked_live_failure_is_promoted_with_evidence_lineage_and_split_controls(
    feedback_client: TestClient,
    database_url: str,
    tmp_path: Path,
    contamination: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ask_phil.online_review import OnlineReview, RegressionPromotion, ReportReview

    receipt = feedback_client.post(
        "/v1/answers",
        json={
            "snapshot_id": "phil-arrival-v1",
            "question": "When did Phil first arrive in Walford?",
        },
    ).json()
    response = receipt["response"]
    response_id = UUID(response["response_id"])
    feedback_client.post(
        f"/v1/responses/{response_id}/feedback",
        headers={"Authorization": "Bearer " + receipt["read_token"]},
        json={
            "submission_id": str(uuid4()),
            "policy_version": "feedback-v1",
            "rating": "not_helpful",
            "categories": ["facts"],
            "comment": "The year does not match the source.",
        },
    ).raise_for_status()
    evaluation = OnlineEvaluation(
        database_url, f"sqlite:///{tmp_path}/feedback.db", policy=OnlinePolicy(background_rate=0)
    )
    evaluation.process()
    now = datetime.now(UTC)
    report = evaluation.report(
        FeedbackCohort(
            served_from=now - timedelta(hours=1),
            served_until=now + timedelta(hours=1),
            feedback_as_of=now,
        )
    )
    review = OnlineReview(database_url)
    checked = review.record(
        ReportReview.model_validate(
            dict(
                report_id=report.report_id,
                reviewer="source-review-test",
                note="Controlled external-model failure; checked against the captured source.",
                dispositions=(
                    {
                        "response_id": response_id,
                        "feedback_revision": 1,
                        "disposition": "confirmed",
                        "note": "Source states February 1990, not 1991.",
                        "response_sha256": document_fingerprint(response),
                    },
                ),
            )
        )
    )
    passage = response["context"][0]
    promotion = RegressionPromotion.model_validate(
        dict(
            review_id=checked.review_id,
            response_id=response_id,
            case={
                "case_id": "online-arrival-regression",
                "group_ids": ["phil-arrival"],
                "split": "regression",
                "category": "arrival-year",
                "question": response["question"],
                "snapshot_id": response["snapshot_id"],
                "expected_status": "answered",
                "required_facts": [
                    {
                        "fact": "Phil first arrived in February 1990.",
                        "sufficient_sets": [["phil-arrival-001"]],
                    }
                ],
                "allowed_alternatives": [],
                "forbidden_assertions": ["Phil arrived in 1991."],
                "evidence": [
                    {
                        "evidence_id": passage["evidence_id"],
                        "text": passage["text"],
                        "source_revision": response["source"]["revision_id"],
                        "sha256": hashlib.sha256(passage["text"].encode()).hexdigest(),
                    }
                ],
                "review_note": "Independent expected date from the original source passage.",
                "synthetic_provenance": "Controlled model output and scripted demo feedback.",
            },
            source_checks=(
                {
                    "fact": "Phil first arrived in February 1990.",
                    "evidence_ids": ("phil-arrival-001",),
                    "note": "Read the passage and independently established the expected year.",
                },
            ),
        )
    )
    output = tmp_path / "regression-v1.json"
    if contamination != "none":
        registry = tmp_path / "data" / "references"
        registry.mkdir(parents=True)
        held_out: dict[str, object] = {"split": "held_out", "case_id": "held-parent"}
        if contamination == "group":
            held_out["group_ids"] = list(promotion.case.group_ids)
        elif contamination == "question":
            held_out["question"] = promotion.case.question
        elif contamination == "evidence":
            held_out["evidence"] = [e.model_dump(mode="json") for e in promotion.case.evidence]
        else:
            promotion = promotion.model_copy(
                update={
                    "case": promotion.case.model_copy(update={"derived_from": ("held-parent",)})
                }
            )
        (registry / "protected.json").write_text(json.dumps({"cases": [held_out]}))
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Held-out"):
            review.promote(promotion, output)
        assert not output.exists()
        return
    result = review.promote(promotion, output)
    assert result.response_sha256 == document_fingerprint(response)
    assert result.generation_id == response_id
    assert json.loads(output.read_bytes())["cases"][0]["split"] == "regression"
    assert result.held_out_labels_exposed is False
    assert (
        json.loads(output.with_suffix(".lineage.json").read_bytes())["original_response"]
        == response
    )
    with pytest.raises(ValueError, match="already|Duplicate"):
        review.promote(promotion, tmp_path / "duplicate.json")
