"""Source reconstruction, reviewed corrections and public graph answers use real storage."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from mlflow import MlflowClient

from ask_phil.connection_graph import ConnectionQuery
from ask_phil.coverage import CoveragePlan
from ask_phil.family_graph import FamilyQuery
from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase
from ask_phil.parentage import ClaimBatch


@pytest.mark.parametrize("change", [None, "candidate", "reference", "admission"])
def test_a_roster_locator_correction_is_bound_to_the_retained_candidate(
    database_url: str, tmp_path: Path, change: str | None
) -> None:
    inputs = tmp_path / "inputs"
    snapshot = tmp_path / "snapshot.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/prepare_coverage.py",
            "--annotations",
            "data/references/core-graph-v1.json",
            "--output",
            str(inputs),
            "--snapshot",
            str(snapshot),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    all_batches = CoveragePlan.model_validate_json((inputs / "plan.json").read_bytes())
    selected = next(b for b in all_batches.batches if b.batch_id == "peggy-mitchell")
    plan = CoveragePlan(version=1, roster=("peggy-mitchell",), batches=(selected,))
    plan_path = inputs / "selected.json"
    plan_path.write_text(plan.model_dump_json())
    reference = json.loads((inputs / selected.reference).read_bytes())
    bad = reference["expected_claims"][0]
    bad["claim_id"] = "peggy-locator-error"
    bad["evidence"][0]["end"] -= 1
    candidate = ClaimBatch.model_validate(
        {
            "snapshot_id": "peggy-mitchell-coverage-v1",
            "snapshot_sha256": reference["snapshot_sha256"],
            "catalogue": reference["catalogue"],
            "extractor": "synthetic locator regression",
            "claims": [bad],
        }
    )
    captures = tmp_path / "captures"
    captures.mkdir()
    raw_path = captures / "peggy-mitchell.json"
    raw_path.write_text(
        json.dumps(
            {
                "snapshot_file_sha256": selected.snapshot_file_sha256,
                "reference_sha256": selected.reference_sha256,
                "state": "complete",
                "failure": None,
                "score": None,
                "batch": candidate.model_dump(mode="json"),
            }
        )
    )
    original = raw_path.read_bytes()
    decisions = tmp_path / "decisions.json"
    decisions.write_text(
        json.dumps(
            {
                "peggy-mitchell/peggy-locator-error": {
                    "raw_claim_sha256": candidate.claims[0].fingerprint,
                    "verdict": "superseded",
                    "superseded_by": ["ref-peggy-mitchell-1"],
                    "reviewer": "Synthetic regression fixture",
                    "note": "Original end offset omits the final character. "
                    "Reference keeps the exact quote.",
                }
            }
        )
    )
    graph = tmp_path / "graph"
    if change == "candidate":
        changed = json.loads(raw_path.read_bytes())
        changed["batch"]["claims"][0]["parent_id"] = "ben-mitchell"
        raw_path.write_text(json.dumps(changed))
    compilation = subprocess.run(
        [
            sys.executable,
            "scripts/assemble_coverage.py",
            "--snapshot",
            str(snapshot),
            "--plan",
            str(plan_path),
            "--captures",
            str(captures),
            "--decisions",
            str(decisions),
            "--output",
            str(graph),
        ],
        capture_output=True,
        timeout=60,
    )
    if change == "candidate":
        assert compilation.returncode != 0
        assert b"reviewed candidate changed" in compilation.stderr
        assert not graph.exists()
        return
    assert compilation.returncode == 0, compilation.stderr.decode()
    if change == "reference":
        changed = json.loads((inputs / selected.reference).read_bytes())
        changed["expected_claims"] = []
        (inputs / selected.reference).write_text(json.dumps(changed))
    if change == "admission":
        changed = json.loads((graph / "admissions.json").read_bytes())
        changed["family"]["decisions"][0]["status"] = "held"
        (graph / "admissions.json").write_text(json.dumps(changed))
    inventory_path = tmp_path / "inventory.json"
    reporting = subprocess.run(
        [
            sys.executable,
            "scripts/report_coverage.py",
            "--snapshot",
            str(snapshot),
            "--plan",
            str(plan_path),
            "--captures",
            str(captures),
            "--graph",
            str(graph),
            "--output",
            str(inventory_path),
        ],
        capture_output=True,
        timeout=60,
    )
    if change in {"reference", "admission"}:
        assert reporting.returncode != 0
        assert not inventory_path.exists()
        return
    assert reporting.returncode == 0, reporting.stderr.decode()
    inventory = json.loads(inventory_path.read_bytes())
    assert inventory["profiles"][0]["character_id"] == "peggy-mitchell"
    held = inventory["profiles"][0]["extraction"][0]["raw_candidate_decisions"]
    assert held == [
        {
            "claim_id": "raw-peggy-mitchell-1",
            "status": "held",
            "reasons": ["evidence_span", "superseded"],
        }
    ]
    assert raw_path.read_bytes() == original
    tracking = MlflowClient(tracking_uri=f"sqlite:///{tmp_path / 'mlflow.db'}")
    runtime = GraphAcceptanceRun(database_url, tracking=tracking).run(
        tmp_path / "runtime.json",
        (
            GraphPhase(
                "corrected",
                "connections",
                snapshot,
                graph / "claims.json",
                graph / "reviews.json",
                (
                    GraphCase(
                        "peggy",
                        "Which biological child of Peggy is supported?",
                        FamilyQuery(
                            character_id="peggy-mitchell", direction="descendants", max_depth=1
                        ),
                        transport="cli",
                    ),
                ),
                typed_query=ConnectionQuery(
                    kind="connection", character_id="peggy-mitchell", target_id="phil-mitchell"
                ),
            ),
        ),
    )
    response = runtime["responses"][0]
    assert response["trace_output_matches"] and response["citations_resolve"]
    paths = response["response"]["graph"]["paths"]
    assert [p["characters"] for p in paths] == [["peggy-mitchell", "phil-mitchell"]]
    assert paths[0]["edges"][0]["claim_ids"] == ["ref-peggy-mitchell-1"]
