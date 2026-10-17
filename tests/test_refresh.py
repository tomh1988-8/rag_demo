import hashlib
import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from llama_index.core.embeddings import MockEmbedding
from pydantic import HttpUrl
from starlette.types import ASGIApp

from ask_phil.identity import Character, IdentityCatalogue
from ask_phil.ingestion import CapturedSource, ScopeRule, SourceBatch, WikipediaPolicy
from ask_phil.storage import EvidenceStore

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("prefect_backend")]


@pytest.fixture(scope="session")
def prefect_backend(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    from prefect.settings import PREFECT_HOME, PREFECT_SERVER_ANALYTICS_ENABLED, temporary_settings
    from prefect.testing.utilities import prefect_test_harness

    with (
        temporary_settings(
            {
                PREFECT_HOME: tmp_path_factory.mktemp("prefect"),
                PREFECT_SERVER_ANALYTICS_ENABLED: False,
            }
        ),
        prefect_test_harness(server_startup_timeout=60),
    ):
        yield


@pytest.fixture
def source_batch() -> SourceBatch:
    html = """<html><script>{"wgRevisionId":17,"wgWikibaseItemId":"Q7490258"}</script>
    <div id="mw-content-text"><div class="mw-parser-output">
    <h2 id="Storylines">Storylines</h2>
    <p>Synthetic fixture: Sharon opens the blue workshop.</p>
    <p>Synthetic fixture: Den visits the workshop.</p>
    </div></div></html>"""
    return SourceBatch(
        format_version=1,
        catalogue=IdentityCatalogue(
            characters=(
                Character(
                    character_id="sharon-watts",
                    name="Sharon Watts",
                    coverage="core",
                    wikidata_id="Q7490258",
                    evidence_sources=("sharon-wiki",),
                    review_note="Authored lifecycle counterexample; not EastEnders canon.",
                ),
            )
        ),
        policies={
            "sharon-wiki": WikipediaPolicy(
                revision_id="17",
                reviewer="Reviewed authored lifecycle fixture; not live source evidence.",
                rules=(
                    ScopeRule(
                        section=("Storylines",), scope="main_series", reason="Synthetic narrative."
                    ),
                ),
            )
        },
        captures=(
            CapturedSource(
                source_id="sharon-wiki",
                kind="wikipedia",
                character_id="sharon-watts",
                url=HttpUrl("https://en.wikipedia.org/wiki/Sharon_Watts"),
                captured_at=datetime.fromisoformat("2026-09-25T15:00:00Z"),
                content=html,
                sha256=hashlib.sha256(html.encode()).hexdigest(),
            ),
        ),
    )


@pytest.fixture
def changed_batch(source_batch: SourceBatch) -> SourceBatch:
    document = source_batch.model_dump(mode="json")
    capture = document["captures"][0]
    capture["content"] = (
        capture["content"]
        .replace('"wgRevisionId":17', '"wgRevisionId":18')
        .replace("blue workshop", "red workshop")
    )
    capture["sha256"] = hashlib.sha256(capture["content"].encode()).hexdigest()
    capture["captured_at"] = "2026-09-26T15:00:00Z"
    document["policies"]["sharon-wiki"]["revision_id"] = "18"
    return SourceBatch.model_validate(document)


def test_prefect_refresh_publishes_a_complete_inspectable_source_and_index_pair(
    database_url: str, source_batch: SourceBatch
) -> None:
    from prefect.client.orchestration import get_client

    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import SourceRefresh
    from ask_phil.retrieval import TextRetriever

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    run = refresh.run(source_batch)

    active = PublicationStore(database_url).active()
    assert run.status == "published"
    assert active.compatibility_id == run.compatibility_id
    assert active.generation == 1
    assert active.manifest.sources[0].revision_id == "17"
    assert active.manifest.index.passages == 2
    inspected = EvidenceStore(database_url).inspect(active.manifest.snapshot_id, "blue")
    assert [p.text for p in inspected.matches] == [
        "Synthetic fixture: Sharon opens the blue workshop."
    ]
    index = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    assert index.manifest(active.manifest.snapshot_id) == active.manifest.index
    with get_client(sync_client=True) as client:
        state = client.read_flow_run(run.flow_run_id).state
        assert state is not None and state.is_completed()


def test_repeated_capture_reuses_logical_snapshot_and_index_without_republication(
    database_url: str, source_batch: SourceBatch
) -> None:
    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import SourceRefresh
    from ask_phil.retrieval import TextRetriever

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    first = refresh.run(source_batch)
    repeated = refresh.run(source_batch)
    checked_later = source_batch.model_copy(
        update={
            "captures": tuple(
                capture.model_copy(
                    update={"captured_at": datetime.fromisoformat("2026-09-26T15:00:00Z")}
                )
                for capture in source_batch.captures
            )
        }
    )
    unchanged = refresh.run(checked_later)

    assert repeated.status == unchanged.status == "skipped"
    assert first.compatibility_id == repeated.compatibility_id == unchanged.compatibility_id
    active = PublicationStore(database_url).active()
    assert active.generation == 1
    assert unchanged.sources[0].outcome == "unchanged"
    assert unchanged.sources[0].checked_at == datetime.fromisoformat("2026-09-26T15:00:00Z")
    assert len(PublicationStore(database_url).runs()) == 3
    result = TextRetriever(
        database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3
    ).retrieve(active.manifest.snapshot_id, "workshop", k=20)
    assert len(result.hits) == 2


def test_revised_passage_projection_preserves_legacy_evidence_and_recovery(
    database_url: str,
) -> None:
    from ask_phil.answers import assemble_context
    from ask_phil.api import create_app
    from ask_phil.evidence import SourceSnapshot
    from ask_phil.publications import PublicationStore, RefreshRun
    from ask_phil.refresh import SourceRefresh
    from ask_phil.retrieval import RetrievedPassage, TextRetriever

    legacy = SourceSnapshot.model_validate_json(
        Path("data/seed/context-fit-legacy-v1.json").read_text()
    )
    assert legacy.imported is not None
    batch = SourceBatch(
        format_version=legacy.imported.format_version,
        catalogue=legacy.imported.catalogue,
        policies=legacy.imported.policies,
        captures=legacy.imported.captures,
    )
    EvidenceStore(database_url).load(legacy)
    embedding = MockEmbedding(embed_dim=3)
    index = TextRetriever(database_url, embedding, "test-embedding-v1", 3).prepare(
        legacy.snapshot_id
    )
    publications = PublicationStore(database_url)
    initial_run = RefreshRun(
        run_id=uuid4(),
        flow_run_id=uuid4(),
        started_at=datetime.fromisoformat("2026-09-25T15:00:00Z"),
        status="running",
        phase="publishing",
        input_sha256=legacy.snapshot_id.removeprefix("sources-"),
    )
    with publications.writer() as conn:
        publications.save_run(initial_run, conn)
        publications.publish(legacy, index, initial_run, conn)
    original = publications.active()
    evidence_path = f"/v1/snapshots/{legacy.snapshot_id}/evidence/{legacy.passages[0].evidence_id}"
    with TestClient(create_app(database_url)) as client:
        original_evidence = client.get(evidence_path).json()
        refresh = SourceRefresh(database_url, embedding, "test-embedding-v1", 3)

        refreshed = refresh.run(batch)

        assert refreshed.status == "published"
        current = publications.active()
        assert current.manifest.snapshot_id != legacy.snapshot_id
        assert current.manifest.input_sha256 != original.manifest.input_sha256
        assert current.generation == 2
        snapshot = EvidenceStore(database_url).snapshot(current.manifest.snapshot_id)
        assert snapshot.imported is not None
        assert snapshot.imported.parser_version == "html-context-fit-v2"
        for passage in snapshot.passages:
            assert assemble_context((RetrievedPassage(passage=passage, similarity=1.0),), 1200)
        assert client.get(evidence_path).json() == original_evidence
        assert EvidenceStore(database_url).snapshot(legacy.snapshot_id).model_dump() == (
            legacy.model_dump()
        )

        repeated = refresh.run(batch)
        assert repeated.status == "skipped"
        assert publications.active() == current
        restored = refresh.rollback()
        assert restored.status == "rolled_back"
        assert publications.active().manifest == original.manifest
        assert publications.active().generation == 3
        assert client.get(evidence_path).json() == original_evidence


def test_killed_refresh_releases_writer_and_retry_records_interruption_and_rebuilds_index(
    database_url: str, source_batch: SourceBatch, changed_batch: SourceBatch, tmp_path: Path
) -> None:
    from prefect.settings import PREFECT_API_URL

    from ask_phil.publications import PublicationStore, RefreshBusy
    from ask_phil.refresh import SourceRefresh
    from ask_phil.retrieval import IndexNotReady, TextRetriever

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    refresh.run(source_batch)
    publications = PublicationStore(database_url)
    before = publications.active()
    batch_path = tmp_path / "changed.json"
    batch_path.write_text(changed_batch.model_dump_json())
    marker = tmp_path / "embedding-blocked"
    worker_code = """
import os
import threading
from pathlib import Path
import httpx
from llama_index.embeddings.ollama import OllamaEmbedding
from ask_phil.ingestion import read_batch
from ask_phil.refresh import SourceRefresh

calls = 0
def provider(request):
    global calls
    calls += 1
    if calls == 2:
        Path(os.environ['ASK_PHIL_TEST_MARKER']).write_text('blocked')
        threading.Event().wait()
    return httpx.Response(200, json={'embeddings': [[0.5, 0.5, 0.5]]})

embedding = OllamaEmbedding(
    model_name='test-embedding', client_kwargs={'transport': httpx.MockTransport(provider)}
)
SourceRefresh(os.environ['DATABASE_URL'], embedding, 'test-embedding-v1', 3).run(
    read_batch(Path(os.environ['ASK_PHIL_TEST_BATCH']))
)
"""
    with (tmp_path / "worker.log").open("w+") as log:
        process = subprocess.Popen(
            [sys.executable, "-c", worker_code],
            env={
                **os.environ,
                "DATABASE_URL": database_url,
                "PREFECT_API_URL": str(PREFECT_API_URL.value()),
                "ASK_PHIL_TEST_BATCH": str(batch_path),
                "ASK_PHIL_TEST_MARKER": str(marker),
            },
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 45
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            if not marker.exists():
                log.seek(0)
                pytest.fail(f"Worker never reached the external embedding boundary: {log.read()}")
            with pytest.raises(RefreshBusy):
                refresh.rollback()
            interrupted = publications.runs()[0]
            assert interrupted.status == "running"
            assert interrupted.snapshot_id is not None
            assert publications.active() == before
            with pytest.raises(IndexNotReady):
                publications.pin(interrupted.snapshot_id)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)

    retried = refresh.run(changed_batch)

    abandoned = publications.run(interrupted.run_id)
    assert abandoned.status == "interrupted"
    assert abandoned.finished_at is not None
    assert retried.status == "published"
    assert retried.snapshot_id == interrupted.snapshot_id
    assert publications.active().compatibility_id == retried.compatibility_id
    retriever = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    assert retriever.manifest(retried.snapshot_id).passages == 2
    assert len(retriever.retrieve(retried.snapshot_id, "workshop", k=20).hits) == 2


@pytest.mark.parametrize("failure_kind", ["provider-unavailable", "zero-vector"])
def test_failed_embedding_withholds_publication_and_retry_replaces_incomplete_artifacts(
    database_url: str,
    source_batch: SourceBatch,
    changed_batch: SourceBatch,
    failure_kind: str,
) -> None:
    from llama_index.embeddings.ollama import OllamaEmbedding

    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import RefreshFailed, SourceRefresh
    from ask_phil.retrieval import IndexNotReady, TextRetriever

    working = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    working.run(source_batch)
    publications = PublicationStore(database_url)
    before = publications.active()
    requests = 0

    def provider(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 2 and failure_kind == "provider-unavailable":
            return httpx.Response(503, json={"error": "Controlled embedding outage."})
        vector = [0.0, 0.0, 0.0] if requests == 2 else [0.5, 0.5, 0.5]
        return httpx.Response(200, json={"embeddings": [vector]})

    embedding = OllamaEmbedding(
        model_name="test-embedding", client_kwargs={"transport": httpx.MockTransport(provider)}
    )
    broken = SourceRefresh(database_url, embedding, "test-embedding-v1", 3)
    with pytest.raises(RefreshFailed) as failure:
        broken.run(changed_batch)

    failed = publications.run(failure.value.run_id)
    assert failed.status == "failed"
    assert failed.phase == "indexing"
    assert failed.snapshot_id is not None
    assert publications.active() == before
    assert EvidenceStore(database_url).inspect(failed.snapshot_id, "red").matches
    with pytest.raises(IndexNotReady):
        publications.pin(failed.snapshot_id)

    retried = working.run(changed_batch)

    assert retried.status == "published"
    assert retried.snapshot_id == failed.snapshot_id
    retriever = TextRetriever(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    assert retriever.manifest(retried.snapshot_id).passages == 2
    assert len(retriever.retrieve(retried.snapshot_id, "workshop", k=20).hits) == 2


def test_changed_review_policy_gets_a_new_identity_even_for_unchanged_capture(
    database_url: str, source_batch: SourceBatch
) -> None:
    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import SourceRefresh

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    original = refresh.run(source_batch)
    revised = source_batch.model_copy(
        update={
            "policies": {
                "sharon-wiki": source_batch.policies["sharon-wiki"].model_copy(
                    update={"reviewer": "Second explicit review of the synthetic source policy."}
                )
            }
        }
    )

    changed = refresh.run(revised)

    assert changed.status == "published"
    assert changed.input_sha256 != original.input_sha256
    assert changed.compatibility_id != original.compatibility_id
    assert changed.sources[0].outcome == "unchanged"
    assert PublicationStore(database_url).active().generation == 2


def test_source_revert_reactivates_retained_compatible_artifacts_and_advances_generation(
    database_url: str, source_batch: SourceBatch, changed_batch: SourceBatch
) -> None:
    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import SourceRefresh

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    first = refresh.run(source_batch)
    publications = PublicationStore(database_url)
    original = publications.active()
    second = refresh.run(changed_batch)

    reverted = refresh.run(source_batch)

    assert reverted.status == "published"
    assert reverted.compatibility_id == first.compatibility_id
    assert reverted.sources[0].outcome == "changed"
    assert publications.active().manifest == original.manifest
    assert publications.active().generation == 3
    assert publications.previous().compatibility_id == second.compatibility_id
    assert not publications.is_current(original.compatibility_id, original.generation)


def test_refresh_reports_duplicate_metadata_without_duplicating_logical_records(
    database_url: str, source_batch: SourceBatch
) -> None:
    from ask_phil.refresh import SourceRefresh

    episode = {
        "id": 100,
        "name": "Synthetic episode metadata",
        "season": 1,
        "number": 1,
        "airdate": "1985-02-19",
        "summary": "Synthetic metadata; not canon evidence.",
        "_links": {"show": {"href": "https://api.tvmaze.com/shows/793"}},
    }
    content = json.dumps([episode, episode])
    duplicate = source_batch.model_copy(
        update={
            "captures": (
                *source_batch.captures,
                CapturedSource(
                    source_id="episode",
                    kind="tvmaze",
                    url=HttpUrl("https://api.tvmaze.com/shows/793/episodes"),
                    captured_at=source_batch.captures[0].captured_at,
                    content=content,
                    sha256=hashlib.sha256(content.encode()).hexdigest(),
                ),
            )
        }
    )
    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)

    result = refresh.run(duplicate)
    repeated = refresh.run(duplicate)

    assert any(i.code == "duplicate_record" and i.source_id == "episode" for i in result.issues)
    assert result.snapshot_id is not None
    imported = EvidenceStore(database_url).snapshot(result.snapshot_id).imported
    assert imported is not None
    assert len(imported.inspect("episode").records) == 1
    assert repeated.status == "skipped"


def test_missing_required_source_record_withholds_publication_and_records_partial_failure(
    database_url: str, source_batch: SourceBatch
) -> None:
    from prefect.client.orchestration import get_client

    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import RefreshFailed, SourceRefresh

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    refresh.run(source_batch)
    publications = PublicationStore(database_url)
    before = publications.active()
    missing = '{"entities":{}}'
    incomplete = source_batch.model_copy(
        update={
            "captures": (
                *source_batch.captures,
                CapturedSource(
                    source_id="sharon-identity",
                    character_id="sharon-watts",
                    kind="wikidata",
                    url=HttpUrl("https://www.wikidata.org/wiki/Special:EntityData/Q7490258.json"),
                    captured_at=source_batch.captures[0].captured_at,
                    content=missing,
                    sha256=hashlib.sha256(missing.encode()).hexdigest(),
                ),
            )
        }
    )

    with pytest.raises(RefreshFailed) as failure:
        refresh.run(incomplete)

    run = publications.run(failure.value.run_id)
    assert run.status == "partial"
    assert any(i.source_id == "sharon-identity" and i.code == "missing_record" for i in run.issues)
    assert publications.active() == before
    assert EvidenceStore(database_url).inspect(before.manifest.snapshot_id, "blue").matches
    with get_client(sync_client=True) as client:
        state = client.read_flow_run(run.flow_run_id).state
        assert state is not None and state.is_failed()


def test_partial_live_capture_retains_received_source_and_keeps_prior_publication(
    database_url: str, source_batch: SourceBatch, changed_batch: SourceBatch
) -> None:
    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import RefreshFailed, SourceRefresh
    from ask_phil.source_records import CapturePlan, SourceRequest

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    refresh.run(source_batch)
    publications = PublicationStore(database_url)
    before = publications.active()
    plan = CapturePlan(
        format_version=1,
        catalogue=changed_batch.catalogue,
        policies=changed_batch.policies,
        requests=(
            SourceRequest(
                source_id="sharon-wiki",
                kind="wikipedia",
                character_id="sharon-watts",
                url=changed_batch.captures[0].url,
            ),
            SourceRequest(
                source_id="sharon-identity",
                kind="wikidata",
                character_id="sharon-watts",
                url=HttpUrl("https://www.wikidata.org/wiki/Special:EntityData/Q7490258.json"),
            ),
        ),
    )

    def source_provider(request: httpx.Request) -> httpx.Response:
        if request.url.host == "en.wikipedia.org":
            return httpx.Response(200, text=changed_batch.captures[0].content)
        return httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(source_provider)) as client:
        with pytest.raises(RefreshFailed) as failure:
            refresh.run(plan, client=client)

    run = publications.run(failure.value.run_id)
    assert run.status == "partial"
    assert [(s.source_id, s.outcome) for s in run.sources] == [
        ("sharon-wiki", "changed"),
        ("sharon-identity", "failed"),
    ]
    assert "503" in str(run.sources[-1].detail)
    assert publications.captures(run.run_id)[0].content == changed_batch.captures[0].content
    assert publications.active() == before


def test_rollback_restores_compatible_pair_and_withdraws_newer_version_for_new_requests(
    database_url: str, source_batch: SourceBatch, changed_batch: SourceBatch
) -> None:
    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import RefreshFailed, SourceRefresh
    from ask_phil.retrieval import IndexNotReady

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    refresh.run(source_batch)
    publications = PublicationStore(database_url)
    original = publications.active()
    change = refresh.run(changed_batch)
    newer = publications.active()
    assert change.sources[0].outcome == "changed"
    assert newer.compatibility_id != original.compatibility_id

    result = refresh.rollback()

    restored = publications.active()
    assert result.status == "rolled_back"
    assert restored.compatibility_id == original.compatibility_id
    assert restored.manifest == original.manifest
    assert restored.generation == 3
    assert not publications.is_current(newer.compatibility_id, newer.generation)
    assert not publications.is_current(original.compatibility_id, original.generation)
    assert publications.is_current(restored.compatibility_id, restored.generation)
    assert EvidenceStore(database_url).inspect(restored.manifest.snapshot_id, "blue").matches
    assert EvidenceStore(database_url).inspect(newer.manifest.snapshot_id, "red").matches
    with pytest.raises(IndexNotReady, match="withdrawn"):
        publications.pin(newer.manifest.snapshot_id)
    with pytest.raises(RefreshFailed):
        refresh.run(changed_batch)
    assert publications.active() == restored


def test_incompatible_embedding_contract_cannot_answer_or_replace_the_active_publication(
    database_url: str, source_batch: SourceBatch, changed_batch: SourceBatch, tmp_path: Path
) -> None:
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.llms.ollama import Ollama
    from ollama import Client

    from ask_phil.api import create_app
    from ask_phil.models import Models, ModelSettings
    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import RefreshFailed, SourceRefresh

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    refresh.run(source_batch)
    refresh.run(changed_batch)
    publications = PublicationStore(database_url)
    before = publications.active()
    settings = ModelSettings(
        answer_model="test-answer",
        answer_digest="a" * 64,
        embedding_model="incompatible-embedding",
        embedding_digest="c" * 64,
        embedding_dimensions=3,
    )

    def provider(request: httpx.Request) -> httpx.Response:
        pytest.fail("An incompatible publication must fail before any model call.")

    transport = httpx.MockTransport(provider)
    models = Models(
        settings,
        OllamaEmbedding(
            model_name="incompatible-embedding", client_kwargs={"transport": transport}
        ),
        Ollama(
            model="test-answer", client=Client(host="http://model.invalid", transport=transport)
        ),
    )
    with TestClient(
        create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/traces.db")
    ) as client:
        response = client.post("/v1/answers", json={"question": "Which workshop?"})
    assert response.status_code == 503
    assert "compatible index" in response.json()["detail"]
    incompatible = SourceRefresh(
        database_url, models.embedding, settings.embedding_id, settings.embedding_dimensions
    )
    with pytest.raises(RefreshFailed) as failure:
        incompatible.rollback()
    assert publications.run(failure.value.run_id).status == "failed"
    assert publications.active() == before


def test_api_exposes_active_manifest_run_details_and_pinned_current_inspection(
    database_url: str, source_batch: SourceBatch, changed_batch: SourceBatch
) -> None:
    from ask_phil.api import create_app
    from ask_phil.refresh import SourceRefresh

    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), "test-embedding-v1", 3)
    original = refresh.run(source_batch)
    with TestClient(create_app(database_url)) as client:
        active = client.get("/v1/publication")
        assert active.status_code == 200
        assert active.json()["compatibility_id"] == original.compatibility_id
        blue = client.get("/v1/inspect", params={"query": "blue"}).json()
        assert blue["publication"]["compatibility_id"] == original.compatibility_id
        assert blue["snapshot_id"] == original.snapshot_id
        assert len(blue["matches"]) == 1
        assert client.get(f"/v1/refresh-runs/{original.run_id}").json()["status"] == "published"
        assert len(client.get("/v1/refresh-runs").json()) == 1
        assert client.get(f"/v1/refresh-runs/{original.run_id}/captures").json()[0]["sha256"] == (
            source_batch.captures[0].sha256
        )
        changed = refresh.run(changed_batch)
        red = client.get("/v1/inspect", params={"query": "red"}).json()
        assert red["publication"]["compatibility_id"] == changed.compatibility_id
        assert red["matches"][0]["source"]["revision_id"] == "18"
        old = client.get(
            f"/v1/snapshots/{original.snapshot_id}/evidence/{blue['matches'][0]['evidence_id']}"
        ).json()
        assert old["matches"] == blue["matches"]


def test_cli_refreshes_recovers_and_inspects_current_publication_over_http(
    database_url: str,
    source_batch: SourceBatch,
    changed_batch: SourceBatch,
    live_api: str,
    http_server: Callable[[ASGIApp], AbstractContextManager[str]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from ask_phil.cli import main

    external = FastAPI()
    embedding_requests: list[str] = []

    @external.get("/api/tags")
    def tags() -> dict[str, object]:
        return {"models": [{"model": "test-embedding", "digest": "b" * 64}]}

    @external.post("/api/embed")
    def embed(body: dict[str, object]) -> dict[str, object]:
        embedding_requests.append(str(body["input"]))
        return {"embeddings": [[0.5, 0.5, 0.5]]}

    config = tmp_path / "models.json"
    config.write_text(
        json.dumps(
            {
                "answer_model": "not-needed-for-refresh",
                "answer_digest": "a" * 64,
                "embedding_model": "test-embedding",
                "embedding_digest": "b" * 64,
                "embedding_dimensions": 3,
            }
        )
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ASK_PHIL_MODELS", str(config))

    def command(*args: str) -> dict[str, object]:
        monkeypatch.setattr(sys, "argv", ["ask-phil", "--api-url", live_api, *args])
        assert main() == 0
        return dict(json.loads(capsys.readouterr().out))

    with http_server(external) as model_url:
        monkeypatch.setenv("ASK_PHIL_OLLAMA_URL", model_url)
        batch_path = tmp_path / "batch.json"
        batch_path.write_text(source_batch.model_dump_json())
        first = command("refresh-sources", str(batch_path))
        assert first["status"] == "published"
        assert len(embedding_requests) == 2
        assert command("publication")["compatibility_id"] == first["compatibility_id"]
        assert command("inspect", "blue")["snapshot_id"] == first["snapshot_id"]
        batch_path.write_text(changed_batch.model_dump_json())
        second = command("refresh-sources", str(batch_path))
        assert second["status"] == "published"

    # Recovery only verifies retained artifacts: the model server is now unavailable.
    recovered = command("rollback-snapshot")
    assert recovered["status"] == "rolled_back"
    assert recovered["compatibility_id"] == first["compatibility_id"]
    monkeypatch.delenv("DATABASE_URL")
    assert command("refresh-runs", str(first["run_id"]))["status"] == "published"
    assert command("publication")["compatibility_id"] == first["compatibility_id"]


def test_answer_pins_one_publication_while_a_concurrent_refresh_changes_the_active_version(
    database_url: str, source_batch: SourceBatch, changed_batch: SourceBatch, tmp_path: Path
) -> None:
    from llama_index.embeddings.ollama import OllamaEmbedding
    from llama_index.llms.ollama import Ollama
    from ollama import Client

    from ask_phil.api import create_app
    from ask_phil.models import Models, ModelSettings
    from ask_phil.publications import PublicationStore
    from ask_phil.refresh import SourceRefresh

    settings = ModelSettings(
        answer_model="test-answer",
        answer_digest="a" * 64,
        embedding_model="test-embedding",
        embedding_digest="b" * 64,
        embedding_dimensions=3,
    )
    refresh = SourceRefresh(database_url, MockEmbedding(embed_dim=3), settings.embedding_id, 3)
    refresh.run(source_batch)
    original = PublicationStore(database_url).active()
    first_passage = EvidenceStore(database_url).snapshot(original.manifest.snapshot_id).passages[0]
    blocked, release = threading.Event(), threading.Event()

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"model": "test-answer", "digest": "a" * 64},
                        {"model": "test-embedding", "digest": "b" * 64},
                    ]
                },
            )
        if request.url.path == "/api/embed":
            blocked.set()
            assert release.wait(30), "Concurrent refresh did not release the external embed call."
            return httpx.Response(200, json={"embeddings": [[0.5, 0.5, 0.5]]})
        assert request.url.path == "/api/chat"
        return httpx.Response(
            200,
            json={
                "model": "test-answer",
                "done": True,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "answer": (
                                "Right, listen. In this synthetic fixture "
                                "Sharon opens the blue workshop."
                            ),
                            "status": "answered",
                            "evidence_ids": [first_passage.evidence_id],
                            "unanswered": [],
                            "qualifications": [],
                        }
                    ),
                },
            },
        )

    transport = httpx.MockTransport(provider)
    models = Models(
        settings,
        OllamaEmbedding(model_name="test-embedding", client_kwargs={"transport": transport}),
        Ollama(
            model="test-answer",
            context_window=4096,
            client=Client(host="http://model.invalid", transport=transport),
        ),
    )
    app = create_app(database_url, models=models, tracking_uri=f"sqlite:///{tmp_path}/traces.db")
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, "/v1/answers", json={"question": "Which workshop?"})
        try:
            if not blocked.wait(15):
                unexpected = pending.result(timeout=10)
                pytest.fail(
                    f"Request never reached embedding: {unexpected.status_code} {unexpected.text}"
                )
            refresh.run(changed_batch)
        finally:
            release.set()
        response = pending.result(timeout=30)
        assert response.status_code == 200, response.text
        receipt = response.json()
        answer = receipt["response"]
        assert answer["snapshot_id"] == original.manifest.snapshot_id
        assert answer["snapshot_sha256"] == original.manifest.snapshot_sha256
        assert answer["publication"] == original.reference.model_dump(mode="json")
        assert (
            answer["citations"][0]["text"] == "Synthetic fixture: Sharon opens the blue workshop."
        )
        assert all(p["source"]["revision_id"] == "17" for p in answer["context"])
        assert client.get("/v1/publication").json()["compatibility_id"] != original.compatibility_id
        saved = client.get(
            f"/v1/responses/{answer['response_id']}",
            headers={"Authorization": f"Bearer {receipt['read_token']}"},
        )
        assert saved.json() == answer
