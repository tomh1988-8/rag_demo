from test_event_claims import reference_batch

from ask_phil.event_evaluation import score_events
from ask_phil.story_events import ExtractedEvents


def test_identity_role_direction_negation_and_time_errors_are_separate() -> None:
    snapshot, batch, _ = reference_batch()
    crime = batch.claims[4]
    reference = ExtractedEvents(claims=(crime,))
    reversed_roles = crime.model_copy(
        update={
            "participants": (
                crime.participants[0].model_copy(update={"role": "victim"}),
                crime.participants[1].model_copy(update={"role": "perpetrator"}),
            )
        }
    )
    score = score_events(
        ExtractedEvents(claims=(reversed_roles,)).model_dump_json(), reference, snapshot
    )
    assert score.schema_valid and score.true_positive == 0
    assert score.dimensions["identity"].true_positive == 1
    assert score.dimensions["role"].true_positive == 1
    assert score.dimensions["direction"].true_positive == 0
    assert score.resolvable_spans == 1 and score.grounded == 0
    wrong = crime.model_copy(
        update={"polarity": "negated", "story_time": "around 2014", "time_precision": "approximate"}
    )
    score = score_events(ExtractedEvents(claims=(wrong,)).model_dump_json(), reference, snapshot)
    assert score.dimensions["negation"].true_positive == 0
    assert score.dimensions["timing"].true_positive == 0
    assert score.dimensions["identity"].true_positive == 1


def test_values_and_exact_grounding_are_independent_and_missing_schema_is_unscored() -> None:
    snapshot, batch, _ = reference_batch()
    claim = batch.claims[0]
    reference = ExtractedEvents(claims=(claim,))
    wrong_quote = claim.model_copy(
        update={"evidence": (claim.evidence[0].model_copy(update={"start": 1}),)}
    )
    score = score_events(
        ExtractedEvents(claims=(wrong_quote,)).model_dump_json(), reference, snapshot
    )
    assert score.true_positive == 1 and score.precision == score.recall == score.f1 == 1
    assert score.resolvable_spans == score.grounded == 0
    missing = score_events("not json", reference, snapshot)
    assert not missing.schema_valid and missing.precision is None and missing.grounded is None
    empty = score_events('{"claims": []}', reference, snapshot)
    assert empty.precision == empty.recall == empty.f1 == 0
