"""A frozen comparison plan owns completeness across its captured arms."""

import gzip
import hashlib
import json
import os
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from ask_phil.evaluation import CapturedAnswers, QualityReview, ScoredReview, document_fingerprint
from ask_phil.evidence import Identifier


@dataclass(frozen=True)
class ComparedAnswers:
    """Disjoint capture chunks reviewed as one planned arm."""

    selected: tuple[str, ...]
    captures: tuple[CapturedAnswers, ...]

    @property
    def cases(self) -> dict[str, dict[str, Any]]:
        rows = {key: row for capture in self.captures for key, row in capture.cases.items()}
        return {key: deepcopy(rows[key]) for key in self.selected}

    def score(self, reviews: Sequence[QualityReview]) -> dict[str, ScoredReview]:
        if len(reviews) != len(self.selected) or {r.case_id for r in reviews} != set(self.selected):
            raise ValueError("Review every planned response exactly once.")
        return {
            key: result
            for capture in self.captures
            for key, result in capture.score(
                [r for r in reviews if r.case_id in capture.cases]
            ).items()
        }


class ComparisonPlan:
    def __init__(self, references: Path, arms: Mapping[str, Sequence[str]]) -> None:
        raw = references.read_bytes()
        document = json.loads(raw)
        cases = {row["case_id"] for row in document["cases"]}
        if len(cases) != len(document["cases"]):
            raise ValueError("Duplicate frozen comparison case identifiers.")
        identifier = TypeAdapter(Identifier)
        if not arms or any(
            not selected or len(set(selected)) != len(selected) or not set(selected) <= cases
            for selected in arms.values()
        ):
            raise ValueError("Select nonempty comparison arms with unique frozen cases.")
        for name in arms:
            identifier.validate_python(name)
        self.references = references
        self._arms = {name: tuple(selected) for name, selected in arms.items()}
        self._reference_sha256 = hashlib.sha256(raw).hexdigest()

    @property
    def arms(self) -> dict[str, tuple[str, ...]]:
        return dict(self._arms)

    @property
    def document(self) -> dict[str, Any]:
        return {
            "version": "comparison-plan-v1",
            "reference_file_sha256": self._reference_sha256,
            "arms": {name: list(selected) for name, selected in self._arms.items()},
        }

    @property
    def fingerprint(self) -> str:
        return document_fingerprint(self.document)

    @contextmanager
    def record(self, directory: Path, *, prior: Sequence[Path] = ()) -> Iterator[None]:
        """Freeze the whole plan before execution and retain progress even on a stop."""
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "comparison-plan.json").open("x") as destination:
            json.dump(self.document, destination, indent=2)
            destination.write("\n")
        initial = self.inspect(directory, *prior)
        frozen = {r["path"]: r["sha256"] for r in initial["source_captures"]}
        if prior:
            with (directory / "comparison-continuation.json").open("x") as destination:
                json.dump(
                    {
                        "version": "comparison-continuation-v1",
                        "plan_sha256": self.fingerprint,
                        "source_captures": initial["source_captures"],
                        "prior_directories": [
                            p
                            for p in initial["capture_directories"]
                            if p != str(directory.resolve())
                        ],
                    },
                    destination,
                    indent=2,
                )
                destination.write("\n")
        try:
            self._require_safe_continuation(initial)
        except ValueError:
            self._save_progress(directory, {**initial, "phase_state": "blocked"})
            raise
        self._save_progress(directory, {**initial, "phase_state": "running"})
        try:
            yield
        finally:
            if any(
                hashlib.sha256(Path(p).read_bytes()).hexdigest() != sha for p, sha in frozen.items()
            ):
                raise ValueError("Prior comparison captures changed during continuation.")
            final = self._read((directory, *prior), closing=directory)[0]
            self._save_progress(directory, {**final, "phase_state": "closed"})

    def inspect(self, directory: Path, *prior: Path) -> dict[str, Any]:
        """Describe every expected observation, including absent and failed work."""
        return self._read((directory, *prior))[0]

    def pending(
        self, directory: Path, *prior: Path, arms: Sequence[str] | None = None
    ) -> dict[str, tuple[str, ...]]:
        """Select only never-attempted work; uncertain attempts require recovery."""
        selected = tuple(self._arms) if arms is None else tuple(arms)
        if (
            not selected
            or len(set(selected)) != len(selected)
            or not set(selected) <= self._arms.keys()
        ):
            raise ValueError("Select unique known comparison arms.")
        progress = self.inspect(directory, *prior)
        self._require_safe_continuation(progress)
        observations = progress["observations"]
        return {
            name: pending
            for name in selected
            if (
                pending := tuple(
                    r["case_id"]
                    for r in observations
                    if r["arm"] == name and r["state"] == "pending"
                )
            )
        }

    @staticmethod
    def _require_safe_continuation(progress: dict[str, Any]) -> None:
        if progress["active_directories"] or any(
            r["state"] in {"failed", "unverified"} for r in progress["observations"]
        ):
            raise ValueError("Recover prior comparison attempts before executing more work.")

    def captures(self, directory: Path, *prior: Path) -> dict[str, ComparedAnswers]:
        """Require the full plan, including arms absent from the directory."""
        progress, captures = self._read((directory, *prior))
        if progress["state"] != "complete":
            raise ValueError("Comparison is incomplete; inspect its planned observations.")
        return {
            name: ComparedAnswers(selected, tuple(captures[name]))
            for name, selected in self._arms.items()
        }

    def _read(
        self, directories: Sequence[Path], *, closing: Path | None = None
    ) -> tuple[dict[str, Any], dict[str, list[CapturedAnswers]]]:
        if hashlib.sha256(self.references.read_bytes()).hexdigest() != self._reference_sha256:
            raise ValueError("Frozen comparison references changed.")
        paths = [directory.resolve() for directory in directories]
        if len(set(paths)) != len(paths):
            raise ValueError("Duplicate comparison input directories.")
        frozen: dict[Path, str] = {}
        frozen_directories: set[Path] = set()
        active_directories: set[Path] = set()
        closing = closing.resolve() if closing else None
        for directory in paths:
            progress_path = directory / "comparison-progress.json"
            if progress_path.exists() and directory != closing:
                progress = json.loads(progress_path.read_bytes())
                if progress.get("plan_sha256") != self.fingerprint:
                    raise ValueError("Retained progress differs from the comparison plan.")
                if progress.get("phase_state") == "running":
                    active_directories.add(directory)
            lineage_path = directory / "comparison-continuation.json"
            if not lineage_path.exists():
                continue
            lineage = json.loads(lineage_path.read_bytes())
            if lineage.get("plan_sha256") != self.fingerprint:
                raise ValueError("Continuation differs from its frozen comparison plan.")
            for name in lineage["prior_directories"]:
                previous = Path(name).resolve()
                frozen_directories.add(previous)
                if previous not in paths:
                    paths.append(previous)
            for source in lineage["source_captures"]:
                path = Path(source["path"]).resolve()
                if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
                    raise ValueError("Prior comparison captures changed after continuation.")
                frozen[path] = source["sha256"]
                if path.parent not in paths:
                    paths.append(path.parent)
        observations: dict[tuple[str, str], dict[str, Any]] = {
            (name, case_id): {"arm": name, "case_id": case_id, "state": "pending"}
            for name, selected in self._arms.items()
            for case_id in selected
        }
        captures: dict[str, list[CapturedAnswers]] = {name: [] for name in self._arms}
        sources = []
        for directory in paths:
            metadata_names = {
                "comparison-plan.json",
                "comparison-progress.json",
                "software-inputs.json",
                "expense.json",
                "recovery.json",
                "comparison-continuation.json",
                "artifact-manifest.json",
            }
            if any(
                path.name not in metadata_names
                and path.name.removesuffix(".json") not in self._arms
                for path in directory.glob("*.json")
            ):
                raise ValueError("Unplanned comparison arm files are present.")
            plan_path = directory / "comparison-plan.json"
            if plan_path.exists() and json.loads(plan_path.read_bytes()) != self.document:
                raise ValueError("The retained comparison plan differs from the frozen plan.")
            for name, selected in self._arms.items():
                path = directory / f"{name}.json"
                if not path.exists():
                    path = path.with_suffix(".json.gz")
                    if not path.exists():
                        continue
                raw = path.read_bytes()
                fingerprint = hashlib.sha256(raw).hexdigest()
                if directory in frozen_directories and path not in frozen:
                    raise ValueError("Prior comparison capture set changed after continuation.")
                if path in frozen and fingerprint != frozen[path]:
                    raise ValueError("Prior comparison captures changed while reading.")
                decoded = gzip.decompress(raw) if path.suffix == ".gz" else raw
                document = json.loads(decoded)
                if document.get("state") in {"running", "finalizing"}:
                    active_directories.add(directory)
                sources.append(
                    {"path": str(path), "sha256": fingerprint, "state": document.get("state")}
                )
                if document.get("reference_file_sha256") != self._reference_sha256:
                    raise ValueError("Comparison capture differs from its frozen references.")
                if document.get("comparison_plan_sha256", self.fingerprint) != self.fingerprint:
                    raise ValueError("Captured comparison plan identity differs.")
                if document.get("arm", document.get("mode", name)) != name:
                    raise ValueError("Captured comparison arm identity differs from the plan.")
                rows = {row["case_id"]: row for row in document["cases"]}
                if len(rows) != len(document["cases"]) or not rows.keys() <= set(selected):
                    raise ValueError("Duplicate or unplanned comparison observations.")
                capture = None
                if document.get("state") in {"complete", "failed"}:
                    read_capture = (
                        CapturedAnswers
                        if document["state"] == "complete"
                        else CapturedAnswers.retained
                    )
                    if path.suffix == ".gz":
                        with tempfile.NamedTemporaryFile(suffix=".json") as archive:
                            archive.write(decoded)
                            archive.flush()
                            capture = read_capture(Path(archive.name), self.references)
                    else:
                        capture = read_capture(path, self.references)
                    if capture and capture.fingerprint != hashlib.sha256(decoded).hexdigest():
                        raise ValueError("Comparison capture changed while reading.")
                    if capture:
                        captures[name].append(capture)
                for case_id, row in rows.items():
                    observation = observations[name, case_id]
                    if observation["state"] != "pending":
                        raise ValueError("Duplicate comparison observations across continuations.")
                    observation.update(
                        state="complete"
                        if capture and case_id in capture.cases
                        else "failed"
                        if document.get("state") == "failed"
                        else "unverified",
                        capture_path=str(path),
                        capture_sha256=fingerprint,
                        response_sha256=row.get("response_sha256"),
                    )
        return {
            "version": "comparison-progress-v1",
            "plan_sha256": self.fingerprint,
            "state": "complete"
            if not active_directories
            and all(r["state"] == "complete" for r in observations.values())
            else "incomplete",
            "observations": list(observations.values()),
            "source_captures": sources,
            "capture_directories": [str(p) for p in paths],
            "active_directories": [str(p) for p in sorted(active_directories)],
        }, captures

    def _save_progress(self, directory: Path, progress: dict[str, Any]) -> None:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as destination:
            temporary = Path(destination.name)
            try:
                json.dump(progress, destination, indent=2)
                destination.write("\n")
                destination.flush()
                os.fsync(destination.fileno())
                os.replace(temporary, directory / "comparison-progress.json")
            finally:
                temporary.unlink(missing_ok=True)
