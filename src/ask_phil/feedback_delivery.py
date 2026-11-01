"""Bounded, restartable delivery of human feedback to the original local MLflow trace."""

import hashlib
import json
import time
from datetime import timedelta
from threading import Event
from typing import Any
from uuid import UUID

from mlflow.entities import AssessmentSource, AssessmentSourceType, Feedback
from psycopg.rows import class_row

from ask_phil.assessment_publication import AssessmentPublication, delete_assessment
from ask_phil.evidence import Record
from ask_phil.feedback import FeedbackInput, FeedbackStore


class DeliveryResult(Record):
    delivered: int = 0
    pending: int = 0
    deleted: int = 0
    cleanup_pending: int = 0
    purged_interactions: int = 0


class PendingDelivery(Record):
    response_id: UUID
    revision: int
    submission: FeedbackInput
    assessment_id: str
    feedback_id: UUID
    tracking_sha256: str


def deliver_feedback(store: FeedbackStore, tracking_uri: str) -> DeliveryResult:
    """Process a finite batch. Durable acceptance does not call this function."""
    store.ensure_schema()
    now = store.clock()
    target_sha256 = hashlib.sha256(tracking_uri.encode()).hexdigest()
    with store.connect() as conn:
        expired = conn.execute(
            "SELECT 1 FROM feedback_interactions WHERE expires_at <= %s LIMIT 1", (now,)
        ).fetchone()
        purged = 0
        if expired:
            conn.execute(
                "INSERT INTO feedback_cleanup (trace_id, assessment_id, tracking_sha256) "
                "SELECT a.document->>'trace_id', r.assessment_id, i.tracking_sha256 "
                "FROM feedback_revisions r "
                "JOIN feedback_interactions i USING (response_id) "
                "JOIN answer_responses a USING (response_id) WHERE i.expires_at <= %s "
                "ON CONFLICT DO NOTHING",
                (now,),
            )
            purged = conn.execute(
                "DELETE FROM feedback_interactions WHERE expires_at <= %s", (now,)
            ).rowcount
        conn.execute(
            "UPDATE feedback_cleanup SET last_failure = 'FeedbackTargetMismatch' "
            "WHERE tracking_sha256 <> %s "
            "AND last_failure IS DISTINCT FROM 'FeedbackTargetMismatch'",
            (target_sha256,),
        )
        conn.execute(
            "UPDATE feedback_revisions r SET last_failure = 'FeedbackTargetMismatch' "
            "FROM feedback_interactions i WHERE r.response_id = i.response_id "
            "AND r.delivery_state = 'pending' AND i.tracking_sha256 <> %s "
            "AND r.last_failure IS DISTINCT FROM 'FeedbackTargetMismatch'",
            (target_sha256,),
        )
    delivered = deleted = 0
    deadline = time.monotonic() + 10
    for _ in range(store.policy.delivery_batch_size):
        if time.monotonic() >= deadline:
            break
        with store.connect() as conn:
            cleanup = conn.execute(
                "SELECT trace_id, assessment_id, tracking_sha256 FROM feedback_cleanup "
                "WHERE tracking_sha256 = %s "
                "ORDER BY assessment_id FOR UPDATE SKIP LOCKED LIMIT 1",
                (target_sha256,),
            ).fetchone()
            if cleanup:
                try:
                    delete_assessment(tracking_uri, cleanup[0], cleanup[1])
                    conn.execute(
                        "DELETE FROM feedback_cleanup WHERE assessment_id = %s", (cleanup[1],)
                    )
                    deleted += 1
                except Exception as exc:
                    conn.execute(
                        "UPDATE feedback_cleanup SET attempts = attempts + 1, last_failure = %s "
                        "WHERE assessment_id = %s",
                        (type(exc).__name__, cleanup[1]),
                    )
                    # Do not immediately hammer a failed deletion twenty times.
                    break
                continue
            if not store.policy.enabled:
                break
            with conn.cursor(row_factory=class_row(PendingDelivery)) as cursor:
                pending = cursor.execute(
                    "SELECT r.response_id, r.revision, r.submission, r.assessment_id, "
                    "i.feedback_id, i.tracking_sha256 "
                    "FROM feedback_revisions r JOIN feedback_interactions i USING (response_id) "
                    "WHERE r.delivery_state = 'pending' AND r.next_attempt_at <= %s "
                    "AND i.expires_at > %s AND i.tracking_sha256 = %s "
                    "AND NOT EXISTS (SELECT 1 FROM feedback_revisions prior "
                    "WHERE prior.response_id = r.response_id AND prior.revision < r.revision "
                    "AND prior.delivery_state <> 'delivered') "
                    "ORDER BY r.accepted_at, r.response_id, r.revision "
                    "FOR UPDATE OF r SKIP LOCKED LIMIT 1",
                    (now, now, target_sha256),
                ).fetchone()
            if pending is None:
                break
            try:
                original = conn.execute(
                    "SELECT document FROM answer_responses WHERE response_id = %s",
                    (pending.response_id,),
                ).fetchone()
                if original is None:
                    raise ValueError("Original response unavailable.")
                previous = conn.execute(
                    "SELECT assessment_id FROM feedback_revisions "
                    "WHERE response_id = %s AND revision = %s",
                    (pending.response_id, pending.revision - 1),
                ).fetchone()
                _deliver(
                    tracking_uri,
                    original[0],
                    pending,
                    previous[0] if previous else None,
                )
                conn.execute(
                    "UPDATE feedback_revisions SET delivery_state = 'delivered', "
                    "attempts = attempts + 1, last_failure = NULL "
                    "WHERE response_id = %s AND revision = %s",
                    (pending.response_id, pending.revision),
                )
                delivered += 1
            except Exception as exc:
                conn.execute(
                    "UPDATE feedback_revisions SET attempts = attempts + 1, last_failure = %s, "
                    "next_attempt_at = %s WHERE response_id = %s AND revision = %s",
                    (
                        type(exc).__name__,
                        now + timedelta(seconds=store.policy.delivery_interval_seconds),
                        pending.response_id,
                        pending.revision,
                    ),
                )
    with store.connect() as conn:
        remaining = conn.execute("SELECT count(*) FROM feedback_cleanup").fetchone()
        queued = conn.execute(
            "SELECT count(*) FROM feedback_revisions r JOIN feedback_interactions i "
            "USING (response_id) WHERE r.delivery_state = 'pending' AND i.expires_at > %s",
            (now,),
        ).fetchone()
    return DeliveryResult(
        delivered=delivered,
        pending=queued[0] if queued else 0,
        deleted=deleted,
        cleanup_pending=remaining[0] if remaining else 0,
        purged_interactions=purged,
    )


def _deliver(
    tracking_uri: str,
    response: dict[str, Any],
    pending: PendingDelivery,
    previous_id: str | None,
) -> None:
    publication = AssessmentPublication(tracking_uri, response)
    submission = pending.submission
    metadata = {
        "feedback_id": str(pending.feedback_id),
        "response_id": str(pending.response_id),
        "revision": str(pending.revision),
        "policy_version": submission.policy_version,
        "categories": json.dumps(submission.categories),
        "interpretation": "Self-selected helpfulness and reported issues; not checked correctness.",
    }
    publication.publish(
        pending.assessment_id,
        Feedback(
            name="human_helpfulness",
            value=submission.rating,
            source=AssessmentSource(
                source_type=AssessmentSourceType.HUMAN, source_id=str(pending.feedback_id)
            ),
            metadata=metadata,
            overrides=previous_id,
        ),
    )


def feedback_worker(store: FeedbackStore, tracking_uri: str, stop: Event, wake: Event) -> None:
    while not stop.is_set():
        try:
            deliver_feedback(store, tracking_uri)
        except Exception:
            # Database outages cannot turn a failed acceptance into a successful receipt.
            # Already committed events stay pending and are picked up on the next pass.
            pass
        wake.wait(store.policy.delivery_interval_seconds)
        wake.clear()
