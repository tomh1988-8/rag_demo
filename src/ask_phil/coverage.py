"""Frozen coverage evidence, reviewed composition and bounded resumable extraction."""

import fcntl
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

import httpx
from mlflow import MlflowClient
from pydantic import Field, TypeAdapter, model_validator

from ask_phil.answering import application_fingerprint
from ask_phil.claim_extraction import ClaimExtractionRun, validate_extraction_inputs
from ask_phil.claims import ClaimReview
from ask_phil.classified_facts import ContextClaim
from ask_phil.connection_evaluation import ConnectionReference
from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record, SourceSnapshot
from ask_phil.openrouter import Budget, OpenRouterProfile
from ask_phil.parentage import ClaimBatch, ParentageClaim, admit_claims
from ask_phil.relationships import RelationshipBatch, RelationshipClaim, admit_relationships
from ask_phil.story_events import EventBatch, EventClaim, EventReview, admit_events


class CoverageBatch(Record):
    batch_id: Identifier
    character_id: Identifier
    kind: Literal["family", "relationships", "events"]
    snapshot: str
    snapshot_file_sha256: Fingerprint
    reference: str
    reference_sha256: Fingerprint
    split: Literal["exposed_development", "regression", "held_out"]
    story_groups: tuple[NonEmpty, ...] = Field(min_length=1)
    reference_complete: Literal[True]
    review_note: NonEmpty
    gaps: tuple[NonEmpty, ...] = Field(min_length=1)


class CoveragePlan(Record):
    version: Literal[1]
    roster: tuple[Identifier, ...] = Field(min_length=1)
    batches: tuple[CoverageBatch, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def coherent_roster(self) -> Self:
        if len(set(self.roster)) != len(self.roster):
            raise ValueError("Coverage roster identities must be unique.")
        if {b.character_id for b in self.batches} != set(self.roster):
            raise ValueError("Every roster identity needs an explicit evaluated slice.")
        if len({b.batch_id for b in self.batches}) != len(self.batches):
            raise ValueError("Coverage batch identifiers must be unique.")
        splits: dict[str, str] = {}
        for batch in self.batches:
            if batch.batch_id == "identity":
                raise ValueError("The identity filename is reserved for run provenance.")
            for group in batch.story_groups:
                if group in splits and splits[group] != batch.split:
                    raise ValueError("A shared story/duplicate group cannot cross a split.")
                splits[group] = batch.split
        return self


class CoverageRun:
    def __init__(
        self,
        profile: OpenRouterProfile,
        key: str,
        client: httpx.Client,
        *,
        budget: Budget,
        tracking: MlflowClient,
    ) -> None:
        self._profile = profile
        self._extraction = ClaimExtractionRun(
            profile, key, client, budget=budget, tracking=tracking
        )

    def run(self, plan_path: Path, output: Path, *, max_batches: int = 1) -> dict[str, Any]:
        if not 1 <= max_batches <= 100:
            raise ValueError("Choose between 1 and 100 new batch attempts per invocation.")
        plan_bytes = plan_path.read_bytes()
        plan = CoveragePlan.model_validate_json(plan_bytes)
        frozen: dict[str, bytes] = {}
        for batch in plan.batches:
            for name, input_name, digest in (
                ("snapshot", batch.snapshot, batch.snapshot_file_sha256),
                ("reference", batch.reference, batch.reference_sha256),
            ):
                contents = (plan_path.parent / input_name).read_bytes()
                if hashlib.sha256(contents).hexdigest() != digest:
                    raise ValueError(f"Changed coverage {name} for {batch.batch_id}.")
                frozen[f"{batch.batch_id}-{name}.json"] = contents
        identity = {
            "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
            "application_sha256": application_fingerprint(),
            "profile": self._profile.model_dump(mode="json"),
        }
        output.mkdir(parents=True, exist_ok=True)
        with (output / ".lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            identity_path = output / "identity.json"
            if identity_path.exists():
                if json.loads(identity_path.read_bytes()) != identity:
                    raise ValueError("Coverage resume requires unchanged inputs, code and model.")
            else:
                with identity_path.open("x") as destination:
                    destination.write(json.dumps(identity, indent=2) + "\n")
            inputs = output / "inputs"
            inputs.mkdir(exist_ok=True)
            for name, contents in frozen.items():
                path = inputs / name
                if path.exists():
                    if path.read_bytes() != contents:
                        raise ValueError("Retained extraction input changed.")
                else:
                    with path.open("xb") as destination:
                        destination.write(contents)
            # Validate every batch before starting any paid work.
            for batch in plan.batches:
                validate_extraction_inputs(
                    inputs / f"{batch.batch_id}-snapshot.json",
                    inputs / f"{batch.batch_id}-reference.json",
                    relationships=batch.kind == "relationships",
                    events=batch.kind == "events",
                )
            attempted = 0
            rows = []
            for batch in plan.batches:
                result_path = output / f"{batch.batch_id}.json"
                if not result_path.exists() and attempted < max_batches:
                    self._extraction.run(
                        inputs / f"{batch.batch_id}-snapshot.json",
                        inputs / f"{batch.batch_id}-reference.json",
                        result_path,
                        relationships=batch.kind == "relationships",
                        events=batch.kind == "events",
                    )
                    attempted += 1
                row: dict[str, Any] = {
                    "batch_id": batch.batch_id,
                    "character_id": batch.character_id,
                    "kind": batch.kind,
                    "state": "pending",
                    "gaps": batch.gaps,
                }
                if result_path.exists():
                    result = json.loads(result_path.read_bytes())
                    if (
                        result["snapshot_file_sha256"] != batch.snapshot_file_sha256
                        or result["reference_sha256"] != batch.reference_sha256
                        or result["application_sha256"] != identity["application_sha256"]
                        or result["profile"] != identity["profile"]
                    ):
                        raise ValueError("Retained extraction differs from the frozen run.")
                    row.update(
                        state=result["state"],
                        failure=result["failure"],
                        score=result["score"],
                        usage=result["usage"],
                        result_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest(),
                    )
                rows.append(row)
            return {
                **identity,
                "state": "complete"
                if all(r["state"] == "complete" for r in rows)
                else "incomplete",
                "batches": rows,
                "limitation": "Scores cover only fully annotated selected spans and identities. "
                "Failed or interrupted attempts are retained and never retried automatically. "
                "No corpus-wide recall or independent canon acceptance is established.",
            }


@dataclass(frozen=True)
class _CoverageSlice:
    batch: CoverageBatch
    source: SourceSnapshot
    reference: dict[str, Any]
    result: dict[str, Any]
    result_sha256: str


@dataclass(frozen=True)
class _CoverageInputs:
    snapshot: SourceSnapshot
    plan: CoveragePlan
    origins: dict[str, str]
    slices: tuple[_CoverageSlice, ...]


class CoverageEvidence:
    """Compose and inspect one frozen run without exposing its artifact protocol.

    Each operation reads and binds its inputs afresh. Review decisions bind raw
    Claim content; extraction scores never establish a support verdict.
    """

    def __init__(self, snapshot_path: Path, plan_path: Path, captures: Path) -> None:
        self._snapshot_path = snapshot_path
        self._plan_path = plan_path
        self._captures = captures

    def _inputs(self) -> _CoverageInputs:
        snapshot = SourceSnapshot.model_validate_json(self._snapshot_path.read_bytes())
        if snapshot.imported is None:
            raise ValueError("Coverage requires a captured source import.")
        plan_bytes = self._plan_path.read_bytes()
        plan = CoveragePlan.model_validate_json(plan_bytes)
        origins = {"plan": hashlib.sha256(plan_bytes).hexdigest()}
        slices = []
        for batch in plan.batches:
            reference_bytes = (self._plan_path.parent / batch.reference).read_bytes()
            source_bytes = (self._plan_path.parent / batch.snapshot).read_bytes()
            if hashlib.sha256(reference_bytes).hexdigest() != batch.reference_sha256 or (
                hashlib.sha256(source_bytes).hexdigest() != batch.snapshot_file_sha256
            ):
                raise ValueError("A frozen coverage reference or source changed.")
            reference = json.loads(reference_bytes)
            if reference["origin_snapshot_sha256"] != snapshot.fingerprint:
                raise ValueError("Coverage references belong to another full snapshot.")
            candidate_bytes = (self._captures / f"{batch.batch_id}.json").read_bytes()
            candidate = json.loads(candidate_bytes)
            if candidate["reference_sha256"] != batch.reference_sha256 or (
                candidate["snapshot_file_sha256"] != batch.snapshot_file_sha256
            ):
                raise ValueError("Retained extraction has different inputs.")
            origins[batch.batch_id] = hashlib.sha256(candidate_bytes).hexdigest()
            slices.append(
                _CoverageSlice(
                    batch=batch,
                    source=SourceSnapshot.model_validate_json(source_bytes),
                    reference=reference,
                    result=candidate,
                    result_sha256=origins[batch.batch_id],
                )
            )
        return _CoverageInputs(snapshot, plan, origins, tuple(slices))

    def assemble(
        self,
        decisions_path: Path,
        output: Path,
        *,
        reference_reviews_path: Path | None = None,
    ) -> None:
        """Bind explicit reviews, admit typed Claims and retain the immutable bundle."""
        inputs = self._inputs()
        snapshot = inputs.snapshot
        assert snapshot.imported is not None
        decisions = json.loads(decisions_path.read_bytes())
        claims: dict[str, list[dict[str, Any]]] = {
            "family_claims": [],
            "relationship_claims": [],
            "event_claims": [],
            "context_claims": [],
        }
        reviews: dict[str, list[dict[str, Any]]] = {"family": [], "relationship": [], "event": []}
        reference_ids: dict[str, set[str]] = {family: set() for family in reviews}
        origins = {"plan": inputs.origins["plan"]}
        reference_reviews = {}
        if reference_reviews_path is not None:
            contents = reference_reviews_path.read_bytes()
            reference_reviews = json.loads(contents)
            if not set(reference_reviews) <= reviews.keys():
                raise ValueError("Reference reviews must identify existing projection families.")
            origins["reference-review-input"] = hashlib.sha256(contents).hexdigest()
        translations = []
        consumed = set()
        for selected in inputs.slices:
            batch = selected.batch
            family = {"family": "family", "relationships": "relationship", "events": "event"}[
                batch.kind
            ]
            reference = selected.reference
            review_cls = EventReview if family == "event" else ClaimReview
            candidate = selected.result
            origins[batch.batch_id] = selected.result_sha256
            raw = candidate.get("batch") or {"claims": [], "context_claims": []}
            candidates = [*raw["claims"], *raw.get("context_claims", [])]
            names = {
                c["claim_id"]: f"raw-{batch.batch_id}-{i + 1}" for i, c in enumerate(candidates)
            }
            for field, expected in (
                (f"{family}_claims", reference["expected_claims"]),
                ("context_claims", reference.get("expected_context_claims", [])),
            ):
                claims[field].extend(expected)
            for raw_claim in candidates:
                origin_id = f"{batch.batch_id}/{raw_claim['claim_id']}"
                claim = {**raw_claim, "claim_id": names[raw_claim["claim_id"]]}
                if claim.get("after_claim_id"):
                    claim["after_claim_id"] = names.get(
                        claim["after_claim_id"], claim["after_claim_id"]
                    )
                field = "context_claims" if "kind" in claim else f"{family}_claims"
                claims[field].append(claim)
                translations.append(
                    {
                        "origin": origin_id,
                        "claim_id": claim["claim_id"],
                        "raw_document_sha256": origins[batch.batch_id],
                    }
                )
                if origin_id not in decisions:
                    raise ValueError(f"Every raw candidate requires a recorded review: {origin_id}")
                decision = dict(decisions[origin_id])
                original: ParentageClaim | RelationshipClaim | EventClaim | ContextClaim
                original = TypeAdapter(
                    ParentageClaim | RelationshipClaim | EventClaim | ContextClaim
                ).validate_python(raw_claim)
                if decision.pop("raw_claim_sha256", None) != original.fingerprint:
                    raise ValueError(f"The reviewed candidate changed: {origin_id}")
                consumed.add(origin_id)
                # Claim fingerprints are filled after full schema validation below.
                reviews[family].append(
                    {
                        **decision,
                        "claim_id": claim["claim_id"],
                        "claim_sha256": "0" * 64,
                    }
                )
            for claim in [
                *reference["expected_claims"],
                *reference.get("expected_context_claims", []),
            ]:
                reference_ids[family].add(claim["claim_id"])
                reviews[family].append(
                    review_cls(
                        claim_id=claim["claim_id"],
                        claim_sha256="0" * 64,
                        verdict="supported",
                        reviewer=reference["reviewer"],
                        note=reference["review_note"],
                        **(
                            {"narrative_commission": claim.get("event_type") == "commission"}
                            if family == "event"
                            else {}
                        ),
                    ).model_dump(mode="json")
                )
        if consumed != set(decisions):
            raise ValueError("A raw review does not identify an actual retained candidate.")
        graph = ConnectionReference.model_validate(
            {
                "version": 1,
                "split": "exposed_development",
                "synthetic": False,
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_sha256": snapshot.fingerprint,
                "catalogue": snapshot.imported.catalogue,
                "origins": origins,
                **claims,
                "cases": [],
                "review_note": "Source-reviewed selected roster excerpts, "
                "preserving raw candidates. "
                "Missing history is unassessed, not false. No independent canon acceptance.",
            }
        )
        common: dict[str, Any] = dict(
            snapshot_id=snapshot.snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            catalogue=snapshot.imported.catalogue,
            extractor="reviewed-roster-composition",
        )
        family_batch = ClaimBatch(**common, claims=graph.family_claims)
        relationships = RelationshipBatch(**common, claims=graph.relationship_claims)
        events = EventBatch(
            **common, claims=graph.event_claims, context_claims=graph.context_claims
        )
        all_claims: tuple[ParentageClaim | RelationshipClaim | EventClaim | ContextClaim, ...] = (
            *graph.family_claims,
            *graph.relationship_claims,
            *graph.event_claims,
            *graph.context_claims,
        )
        fingerprints = {c.claim_id: c.fingerprint for c in all_claims}
        for family in reviews:
            for review in reviews[family]:
                review["claim_sha256"] = fingerprints[review["claim_id"]]
            positions = {review["claim_id"]: i for i, review in enumerate(reviews[family])}
            changed = set()
            for review in reference_reviews.get(family, []):
                typed_review = (EventReview if family == "event" else ClaimReview).model_validate(
                    review
                )
                identifier = typed_review.claim_id
                if (
                    identifier not in reference_ids[family]
                    or identifier in changed
                    or (typed_review.claim_sha256 != fingerprints[identifier])
                ):
                    raise ValueError(
                        "Reference reviews require unique, content-bound original Claims."
                    )
                changed.add(identifier)
                reviews[family][positions[identifier]] = typed_review.model_dump(mode="json")
        family_reviews = TypeAdapter(tuple[ClaimReview, ...]).validate_python(reviews["family"])
        relationship_reviews = TypeAdapter(tuple[ClaimReview, ...]).validate_python(
            reviews["relationship"]
        )
        event_reviews = TypeAdapter(tuple[EventReview, ...]).validate_python(reviews["event"])
        admissions = {
            "family": admit_claims(snapshot, family_batch, family_reviews).model_dump(mode="json"),
            "relationship": admit_relationships(
                snapshot, relationships, relationship_reviews
            ).model_dump(mode="json"),
            "event": admit_events(snapshot, events, event_reviews).model_dump(mode="json"),
        }
        documents = {
            name: (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode()
            for name, document in {
                "reviews": reviews,
                "admissions": admissions,
                "origins": translations,
            }.items()
        }
        graph = graph.model_copy(
            update={
                "origins": {
                    **graph.origins,
                    **{
                        f"artifact/{name}": hashlib.sha256(contents).hexdigest()
                        for name, contents in documents.items()
                    },
                }
            }
        )
        documents["claims"] = (graph.model_dump_json(indent=2) + "\n").encode()
        output.mkdir(parents=True, exist_ok=True)
        for name, contents in documents.items():
            with (output / f"{name}.json").open("xb") as destination:
                destination.write(contents)

    def report(self, graph_path: Path) -> dict[str, Any]:
        """Derive an inventory only from artifacts bound to this run's frozen evidence."""
        inputs = self._inputs()
        snapshot, plan = inputs.snapshot, inputs.plan
        assert snapshot.imported is not None
        graph = ConnectionReference.model_validate_json((graph_path / "claims.json").read_bytes())
        if (
            graph.snapshot_sha256 != snapshot.fingerprint
            or graph.origins["plan"] != inputs.origins["plan"]
        ):
            raise ValueError("Coverage report inputs belong to different revisions.")
        artifacts = {}
        for name in ("admissions", "reviews", "origins"):
            contents = (graph_path / f"{name}.json").read_bytes()
            if hashlib.sha256(contents).hexdigest() != graph.origins[f"artifact/{name}"]:
                raise ValueError("A frozen graph admission/review artifact changed.")
            artifacts[name] = json.loads(contents)
        admissions = artifacts["admissions"]
        decisions = {
            row["claim_id"]: row
            for audit in admissions.values()
            for row in [*audit["decisions"], *audit.get("text_decisions", [])]
        }
        rows = []
        groups: dict[str, list[str]] = {}
        for character in snapshot.imported.report().characters:
            identifier = character.character.character_id
            if identifier not in plan.roster:
                continue
            batches = [s for s in inputs.slices if s.batch.character_id == identifier]
            measured = []
            selected_passages = {}
            for selected in batches:
                batch = selected.batch
                if selected.result_sha256 != graph.origins[batch.batch_id]:
                    raise ValueError("An extraction changed after graph review.")
                result, reference = selected.result, selected.reference
                selected_passages.update({p.evidence_id: p for p in selected.source.passages})
                ids = [
                    c["claim_id"]
                    for c in [
                        *reference["expected_claims"],
                        *reference.get("expected_context_claims", []),
                    ]
                ]
                measured.append(
                    {
                        "batch_id": batch.batch_id,
                        "kind": batch.kind,
                        "state": result["state"],
                        "failure": result["failure"],
                        "extraction_score": result["score"],
                        "reviewed_reference_decisions": [decisions[cid] for cid in ids],
                        "raw_candidate_decisions": [
                            decisions[origin["claim_id"]]
                            for origin in artifacts["origins"]
                            if origin["origin"].split("/", 1)[0] == batch.batch_id
                        ],
                        "reference_sha256": batch.reference_sha256,
                        "result_sha256": graph.origins[batch.batch_id],
                        "review_note": batch.review_note,
                        "split": batch.split,
                        "story_groups": batch.story_groups,
                    }
                )
                for group in batch.story_groups:
                    groups.setdefault(group, []).append(batch.batch_id)
            source_passages = [
                p
                for p in snapshot.passages
                if p.location
                and p.location.source_id in character.character.evidence_sources
                and not p.evidence_id.startswith("coverage-")
            ]
            rows.append(
                {
                    "character_id": identifier,
                    "source_text": character.model_dump(mode="json"),
                    "source_passages": len(source_passages),
                    "source_characters": sum(len(p.text) for p in source_passages),
                    "selected_characters": sum(len(p.text) for p in selected_passages.values()),
                    "extraction": measured,
                    "known_gaps": list(dict.fromkeys(g for s in batches for g in s.batch.gaps)),
                }
            )
        return {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_sha256": snapshot.fingerprint,
            "plan_sha256": graph.origins["plan"],
            "profiles": rows,
            "story_groups": groups,
            "exact_duplicate_paragraphs": [
                group.model_dump(mode="json")
                for group in snapshot.imported.report().duplicate_paragraphs
            ],
            "admissions": admissions,
            "limitation": "Per-batch value and grounding scores cover fully annotated selected "
            "excerpts only. Other captured text remains available and unassessed for extraction. "
            "Curated graph capability is separate from original extraction quality. All cases "
            "are exposed development, without human adjudication or independent corroboration.",
        }
