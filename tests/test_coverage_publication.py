"""Source reconstruction, reviewed corrections and public graph answers use real storage."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from mlflow import MlflowClient

from ask_phil.connection_graph import ConnectionQuery
from ask_phil.coverage import CoverageEvidence, CoveragePlan
from ask_phil.family_graph import FamilyQuery
from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase
from ask_phil.parentage import ClaimBatch
from ask_phil.relationships import RelationshipClaim


def _locator_correction(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
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
    return snapshot, plan_path, captures, decisions


def test_a_roster_locator_correction_is_bound_to_the_retained_candidate(
    database_url: str, tmp_path: Path
) -> None:
    snapshot, plan_path, captures, decisions = _locator_correction(tmp_path)
    raw_path = captures / "peggy-mitchell.json"
    original = raw_path.read_bytes()
    graph = tmp_path / "graph"
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
    assert compilation.returncode == 0, compilation.stderr.decode()
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


def test_same_marriage_accounts_can_be_explicitly_consolidated_without_rewriting_references(
    tmp_path: Path,
) -> None:
    inputs, snapshot = tmp_path / "inputs", tmp_path / "snapshot.json"
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
    original = CoveragePlan.model_validate_json((inputs / "plan.json").read_bytes())
    batches = tuple(b for b in original.batches if b.batch_id in {"martin-fowler", "stacey-slater"})
    plan = original.model_copy(
        update={"roster": ("martin-fowler", "stacey-slater"), "batches": batches}
    )
    plan_path = inputs / "selected.json"
    plan_path.write_text(plan.model_dump_json())
    captures = tmp_path / "captures"
    captures.mkdir()
    frozen = {}
    for batch in batches:
        frozen[batch.reference] = (inputs / batch.reference).read_bytes()
        (captures / f"{batch.batch_id}.json").write_text(
            json.dumps(
                {
                    "snapshot_file_sha256": batch.snapshot_file_sha256,
                    "reference_sha256": batch.reference_sha256,
                    "batch": None,
                }
            )
        )
    stacey = RelationshipClaim.model_validate(
        json.loads((inputs / "stacey-slater-reference.json").read_bytes())["expected_claims"][0]
    )
    reviews = tmp_path / "reference-reviews.json"
    reviews.write_text(
        json.dumps(
            {
                "relationship": [
                    {
                        "claim_id": stacey.claim_id,
                        "claim_sha256": stacey.fingerprint,
                        "verdict": "superseded",
                        "superseded_by": ["ref-martin-fowler-1"],
                        "reviewer": "Synthetic orchestration regression with source-based claims",
                        "note": "Same marriage. Preserve the relative account in the audit; "
                        "use the "
                        "less-specific unknown-date assertion as the current shared episode.",
                    }
                ]
            }
        )
    )
    decisions = tmp_path / "decisions.json"
    decisions.write_text("{}")
    graph = tmp_path / "graph"
    CoverageEvidence(snapshot, plan_path, captures).assemble(
        decisions, graph, reference_reviews_path=reviews
    )
    admission = json.loads((graph / "admissions.json").read_bytes())["relationship"]
    assert {d["claim_id"]: (d["status"], d["reasons"]) for d in admission["decisions"]} == {
        "ref-martin-fowler-1": ("admitted", []),
        "ref-stacey-slater-1": ("held", ["superseded"]),
    }
    assert all((inputs / name).read_bytes() == contents for name, contents in frozen.items())


@pytest.mark.parametrize(
    "change",
    ["candidate", "reference", "source", "capture", "reviews", "admissions", "origins", "plan"],
)
def test_coverage_evidence_rejects_changed_reviews_and_artifacts(
    tmp_path: Path, change: str
) -> None:
    snapshot, plan_path, captures, decisions = _locator_correction(tmp_path)
    coverage = CoverageEvidence(snapshot, plan_path, captures)
    raw_path = captures / "peggy-mitchell.json"
    graph = tmp_path / "graph"
    if change == "candidate":
        changed = json.loads(raw_path.read_bytes())
        changed["batch"]["claims"][0]["parent_id"] = "ben-mitchell"
        raw_path.write_text(json.dumps(changed))
        with pytest.raises(ValueError, match="reviewed candidate changed"):
            coverage.assemble(decisions, graph)
        assert not graph.exists()
        return
    coverage.assemble(decisions, graph)
    selected = CoveragePlan.model_validate_json(plan_path.read_bytes()).batches[0]
    changed_path = {
        "reference": plan_path.parent / selected.reference,
        "source": plan_path.parent / selected.snapshot,
        "capture": raw_path,
        "reviews": graph / "reviews.json",
        "admissions": graph / "admissions.json",
        "origins": graph / "origins.json",
        "plan": plan_path,
    }[change]
    changed_path.write_bytes(changed_path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        coverage.report(graph)


def test_reviewed_coverage_replays_retained_claims_and_inventory(tmp_path: Path) -> None:
    snapshot, plan_path, _, _ = _locator_correction(tmp_path)
    retained = Path("docs/implementation/issue-20")
    coverage = CoverageEvidence(snapshot, plan_path.parent / "plan.json", retained / "extraction")
    graph = tmp_path / "graph"
    coverage.assemble(
        retained / "raw-reviews.json",
        graph,
        reference_reviews_path=retained / "reference-reviews.json",
    )
    expected = {
        name: (retained / "graph" / f"{name}.json").read_bytes()
        for name in ("claims", "reviews", "admissions", "origins")
    }
    assert {name: (graph / f"{name}.json").read_bytes() for name in expected} == expected
    assert json.loads(json.dumps(coverage.report(graph))) == json.loads(
        (retained / "coverage.json").read_bytes()
    )
    with pytest.raises(FileExistsError):
        coverage.assemble(
            retained / "raw-reviews.json",
            graph,
            reference_reviews_path=retained / "reference-reviews.json",
        )
    assert {name: (graph / f"{name}.json").read_bytes() for name in expected} == expected


def test_changed_coverage_source_is_rejected_before_reviewed_composition(tmp_path: Path) -> None:
    snapshot, plan_path, captures, decisions = _locator_correction(tmp_path)
    batch = CoveragePlan.model_validate_json(plan_path.read_bytes()).batches[0]
    source = plan_path.parent / batch.snapshot
    source.write_bytes(source.read_bytes() + b"\n")
    graph = tmp_path / "graph"
    result = subprocess.run(
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
    assert result.returncode != 0, "Composition accepted changed frozen source bytes."
    assert not graph.exists()
