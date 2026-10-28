"""Frozen evaluation runs and independently reviewed answer/retrieval scoring."""

import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal, Self

if TYPE_CHECKING:
    from mlflow import MlflowClient

from pydantic import Field, StrictBool, TypeAdapter

from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record

CriticalFailure = Literal["false_premise", "unsupported_negative", "false_citation"]
_CASE_IDENTIFIER = TypeAdapter(Identifier)
_RUN_FIELDS = {
    "recorded_at",
    "reference_file_sha256",
    "case_ids",
    "cases",
    "state",
    "run_id",
    "failure_type",
    "tracking_failure_type",
    "input_artifacts",
    "result_artifact",
    "tracking_status",
    "recorder_version",
}
_CASE_FIELDS = {
    "case_id",
    "reference",
    "reference_sha256",
    "response_sha256",
    "state",
    "failure_type",
    "verification_state",
    "verification_failure_type",
    "paired",
}


class ClaimReview(Record):
    claim: NonEmpty
    correct: StrictBool | None
    grounded: StrictBool | None
    citation_supported: StrictBool | None


class FactReview(Record):
    fact: NonEmpty
    covered: StrictBool | None


class QualityReview(Record):
    """External review annotations, never the answer model's self-reported confidence."""

    case_id: Identifier
    response_sha256: Fingerprint
    reference_sha256: Fingerprint
    reviewer: NonEmpty
    rationale: NonEmpty
    claims: tuple[ClaimReview, ...]
    required_facts: tuple[FactReview, ...]
    answerability: StrictBool | None
    relevance: StrictBool | None = None
    critical_failures: tuple[CriticalFailure, ...] = ()


class ReviewMetric(Record):
    passed: int
    assessed: int
    unassessed: int
    value: float | None


class AnswerQuality(Record):
    correctness: ReviewMetric
    groundedness: ReviewMetric
    completeness: ReviewMetric
    citation_support: ReviewMetric
    answerability: ReviewMetric
    relevance: ReviewMetric
    critical_failures: tuple[CriticalFailure, ...]


class ScoredReview(Record):
    review: QualityReview
    scores: AnswerQuality


@dataclass(frozen=True)
class EvaluationTracking:
    client: "MlflowClient"
    experiment: str
    tags: dict[str, str]


class EvaluationRun:
    """Journal a selected frozen case before executing it, and own run completion."""

    def __init__(
        self,
        output: Path,
        references: Path,
        case_ids: Sequence[str],
        *,
        metadata: dict[str, Any] | None = None,
        tracking: EvaluationTracking | None = None,
        artifacts: Sequence[Path] = (),
    ) -> None:
        self.output = output
        self._references, reference_sha256 = _references(references)
        if (
            not case_ids
            or len(set(case_ids)) != len(case_ids)
            or any(identifier not in self._references for identifier in case_ids)
        ):
            raise ValueError("Select unique, known frozen cases for the evaluation.")
        if _RUN_FIELDS.intersection(metadata or {}):
            raise ValueError("Run identity and state belong to the evaluation module.")
        self._tracking = tracking
        self._tracking_finished = False
        self._artifacts = (references, *artifacts)
        self._input_fingerprints = {path: _file_fingerprint(path) for path in self._artifacts}
        if self._input_fingerprints[references] != reference_sha256:
            raise ValueError("The frozen references changed while preparing the evaluation.")
        self._active = False
        self._document: dict[str, Any] = {
            **deepcopy(metadata or {}),
            "recorded_at": datetime.now(UTC).isoformat(),
            "reference_file_sha256": reference_sha256,
            "recorder_version": "frozen-evaluation-run-v1",
            "input_artifacts": [
                {
                    "artifact_path": f"inputs/{index}/{path.name}",
                    "sha256": self._input_fingerprints[path],
                }
                for index, path in enumerate(self._artifacts)
            ],
            "result_artifact": f"result/{output.name}",
            "case_ids": list(case_ids),
            "cases": [],
            "state": "running",
        }

    def __enter__(self) -> Self:
        self.output.parent.mkdir(parents=True, exist_ok=True)
        with self.output.open("x") as destination:
            destination.write(json.dumps(self._document, indent=2, ensure_ascii=True) + "\n")
        try:
            if self._tracking:
                client = self._tracking.client
                experiment = client.get_experiment_by_name(self._tracking.experiment)
                experiment_id = (
                    experiment.experiment_id
                    if experiment
                    else client.create_experiment(
                        self._tracking.experiment,
                        artifact_location=Path("artifacts/mlflow").resolve().as_uri(),
                    )
                )
                self._document["run_id"] = client.create_run(
                    experiment_id, tags=self._tracking.tags
                ).info.run_id
                self._save()
            self._active = True
        except BaseException as exc:
            self._fail(exc)
            raise
        return self

    def annotate(self, **metadata: Any) -> None:
        """Retain measured expenditure and case-specific run metadata."""
        if not self._active or _RUN_FIELDS.intersection(metadata):
            raise ValueError("Run identity and state belong to the evaluation module.")
        self._document.update(deepcopy(metadata))
        self._save()

    def capture(
        self,
        case_id: str,
        execute: Callable[[], dict[str, Any]],
        *,
        verify: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Retain execution before optional readback; verification cannot change evidence."""
        return self._capture(self._start(case_id), execute, verify)

    def capture_pair(
        self,
        case_id: str,
        captures: Mapping[str, Callable[[], dict[str, Any]]],
        *,
        primary: str,
        verify: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        """Journal each comparison answer independently before selecting the primary."""
        if len(captures) != 2 or primary not in captures:
            raise ValueError("Select two named captures and their primary response.")
        row = self._start(case_id)
        paired = {name: {"state": "pending"} for name in captures}
        row["paired"] = paired
        try:
            for name, execute in captures.items():
                self._capture(paired[name], execute, verify)
            row["response"] = deepcopy(paired[primary]["response"])
            row["response_sha256"] = paired[primary]["response_sha256"]
            row["state"] = "complete"
            self._save()
            return deepcopy(row)
        except BaseException as exc:
            row.update(state="failed", failure_type=type(exc).__name__)
            self._save()
            raise

    @property
    def cases(self) -> tuple[dict[str, Any], ...]:
        """Detached retained outcomes for presentation and domain summaries."""
        return tuple(deepcopy(self._document["cases"]))

    def _start(self, case_id: str) -> dict[str, Any]:
        if not self._active or case_id not in self._document["case_ids"]:
            raise ValueError("Case is not selected for this evaluation run.")
        if any(row["case_id"] == case_id for row in self._document["cases"]):
            raise ValueError("Duplicate captured case identifier.")
        reference = self._references[case_id]
        row = {
            "case_id": case_id,
            "reference": reference,
            "reference_sha256": document_fingerprint(reference),
            "state": "attempting",
        }
        self._document["cases"].append(row)
        return row

    def _capture(
        self,
        row: dict[str, Any],
        execute: Callable[[], dict[str, Any]],
        verify: Callable[[dict[str, Any]], dict[str, Any]] | None,
    ) -> dict[str, Any]:
        row["state"] = "attempting"
        self._save()
        try:
            result = execute()
            if _CASE_FIELDS.intersection(result):
                raise ValueError("Case identity and state belong to the evaluation module.")
            row.update(deepcopy(result))
            if "response" in row:
                row["response_sha256"] = document_fingerprint(row["response"])
            if verify is not None:
                self._verify(row, verify)
            row["state"] = "complete"
            self._save()
            return deepcopy(row)
        except BaseException as exc:
            row.update(state="failed", failure_type=type(exc).__name__)
            self._save()
            raise

    def _verify(
        self, row: dict[str, Any], verify: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        row["verification_state"] = "running"
        self._save()
        try:
            result = verify(deepcopy(row))
            if (_CASE_FIELDS | row.keys()).intersection(result):
                raise ValueError("Verification cannot replace captured evidence or its state.")
            row.update(deepcopy(result))
            row["verification_state"] = "complete"
        except BaseException as exc:
            row.update(verification_state="failed", verification_failure_type=type(exc).__name__)
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._active = False
        if exc is not None:
            self._fail(exc)
            return
        try:
            if any(
                _file_fingerprint(path) != fingerprint
                for path, fingerprint in self._input_fingerprints.items()
            ):
                raise ValueError("A frozen evaluation input changed during this evaluation.")
            if [row["case_id"] for row in self._document["cases"]] != self._document[
                "case_ids"
            ] or any(row["state"] != "complete" for row in self._document["cases"]):
                raise ValueError(
                    "Evaluation must complete all declared cases exactly once in order."
                )
            self._document["state"] = "finalizing" if self._tracking else "complete"
            self._save()
            self._publish()
            if self._tracking:
                self._document["state"] = "complete"
                self._save()
        except BaseException as failure:
            self._fail(failure)
            raise

    def _publish(self) -> None:
        if self._tracking is None:
            return
        client = self._tracking.client
        run_id = self._document["run_id"]
        for key, value in self._document.items():
            if key not in {"run_id", "state"} and isinstance(value, (str, int, float, bool)):
                client.log_param(run_id, key, value)
        scored = tuple(
            ScoredReview.model_validate({"review": row["review"], "scores": row["scores"]})
            for row in self._document["cases"]
            if "review" in row
        )
        log_review_metrics(client, run_id, scored)
        for index, path in enumerate(self._artifacts):
            client.log_artifact(run_id, str(path), artifact_path=f"inputs/{index}")
        # The downloadable journal stays unreviewable until termination succeeds.
        client.log_artifact(run_id, str(self.output), artifact_path="result")
        client.set_terminated(run_id)
        self._tracking_finished = True
        self._document["tracking_status"] = "FINISHED"
        with tempfile.TemporaryDirectory(prefix="ask-phil-evaluation-publish-") as directory:
            published = Path(directory) / self.output.name
            published.write_text(
                json.dumps({**self._document, "state": "complete"}, indent=2, ensure_ascii=True)
                + "\n",
                encoding="utf-8",
            )
            client.log_artifact(run_id, str(published), artifact_path="result")

    def _fail(self, exc: BaseException) -> None:
        self._document.update(state="failed", failure_type=type(exc).__name__)
        # After acknowledged termination, an uncertain final upload must not revoke
        # a completed remote result. Its retained state determines review eligibility.
        if self._tracking and "run_id" in self._document and not self._tracking_finished:
            try:
                self._tracking.client.set_terminated(self._document["run_id"], status="FAILED")
            except BaseException as failure:
                self._document["tracking_failure_type"] = type(failure).__name__
        self._save()

    def _save(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.output.parent, delete=False
        ) as destination:
            temporary = Path(destination.name)
            try:
                json.dump(self._document, destination, indent=2, ensure_ascii=True)
                destination.write("\n")
                destination.flush()
                os.fsync(destination.fileno())
                os.replace(temporary, self.output)
            finally:
                temporary.unlink(missing_ok=True)


def document_fingerprint(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def review_capture(
    capture_path: Path,
    reviews_path: Path,
    references_path: Path,
    output: Path,
    *,
    tracking: EvaluationTracking | None = None,
) -> dict[str, Any]:
    """Review a frozen capture once, preserving the identity of every recorded case."""
    capture, capture_sha256 = _read_document(capture_path)
    references, reference_sha256 = _references(references_path)
    if capture.get("state") != "complete":
        raise ValueError("Capture must be complete before review.")
    if capture.get("reference_file_sha256") != reference_sha256:
        raise ValueError("Capture must match these frozen references.")
    identifiers = [_case_id(row) for row in capture["cases"]]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate captured case identifiers.")
    if any(identifier not in references for identifier in identifiers):
        raise ValueError("Unknown captured case identifier.")
    if "case_ids" in capture and capture["case_ids"] != identifiers:
        raise ValueError("Capture must contain all declared cases exactly once in order.")
    rows = {}
    for row in capture["cases"]:
        identifier = _case_id(row)
        reference = references[identifier]
        if row.get("state", "complete") != "complete":
            raise ValueError("Every captured case must be complete before review.")
        if "reference" in row and row["reference"] != reference:
            raise ValueError("Captured reference differs from these frozen references.")
        if "reference_sha256" in row and row["reference_sha256"] != document_fingerprint(reference):
            raise ValueError("Captured reference fingerprint differs.")
        if references[identifier].get("operation") == "reset":
            if "reset" not in row or "response" in row:
                raise ValueError("A reset case must record its reset outcome.")
            continue
        response = row.get("response")
        if (
            not isinstance(response, dict)
            or not isinstance(response.get("answer"), str)
            or not response["answer"].strip()
        ):
            raise ValueError("A captured case is missing a usable served response.")
        if "response_sha256" in row and row["response_sha256"] != document_fingerprint(
            row["response"]
        ):
            raise ValueError("Captured response fingerprint differs.")
        rows[identifier] = row
    if not rows:
        raise ValueError("Capture has no served responses to review.")
    annotations, reviews_sha256 = _read_document(reviews_path)
    reviews = [QualityReview.model_validate(row) for row in annotations["reviews"]]
    if len(reviews) != len(rows) or {review.case_id for review in reviews} != rows.keys():
        raise ValueError("Review every captured response exactly once.")
    scored = tuple(
        score_captured_answer(
            review,
            rows[review.case_id]["response"],
            references[review.case_id],
            _required_facts(references[review.case_id]),
        )
        for review in reviews
    )
    metadata = {
        "kind": "captured-answer-review",
        "expenditure_category": "offline_evaluation",
        "source_run_id": capture.get("run_id"),
        "answer_model_calls_in_review": 0,
        "review_model_cost_usd": 0,
        "model_calls": 0,
        "cost_usd": "0",
        "capture_sha256": capture_sha256,
        "reviews_sha256": reviews_sha256,
        "scorer": "reviewed-binary-dimensions-v2",
    }
    evaluation = EvaluationRun(
        output,
        references_path,
        tuple(review.case_id for review in reviews),
        metadata=metadata,
        tracking=tracking,
        artifacts=(capture_path, reviews_path),
    )
    if any(
        evaluation._input_fingerprints[path] != fingerprint
        for path, fingerprint in (
            (references_path, reference_sha256),
            (capture_path, capture_sha256),
            (reviews_path, reviews_sha256),
        )
    ):
        raise ValueError("Frozen evaluation inputs changed while preparing the review.")
    with evaluation as run:
        for result in scored:
            run.capture(result.review.case_id, partial(result.model_dump, mode="json"))
    result_document: dict[str, Any] = json.loads(output.read_bytes())
    return result_document


def _file_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_document(path: Path) -> tuple[dict[str, Any], str]:
    data = path.read_bytes()
    document = json.loads(data)
    if not isinstance(document, dict):
        raise ValueError("Evaluation artifacts must be JSON objects.")
    return document, hashlib.sha256(data).hexdigest()


def _case_id(row: dict[str, Any]) -> str:
    identifier = row.get("case_id", row.get("reference", {}).get("case_id"))
    if not isinstance(identifier, str):
        raise ValueError("Every captured case needs an identifier.")
    if "case_id" in row and "reference" in row and row["reference"].get("case_id") != identifier:
        raise ValueError("Captured case and reference identifiers differ.")
    return _CASE_IDENTIFIER.validate_python(identifier)


def _references(path: Path) -> tuple[dict[str, dict[str, Any]], str]:
    document, fingerprint = _read_document(path)
    rows = document.get("steps", document.get("cases", []))
    identifiers = [_case_id(row) for row in rows]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate frozen reference case identifiers.")
    return dict(zip(identifiers, rows, strict=True)), fingerprint


def _required_facts(reference: dict[str, Any]) -> tuple[str, ...]:
    facts = reference.get("expected_facts", reference.get("required_facts", []))
    return tuple(fact["fact"] if isinstance(fact, dict) else fact for fact in facts)


def score_captured_answer(
    review: QualityReview, response: object, reference: object, required_facts: tuple[str, ...]
) -> ScoredReview:
    """Reject stale/incomplete annotations before scoring a captured response."""
    if review.response_sha256 != document_fingerprint(
        response
    ) or review.reference_sha256 != document_fingerprint(reference):
        raise ValueError("Stale review: response or reference fingerprint differs.")
    if tuple(f.fact for f in review.required_facts) != required_facts:
        raise ValueError("Review must assess every required fact in reference order.")
    return ScoredReview(review=review, scores=score_answer_review(review))


def log_review_metrics(
    client: "MlflowClient", run_id: str, results: tuple[ScoredReview, ...]
) -> None:
    for result in results:
        for dimension, metric in result.scores.model_dump().items():
            prefix = f"{result.review.case_id}.{dimension}"
            if dimension == "critical_failures":
                client.log_metric(run_id, prefix, len(metric))
            else:
                for name in ("passed", "assessed", "unassessed", "value"):
                    if metric[name] is not None:
                        client.log_metric(run_id, f"{prefix}.{name}", metric[name])


def score_answer_review(review: QualityReview) -> AnswerQuality:
    """Reviewed binary labels only. Missing assessments never become passes or failures.

    Correctness compares claims with references; groundedness compares with actual
    context; citation support checks the claim's cited passages. Completeness counts
    required facts/qualifications, answerability the appropriateness of the outcome.
    A zero denominator is unavailable. No combined score hides critical failures.
    """

    def metric(labels: tuple[bool | None, ...]) -> ReviewMetric:
        known = [value for value in labels if value is not None]
        passed = sum(known)
        return ReviewMetric(
            passed=passed,
            assessed=len(known),
            unassessed=len(labels) - len(known),
            value=passed / len(known) if known else None,
        )

    return AnswerQuality(
        correctness=metric(tuple(c.correct for c in review.claims)),
        groundedness=metric(tuple(c.grounded for c in review.claims)),
        completeness=metric(tuple(f.covered for f in review.required_facts)),
        citation_support=metric(tuple(c.citation_supported for c in review.claims)),
        answerability=metric((review.answerability,)),
        relevance=metric((review.relevance,)),
        critical_failures=review.critical_failures,
    )


class FactLabel(Record):
    fact: str
    sufficient_sets: tuple[tuple[Identifier, ...], ...] = Field(min_length=1)


class RetrievalReference(Record):
    case_id: Identifier
    question: str
    answerable: bool
    relevant_ids: tuple[Identifier, ...]
    required_facts: tuple[FactLabel, ...]


class RetrievalScore(Record):
    k: int
    relevant_passage_count: int
    recall_at_k: float | None
    hit_at_k: float | None
    mrr_at_k: float | None
    required_fact_count: int
    context_fact_coverage: float | None
    context_sufficient: bool


def score_retrieval(
    reference: RetrievalReference,
    retrieved_ids: tuple[str, ...],
    context_ids: tuple[str, ...],
    *,
    k: int,
) -> RetrievalScore:
    """Deduplicate before top-k; exact snapshot-local IDs, binary passage relevance.

    Recall/Hit/MRR exclude unanswerable cases with no relevant passages. Context
    coverage uses independently labelled whole-span sufficient sets per required fact.
    No sufficient answer exists for a reference marked unanswerable in this snapshot.
    """
    if k < 1:
        raise ValueError("k must be positive")
    top = tuple(dict.fromkeys(retrieved_ids))[:k]
    relevant = set(reference.relevant_ids)
    ranks = [i for i, identifier in enumerate(top, 1) if identifier in relevant]
    context = set(context_ids)
    covered = sum(
        any(set(sufficient).issubset(context) for sufficient in fact.sufficient_sets)
        for fact in reference.required_facts
    )
    fact_count = len(reference.required_facts)
    return RetrievalScore(
        k=k,
        relevant_passage_count=len(relevant),
        recall_at_k=len(ranks) / len(relevant) if relevant else None,
        hit_at_k=float(bool(ranks)) if relevant else None,
        mrr_at_k=(1 / ranks[0] if ranks else 0.0) if relevant else None,
        required_fact_count=fact_count,
        context_fact_coverage=covered / fact_count if fact_count else None,
        context_sufficient=reference.answerable and fact_count > 0 and covered == fact_count,
    )
