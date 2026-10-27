from test_relationship_claims import reference_batch

from ask_phil.relationship_evaluation import score_relationships
from ask_phil.relationships import ExtractedRelationships


def test_value_episode_and_grounding_failures_are_separate() -> None:
    snapshot, batch, _ = reference_batch()
    # Only one of two marriage episodes was extracted, twice, with an unsupported quote.
    first = next(c for c in batch.claims if c.claim_id == "kat-alfie-marriage")
    short = first.model_copy(
        update={"evidence": (first.evidence[0].model_copy(update={"end": 3, "quote": "Kat"}),)}
    )
    duplicate = short.model_copy(update={"claim_id": "duplicate-marriage"})
    predicted = ExtractedRelationships(claims=(short, duplicate))
    reference = ExtractedRelationships(
        claims=tuple(c for c in batch.claims if c.claim_id.startswith("kat-alfie"))
    )
    score = score_relationships(predicted.model_dump_json(), reference, snapshot)
    assert score.schema_valid
    assert score.expected == 2 and score.predicted == 2 and score.duplicates == 1
    assert score.true_positive == 1
    assert score.precision == 1.0 and score.recall == 0.5
    assert score.resolvable_spans == 2 and score.grounded == 0
    assert score.episode_pairs_expected == 1 and score.episode_pairs_correct == 0
    assert score.ordering_expected == 1 and score.ordering_correct == 0
    assert score.by_relation["remarriage"].recall == 0.0


def test_arbitrary_ids_and_symmetric_roles_do_not_break_episode_or_order_matching() -> None:
    snapshot, batch, _ = reference_batch()
    first, second = tuple(c for c in batch.claims if c.claim_id.startswith("kat-alfie"))
    reference = ExtractedRelationships(claims=(first, second))
    one = first.model_copy(
        update={
            "claim_id": "model-one",
            "episode_id": "model-episode-one",
            "subject_id": "alfie-moon",
            "object_id": "kat-slater",
        }
    )
    two = second.model_copy(
        update={
            "claim_id": "model-two",
            "episode_id": "model-episode-two",
            "after_claim_id": "model-one",
        }
    )
    score = score_relationships(
        ExtractedRelationships(claims=(one, two)).model_dump_json(), reference, snapshot
    )
    assert score.true_positive == 2 and score.f1 == 1.0
    assert score.episode_pairs_correct == 1 and score.ordering_correct == 1
    collapsed = two.model_copy(update={"episode_id": "model-episode-one"})
    bad = score_relationships(
        ExtractedRelationships(claims=(one, collapsed)).model_dump_json(), reference, snapshot
    )
    assert bad.true_positive == 2 and bad.episode_pairs_correct == 0


def test_schema_and_directed_role_errors_remain_separate_from_quote_resolution() -> None:
    snapshot, batch, _ = reference_batch()
    adoption = batch.claims[8]
    expected = ExtractedRelationships(claims=(adoption,))
    reversed_role = adoption.model_copy(
        update={"subject_id": "sharon-watts", "object_id": "den-watts"}
    )
    score = score_relationships(
        ExtractedRelationships(claims=(reversed_role,)).model_dump_json(), expected, snapshot
    )
    assert score.schema_valid and score.resolvable_spans == 1
    assert score.true_positive == 0 and score.grounded == 0 and score.recall == 0.0
    invalid = score_relationships(
        '{"claims": [{"relation": "guardian-is-adoption"}]}', expected, snapshot
    )
    assert not invalid.schema_valid and invalid.precision is None and invalid.grounded is None
