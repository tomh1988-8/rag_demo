"""Private feedback capabilities and transport shared by one-shot and interactive CLI use."""

import sys
from pathlib import Path
from uuid import UUID, uuid4

import httpx

from ask_phil.answers import AnswerReceipt
from ask_phil.feedback import FeedbackInput, FeedbackPolicy
from ask_phil.sessions import SessionReceipt


def feedback_access(receipt_path: Path, session_path: Path | None) -> tuple[str, str]:
    try:
        receipt = AnswerReceipt.model_validate_json(receipt_path.read_bytes())
        session = (
            SessionReceipt.model_validate_json(session_path.read_bytes()) if session_path else None
        )
    except ValueError:
        raise ValueError("Invalid private feedback receipt.") from None
    return (
        f"/v1/sessions/{session.session.session_id}/responses/{receipt.response.response_id}/feedback"
        if session
        else f"/v1/responses/{receipt.response.response_id}/feedback",
        session.feedback_token if session else receipt.read_token,
    )


def submit_feedback(
    client: httpx.Client,
    path: str,
    token: str,
    submission: FeedbackInput,
) -> httpx.Response:
    policy = client.get("/v1/feedback-policy")
    policy.raise_for_status()
    notice = FeedbackPolicy.model_validate(policy.json())
    print(notice.use_notice, file=sys.stderr)
    print(f"Feedback retention: {notice.retention_days} days.", file=sys.stderr)
    print(f"Feedback submission ID (reuse to retry): {submission.submission_id}", file=sys.stderr)
    return client.post(
        path,
        headers={"Authorization": f"Bearer {token}"},
        json=submission.model_dump(mode="json"),
    )


def feedback_input(
    rating: str,
    categories: list[str],
    comment: str,
    proposed_correction: str,
    submission_id: UUID | None = None,
) -> FeedbackInput:
    try:
        return FeedbackInput.model_validate(
            {
                "submission_id": submission_id or uuid4(),
                "policy_version": "feedback-v1",
                "rating": rating,
                "categories": categories,
                "comment": comment,
                "proposed_correction": proposed_correction,
            }
        )
    except ValueError:
        raise ValueError(
            "Invalid feedback; check the rating, categories and text budget."
        ) from None
