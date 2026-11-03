import hashlib

import pytest

from ask_phil.evidence import Passage
from ask_phil.retrieval import RetrievedPassage
from ask_phil.text_retrieval import RankedQuery, fuse_rankings, select_variants


def hit(identifier: str) -> RetrievedPassage:
    text = f"Captured passage {identifier}."
    return RetrievedPassage(
        passage=Passage(
            evidence_id=identifier,
            text=text,
            sha256=hashlib.sha256(text.encode()).hexdigest(),
            start=0,
            end=len(text),
        ),
        similarity=0.5,
    )


def test_fusion_ranks_complementary_queries_by_independent_one_based_example() -> None:
    a, b, c = (hit(identifier) for identifier in ("a", "b", "c"))
    result = fuse_rankings(
        (
            RankedQuery(query="original", hits=(a, b, c)),
            RankedQuery(query="variant", hits=(b, c, a)),
        ),
        constant=60,
        limit=3,
    )

    assert [candidate.passage.evidence_id for candidate in result] == ["b", "a", "c"]
    # Independently worked: b=1/62+1/61, a=1/61+1/63, c=1/63+1/62.
    assert [candidate.score for candidate in result] == pytest.approx(
        [0.03252247488101534, 0.032266458495966696, 0.03200204813108039]
    )
    assert result[0].ranks == (2, 1)


def test_repeated_query_and_evidence_cannot_cast_extra_fusion_votes() -> None:
    a, b = hit("a"), hit("b")
    result = fuse_rankings(
        (
            RankedQuery(query="Original question?", hits=(a, a, b)),
            RankedQuery(query="  ORIGINAL  QUESTION? ", hits=(a, b)),
            RankedQuery(query="faithful variant", hits=(b,)),
        ),
        constant=60,
        limit=2,
    )

    assert [c.passage.evidence_id for c in result] == ["b", "a"]
    assert result[0].score == pytest.approx(0.032266458495966696)
    assert result[0].ranks == (3, 1)
    assert result[1].score == pytest.approx(0.01639344262295082)


def test_faithful_variants_preserve_character_date_negation_and_question_intent() -> None:
    original = "Why was Phil Mitchell not convicted in 1990?"
    accepted = select_variants(
        original,
        (
            "EastEnders: Why was Phil Mitchell not convicted in 1990?",
            "EastEnders: Why was Phil Mitchell not convicted in 1990?",
        ),
        max_variants=2,
    )
    assert accepted.queries == (
        original,
        "EastEnders: Why was Phil Mitchell not convicted in 1990?",
    )
    assert accepted.proposals[1].reason == "duplicate"
    assert accepted.fallback_reason is None

    for drifting in (
        "Why was Grant Mitchell not convicted in 1990?",
        "Why was Phil Mitchell not convicted in 1991?",
        "Why was Phil Mitchell convicted in 1990?",
        "When was Phil Mitchell not convicted in 1990?",
        "Why was Phil Mitchell not acquitted in 1990?",
    ):
        rejected = select_variants(original, (drifting,), max_variants=2)
        assert rejected.queries == (original,)
        assert rejected.fallback_reason == "unfaithful_variants"


def test_equal_fusion_scores_sort_by_evidence_identity_and_reject_revision_collisions() -> None:
    a, b = hit("a"), hit("b")
    result = fuse_rankings(
        (RankedQuery(query="first", hits=(b, a)), RankedQuery(query="second", hits=(a, b))), limit=2
    )
    assert [c.passage.evidence_id for c in result] == ["a", "b"]
    changed = a.model_copy(update={"passage": b.passage.model_copy(update={"evidence_id": "a"})})
    with pytest.raises(ValueError, match="one captured passage"):
        fuse_rankings(
            (RankedQuery(query="one", hits=(a,)), RankedQuery(query="two", hits=(changed,)))
        )


@pytest.mark.parametrize(
    "original,drift",
    [
        ("Did Phil accuse Grant?", "Did Grant accuse Phil?"),
        ("Did Phil say Grant was not convicted?", "Did Phil not say Grant was convicted?"),
    ],
)
def test_identical_word_bags_cannot_swap_roles_or_change_negation_scope(
    original: str,
    drift: str,
) -> None:
    result = select_variants(original, (drift,), max_variants=2)
    assert result.queries == (original,)
    assert result.fallback_reason == "unfaithful_variants"
