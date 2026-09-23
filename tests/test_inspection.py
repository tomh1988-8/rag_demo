import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ask_phil.api import create_app
from ask_phil.evidence import SourceSnapshot
from ask_phil.storage import EvidenceStore, SnapshotConflict

pytestmark = pytest.mark.integration


def test_captured_arrival_passage_can_be_inspected_through_the_api(
    database_url: str, seed: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(seed)
    with TestClient(create_app(database_url)) as client:
        response = client.get(
            "/v1/snapshots/phil-arrival-v1/inspect",
            params={"query": "When does Phil Mitchell first arrive in Walford?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert [p["evidence_id"] for p in body["matches"]] == ["phil-arrival-001"]
    assert "February 1990" in body["matches"][0]["text"]
    assert body["source"]["revision_id"] == "1375499431"
    assert body["source"]["support_status"] == "source_supported"
    assert "not a generated answer" in body["limitation"]


def test_original_evidence_resolves_after_reimport_and_application_restart(
    database_url: str, seed: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(seed)
    with TestClient(create_app(database_url)) as first_app:
        original = first_app.get(
            "/v1/snapshots/phil-arrival-v1/inspect", params={"query": "The Arches"}
        ).json()

    EvidenceStore(database_url).load(seed)
    with TestClient(create_app(database_url)) as restarted_app:
        evidence = restarted_app.get("/v1/snapshots/phil-arrival-v1/evidence/phil-arrival-001")
    assert evidence.status_code == 200
    assert evidence.json()["snapshot_sha256"] == original["snapshot_sha256"]
    assert evidence.json()["matches"] == original["matches"]
    assert evidence.json()["source"] == original["source"]


def test_reviewed_seed_cases_include_an_honest_empty_result(
    database_url: str, seed: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(seed)
    references = json.loads(Path("data/references/phil-arrival-v1.json").read_text())
    with TestClient(create_app(database_url)) as client:
        for case in references["cases"]:
            response = client.get(
                "/v1/snapshots/phil-arrival-v1/inspect", params={"query": case["question"]}
            )
            assert response.status_code == 200
            body = response.json()
            assert [p["evidence_id"] for p in body["matches"]] == case["expected_evidence_ids"]
            assert "never happened" in body["limitation"]
            assert "Family relationships" in body["source"]["gaps"]


def test_snapshot_identifier_cannot_be_reassigned_to_changed_evidence(
    database_url: str, seed: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(seed)
    changed = seed.model_dump(mode="json")
    changed["source"]["coverage"] = "A different claim about coverage."
    with pytest.raises(SnapshotConflict):
        EvidenceStore(database_url).load(SourceSnapshot.model_validate(changed))
    with TestClient(create_app(database_url)) as client:
        response = client.get(
            "/v1/snapshots/phil-arrival-v1/inspect", params={"query": "The Arches"}
        )
    assert response.json()["snapshot_sha256"] == seed.fingerprint
    assert len(response.json()["matches"]) == 1


@pytest.mark.parametrize("query,limit", [("   ", 10), ("x" * 501, 10), ("Phil", 0), ("Phil", 21)])
def test_invalid_search_is_rejected(database_url: str, query: str, limit: int) -> None:
    with TestClient(create_app(database_url)) as client:
        response = client.get(
            "/v1/snapshots/phil-arrival-v1/inspect", params={"query": query, "limit": limit}
        )
    assert response.status_code == 422


def test_unknown_snapshot_and_evidence_are_not_reported_as_empty_searches(
    database_url: str, seed: SourceSnapshot
) -> None:
    EvidenceStore(database_url).load(seed)
    with TestClient(create_app(database_url)) as client:
        assert (
            client.get("/v1/snapshots/not-loaded/inspect", params={"query": "Phil"}).status_code
            == 404
        )
        assert client.get("/v1/snapshots/phil-arrival-v1/evidence/not-present").status_code == 404


def test_empty_database_reports_unavailable_instead_of_fabricating_evidence(
    database_url: str,
) -> None:
    with TestClient(create_app(database_url)) as client:
        response = client.get("/v1/snapshots/phil-arrival-v1/inspect", params={"query": "Phil"})
    assert response.status_code == 503
    assert response.json() == {"detail": "Evidence storage is unavailable."}
