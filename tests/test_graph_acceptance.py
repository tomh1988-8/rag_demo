"""Retained graph acceptance is observed through its run artifact and real application."""

import importlib.util
import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from mlflow import MlflowClient
from mlflow.entities import Trace

from ask_phil.family_graph import FamilyQuery


def test_composed_acceptance_records_all_four_public_graph_families(
    database_url: str, tmp_path: Path
) -> None:
    from ask_phil.connection_graph import ConnectionQuery
    from ask_phil.event_graph import EventQuery
    from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase
    from ask_phil.relationship_graph import RelationshipQuery

    cases = (
        GraphCase(
            "connection",
            "How are Peggy and Ben connected?",
            ConnectionQuery(
                kind="connection",
                character_id="peggy-mitchell",
                target_id="ben-mitchell",
                max_depth=2,
            ),
            transport="cli",
        ),
        GraphCase(
            "family",
            "Who are Ben's biological ancestors?",
            FamilyQuery(character_id="ben-mitchell", direction="ancestors"),
        ),
        GraphCase(
            "history",
            "How are Sharon and Den related?",
            RelationshipQuery(
                kind="relationship_history", character_id="sharon-watts", partner_id="den-watts"
            ),
        ),
        GraphCase(
            "event",
            "What were Max and Bobby's roles?",
            EventQuery(
                kind="crime_history", character_id="max-branning", participant_id="bobby-beale"
            ),
            transport="session",
        ),
    )
    phase = GraphPhase(
        name="composition",
        kind="connections",
        snapshot=Path("data/seed/connections-pilot-v1.json"),
        batch=Path("data/references/connections-v1.json"),
        reviews=Path("docs/implementation/issue-16/claim-reviews.json"),
        cases=cases,
    )
    tracking = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/four-families.db")
    document = GraphAcceptanceRun(database_url, tracking=tracking).run(
        tmp_path / "four-families.json", (phase,)
    )
    assert document["state"] == "complete"
    assert len(document["responses"]) == 4
    assert all(
        r["trace_output_matches"] and r["all_citations_resolve"] for r in document["responses"]
    )
    assert document["checks"][0]["audit_readback_matches"] is True
    assert document["checks"][0]["original_response_survives_restart"] is True
    assert document["responses"][-1]["session_reset"] is True


def test_life_event_acceptance_verifies_typed_kinds_and_cli_classification_outcomes(
    database_url: str, tmp_path: Path
) -> None:
    from test_life_events import life_reference

    from ask_phil.event_graph import EventQuery
    from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase

    _, batch, reviews = life_reference()
    batch_path, reviews_path = tmp_path / "batch.json", tmp_path / "reviews.json"
    batch_path.write_text(batch.model_dump_json())
    reviews_path.write_text(json.dumps([r.model_dump() for r in reviews]))
    phase = GraphPhase(
        name="life-and-text",
        kind="events",
        snapshot=Path("data/seed/life-events-pilot-v1.json"),
        batch=batch_path,
        reviews=reviews_path,
        cases=(
            GraphCase(
                "pregnancy",
                "What happened to Peggy?",
                EventQuery(
                    kind="life_events", character_id="peggy-mitchell", event_id="peggy-pregnancy"
                ),
            ),
            GraphCase(
                "theme",
                "Is the shared theme a connection?",
                EventQuery(
                    kind="theme", character_id="peggy-mitchell", participant_id="phil-mitchell"
                ),
                transport="cli",
            ),
        ),
    )
    output = tmp_path / "life-acceptance.json"
    tracking = MlflowClient(tracking_uri=f"sqlite:///{tmp_path}/life-traces.db")
    document = GraphAcceptanceRun(database_url, tracking=tracking).run(output, (phase,))
    assert document["state"] == "complete"
    first, second = document["responses"]
    assert first["response"]["status"] == "partial" and first["trace_output_matches"]
    assert second["response"]["graph"]["status"] == "ineligible" and second["trace_output_matches"]


@pytest.mark.integration
def test_later_trace_failure_retains_captured_graph_answers(
    database_url: str, tmp_path: Path
) -> None:
    from ask_phil.graph_acceptance import GraphAcceptanceRun, GraphCase, GraphPhase

    class UnavailableSecondTrace(MlflowClient):
        calls = 0

        def get_trace(self, trace_id: str, **kwargs: Any) -> Trace:
            self.calls += 1
            if self.calls == 2:
                raise TimeoutError("Private tracking details must not enter the artifact.")
            trace: Trace = super().get_trace(trace_id, **kwargs)
            return trace

    output = tmp_path / "acceptance.json"
    tracking = UnavailableSecondTrace(tracking_uri=f"sqlite:///{tmp_path}/mlflow.db")
    query = FamilyQuery(character_id="ben-mitchell", direction="ancestors")
    phase = GraphPhase(
        name="raw-pilot",
        kind="family",
        snapshot=Path("data/seed/family-pilot-v1.json"),
        batch=Path("docs/implementation/issue-11/claims.json"),
        reviews=Path("docs/implementation/issue-11/claim-reviews.json"),
        cases=(
            GraphCase("ancestors", "Who are Ben's biological ancestors?", query),
            GraphCase("ancestors-again", "Show Ben's biological ancestors", query),
        ),
    )

    with pytest.raises(TimeoutError):
        GraphAcceptanceRun(database_url, tracking=tracking).run(output, (phase,))

    retained = json.loads(output.read_text())
    assert retained["state"] == "failed"
    assert retained["failure_type"] == "TimeoutError"
    assert [r["case_id"] for r in retained["responses"]] == ["ancestors", "ancestors-again"]
    first, second = retained["responses"]
    assert first["verification_state"] == "complete"
    assert first["trace_output_matches"] is True
    assert second["verification_state"] == "failed"
    assert second["response"]["graph"]["status"] == "found"
    assert second["response"]["citations"]
    assert "Private tracking details" not in output.read_text()
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        GraphAcceptanceRun(database_url, tracking=tracking).run(output, (phase,))
    assert output.read_bytes() == original


@pytest.mark.integration
def test_family_acceptance_command_retains_verified_http_and_cli_outcomes(
    database_url: str, tmp_path: Path, record_property: Callable[[str, object], None]
) -> None:
    output = tmp_path / "family.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/record_family_acceptance.py",
            "--database-url",
            database_url,
            "--output",
            str(output),
            "--tracking-uri",
            f"sqlite:///{tmp_path}/family-traces.db",
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text())
    assert document["state"] == "complete"
    assert len(document["responses"]) == 9
    assert {row["transport"] for row in document["responses"]} == {"api", "cli"}
    assert all(row["trace_output_matches"] for row in document["responses"])
    assert document["original_response_survives_restart"] is True
    assert document["graph_reference_comparison"]["recall"] == 2 / 3
    assert document["graph_reference_comparison"]["missing"] == [
        ["ben-mitchell", "phil-mitchell", "peggy-mitchell"]
    ]
    record_property("acceptance_artifact", str(output))
    record_property("tracking_uri", f"sqlite:///{tmp_path}/family-traces.db")


@pytest.mark.integration
@pytest.mark.parametrize("kind,count", [("relationship", 28), ("event", 24)])
def test_history_acceptance_commands_retain_both_projections_and_actual_traces(
    database_url: str,
    tmp_path: Path,
    kind: str,
    count: int,
    record_property: Callable[[str, object], None],
) -> None:
    output = tmp_path / f"{kind}.json"
    result = subprocess.run(
        [
            sys.executable,
            f"scripts/record_{kind}_acceptance.py",
            "--database-url",
            database_url,
            "--output",
            str(output),
            "--tracking-uri",
            f"sqlite:///{tmp_path}/{kind}-traces.db",
        ],
        capture_output=True,
        text=True,
        timeout=150,
    )
    assert result.returncode == 0, result.stderr
    document = json.loads(output.read_text())
    assert document["state"] == "complete"
    assert len(document["responses"]) == count
    assert set(document["admissions"]) == {"raw-pilot", "reviewed-with-raw-retained"}
    assert all(row["trace_output_matches"] for row in document["responses"])
    assert all(row["original_response_survives_restart"] for row in document["checks"])
    assert document["paid_serving_calls"] == 0
    if kind == "event":
        assert all(row["event_session_and_reset"] for row in document["checks"])
        raw, reviewed = [r for r in document["responses"] if r["case_id"] == "context-stop"]
        assert raw["response"]["graph"]["status"] == "empty"
        assert raw["response"]["execution"]["stop_reason"] is None
        assert reviewed["response"]["execution"]["stop_reason"] == "context_limit"
        assert "graph" not in reviewed["response"] and reviewed["tool_output"]
    record_property("acceptance_artifact", str(output))
    record_property("tracking_uri", f"sqlite:///{tmp_path}/{kind}-traces.db")


@pytest.mark.integration
def test_history_assessment_uses_the_reference_frozen_after_tracking_setup(
    database_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = Path(__file__).resolve().parents[1]
    reference_path = Path("data/references/relationships-v2.json")
    for path in (
        reference_path,
        Path("data/seed/relationship-pilot-v1.json"),
        *(
            Path("docs/implementation/issue-12") / name
            for name in (
                "raw-claims.json",
                "raw-claim-reviews.json",
                "reviewed-claims-v2.json",
                "reviewed-claim-reviews-v2.json",
            )
        ),
    ):
        destination = tmp_path / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / path, destination)
    spec = importlib.util.spec_from_file_location(
        "relationship_acceptance", root / "scripts/record_relationship_acceptance.py"
    )
    assert spec is not None and spec.loader is not None
    command = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(command)

    def tracking_setup(*, tracking_uri: str) -> MlflowClient:
        reference = json.loads(reference_path.read_bytes())
        reference["expected_claims"] = []
        reference_path.write_text(json.dumps(reference))
        return MlflowClient(tracking_uri=tracking_uri)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_DIR", str(root / ".git"))
    monkeypatch.setattr(command, "MlflowClient", tracking_setup)
    output = tmp_path / "reference-change.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_relationship_acceptance.py",
            "--database-url",
            database_url,
            "--output",
            str(output),
            "--tracking-uri",
            f"sqlite:///{tmp_path}/traces.db",
        ],
    )
    assert command.main() == 0

    retained = json.loads(output.read_bytes())
    assert retained["state"] == "complete"
    assert all(
        row["reference_comparison"]["expected"] == 0
        for row in retained["responses"]
        if row["transport"] == "api"
    )
