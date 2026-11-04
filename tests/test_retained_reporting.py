"""Retained report consistency through real storage and the evaluation interface."""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from test_answers_api import models as models
from test_feedback_api import feedback_client as feedback_client
from test_feedback_api import feedback_clock as feedback_clock

from ask_phil.answers import AnswerRecord
from ask_phil.feedback import FeedbackInput, FeedbackStore
from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.online_evaluation import OnlinePolicy
from ask_phil.online_workflow import OnlineEvaluation
from ask_phil.responses import ResponseLedger

pytestmark = pytest.mark.integration


def test_report_keeps_one_retained_cohort_when_feedback_expires_during_its_read(
    feedback_client: TestClient,
    feedback_clock: list[datetime],
    database_url: str,
    tmp_path: Path,
) -> None:
    receipt = feedback_client.post(
        "/v1/answers", json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"}
    ).json()
    response_id = receipt["response"]["response_id"]
    feedback_client.post(
        f"/v1/responses/{response_id}/feedback",
        headers={"Authorization": "Bearer " + receipt["read_token"]},
        json={"submission_id": str(uuid4()), "policy_version": "feedback-v1", "rating": "helpful"},
    ).raise_for_status()
    evaluation = OnlineEvaluation(
        database_url,
        f"sqlite:///{tmp_path}/feedback.db",
        policy=OnlinePolicy(background_rate=0, feedback_rate=0),
        clock=lambda: feedback_clock[0],
    )
    evaluation.process()
    now = feedback_clock[0]
    cohort = FeedbackCohort(
        served_from=now - timedelta(hours=1),
        served_until=now + timedelta(hours=1),
        feedback_as_of=now,
    )
    before = evaluation.report(cohort)
    assert (before.feedback.counts.eligible, before.triaged_revisions) == (1, 1)

    # A real database lock pauses report reads while another transaction expires
    # the interaction. Inspection below is only fault coordination; all behavior
    # assertions use the report interface.
    with (
        psycopg.connect(database_url) as lock,
        psycopg.connect(database_url, autocommit=True) as concurrent,
        ThreadPoolExecutor(max_workers=1) as workers,
    ):
        lock.execute("LOCK TABLE online_triage IN ACCESS EXCLUSIVE MODE")
        future = workers.submit(evaluation.report, cohort)
        try:
            deadline = time.monotonic() + 2
            waiting = False
            while time.monotonic() < deadline:
                row = concurrent.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_locks l JOIN pg_stat_activity a "
                    "ON a.pid=l.pid WHERE l.relation='online_triage'::regclass "
                    "AND NOT l.granted AND a.query LIKE 'SELECT%')"
                ).fetchone()
                if row and row[0]:
                    waiting = True
                    break
                time.sleep(0.01)
            assert waiting, "The report did not reach the controlled concurrent read."
            concurrent.execute(
                "UPDATE feedback_interactions SET expires_at=%s WHERE response_id=%s",
                (now - timedelta(seconds=1), response_id),
            )
        finally:
            lock.rollback()
        report = future.result(timeout=10)

    assert (report.feedback.counts.eligible, report.triaged_revisions) == (1, 1)
    assert report.feedback.counts.rated == 1
    assert len(report.feedback.review_priorities) == 1
    after = evaluation.report(cohort)
    assert (after.feedback.counts.eligible, after.triaged_revisions) == (0, 0)


def test_large_report_keeps_all_review_items_and_the_full_retained_denominators(
    feedback_client: TestClient,
    feedback_clock: list[datetime],
    database_url: str,
    tmp_path: Path,
) -> None:
    original = feedback_client.post(
        "/v1/answers", json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"}
    ).json()
    template = AnswerRecord.model_validate(original["response"])
    uri = f"sqlite:///{tmp_path}/feedback.db"
    store = FeedbackStore(database_url, tracking_uri=uri, clock=lambda: feedback_clock[0])
    ledger = ResponseLedger(database_url)
    # Replayed deliveries share a generation; they are interactions, not new
    # independent factual examples. No fresh model execution is needed.
    receipts = [(template.response_id, original["read_token"])]
    for _ in range(100):
        response = template.model_copy(update={"response_id": uuid4()})
        receipt = ledger.save(response)
        store.record_delivery(response)
        receipts.append((response.response_id, receipt.read_token))
    for index, (response_id, token) in enumerate(receipts):
        store.accept(
            response_id,
            token,
            FeedbackInput(
                submission_id=uuid4(),
                policy_version="feedback-v1",
                rating="not_helpful" if index == 100 else "helpful",
                categories=("facts",) if index == 100 else (),
            ),
        )
    foreign = template.model_copy(update={"response_id": uuid4()})
    ledger.save(foreign)
    FeedbackStore(
        database_url,
        tracking_uri="sqlite:///other-backend.db",
        clock=lambda: feedback_clock[0],
    ).record_delivery(foreign)
    now = feedback_clock[0]
    cohort = FeedbackCohort(
        served_from=now - timedelta(hours=1),
        served_until=now + timedelta(hours=1),
        feedback_as_of=now,
    )
    page = store.report(cohort, offset=100)
    assert (page.counts.eligible, page.counts.rated, page.counts.positive) == (102, 101, 100)
    assert page.total_review_items == 101
    assert len(page.review_priorities) == 1
    assert page.next_offset is None
    evaluation = OnlineEvaluation(
        database_url,
        uri,
        policy=OnlinePolicy(background_rate=0, feedback_rate=0),
        clock=lambda: feedback_clock[0],
    )
    report = evaluation.report(cohort)
    assert report.feedback.counts == page.counts
    assert len(report.feedback.review_priorities) == 101
    assert {p.response_id for p in report.feedback.review_priorities} == {
        response_id for response_id, _ in receipts
    }
    assert report.feedback.next_offset is None
    assert report.online_eligible == 101
    assert report.states == {"undiscovered": 101, "ineligible_backend": 1}
    assert (report.pending_triage_revisions, report.triaged_revisions) == (101, 0)
    assert report.sample_coverage == 0
    assert report.score_coverage is None


@pytest.mark.parametrize("discovered", [False, True])
def test_report_preserves_unknown_serving_expense_in_an_incomplete_retained_receipt(
    feedback_client: TestClient,
    feedback_clock: list[datetime],
    database_url: str,
    tmp_path: Path,
    discovered: bool,
) -> None:
    receipt = feedback_client.post(
        "/v1/answers", json={"snapshot_id": "phil-arrival-v1", "question": "When did Phil arrive?"}
    ).json()
    # An incomplete legacy receipt is a storage input, not evidence of a free
    # model call. The report must preserve the missing measurement.
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "UPDATE answer_responses SET document=document-'estimated_api_cost_usd' "
            "WHERE response_id=%s",
            (receipt["response"]["response_id"],),
        )
    evaluation = OnlineEvaluation(
        database_url,
        f"sqlite:///{tmp_path}/feedback.db",
        policy=OnlinePolicy(background_rate=0, feedback_rate=0),
        clock=lambda: feedback_clock[0],
    )
    if discovered:
        evaluation.process()
    now = feedback_clock[0]
    report = evaluation.report(
        FeedbackCohort(
            served_from=now - timedelta(hours=1),
            served_until=now + timedelta(hours=1),
            feedback_as_of=now,
        )
    )
    assert report.feedback.counts.eligible == 1
    assert report.serving_cost_usd is None
    assert len(report.jobs) == int(discovered)
