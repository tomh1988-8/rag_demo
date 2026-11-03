import hashlib
from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl

from ask_phil.evidence import SourceSnapshot
from ask_phil.identity import Character, IdentityCatalogue
from ask_phil.ingestion import build_snapshot
from ask_phil.retrieval import RetrievedPassage
from ask_phil.source_records import CapturedSource, ScopeRule, SourceBatch, WikipediaPolicy
from ask_phil.source_windows import expand_context


@pytest.fixture
def window_source() -> SourceSnapshot:
    html = """<html><script>{"wgRevisionId":17,"wgWikibaseItemId":"Q202104"}</script>
    <div id="mw-content-text"><div class="mw-parser-output">
    <h2 id="Storylines">Storylines</h2>
    <p>Phil was accused of a fictional robbery.</p>
    <p>He was not convicted of that fictional robbery.</p>
    <h2 id="Casting">Casting</h2><p>The performer won an award.</p>
    <h2 id="Other_media">Other media</h2><p>A spin-off says he was convicted.</p>
    </div></div></html>"""
    character = Character(
        character_id="phil-mitchell",
        name="Phil Mitchell",
        coverage="core",
        wikidata_id="Q202104",
        review_note="Synthetic structural counterexample, not canon evidence.",
        evidence_sources=("phil-test",),
    )
    batch = SourceBatch(
        format_version=1,
        catalogue=IdentityCatalogue(characters=(character,)),
        captures=(
            CapturedSource(
                source_id="phil-test",
                kind="wikipedia",
                character_id="phil-mitchell",
                url=HttpUrl("https://en.wikipedia.org/w/index.php?title=Phil_Mitchell&oldid=17"),
                captured_at=datetime(2026, 9, 25, tzinfo=UTC),
                content=html,
                sha256=hashlib.sha256(html.encode()).hexdigest(),
            ),
        ),
        policies={
            "phil-test": WikipediaPolicy(
                revision_id="17",
                reviewer="Authored counterexample, not canon evidence.",
                rules=(
                    ScopeRule(section=("Storylines",), scope="main_series", reason="Test story."),
                    ScopeRule(section=("Casting",), scope="production", reason="Test production."),
                    ScopeRule(
                        section=("Other media",), scope="other_media", reason="Test spin-off."
                    ),
                ),
            )
        },
    )
    snapshot = build_snapshot(batch, "window-test")
    return snapshot.model_copy(
        update={
            "source": snapshot.source.model_copy(update={"support_status": "synthetic_fixture"}),
            "passages": tuple(
                p.model_copy(
                    update={
                        "source": p.source.model_copy(
                            update={"support_status": "synthetic_fixture"}
                        )
                    }
                )
                for p in snapshot.passages
                if p.source
            ),
        }
    )


def test_expansion_retains_adjacent_qualification_and_merges_overlapping_windows(
    window_source: SourceSnapshot,
) -> None:
    result = expand_context(
        window_source,
        tuple(RetrievedPassage(passage=p, similarity=1) for p in window_source.passages),
        byte_budget=1200,
        neighbours=1,
    )

    assert [p.text for p in result.context] == [
        "Phil was accused of a fictional robbery.",
        "He was not convicted of that fictional robbery.",
    ]
    assert len(result.windows) == 1
    assert result.windows[0].original_evidence_ids == tuple(
        p.evidence_id for p in window_source.passages
    )
    assert len(set(p.evidence_id for p in result.context)) == 2
    assert all(p.location and p.location.section_id == "Storylines" for p in result.context)
    assert all(p.source and p.source.revision_id == "17" for p in result.context)


def test_truncation_omits_a_whole_window_instead_of_losing_its_qualification(
    window_source: SourceSnapshot,
) -> None:
    result = expand_context(
        window_source,
        (RetrievedPassage(passage=window_source.passages[0], similarity=1),),
        byte_budget=180,
        neighbours=1,
    )

    assert result.context == ()
    assert result.truncated
    assert not result.windows[0].selected
    assert len(result.windows[0].spans) == 2


def test_expansion_rejects_a_hit_with_a_different_captured_revision(
    window_source: SourceSnapshot,
) -> None:
    passage = window_source.passages[0]
    assert passage.source is not None
    changed = passage.model_copy(
        update={"source": passage.source.model_copy(update={"revision_id": "18"})}
    )
    with pytest.raises(ValueError, match="exact captured snapshot"):
        expand_context(
            window_source, (RetrievedPassage(passage=changed, similarity=1),), byte_budget=1200
        )
