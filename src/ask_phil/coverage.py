"""Bounded, resumable extraction of reviewed coverage slices without replaying attempts."""

import fcntl
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, Self

import httpx
from mlflow import MlflowClient
from pydantic import Field, model_validator

from ask_phil.answering import application_fingerprint
from ask_phil.claim_extraction import ClaimExtractionRun, validate_extraction_inputs
from ask_phil.evidence import Fingerprint, Identifier, NonEmpty, Record
from ask_phil.openrouter import Budget, OpenRouterProfile


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
