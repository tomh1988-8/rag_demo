from test_source_windows import window_source as window_source

from ask_phil.evidence import SourceSnapshot
from ask_phil.retrieval import RetrievedPassage
from ask_phil.source_windows import expand_context
from ask_phil.text_evaluation import SpanExpectation, score_text_context


def test_context_score_counts_source_spans_after_expansion_and_truncation(
    window_source: SourceSnapshot,
) -> None:
    # Independently labelled accusation and qualification in this authored fixture.
    facts = (
        (
            SpanExpectation(
                source_id="phil-test",
                revision_id="17",
                start=0,
                end=40,
                text="Phil was accused of a fictional robbery.",
            ),
        ),
        (
            SpanExpectation(
                source_id="phil-test",
                revision_id="17",
                start=42,
                end=89,
                text="He was not convicted of that fictional robbery.",
            ),
        ),
    )
    original = score_text_context(window_source, facts, window_source.passages[:1], answerable=True)
    assert original.covered_facts == 1
    assert original.required_facts == 2
    assert original.coverage == 0.5
    assert not original.sufficient

    expanded = expand_context(
        window_source,
        (RetrievedPassage(passage=window_source.passages[0], similarity=1),),
        byte_budget=1200,
    ).context
    score = score_text_context(window_source, facts, expanded, answerable=True)
    assert score.coverage == 1.0
    assert score.sufficient
    absent = score_text_context(window_source, (), expanded, answerable=False)
    assert absent.coverage is None
    assert not absent.sufficient
