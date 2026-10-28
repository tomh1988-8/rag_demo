"""Combine retained candidates and explicit reviews; never infer a support verdict from a score."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from ask_phil.claims import ClaimReview
from ask_phil.classified_facts import ContextClaim
from ask_phil.connection_evaluation import ConnectionReference
from ask_phil.coverage import CoveragePlan
from ask_phil.evidence import SourceSnapshot
from ask_phil.parentage import ClaimBatch, ParentageClaim, admit_claims
from ask_phil.relationships import RelationshipBatch, RelationshipClaim, admit_relationships
from ask_phil.story_events import EventBatch, EventClaim, EventReview, admit_events


def assemble(
    snapshot_path: Path, plan_path: Path, captures: Path, decisions_path: Path, output: Path
) -> None:
    snapshot = SourceSnapshot.model_validate_json(snapshot_path.read_bytes())
    assert snapshot.imported is not None
    plan = CoveragePlan.model_validate_json(plan_path.read_bytes())
    decisions = json.loads(decisions_path.read_bytes())
    claims: dict[str, list[dict[str, Any]]] = {
        "family_claims": [],
        "relationship_claims": [],
        "event_claims": [],
        "context_claims": [],
    }
    reviews: dict[str, list[dict[str, Any]]] = {"family": [], "relationship": [], "event": []}
    origins = {"plan": hashlib.sha256(plan_path.read_bytes()).hexdigest()}
    translations = []
    consumed = set()
    for batch in plan.batches:
        family = {"family": "family", "relationships": "relationship", "events": "event"}[
            batch.kind
        ]
        reference_bytes = (plan_path.parent / batch.reference).read_bytes()
        if hashlib.sha256(reference_bytes).hexdigest() != batch.reference_sha256:
            raise ValueError("The frozen reference changed.")
        reference = json.loads(reference_bytes)
        if reference["origin_snapshot_sha256"] != snapshot.fingerprint:
            raise ValueError("Coverage references belong to another full snapshot.")
        review_cls = EventReview if family == "event" else ClaimReview
        candidate_path = captures / f"{batch.batch_id}.json"
        candidate_bytes = candidate_path.read_bytes()
        candidate = json.loads(candidate_bytes)
        if candidate["reference_sha256"] != batch.reference_sha256 or (
            candidate["snapshot_file_sha256"] != batch.snapshot_file_sha256
        ):
            raise ValueError("Retained extraction has different inputs.")
        origins[batch.batch_id] = hashlib.sha256(candidate_bytes).hexdigest()
        raw = candidate.get("batch") or {"claims": [], "context_claims": []}
        candidates = [*raw["claims"], *raw.get("context_claims", [])]
        names = {c["claim_id"]: f"raw-{batch.batch_id}-{i + 1}" for i, c in enumerate(candidates)}
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
        for claim in [*reference["expected_claims"], *reference.get("expected_context_claims", [])]:
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
            "review_note": "Source-reviewed selected roster excerpts, preserving raw candidates. "
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
    events = EventBatch(**common, claims=graph.event_claims, context_claims=graph.context_claims)
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--captures", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assemble(args.snapshot, args.plan, args.captures, args.decisions, args.output)


if __name__ == "__main__":
    main()
