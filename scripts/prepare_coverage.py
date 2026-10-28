"""Rebuild exact reviewed excerpts and a coherent full-corpus snapshot from retained sources."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ask_phil.claim_extraction import validate_extraction_inputs
from ask_phil.coverage import CoveragePlan
from ask_phil.evidence import Passage, SourceSnapshot
from ask_phil.identity import IdentityCatalogue
from ask_phil.ingestion import build_snapshot, read_batch


def retain(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != contents:
            raise ValueError(f"Refusing to replace retained input: {path}")
    else:
        with path.open("xb") as destination:
            destination.write(contents)


def encode(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def prepare(annotations: Path, output: Path, snapshot_path: Path) -> CoveragePlan:
    definition = json.loads(annotations.read_bytes())
    capture = Path(definition["capture"])
    if hashlib.sha256(capture.read_bytes()).hexdigest() != definition["capture_sha256"]:
        raise ValueError("The captured corpus changed; review a new annotation version.")
    original = build_snapshot(read_batch(capture), definition["snapshot_id"])
    assert original.imported is not None
    catalogue = original.imported.catalogue
    characters = {c.character_id: c for c in catalogue.characters}
    excerpts: dict[str, tuple[Passage, ...]] = {}
    for batch in definition["batches"]:
        selected = []
        for selection in batch["selections"]:
            document = next(
                d for d in original.imported.documents if d.source_id == selection["source_id"]
            )
            quote = selection["quote"]
            if document.text.count(quote) != 1:
                raise ValueError("An annotation must identify one exact retained source span.")
            start = document.text.index(quote)
            end = start + len(quote)
            parent = next(
                p
                for p in original.passages
                if p.location
                and p.location.source_id == document.source_id
                and p.start <= start < p.end
            )
            selected.append(
                Passage(
                    evidence_id=selection["evidence_id"],
                    text=quote,
                    sha256=hashlib.sha256(quote.encode()).hexdigest(),
                    start=start,
                    end=end,
                    source=parent.source,
                    location=parent.location,
                )
            )
        excerpts[batch["batch_id"]] = tuple(selected)
    # Validation rechecks document offsets, narrative scope, identities and capture metadata.
    snapshot = SourceSnapshot.model_validate(
        {
            **original.model_dump(),
            "passages": (*original.passages, *(p for rows in excerpts.values() for p in rows)),
        }
    )
    retain(snapshot_path, (snapshot.model_dump_json(indent=2) + "\n").encode())
    plan_rows = []
    for batch in definition["batches"]:
        identifier = batch["batch_id"]
        selected_catalogue = IdentityCatalogue(
            characters=tuple(characters[c] for c in batch["catalogue_ids"])
        )
        scoped = SourceSnapshot(
            snapshot_id=f"{identifier}-coverage-v1",
            fixture_version=1,
            source=snapshot.source,
            passages=excerpts[identifier],
        )
        source_bytes = (scoped.model_dump_json(indent=2) + "\n").encode()
        reference = {
            **batch["reference"],
            "snapshot_sha256": scoped.fingerprint,
            "catalogue": selected_catalogue.model_dump(mode="json"),
            "origin_snapshot_sha256": snapshot.fingerprint,
            "annotation_sha256": hashlib.sha256(annotations.read_bytes()).hexdigest(),
            "reviewer": definition["reviewer"],
            "review_note": batch["review_note"],
            "synthetic": False,
            "cross_source_checked": False,
            "split": "exposed_development",
            "story_groups": batch["story_groups"],
            "completeness": "All explicit in-catalogue assertions of the selected family "
            "within these excerpts; events are restricted to the declared incidents.",
        }
        reference_bytes = encode(reference)
        source_name, reference_name = f"{identifier}-source.json", f"{identifier}-reference.json"
        retain(output / source_name, source_bytes)
        retain(output / reference_name, reference_bytes)
        validate_extraction_inputs(
            output / source_name,
            output / reference_name,
            relationships=batch["kind"] == "relationships",
            events=batch["kind"] == "events",
        )
        plan_rows.append(
            {
                "batch_id": identifier,
                "character_id": batch["character_id"],
                "kind": batch["kind"],
                "snapshot": source_name,
                "snapshot_file_sha256": hashlib.sha256(source_bytes).hexdigest(),
                "reference": reference_name,
                "reference_sha256": hashlib.sha256(reference_bytes).hexdigest(),
                "split": "exposed_development",
                "story_groups": batch["story_groups"],
                "reference_complete": True,
                "review_note": batch["review_note"],
                "gaps": batch["gaps"],
            }
        )
    plan = CoveragePlan.model_validate(
        {
            "version": 1,
            "roster": [c.character_id for c in catalogue.characters if c.coverage == "core"],
            "batches": plan_rows,
        }
    )
    retain(output / "plan.json", (plan.model_dump_json(indent=2) + "\n").encode())
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    plan = prepare(args.annotations, args.output, args.snapshot)
    print(json.dumps({"batches": len(plan.batches), "profiles": len(plan.roster)}))


if __name__ == "__main__":
    main()
