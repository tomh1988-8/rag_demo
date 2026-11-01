"""Explicit report dispositions and source-checked regression promotion."""

import hashlib
import json
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb
from pydantic import Field, field_validator

from ask_phil.answers import AnswerRecord
from ask_phil.evaluation import document_fingerprint
from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record
from ask_phil.feedback import FeedbackStore
from ask_phil.online_evaluation import OnlineReport
from ask_phil.quality_comparison import ComparisonCase, ComparisonDataset
from ask_phil.reference_data import reference_directory
from ask_phil.security import redact_text
from ask_phil.storage import EvidenceStore


class ItemDisposition(Record):
    response_id: UUID
    feedback_revision: int = Field(ge=1)
    response_sha256: Fingerprint
    disposition: Literal["unresolved", "confirmed", "rejected", "duplicate", "needs_source_review"]
    note: NonEmpty

    @field_validator("note")
    @classmethod
    def redact_note(cls, value: str) -> str:
        return redact_text(value)


class ReportReview(Record):
    review_id: UUID = Field(default_factory=uuid4)
    report_id: UUID
    reviewer: NonEmpty
    note: NonEmpty
    dispositions: tuple[ItemDisposition, ...]

    @field_validator("note", "reviewer")
    @classmethod
    def redact_note(cls, value: str) -> str:
        return redact_text(value)


class SourceCheck(Record):
    fact: NonEmpty
    evidence_ids: tuple[Identifier, ...] = Field(min_length=1)
    note: NonEmpty


class RegressionPromotion(Record):
    review_id: UUID
    response_id: UUID
    case: ComparisonCase
    source_checks: tuple[SourceCheck, ...] = Field(min_length=1)


class PromotedRegression(Record):
    promotion_id: UUID
    review_id: UUID
    response_id: UUID
    generation_id: UUID
    response_sha256: Fingerprint
    dataset_sha256: Fingerprint
    held_out_labels_exposed: Literal[False] = False


class OnlineReview:
    def __init__(self, database_url: str) -> None:
        self.store = FeedbackStore(database_url)

    def _ensure(self) -> None:
        with self.store.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728204)")
            conn.execute("""CREATE TABLE IF NOT EXISTS online_reviews (
                review_id uuid PRIMARY KEY,
                report_id uuid NOT NULL REFERENCES online_reports ON DELETE CASCADE,
                document jsonb NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS online_promotions (
                generation_id uuid PRIMARY KEY, document jsonb NOT NULL
            )""")

    def report(self, report_id: UUID) -> OnlineReport:
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT document FROM online_reports WHERE report_id=%s", (report_id,)
            ).fetchone()
        if row is None:
            raise LookupError("Online report is unavailable.")
        report = OnlineReport.model_validate(row[0])
        # Original retained feedback is required for review, even if a private old report survives.
        with self.store.connect() as conn:
            for item in report.feedback.review_priorities:
                if (
                    conn.execute(
                        "SELECT 1 FROM feedback_interactions WHERE response_id=%s "
                        "AND expires_at > %s",
                        (item.response_id, self.store.clock()),
                    ).fetchone()
                    is None
                ):
                    raise LookupError("Report evidence has expired; create a current report.")
        return report

    def response(self, report_id: UUID, response_id: UUID) -> AnswerRecord:
        report = self.report(report_id)
        if response_id not in {j.response_id for j in report.jobs} | {
            p.response_id for p in report.feedback.review_priorities
        }:
            raise ValueError("Response does not belong to this report.")
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT document FROM answer_responses WHERE response_id=%s", (response_id,)
            ).fetchone()
        if row is None:
            raise LookupError("Original response is unavailable.")
        return AnswerRecord.model_validate(row[0])

    def record(self, review: ReportReview) -> ReportReview:
        self._ensure()
        report = self.report(review.report_id)
        required = {(r.response_id, r.feedback_revision) for r in report.required_reviews}
        supplied = {(r.response_id, r.feedback_revision) for r in review.dispositions}
        allowed = {(p.response_id, p.signal.revision) for p in report.feedback.review_priorities}
        if len(supplied) != len(review.dispositions) or required - supplied or supplied - allowed:
            raise ValueError("Review must cover every required item once with its report revision.")
        for item in review.dispositions:
            original = self.response(review.report_id, item.response_id)
            if item.response_sha256 != document_fingerprint(original.model_dump(mode="json")):
                raise ValueError("Disposition must bind the original response and evidence.")
        with self.store.connect() as conn:
            previous = conn.execute(
                "SELECT document FROM online_reviews WHERE review_id=%s", (review.review_id,)
            ).fetchone()
            if previous and previous[0] != review.model_dump(mode="json"):
                raise ValueError("Review identity already has a different immutable disposition.")
            conn.execute(
                "INSERT INTO online_reviews VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (review.review_id, review.report_id, Jsonb(review.model_dump(mode="json"))),
            )
        return review

    def history(self, report_id: UUID) -> tuple[ReportReview, ...]:
        self._ensure()
        self.report(report_id)
        with self.store.connect() as conn:
            rows = conn.execute(
                "SELECT document FROM online_reviews WHERE report_id=%s ORDER BY review_id",
                (report_id,),
            ).fetchall()
        return tuple(ReportReview.model_validate(r[0]) for r in rows)

    def promote(self, request: RegressionPromotion, output: Path) -> PromotedRegression:
        self._ensure()
        if output.exists() or output.with_suffix(".lineage.json").exists():
            raise FileExistsError("Preserve existing versioned regression artifacts.")
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT document FROM online_reviews WHERE review_id=%s", (request.review_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Promotion needs an existing report review.")
        review = ReportReview.model_validate(row[0])
        if not any(
            d.response_id == request.response_id and d.disposition == "confirmed"
            for d in review.dispositions
        ):
            raise ValueError("Only a confirmed, inspected failure can become a regression.")
        response = self.response(review.report_id, request.response_id)
        case = request.case
        if (
            case.split != "regression"
            or case.snapshot_id != response.snapshot_id
            or case.question != response.question
            or not case.required_facts
        ):
            raise ValueError(
                "Regression must bind the original question, snapshot and independent facts."
            )
        snapshot = EvidenceStore(self.store.database_url).snapshot(response.snapshot_id)
        passages = {p.evidence_id: p for p in snapshot.passages}
        for evidence in case.evidence:
            passage = passages.get(evidence.evidence_id)
            source = passage.source or snapshot.source if passage else snapshot.source
            if (
                passage is None
                or evidence.text != passage.text
                or evidence.sha256 != passage.sha256
                or evidence.source_revision != source.revision_id
            ):
                raise ValueError(
                    "Regression evidence must resolve to the original trusted source revision."
                )
        evidence_ids = {e.evidence_id for e in case.evidence}
        facts = {f.fact for f in case.required_facts}
        checks = {c.fact: c for c in request.source_checks}
        if (
            len(checks) != len(request.source_checks)
            or facts != set(checks)
            or any(not set(check.evidence_ids) <= evidence_ids for check in checks.values())
            or any(
                not any(set(s) <= set(checks[f.fact].evidence_ids) for s in f.sufficient_sets)
                for f in case.required_facts
            )
        ):
            raise ValueError("Each independent expected fact needs a documented source check.")
        registry = self._check_splits(case)
        dataset = ComparisonDataset(dataset_id=case.case_id, cases=(case,))
        generation_id = getattr(response, "generation_id", None) or response.response_id
        result = PromotedRegression(
            promotion_id=uuid4(),
            review_id=review.review_id,
            response_id=response.response_id,
            generation_id=generation_id,
            response_sha256=document_fingerprint(response.model_dump(mode="json")),
            dataset_sha256=dataset.fingerprint,
        )
        lineage = {
            **result.model_dump(mode="json"),
            "original_response": response.model_dump(mode="json"),
            "review": review.model_dump(mode="json"),
            "source_checks": [c.model_dump(mode="json") for c in request.source_checks],
            "registry_fingerprints": registry,
            "limitation": "Reviewer source checks establish this source-supported expectation; "
            "they do not establish independent canon corroboration or held-out acceptance.",
        }
        with self.store.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(728205)")
            if conn.execute(
                "SELECT 1 FROM online_promotions WHERE generation_id=%s", (generation_id,)
            ).fetchone():
                raise ValueError("Duplicate generation already promoted; retain its story group.")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x") as destination:
                destination.write(dataset.model_dump_json(indent=2) + "\n")
            with output.with_suffix(".lineage.json").open("x") as destination:
                destination.write(json.dumps(lineage, indent=2) + "\n")
            conn.execute(
                "INSERT INTO online_promotions VALUES (%s,%s)",
                (generation_id, Jsonb(result.model_dump(mode="json"))),
            )
        return result

    def _check_splits(self, case: ComparisonCase) -> dict[str, str]:
        registry = {}
        question = " ".join(case.question.casefold().split())
        evidence = {" ".join(e.text.casefold().split()) for e in case.evidence}

        def strings(value: Any) -> set[str]:
            if isinstance(value, str):
                return {" ".join(value.casefold().split())}
            if isinstance(value, dict):
                return {s for nested in value.values() for s in strings(nested)}
            if isinstance(value, list):
                return {s for nested in value for s in strings(nested)}
            return set()

        def inspect(value: Any, protected: bool = False) -> None:
            if isinstance(value, dict):
                prior = value.get("prior_group_splits", {})
                if any(prior.get(group) == "held_out" for group in case.group_ids):
                    raise ValueError("Held-out contamination: story group remains reserved.")
                protected = protected or value.get("split") == "held_out"
                if protected:
                    groups = set(value.get("group_ids", ())) | {value.get("group_id", "")}
                    material = strings(value)
                    if (
                        groups.intersection(case.group_ids)
                        or " ".join(str(value.get("question", "")).casefold().split()) == question
                        or any(text in retained for text in evidence for retained in material)
                        or value.get("case_id") in case.derived_from
                    ):
                        raise ValueError(
                            "Held-out contamination: retire/adjudicate the overlapping group first."
                        )
                for nested in value.values():
                    inspect(nested, protected)
            elif isinstance(value, list):
                for nested in value:
                    inspect(nested, protected)

        for path in sorted(reference_directory().glob("*.json")):
            raw = path.read_bytes()
            registry[str(path)] = hashlib.sha256(raw).hexdigest()
            inspect(json.loads(raw))
        return registry
