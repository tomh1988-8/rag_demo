import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ask_phil.answers import assemble_context
from ask_phil.api import create_app
from ask_phil.identity import IdentityCatalogue
from ask_phil.ingestion import build_snapshot, read_batch
from ask_phil.retrieval import RetrievedPassage
from ask_phil.storage import EvidenceStore


@pytest.mark.integration
def test_character_inventory_distinguishes_primary_history_from_supporting_mentions(
    database_url: str,
) -> None:
    snapshot = build_snapshot(read_batch(Path("data/sources/real-sources-v1.json.gz")), "coverage")
    EvidenceStore(database_url).load(snapshot)
    with TestClient(create_app(database_url)) as client:
        response = client.get("/v1/snapshots/coverage/sources")
        assert response.status_code == 200
        inventory = {row["character"]["character_id"]: row for row in response.json()["characters"]}
        sharon = inventory["sharon-watts"]
        assert sharon["identity_resolution"] == {
            "status": "resolved",
            "character_ids": ["sharon-watts"],
        }
        assert sharon["primary_source_ids"] == ["sharon-wiki"]
        assert sharon["admitted_paragraphs"] == 30
        assert sharon["admitted_sections"] == [
            ["Storylines", "1985–1995"],
            ["Storylines", "2001–2006"],
            ["Storylines", "2012–present"],
        ]
        den = inventory["den-watts"]
        assert den["character"]["coverage"] == "supporting"
        assert den["admitted_paragraphs"] == 0
        assert "sharon-wiki" in den["mentioned_in_source_ids"]
        assert "No admitted primary narrative history." in den["gaps"]
        assert "Capture time does not establish current storyline completeness." in sharon["gaps"]


def test_inventory_exposes_duplicate_accounts_without_claiming_independent_corroboration() -> None:
    from ask_phil.source_records import SourceBatch

    batch = read_batch(Path("data/sources/real-sources-v1.json.gz"))
    characters = tuple(
        c.model_copy(update={"evidence_sources": (source_id,)})
        for c, source_id in zip(
            batch.catalogue.characters[:2], ("sharon-wiki", "ben-wiki"), strict=True
        )
    )
    captures = []
    for capture in batch.captures:
        if capture.source_id not in {"sharon-wiki", "ben-wiki"}:
            continue
        character = next(c for c in characters if c.character_id == capture.character_id)
        revision = batch.policies[capture.source_id].revision_id
        content = (
            f'<script>{{"wgRevisionId":{revision},"wgWikibaseItemId":"{character.wikidata_id}"}}</script>'
            '<div id="mw-content-text"><div class="mw-parser-output">'
            '<h2 id="Storylines">Storylines</h2><p>Authored duplicated story account.</p>'
            "</div></div>"
        )
        captures.append(
            capture.model_copy(
                update={"content": content, "sha256": hashlib.sha256(content.encode()).hexdigest()}
            )
        )
    snapshot = build_snapshot(
        SourceBatch(
            format_version=1,
            catalogue=IdentityCatalogue(characters=characters),
            policies={k: v for k, v in batch.policies.items() if k in {"sharon-wiki", "ben-wiki"}},
            captures=tuple(captures),
        ),
        "duplicate-accounts",
    )
    assert snapshot.imported is not None
    groups = snapshot.imported.report().model_dump()["duplicate_paragraphs"]
    assert len(groups) == 1
    assert groups[0]["locations"] == (
        {"source_id": "sharon-wiki", "paragraph_ordinal": 0},
        {"source_id": "ben-wiki", "paragraph_ordinal": 0},
    )


def test_full_curated_roster_uses_the_generic_import_and_preserves_citable_history() -> None:
    snapshot = build_snapshot(
        read_batch(Path("data/sources/core-profiles-v2.json.gz")), "full-roster"
    )
    assert snapshot.imported is not None
    report = snapshot.imported.report()
    assert {c.name for c in report.catalogue.characters if c.coverage == "core"} == {
        "Phil Mitchell",
        "Grant Mitchell",
        "Peggy Mitchell",
        "Sharon Watts",
        "Ben Mitchell",
        "Ian Beale",
        "Kathy Beale",
        "Cindy Beale",
        "Lucy Beale",
        "Bobby Beale",
        "Martin Fowler",
        "Kat Slater",
        "Stacey Slater",
        "Alfie Moon",
        "Pat Butcher",
        "Janine Butcher",
        "Dot Cotton",
        "Denise Fox",
        "Max Branning",
        "Linda Carter",
    }
    assert len(report.sources) == 20
    assert all(
        c.admitted_paragraphs > 0 for c in report.characters if c.character.coverage == "core"
    )
    assert any("Backstory" in section for c in report.characters for section in c.admitted_sections)
    assert not any(p.source and "Redwater" in p.source.section for p in snapshot.passages)
    for passage in snapshot.passages:
        assert passage.location is not None
        document = next(
            d for d in snapshot.imported.documents if d.source_id == passage.location.source_id
        )
        assert document.text[passage.start : passage.end] == passage.text
        assert assemble_context((RetrievedPassage(passage=passage, similarity=1.0),)) == (passage,)


def test_ambiguous_cindy_williams_name_cannot_tag_the_daughter_as_cindy_beale() -> None:
    snapshot = build_snapshot(
        read_batch(Path("data/sources/core-profiles-v2.json.gz")), "cindy-links"
    )
    assert snapshot.imported is not None
    assert snapshot.imported.catalogue.resolve("Cindy Williams").status == "unknown"
    daughter_passages = [
        p
        for p in snapshot.passages
        if p.location
        and p.location.source_id == "martin-fowler-wiki"
        and p.location.paragraph_ordinal == 18
    ]
    assert daughter_passages
    assert all(
        p.location and "cindy-beale" not in p.location.character_ids for p in daughter_passages
    )
