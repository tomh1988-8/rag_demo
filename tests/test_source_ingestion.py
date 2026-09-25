import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path

import httpx
import pytest
from pydantic import HttpUrl

from ask_phil.ingestion import (
    CapturedSource,
    ScopeRule,
    SourceRequest,
    WikipediaPolicy,
    capture_sources,
    parse_wikipedia,
)


def test_mixed_page_retains_order_and_exclusions_without_losing_main_series_history() -> None:
    html = """<html><script>{"wgRevisionId":17,"wgWikibaseItemId":"Q3955054"}</script>
    <div id="mw-content-text"><div class="mw-parser-output">
    <h2 id="Storylines">Storylines</h2><h3 id="Before_1990">Before 1990</h3>
    <p>Kat mentions Redwater in Walford.<sup class="reference">[1]</sup></p>
    <h3 id="Other_media">Other media</h3><p>Kat visits Ireland in the spin-off.</p>
    <p>The podcast describes another event.</p>
    <h2 id="Casting">Casting</h2><p>Jessie Wallace portrays Kat.</p>
    </div></div></html>"""
    capture = CapturedSource(
        source_id="kat",
        kind="wikipedia",
        character_id="kat-slater",
        url=HttpUrl("https://en.wikipedia.org/w/index.php?title=Kat_Slater&oldid=17"),
        captured_at=datetime.fromisoformat("2026-09-25T12:00:00Z"),
        content=html,
        sha256=hashlib.sha256(html.encode()).hexdigest(),
    )
    policy = WikipediaPolicy(
        revision_id="17",
        reviewer="Authored structural counterexample, not canon evidence.",
        rules=(
            ScopeRule(section=("Storylines",), scope="main_series", reason="Reviewed narrative."),
            ScopeRule(
                section=("Storylines", "Other media"),
                scope="other_media",
                reason="Spin-off and podcast are outside main-series scope.",
            ),
            ScopeRule(section=("Casting",), scope="production", reason="Performer information."),
        ),
    )

    result = parse_wikipedia(capture, policy)

    assert result.revision_id == "17"
    assert [span.scope for span in result.spans] == [
        "main_series",
        "other_media",
        "other_media",
        "production",
    ]
    assert result.spans[0].text == "Kat mentions Redwater in Walford."
    assert [span.ordinal for span in result.spans] == [0, 1, 2, 3]
    assert result.spans[0].section_id == "Before_1990"
    assert result.spans[1].section_id == result.spans[2].section_id == "Other_media"
    assert all(result.text[s.start : s.end] == s.text for s in result.spans)
    assert result.spans[3].reason == "Performer information."


@pytest.fixture
def identity_request() -> SourceRequest:
    return SourceRequest(
        source_id="identity",
        kind="wikidata",
        character_id="sharon-watts",
        url=HttpUrl("https://www.wikidata.org/wiki/Special:EntityData/Q7490258.json"),
    )


def test_source_capture_preserves_response(identity_request: SourceRequest) -> None:
    content = '{"entities":{}}'
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, content=content, headers={"content-type": "application/json"}
            )
        )
    ) as client:
        captured = capture_sources((identity_request,), client)[0]
    assert captured.content == content
    assert captured.url == identity_request.url
    assert captured.captured_at.tzinfo is not None


def test_source_capture_rejects_http_failure(identity_request: SourceRequest) -> None:
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429))) as client:
        with pytest.raises(ValueError, match="429"):
            capture_sources((identity_request,), client)


def test_source_request_rejects_wrong_host() -> None:
    with pytest.raises(ValueError, match="official"):
        SourceRequest(
            source_id="wrong", kind="wikidata", url=HttpUrl("https://example.com/Q7490258.json")
        )


def test_real_inputs_preserve_narrative_provenance_and_keep_metadata_out_of_retrieval() -> None:
    from ask_phil.ingestion import SourceBatch, build_snapshot

    batch = SourceBatch.model_validate_json(
        gzip.decompress(Path("data/sources/real-sources-v1.json.gz").read_bytes())
    )
    snapshot = build_snapshot(batch, "real-sources-v1")
    assert snapshot.imported is not None
    imported = snapshot.imported
    assert imported.catalogue.resolve("Sharon Rickman").character_ids == ("sharon-watts",)
    assert imported.catalogue.resolve("Max Bowden").status == "performer"
    assert imported.catalogue.characters[3].coverage == "supporting"
    assert imported.catalogue.resolve("Dirty Den").character_ids == ("den-watts",)
    assert imported.catalogue.resolve("Dennis Alan Watts").character_ids == ("den-watts",)
    sharon = next(d for d in imported.documents if d.source_id == "sharon-wiki")
    ben = next(d for d in imported.documents if d.source_id == "ben-wiki")
    assert sum(s.scope == "main_series" for s in sharon.spans) == 30
    assert sum(s.scope == "main_series" for s in ben.spans) == 19
    assert any("spring in 1988" in p.text for p in snapshot.passages)
    assert any("information about Redwater" in p.text for p in snapshot.passages)
    assert not any("Dimitri" in p.text for p in snapshot.passages)
    assert all(len(p.text.encode()) <= 1200 for p in snapshot.passages)
    assert all(
        p.source and p.source.support_status == "source_supported" for p in snapshot.passages
    )
    assert all(p.location and p.location.source_id.endswith("-wiki") for p in snapshot.passages)
    assert any(p.location and "den-watts" in p.location.character_ids for p in snapshot.passages)
    episode = next(r for r in imported.records if r.role == "episode_metadata")
    assert episode.record_id == "116520"
    assert episode.fields["airdate"] == "1985-02-19"
    assert "story_event_date" not in episode.fields
    assert any(i.code == "missing_field" and "summary" in i.detail for i in imported.issues)
    assert any(r.role == "identity_linkage" and r.record_id == "Q7490258" for r in imported.records)
    for passage in snapshot.passages:
        assert passage.location is not None
        document = next(d for d in imported.documents if d.source_id == passage.location.source_id)
        assert document.text[passage.start : passage.end] == passage.text


def test_imported_citation_cannot_be_reassigned_to_an_excluded_paragraph() -> None:
    from ask_phil.evidence import SourceSnapshot
    from ask_phil.ingestion import SourceBatch, build_snapshot

    batch = SourceBatch.model_validate_json(
        gzip.decompress(Path("data/sources/real-sources-v1.json.gz").read_bytes())
    )
    document = build_snapshot(batch, "citation-integrity").model_dump(mode="json")
    document["passages"][0]["location"]["paragraph_ordinal"] = 0
    with pytest.raises(ValueError, match="admitted paragraph"):
        SourceSnapshot.model_validate(document)


def test_malformed_nested_episode_input_is_an_explicit_import_failure() -> None:
    from ask_phil.ingestion import SourceBatch, build_snapshot

    batch = json.loads(gzip.decompress(Path("data/sources/real-sources-v1.json.gz").read_bytes()))
    episode = next(c for c in batch["captures"] if c["source_id"] == "episode")
    episode["content"] = '[{"id":116520,"_links":[]}]'
    episode["sha256"] = hashlib.sha256(episode["content"].encode()).hexdigest()
    with pytest.raises(ValueError, match="episode: malformed"):
        build_snapshot(SourceBatch.model_validate(batch), "bad-episode")


def test_missing_sections_and_records_are_reported_separately_from_scope_exclusions() -> None:
    from ask_phil.ingestion import SourceBatch, build_snapshot

    batch = json.loads(gzip.decompress(Path("data/sources/real-sources-v1.json.gz").read_bytes()))
    identity = next(c for c in batch["captures"] if c["source_id"] == "sharon-identity")
    identity["content"] = '{"entities":{}}'
    identity["sha256"] = hashlib.sha256(identity["content"].encode()).hexdigest()
    batch["policies"]["sharon-wiki"]["rules"].append(
        {
            "section": ["Storylines", "Absent section"],
            "scope": "main_series",
            "reason": "Expected in this authored incomplete-input counterexample.",
        }
    )
    snapshot = build_snapshot(SourceBatch.model_validate(batch), "incomplete-import")
    assert snapshot.imported is not None
    report = snapshot.imported.report()
    codes = {(i.source_id, i.code) for i in report.issues}
    assert ("sharon-identity", "missing_record") in codes
    assert ("sharon-wiki", "missing_section") in codes
    assert (
        next(s for s in report.sources if s.source_id == "sharon-identity").structured_records == 0
    )
    kat = next(s for s in report.sources if s.source_id == "kat-wiki")
    assert kat.admitted_paragraphs == 30
    assert kat.excluded_paragraphs == 5


@pytest.mark.parametrize(
    "change", ["revision", "identity", "duplicate_rule", "html", "json", "sitelinks", "fingerprint"]
)
def test_incompatible_or_malformed_source_cannot_create_a_snapshot(change: str) -> None:
    from ask_phil.ingestion import SourceBatch, build_snapshot

    batch = json.loads(gzip.decompress(Path("data/sources/real-sources-v1.json.gz").read_bytes()))
    source_id = "sharon-identity" if change in {"json", "sitelinks"} else "sharon-wiki"
    source = next(c for c in batch["captures"] if c["source_id"] == source_id)
    if change == "revision":
        batch["policies"]["sharon-wiki"]["revision_id"] = "17"
    elif change == "identity":
        batch["catalogue"]["characters"][0]["wikidata_id"] = "Q17"
    elif change == "duplicate_rule":
        batch["policies"]["sharon-wiki"]["rules"].append(
            {
                "section": ["Storylines"],
                "scope": "other_media",
                "reason": "Conflicting scope rule.",
            }
        )
    elif change == "html":
        source["content"] = '<html><div id="mw-content-text">Truncated input'
    elif change == "json":
        source["content"] = "{broken"
    elif change == "sitelinks":
        entity = json.loads(source["content"])
        entity["entities"]["Q7490258"]["sitelinks"] = []
        source["content"] = json.dumps(entity)
    source["sha256"] = hashlib.sha256(source["content"].encode()).hexdigest()
    if change == "fingerprint":
        source["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        build_snapshot(SourceBatch.model_validate(batch), "rejected-input")


@pytest.mark.parametrize("conflict", [False, True])
def test_duplicate_episode_records_are_reported_and_conflicting_duplicates_fail(
    conflict: bool,
) -> None:
    from ask_phil.ingestion import SourceBatch, build_snapshot

    batch = json.loads(gzip.decompress(Path("data/sources/real-sources-v1.json.gz").read_bytes()))
    capture = next(c for c in batch["captures"] if c["source_id"] == "episode")
    episodes = json.loads(capture["content"])
    episodes.append({**episodes[0], **({"airdate": "1985-02-20"} if conflict else {})})
    capture["content"] = json.dumps(episodes)
    capture["sha256"] = hashlib.sha256(capture["content"].encode()).hexdigest()
    if conflict:
        with pytest.raises(ValueError, match="conflicting duplicate"):
            build_snapshot(SourceBatch.model_validate(batch), "conflicting-episodes")
    else:
        snapshot = build_snapshot(SourceBatch.model_validate(batch), "duplicate-episodes")
        assert snapshot.imported is not None
        assert sum(r.role == "episode_metadata" for r in snapshot.imported.records) == 1
        assert sum(i.code == "duplicate_record" for i in snapshot.imported.issues) == 1


def test_capture_stops_on_oversized_response(identity_request: SourceRequest) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 5_000_001))
    ) as client:
        with pytest.raises(ValueError, match="byte limit"):
            capture_sources((identity_request,), client)


def test_capture_stops_on_interrupted_response(identity_request: SourceRequest) -> None:

    def interrupted(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadError("Interrupted upstream response")

    with httpx.Client(transport=httpx.MockTransport(interrupted)) as client:
        with pytest.raises(ValueError, match="transport failed"):
            capture_sources((identity_request,), client)


def test_real_source_retention_matches_reviewed_ordered_paragraph_labels() -> None:
    from ask_phil.ingestion import build_snapshot, read_batch

    path = Path("data/sources/real-sources-v1.json.gz")
    reference = json.loads(Path("data/references/source-ingestion-v1.json").read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == reference["batch_sha256"]
    snapshot = build_snapshot(read_batch(path), "reviewed-retention")
    assert snapshot.imported is not None
    for document in snapshot.imported.documents:
        expected = reference["sources"][document.source_id]
        admitted = [s for s in document.spans if s.scope == "main_series"]
        excluded = [s for s in document.spans if s.scope == "other_media"]
        assert [s.sha256 for s in admitted] == [p["sha256"] for p in expected["admitted"]]
        assert [s.sha256 for s in excluded] == [p["sha256"] for p in expected["excluded"]]
        for span in admitted:
            fragments = [
                p
                for p in snapshot.passages
                if p.location
                and p.location.source_id == document.source_id
                and p.location.paragraph_ordinal == span.ordinal
            ]
            assert "".join(p.text for p in fragments) == span.text
