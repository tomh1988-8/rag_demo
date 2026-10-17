"""Record source/text refresh acceptance in an empty disposable PostgreSQL database."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from llama_index.core.embeddings import MockEmbedding
from prefect.client.orchestration import get_client
from prefect.settings import PREFECT_HOME, PREFECT_SERVER_ANALYTICS_ENABLED, temporary_settings
from prefect.testing.utilities import prefect_test_harness

from ask_phil.answering import application_fingerprint
from ask_phil.api import create_app
from ask_phil.ingestion import read_batch
from ask_phil.publications import PublicationNotFound, PublicationStore
from ask_phil.refresh import SourceRefresh
from ask_phil.retrieval import IndexNotReady
from ask_phil.storage import EvidenceStore


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; acceptance records are immutable.")
    database_url = os.environ["DATABASE_URL"]
    publications = PublicationStore(database_url)
    if publications.runs():
        parser.error("Acceptance needs a new disposable database with no refresh history.")
    try:
        publications.active()
    except PublicationNotFound:
        pass
    else:
        parser.error("Acceptance needs an empty publication history.")

    source_path = Path("data/sources/real-sources-v1.json.gz")
    batch = read_batch(source_path)
    with (
        TemporaryDirectory(prefix="ask-phil-prefect-") as prefect_home,
        temporary_settings(
            {PREFECT_HOME: Path(prefect_home), PREFECT_SERVER_ANALYTICS_ENABLED: False}
        ),
        prefect_test_harness(server_startup_timeout=60),
    ):
        refresh = SourceRefresh(
            database_url, MockEmbedding(embed_dim=3), "controlled-constant-v1", 3
        )
        first = refresh.run(batch)
        original = publications.active()
        repeated = refresh.run(batch)
        assert repeated.status == "skipped"
        assert publications.active() == original
        source_id = next(iter(batch.policies))
        policies = dict(batch.policies)
        policies[source_id] = policies[source_id].model_copy(
            update={
                "reviewer": policies[source_id].reviewer
                + " Lifecycle acceptance re-review of identical captured content."
            }
        )
        changed = refresh.run(batch.model_copy(update={"policies": policies}))
        newer = publications.active()
        assert newer.compatibility_id != original.compatibility_id
        restored_run = refresh.rollback()
        restored = publications.active()
        assert restored.manifest == original.manifest
        assert restored.generation == 3
        assert publications.is_current(restored.compatibility_id, restored.generation)
        assert not publications.is_current(original.compatibility_id, original.generation)
        try:
            publications.pin(newer.manifest.snapshot_id)
        except IndexNotReady:
            withdrawn_rejected = True
        else:
            raise AssertionError("The withdrawn snapshot remained eligible for new answers.")
        snapshot = EvidenceStore(database_url).snapshot(original.manifest.snapshot_id)
        evidence_id = snapshot.passages[0].evidence_id
        with TestClient(create_app(database_url)) as api:
            current = api.get("/v1/publication")
            evidence = api.get(
                f"/v1/snapshots/{original.manifest.snapshot_id}/evidence/{evidence_id}"
            )
            withdrawn_evidence = api.get(
                f"/v1/snapshots/{newer.manifest.snapshot_id}/evidence/{evidence_id}"
            )
            history = api.get("/v1/refresh-runs")
            assert (
                current.status_code == evidence.status_code == withdrawn_evidence.status_code == 200
            )
            assert len(history.json()) == 4
        runs = [first, repeated, changed, restored_run]
        with get_client(sync_client=True) as client:
            flow_states = {}
            for run in runs:
                state = client.read_flow_run(run.flow_run_id).state
                assert state is not None and state.is_completed()
                flow_states[str(run.flow_run_id)] = state.type.value

    paths = [
        *sorted(Path("src/ask_phil").glob("*.py")),
        Path("scripts/record_refresh_acceptance.py"),
        Path("pyproject.toml"),
        Path("uv.lock"),
        Path("config/local-models.json"),
        source_path,
    ]
    result = {
        "format_version": "source-text-refresh-acceptance-v1",
        "application_sha256": application_fingerprint(),
        "inputs_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "python": platform.python_version(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in [
                "prefect",
                "psycopg",
                "llama-index-core",
                "llama-index-vector-stores-postgres",
            ]
        },
        "limitations": [
            "Frozen public source captures; no new live source fetch.",
            "Controlled constant 3-dimensional embeddings; no retrieval or answer-quality claim.",
            "Second publication changes review policy only; "
            "source-change cases are in test_refresh.",
            "Disposable real PostgreSQL/pgvector and isolated real Prefect backend.",
            "No paid provider calls; no credentials recorded.",
        ],
        "runs": [run.model_dump(mode="json") for run in runs],
        "prefect_states": flow_states,
        "original": original.model_dump(mode="json"),
        "newer": newer.model_dump(mode="json"),
        "restored": restored.model_dump(mode="json"),
        "withdrawn_rejected_for_new_answers": withdrawn_rejected,
        "http": {
            "current": current.status_code,
            "original_evidence": evidence.status_code,
            "withdrawn_evidence": withdrawn_evidence.status_code,
            "recorded_runs": len(history.json()),
        },
    }
    with args.output.open("x") as output:
        output.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"recorded": str(args.output), "runs": len(runs)}))


if __name__ == "__main__":
    main()
