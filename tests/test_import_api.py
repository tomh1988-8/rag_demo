import gzip
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ask_phil.api import create_app
from ask_phil.ingestion import SourceBatch, build_snapshot
from ask_phil.storage import EvidenceStore

pytestmark = pytest.mark.integration


def test_imported_sources_are_inspectable_after_reimport_and_application_restart(
    database_url: str,
) -> None:
    batch = SourceBatch.model_validate_json(
        gzip.decompress(Path("data/sources/real-sources-v1.json.gz").read_bytes())
    )
    snapshot = build_snapshot(batch, "import-api")
    EvidenceStore(database_url).load(snapshot)
    with TestClient(create_app(database_url)) as client:
        report = client.get("/v1/snapshots/import-api/sources")
        assert report.status_code == 200
        source = next(s for s in report.json()["sources"] if s["source_id"] == "sharon-wiki")
        assert source["admitted_paragraphs"] == 30
        assert source["revision_id"] == "1372798905"
        assert source["review_required_paragraphs"] > 0
        assert client.get(
            "/v1/snapshots/import-api/identities", params={"name": "Kat Moon"}
        ).json() == {"status": "resolved", "character_ids": ["kat-slater"]}
        found = client.get(
            "/v1/snapshots/import-api/inspect", params={"query": "signet ring"}
        ).json()
        assert len(found["matches"]) == 1
        passage = found["matches"][0]
        assert passage["source"]["revision_id"] == "1372798905"
        assert (
            client.get("/v1/snapshots/import-api/inspect", params={"query": "Dimitri"}).json()[
                "matches"
            ]
            == []
        )
        retained = client.get("/v1/snapshots/import-api/sources/kat-wiki").json()
        excluded = [s for s in retained["document"]["spans"] if s["scope"] == "other_media"]
        assert len(excluded) == 5
        assert any("Dimitri" in s["text"] for s in excluded)
        assert retained["capture"]["content"].startswith("<!DOCTYPE html>")
        assert client.get("/v1/snapshots/import-api/sources/unknown").status_code == 404
        assert client.get("/v1/snapshots/unknown/sources").status_code == 404

    EvidenceStore(database_url).load(snapshot)
    with TestClient(create_app(database_url)) as restarted:
        resolved = restarted.get(
            f"/v1/snapshots/import-api/evidence/{passage['evidence_id']}"
        ).json()
        assert resolved["matches"] == [passage]
        assert restarted.get("/v1/snapshots/import-api/sources").json() == report.json()
