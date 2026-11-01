"""Original-answer binding and restartable publication through the existing MLflow adapter."""

import os
import time
from threading import Event
from typing import Any

from mlflow.entities import Feedback
from mlflow.exceptions import MlflowException
from mlflow.tracing.client import TracingClient


def _tracking(uri: str) -> TracingClient:
    if uri.startswith(("http://", "https://")) and (
        float(os.environ.get("MLFLOW_HTTP_REQUEST_TIMEOUT", "120")) > 5
        or int(os.environ.get("MLFLOW_HTTP_REQUEST_MAX_RETRIES", "7")) != 0
    ):
        raise ValueError("Configure a maximum five-second MLflow timeout and zero HTTP retries.")
    return TracingClient(tracking_uri=uri)


class AssessmentPublication:
    """Bind one retained answer before publishing assessments or running its judge."""

    def __init__(
        self,
        tracking_uri: str,
        response: dict[str, Any],
        *,
        deadline: float | None = None,
        cancellation: Event | None = None,
    ) -> None:
        self._tracking = _tracking(tracking_uri)
        self._trace_id = response["trace_id"]
        self._deadline = deadline
        self._cancellation = cancellation
        self._check()
        trace = self._tracking.get_trace(self._trace_id)
        roots = [span for span in trace.data.spans if span.parent_id is None]
        if len(roots) != 1 or roots[0].outputs != response:
            raise ValueError("Original trace does not match the served response.")

    def _check(self) -> None:
        if (self._cancellation is not None and self._cancellation.is_set()) or (
            self._deadline is not None and time.monotonic() >= self._deadline
        ):
            raise TimeoutError("Assessment publication deferred.")

    def publish(self, assessment_id: str, assessment: Feedback) -> None:
        """Return only after the stable identity, payload and supersession agree."""
        self._check()
        try:
            existing = self._tracking.get_assessment(self._trace_id, assessment_id)
        except MlflowException as exc:
            if exc.error_code != "RESOURCE_DOES_NOT_EXIST":
                raise
            # The pinned self-hosted backend enforces this public entity's identity;
            # replay after a lost acknowledgement reads the original assessment.
            assessment.assessment_id = assessment_id
            self._check()
            self._tracking.log_assessment(self._trace_id, assessment)
            self._check()
            existing = self._tracking.get_assessment(self._trace_id, assessment_id)
        if (
            existing.assessment_id != assessment_id
            or existing.trace_id != self._trace_id
            or existing.name != assessment.name
            or existing.feedback != assessment.feedback
            or existing.source != assessment.source
            or existing.metadata != assessment.metadata
            or existing.overrides != assessment.overrides
        ):
            raise ValueError("Assessment readback differs from the accepted assessment.")


def delete_assessment(tracking_uri: str, trace_id: str, assessment_id: str) -> None:
    """Finish retention cleanup even if an earlier deletion lost its acknowledgement."""
    try:
        _tracking(tracking_uri).delete_assessment(trace_id, assessment_id)
    except MlflowException as exc:
        if exc.error_code != "RESOURCE_DOES_NOT_EXIST":
            raise
