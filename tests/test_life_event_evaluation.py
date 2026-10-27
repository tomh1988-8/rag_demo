from test_life_events import life_reference

from ask_phil.event_evaluation import score_events
from ask_phil.story_events import ExtractedEvents


def test_event_types_and_themes_have_separate_value_and_grounding_scores() -> None:
    snapshot, batch, _ = life_reference()
    reference = ExtractedEvents(claims=batch.claims, context_claims=batch.context_claims)
    wrong_theme = batch.context_claims[0].model_copy(update={"theme": "manosphere"})
    fact = batch.context_claims[1]
    bad_quote = fact.model_copy(
        update={
            "evidence": (fact.evidence[0].model_copy(update={"start": 1}),),
        }
    )
    raw = ExtractedEvents(claims=batch.claims, context_claims=(wrong_theme, bad_quote))
    score = score_events(raw.model_dump_json(), reference, snapshot)
    assert score.f1 == 1 and score.true_positive == 5
    assert score.by_event_type["pregnancy"].grounded == 3
    assert score.by_event_type["death"].grounded == 2
    assert score.context_score is not None
    assert score.context_score.true_positive == 1 and score.context_score.f1 == 0.5
    assert score.context_score.resolvable_spans == 1 and score.context_score.grounded == 0
    assert score.by_theme["domestic_abuse"].recall == 0
    assert score.by_theme["manosphere"].precision == 0
    assert score.by_classification["unclassified"].f1 == 1
    assert score.by_classification["unclassified"].grounded == 0
