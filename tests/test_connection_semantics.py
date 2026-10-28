import pytest
from pydantic import ValidationError

from ask_phil.connection_graph import (
    BiologicalStep,
    ConnectionMeaning,
    ConnectionPath,
    ConnectionQuery,
    RelationshipStep,
)


def biological(parent: str, child: str, origin: str, target: str) -> BiologicalStep:
    return BiologicalStep.model_validate(
        {
            "kind": "biological",
            "from_id": origin,
            "to_id": target,
            "direction": "parent_to_child" if origin == parent else "child_to_parent",
            "edge": {
                "parent_id": parent,
                "child_id": child,
                "claim_ids": ["synthetic-parentage"],
                "evidence": [
                    {"evidence_id": "synthetic-family", "start": 0, "end": 1, "quote": "x"}
                ],
            },
        }
    )


@pytest.mark.parametrize(
    "characters,parents,meaning",
    [
        (("a", "b", "c"), (("a", "b"), ("b", "c")), "biological_grandparent"),
        (("c", "b", "a"), (("b", "c"), ("a", "b")), "biological_grandchild"),
        (("b", "a", "c"), (("a", "b"), ("a", "c")), "biological_sibling"),
    ],
)
def test_derived_biological_meanings_follow_direction(
    characters: tuple[str, ...],
    parents: tuple[tuple[str, str], ...],
    meaning: ConnectionMeaning,
) -> None:
    steps = tuple(
        biological(p, c, characters[i], characters[i + 1]) for i, (p, c) in enumerate(parents)
    )
    path = ConnectionPath(characters=characters, steps=steps, meaning=meaning)
    assert path.meaning == meaning
    with pytest.raises(ValidationError, match="Derived meaning"):
        ConnectionPath.model_validate(path.model_dump() | {"meaning": "biological_parent"})


def test_social_step_cannot_become_biological_ancestry() -> None:
    adoption = RelationshipStep.model_validate(
        {
            "kind": "relationship",
            "from_id": "b",
            "to_id": "c",
            "direction": "subject_to_object",
            "claim": {
                "claim_id": "synthetic-adoption",
                "subject_id": "b",
                "object_id": "c",
                "relation": "adoptive_parent",
                "episode_id": "synthetic-episode",
                "status": "unknown",
                "polarity": "affirmed",
                "certainty": "certain",
                "story_time": "unknown",
                "time_precision": "unknown",
                "after_claim_id": None,
                "evidence": [
                    {"evidence_id": "synthetic-adoption", "start": 0, "end": 1, "quote": "x"}
                ],
            },
        }
    )
    steps = (biological("a", "b", "a", "b"), adoption)
    assert ConnectionPath(characters=("a", "b", "c"), steps=steps, meaning="connection")
    with pytest.raises(ValidationError, match="Derived meaning"):
        ConnectionPath(characters=("a", "b", "c"), steps=steps, meaning="biological_grandparent")


def test_paths_reject_reversed_edges_repeated_characters_and_disjoint_steps() -> None:
    step = biological("a", "b", "a", "b")
    with pytest.raises(ValidationError, match="direction"):
        BiologicalStep.model_validate(step.model_dump() | {"direction": "child_to_parent"})
    with pytest.raises(ValidationError, match="repeat characters"):
        ConnectionPath(
            characters=("a", "b", "a"),
            steps=(step, biological("a", "b", "b", "a")),
            meaning="connection",
        )
    with pytest.raises(ValidationError, match="next pair"):
        ConnectionPath(characters=("a", "c"), steps=(step,), meaning="biological_parent")


@pytest.mark.parametrize(
    "change",
    [
        {"max_depth": 7},
        {"max_paths": 21},
        {"max_expansions": 5001},
        {"target_id": "a"},
        {"sql": "SELECT * FROM source_snapshots"},
    ],
)
def test_connection_arguments_cannot_bypass_typed_bounds(change: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ConnectionQuery.model_validate(
            {"kind": "connection", "character_id": "a", "target_id": "b", **change}
        )
