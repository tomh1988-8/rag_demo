"""Inspect measured extraction and admitted capabilities beside unassessed profile history."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from ask_phil.connection_evaluation import ConnectionReference
from ask_phil.coverage import CoveragePlan
from ask_phil.evidence import SourceSnapshot


def report(
    snapshot_path: Path, plan_path: Path, captures: Path, graph_path: Path
) -> dict[str, Any]:
    snapshot = SourceSnapshot.model_validate_json(snapshot_path.read_bytes())
    assert snapshot.imported is not None
    plan = CoveragePlan.model_validate_json(plan_path.read_bytes())
    graph = ConnectionReference.model_validate_json((graph_path / "claims.json").read_bytes())
    if (
        graph.snapshot_sha256 != snapshot.fingerprint
        or graph.origins["plan"] != hashlib.sha256(plan_path.read_bytes()).hexdigest()
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
        batches = [b for b in plan.batches if b.character_id == identifier]
        measured = []
        selected_passages = {}
        for batch in batches:
            raw_bytes = (captures / f"{batch.batch_id}.json").read_bytes()
            if hashlib.sha256(raw_bytes).hexdigest() != graph.origins[batch.batch_id]:
                raise ValueError("An extraction changed after graph review.")
            result = json.loads(raw_bytes)
            reference_bytes = (plan_path.parent / batch.reference).read_bytes()
            source_bytes = (plan_path.parent / batch.snapshot).read_bytes()
            if hashlib.sha256(reference_bytes).hexdigest() != batch.reference_sha256 or (
                hashlib.sha256(source_bytes).hexdigest() != batch.snapshot_file_sha256
            ):
                raise ValueError("A frozen coverage reference or source changed.")
            reference = json.loads(reference_bytes)
            scoped = SourceSnapshot.model_validate_json(source_bytes)
            selected_passages.update({p.evidence_id: p for p in scoped.passages})
            if result["reference_sha256"] != batch.reference_sha256:
                raise ValueError("Extraction reference differs from the reviewed plan.")
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
                "known_gaps": list(dict.fromkeys(g for b in batches for g in b.gaps)),
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = report(args.snapshot, args.plan, args.captures, args.graph)
    with args.output.open("x") as destination:
        destination.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"profiles": len(result["profiles"])}))


if __name__ == "__main__":
    main()
