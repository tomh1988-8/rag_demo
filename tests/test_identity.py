import pytest

from ask_phil.identity import Character, IdentityCatalogue


def test_reviewed_alias_resolves_to_character_but_performer_does_not() -> None:
    catalogue = IdentityCatalogue(
        characters=(
            Character(
                character_id="sharon-watts",
                name="Sharon Watts",
                aliases=("Sharon Rickman", "Sharon Mitchell"),
                performers=("Letitia Dean",),
                coverage="core",
                wikidata_id="Q7490258",
                review_note="Reviewed Wikipedia identity/alias fields; not plot corroboration.",
            ),
        )
    )

    resolved = catalogue.resolve("  SHARON\t Mitchell ")
    assert resolved.status == "resolved"
    assert resolved.character_ids == ("sharon-watts",)
    actor = catalogue.resolve("Letitia Dean")
    assert actor.status == "performer"
    assert actor.character_ids == ()
    assert catalogue.resolve("Sharon Unknown").status == "unknown"


def test_shared_alias_requires_clarification_and_duplicate_identifiers_are_rejected() -> None:
    first = Character(
        character_id="ben-mitchell",
        name="Ben Mitchell",
        aliases=("Mitchell",),
        performers=("Charlie Jones", "Max Bowden"),
        coverage="core",
        wikidata_id="Q2766568",
        review_note="Reviewed recasts; one character.",
    )
    second = Character(
        character_id="sharon-watts",
        name="Sharon Watts",
        aliases=("Mitchell",),
        coverage="core",
        wikidata_id="Q7490258",
        review_note="Ambiguity test.",
    )
    catalogue = IdentityCatalogue(characters=(first, second))
    assert catalogue.resolve("Mitchell").status == "ambiguous"
    assert catalogue.resolve("Mitchell").character_ids == ("ben-mitchell", "sharon-watts")
    assert catalogue.resolve("Charlie Jones").status == "performer"
    assert catalogue.resolve("Max Bowden").status == "performer"
    with pytest.raises(ValueError, match="unique"):
        IdentityCatalogue(characters=(first, first))
