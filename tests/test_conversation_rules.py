from uuid import uuid4

import pytest

from ask_phil.conversation import ReferenceTurn, resolve_reference
from ask_phil.identity import Character, IdentityCatalogue


def catalogue() -> IdentityCatalogue:
    return IdentityCatalogue(
        characters=(
            Character(
                character_id="phil-mitchell",
                name="Phil Mitchell",
                coverage="core",
                wikidata_id="Q1",
                review_note="Synthetic identity fixture.",
            ),
            Character(
                character_id="grant-mitchell",
                name="Grant Mitchell",
                coverage="core",
                wikidata_id="Q2",
                review_note="Synthetic identity fixture.",
            ),
            Character(
                character_id="kat-slater",
                name="Kat Slater",
                aliases=("Kat Moon",),
                coverage="core",
                wikidata_id="Q3",
                review_note="Synthetic identity fixture.",
            ),
        )
    )


def test_followup_resolves_only_reviewed_character_references() -> None:
    turn_id = uuid4()
    history = (ReferenceTurn(turn_id=turn_id, character_ids=("phil-mitchell",)),)
    resolved = resolve_reference("When did he arrive?", catalogue(), history)
    assert resolved.question == "When did Phil Mitchell arrive?"
    assert resolved.character_ids == ("phil-mitchell",)
    assert resolved.context_turn_id == turn_id
    assert resolved.clarification is None

    alias = resolve_reference("Who is Kat Moon's father?", catalogue(), ())
    assert alias.character_ids == ("kat-slater",)
    assert alias.question == "Who is Kat Slater's father?"


@pytest.mark.parametrize(
    "question,ids",
    [
        ("When did he arrive?", ()),
        ("When did Mitchell arrive?", ()),
        ("When did he arrive?", ("phil-mitchell", "grant-mitchell")),
    ],
)
def test_missing_or_ambiguous_identity_requests_clarification(
    question: str, ids: tuple[str, ...]
) -> None:
    result = resolve_reference(
        question, catalogue(), (ReferenceTurn(turn_id=uuid4(), character_ids=ids),)
    )
    assert result.clarification
    if "phil-mitchell" in result.character_ids:
        assert "Phil Mitchell" in result.clarification
        assert "Grant Mitchell" in result.clarification


def test_truncated_or_unreviewed_references_cannot_be_reconstructed() -> None:
    history = (ReferenceTurn(turn_id=uuid4(), character_ids=("phil-mitchell",)),) + tuple(
        ReferenceTurn(turn_id=uuid4(), character_ids=()) for _ in range(8)
    )
    assert resolve_reference("When did he arrive?", catalogue(), history).clarification
    assert resolve_reference("Who is Phil Unknown's father?", catalogue(), ()).clarification


def test_explicit_selection_answers_the_pending_ambiguous_question() -> None:
    pending = ReferenceTurn(
        turn_id=uuid4(),
        character_ids=("phil-mitchell", "grant-mitchell"),
        pending_question="When did he arrive?",
    )
    selected = resolve_reference("Phil Mitchell", catalogue(), (pending,))
    assert selected.question == "When did Phil Mitchell arrive?"
    assert selected.context_turn_id == pending.turn_id
    assert selected.clarification is None


def test_reference_expansion_cannot_exceed_the_question_budget() -> None:
    result = resolve_reference(
        "he " * 150,
        catalogue(),
        (ReferenceTurn(turn_id=uuid4(), character_ids=("phil-mitchell",)),),
    )
    assert result.clarification
    assert len(result.question.encode()) <= 1000


def test_relationship_qualifiers_and_object_pronouns_keep_their_meaning() -> None:
    former = resolve_reference("Who was Phil Mitchell's former wife?", catalogue(), ())
    assert former.question == "Who was Phil Mitchell's former wife?"
    assert former.clarification is None
    former_noun = resolve_reference("Who was the former wife of Phil Mitchell?", catalogue(), ())
    assert former_noun.clarification is None
    kat = (ReferenceTurn(turn_id=uuid4(), character_ids=("kat-slater",)),)
    object_reference = resolve_reference("Who married her before she left?", catalogue(), kat)
    assert object_reference.question == "Who married Kat Slater before Kat Slater left?"
    assert resolve_reference(
        "When did Phil Mitchell first meet her?", catalogue(), ()
    ).clarification


def test_explicit_new_subject_preserves_aliases_and_resolves_its_possessive() -> None:
    history = (ReferenceTurn(turn_id=uuid4(), character_ids=("phil-mitchell",)),)
    result = resolve_reference("Who is Kat Moon and who is her father?", catalogue(), history)
    assert result.question == "Who is Kat Slater and who is Kat Slater's father?"
    assert result.character_ids == ("kat-slater",)
    assert result.clarification is None


@pytest.mark.parametrize("question", ["who is cindy williams?", "who is max bowden?"])
def test_partial_and_performer_names_do_not_create_character_reference_state(question: str) -> None:
    import gzip
    import json
    from pathlib import Path

    batch = json.loads(gzip.decompress(Path("data/sources/core-profiles-v2.json.gz").read_bytes()))
    result = resolve_reference(question, IdentityCatalogue.model_validate(batch["catalogue"]), ())
    assert result.clarification
    assert result.character_ids == ()


def test_selection_replaces_ambiguous_surname_and_resumes_all_parts() -> None:
    pending = ReferenceTurn(
        turn_id=uuid4(),
        character_ids=("phil-mitchell", "grant-mitchell"),
        pending_question="When did Mitchell arrive and who is his mother?",
    )
    selected = resolve_reference("Phil Mitchell", catalogue(), (pending,))
    assert selected.question == "When did Phil Mitchell arrive and who is Phil Mitchell's mother?"
    assert selected.clarification is None


def test_named_objects_do_not_replace_a_preceding_retained_subject() -> None:
    history = (ReferenceTurn(turn_id=uuid4(), character_ids=("phil-mitchell",)),)
    result = resolve_reference("Was he married to Kat Slater?", catalogue(), history)
    assert result.question == "Was Phil Mitchell married to Kat Slater?"
    assert result.clarification is None
    result = resolve_reference("Is he Grant Mitchell's brother?", catalogue(), history)
    assert result.question == "Is Phil Mitchell Grant Mitchell's brother?"


def test_distinct_unnamed_participants_require_a_question_with_both_names() -> None:
    history = (ReferenceTurn(turn_id=uuid4(), character_ids=("phil-mitchell",)),)
    assert resolve_reference("Did he marry her?", catalogue(), history).clarification
    pending = ReferenceTurn(
        turn_id=uuid4(),
        character_ids=("phil-mitchell", "kat-slater"),
        pending_question="Did he marry her?",
    )
    result = resolve_reference("Phil Mitchell", catalogue(), (pending,))
    assert result.clarification
    assert result.question != "Did Phil Mitchell marry Phil Mitchell?"


@pytest.mark.parametrize(
    "question,expected",
    [
        ("When did Phil arrive?", "When did Phil Mitchell arrive?"),
        ("Who is Phil's father?", "Who is Phil Mitchell's father?"),
        ("When did that character arrive?", "When did Phil Mitchell arrive?"),
        ("When did the latter arrive?", "When did Phil Mitchell arrive?"),
    ],
)
def test_supported_selection_preserves_the_pending_request(question: str, expected: str) -> None:
    missing = resolve_reference(question, catalogue(), ())
    assert missing.clarification
    pending = ReferenceTurn(
        turn_id=uuid4(), character_ids=missing.character_ids, pending_question=missing.question
    )
    result = resolve_reference("Phil Mitchell", catalogue(), (pending,))
    assert result.clarification is None
    assert result.question == expected


def test_missing_identity_stops_older_context_from_reappearing() -> None:
    history = (
        ReferenceTurn(turn_id=uuid4(), character_ids=("phil-mitchell",)),
        ReferenceTurn(turn_id=uuid4(), character_ids=(), pending_question="Who is Phil Unknown?"),
    )
    assert resolve_reference("When did he arrive?", catalogue(), history).clarification
    selected = resolve_reference("Phil Mitchell", catalogue(), history)
    assert selected.clarification
    assert selected.character_ids == ()
