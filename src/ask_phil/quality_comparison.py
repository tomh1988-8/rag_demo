"""Grouped case references and controlled, paired development comparisons."""

import hashlib
from collections import defaultdict
from statistics import mean
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from ask_phil.evaluation import AnswerQuality, FactLabel, RetrievalScore, document_fingerprint
from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record

Split = Literal["development", "judge_calibration", "judge_validation", "held_out", "regression"]
Measurement = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class ComparisonEvidence(Record):
    evidence_id: Identifier
    text: NonEmpty
    source_revision: NonEmpty
    sha256: Fingerprint

    @model_validator(mode="after")
    def validate_text(self) -> Self:
        if hashlib.sha256(self.text.encode()).hexdigest() != self.sha256:
            raise ValueError("Reference evidence fingerprint differs from retained text.")
        return self


class ComparisonCase(Record):
    case_id: Identifier
    group_ids: tuple[Identifier, ...] = Field(min_length=1)
    split: Split
    category: Identifier
    question: NonEmpty
    snapshot_id: Identifier
    session: Identifier | None = None
    derived_from: tuple[Identifier, ...] = ()
    expected_status: Literal["answered", "partial", "clarification", "insufficient_evidence"]
    required_facts: tuple[FactLabel, ...]
    allowed_alternatives: tuple[NonEmpty, ...]
    forbidden_assertions: tuple[NonEmpty, ...]
    evidence: tuple[ComparisonEvidence, ...]
    review_note: NonEmpty
    synthetic_provenance: NonEmpty | None


class ComparisonDataset(Record):
    dataset_id: Identifier
    cases: tuple[ComparisonCase, ...] = Field(min_length=1)
    prior_group_splits: dict[str, Split] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_splits(self) -> Self:
        cases = {case.case_id: case for case in self.cases}
        if len(cases) != len(self.cases):
            raise ValueError("Duplicate case identifiers.")
        groups = dict(self.prior_group_splits)
        questions: dict[str, Split] = {}
        sessions: dict[str, Split] = {}
        evidence_splits: dict[str, Split] = {}
        for case in self.cases:
            for group in case.group_ids:
                if groups.setdefault(group, case.split) != case.split:
                    raise ValueError("Related group crosses a dataset split.")
            normalized = " ".join(case.question.casefold().split())
            if questions.setdefault(normalized, case.split) != case.split:
                raise ValueError("Duplicate question crosses a dataset split.")
            if case.session and sessions.setdefault(case.session, case.split) != case.split:
                raise ValueError("Conversation crosses a dataset split.")
            for passage in case.evidence:
                material = " ".join(passage.text.casefold().split())
                if evidence_splits.setdefault(material, case.split) != case.split:
                    raise ValueError("Repeated evidence material crosses a dataset split.")
            for parent in case.derived_from:
                if parent not in cases or cases[parent].split != case.split:
                    raise ValueError("Derivative must retain its known parent's split.")
        return self

    @property
    def fingerprint(self) -> str:
        return document_fingerprint(self.model_dump(mode="json"))


class ComparisonConfiguration(Record):
    configuration_id: Identifier
    retrieval_version: Identifier
    context_version: Identifier
    context_bytes: int = Field(gt=0)
    retrieval_k: int = Field(gt=0)
    answer_settings_sha256: Fingerprint
    prompt_sha256: Fingerprint
    snapshot_sha256: Fingerprint
    cache_mode: Literal["off", "cold", "warm"]
    cache_namespace: Identifier


class ComparisonObservation(Record):
    case_id: Identifier
    repeat: int = Field(ge=0)
    response_sha256: Fingerprint
    quality: AnswerQuality
    retrieval: RetrievalScore | None = None
    serving_cost_usd: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    elapsed_ms: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    stage_ms: dict[str, Measurement | None] = Field(default_factory=dict)


class ComparisonRun(Record):
    dataset_sha256: Fingerprint
    code_revision: NonEmpty
    application_sha256: Fingerprint
    configuration: ComparisonConfiguration
    observations: tuple[ComparisonObservation, ...] = Field(min_length=1)
    offline_evaluation_cost_usd: float | None = Field(default=0, ge=0, allow_inf_nan=False)


def compare_development(
    dataset: ComparisonDataset,
    baseline: ComparisonRun,
    candidate: ComparisonRun,
    *,
    changed_factor: Literal["repeat_control", "retrieval", "context", "prompt", "answer_settings"],
) -> dict[str, Any]:
    """Paired macro case means; repeats measure variation, not new independent cases."""
    if any(run.dataset_sha256 != dataset.fingerprint for run in (baseline, candidate)):
        raise ValueError("Both runs must use the exact frozen dataset.")
    if (baseline.code_revision, baseline.application_sha256) != (
        candidate.code_revision,
        candidate.application_sha256,
    ):
        raise ValueError("Controlled configuration comparisons require identical serving source.")
    left = baseline.configuration.model_dump()
    right = candidate.configuration.model_dump()
    changes = {key for key in left if left[key] != right[key]}
    allowed = {"configuration_id", "cache_namespace"} | {
        "repeat_control": set(),
        "retrieval": {"retrieval_version", "retrieval_k"},
        "context": {"context_version", "context_bytes"},
        "prompt": {"prompt_sha256"},
        "answer_settings": {"answer_settings_sha256"},
    }[changed_factor]
    if changes - allowed:
        raise ValueError("Uncontrolled configuration changes in paired comparison.")
    if changed_factor != "repeat_control" and not changes & (
        allowed - {"configuration_id", "cache_namespace"}
    ):
        raise ValueError("The declared comparison factor did not change.")
    if left["cache_mode"] != "off" or right["cache_mode"] != "off":
        raise ValueError("Model-quality comparisons require uncached runs.")
    if left["cache_namespace"] == right["cache_namespace"]:
        raise ValueError("Isolate run and partition cache namespaces even when disabled.")
    cases = {case.case_id: case for case in dataset.cases}

    def index(run: ComparisonRun) -> dict[tuple[str, int], ComparisonObservation]:
        result = {}
        for observation in run.observations:
            if (
                observation.case_id not in cases
                or cases[observation.case_id].split != "development"
            ):
                raise ValueError("Compare known development cases only; holdout remains reserved.")
            key = observation.case_id, observation.repeat
            if key in result:
                raise ValueError("Duplicate case/repeat observation.")
            result[key] = observation
        return result

    before, after = index(baseline), index(candidate)
    if before.keys() != after.keys():
        raise ValueError("Runs must contain identical case/repeat pairs.")
    identifiers = sorted({key[0] for key in before})
    per_case: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    dimensions: dict[str, Any] = {}
    names = tuple(name for name in AnswerQuality.model_fields if name != "critical_failures")
    for identifier in identifiers:
        pairs = [key for key in before if key[0] == identifier]
        per_case[identifier] = {"category": cases[identifier].category, "repeats": len(pairs)}
        for dimension in names:
            a = [getattr(before[key].quality, dimension).value for key in pairs]
            b = [getattr(after[key].quality, dimension).value for key in pairs]
            matched = [(x, y) for x, y in zip(a, b, strict=True) if x is not None and y is not None]
            av = [x for x in a if x is not None]
            bv = [x for x in b if x is not None]
            per_case[identifier][dimension] = {
                "baseline_mean": mean(av) if av else None,
                "candidate_mean": mean(bv) if bv else None,
                "paired_delta": mean(y - x for x, y in matched) if matched else None,
                "paired_assessed": len(matched),
                "baseline_assessed": len(av),
                "candidate_assessed": len(bv),
                "baseline_range": [min(av), max(av)] if av else None,
                "candidate_range": [min(bv), max(bv)] if bv else None,
            }
            for role, values in (("baseline", av), ("candidate", bv)):
                if any(value < 1 for value in values):
                    failures.append(
                        {
                            "case_id": identifier,
                            "category": cases[identifier].category,
                            "dimension": dimension,
                            "run": role,
                        }
                    )
        for role, indexed in (("baseline", before), ("candidate", after)):
            critical = sorted({f for key in pairs for f in indexed[key].quality.critical_failures})
            if critical:
                failures.append(
                    {
                        "case_id": identifier,
                        "category": cases[identifier].category,
                        "dimension": "critical_failures",
                        "run": role,
                        "failures": critical,
                    }
                )
    for dimension in names:
        values = [per_case[identifier][dimension] for identifier in identifiers]
        dimensions[dimension] = {}
        for field in ("baseline_mean", "candidate_mean", "paired_delta"):
            known = [value[field] for value in values if value[field] is not None]
            dimensions[dimension][field] = mean(known) if known else None
            dimensions[dimension][field + "_cases"] = len(known)
    categories: dict[str, list[str]] = defaultdict(list)
    for identifier in identifiers:
        categories[cases[identifier].category].append(identifier)
    # Connected story groups count once even when a case links two group names.
    components: list[set[str]] = []
    for identifier in identifiers:
        connected = set(cases[identifier].group_ids)
        overlaps = [group for group in components if group & connected]
        for group in overlaps:
            connected.update(group)
            components.remove(group)
        components.append(connected)

    def total_cost(run: ComparisonRun) -> float | None:
        costs = [row.serving_cost_usd for row in run.observations]
        return sum(cost for cost in costs if cost is not None) if None not in costs else None

    def critical_gate(run: ComparisonRun) -> str:
        incomplete = False
        for observation in run.observations:
            if observation.quality.critical_failures:
                return "failed"
            for name in ("correctness", "groundedness", "citation_support"):
                metric = getattr(observation.quality, name)
                if metric.value is not None and metric.value < 1:
                    return "failed"
                incomplete |= metric.unassessed > 0 or metric.value is None
        return "unavailable" if incomplete else "passed"

    return {
        "kind": "controlled-development-comparison-v1",
        "code_revision": baseline.code_revision,
        "application_sha256": baseline.application_sha256,
        "dataset_sha256": dataset.fingerprint,
        "changed_factor": changed_factor,
        "case_count": len(identifiers),
        "independent_groups": len(components),
        "paired_observations": len(before),
        "dimensions": dimensions,
        "per_case": per_case,
        "categories": dict(categories),
        "failures": failures,
        "critical_gates": {
            "baseline": critical_gate(baseline),
            "candidate": critical_gate(candidate),
        },
        "stage_measurements": {
            role: [row.model_dump(mode="json", exclude={"quality"}) for row in run.observations]
            for role, run in (("baseline", baseline), ("candidate", candidate))
        },
        "serving_cost_usd": {"baseline": total_cost(baseline), "candidate": total_cost(candidate)},
        "offline_evaluation_cost_usd": {
            "baseline": baseline.offline_evaluation_cost_usd,
            "candidate": candidate.offline_evaluation_cost_usd,
        },
        "limitation": "Development only. Repeats are dependent; ranges are observed variation, "
        "not confidence intervals. Story groups, not repeats, bound independent sample size.",
    }
