import pytest

from ask_phil.identity import Character, IdentityCatalogue


@pytest.fixture
def catalogue() -> IdentityCatalogue:
    return IdentityCatalogue(
        characters=(
            Character(
                character_id="sharon-watts",
                name="Sharon Watts",
                aliases=("Sharon Rickman", "Sharon Mitchell", "Mitchell"),
                performers=("Letitia Dean",),
                coverage="core",
                wikidata_id="Q7490258",
                review_note="Reviewed Wikipedia identity/alias fields; not plot corroboration.",
            ),
            Character(
                character_id="ben-mitchell",
                name="Ben Mitchell",
                aliases=("Mitchell",),
                performers=("Charlie Jones", "Max Bowden"),
                coverage="core",
                wikidata_id="Q2766568",
                review_note="Reviewed recasts; one character.",
            ),
        )
    )


def test_reviewed_alias_resolves_to_character(catalogue: IdentityCatalogue) -> None:
    resolved = catalogue.resolve("  SHARON\t Mitchell ")
    assert resolved.status == "resolved"
    assert resolved.character_ids == ("sharon-watts",)


@pytest.mark.parametrize("name", ["Letitia Dean", "Charlie Jones", "Max Bowden"])
def test_performers_are_not_character_aliases(catalogue: IdentityCatalogue, name: str) -> None:
    actor = catalogue.resolve(name)
    assert actor.status == "performer"
    assert actor.character_ids == ()


def test_unreviewed_name_is_unknown(catalogue: IdentityCatalogue) -> None:
    assert catalogue.resolve("Sharon Unknown").status == "unknown"


def test_shared_alias_requires_clarification(catalogue: IdentityCatalogue) -> None:
    assert catalogue.resolve("Mitchell").status == "ambiguous"
    assert set(catalogue.resolve("Mitchell").character_ids) == {"ben-mitchell", "sharon-watts"}


def test_duplicate_identifiers_are_rejected(catalogue: IdentityCatalogue) -> None:
    with pytest.raises(ValueError, match="unique"):
        IdentityCatalogue(characters=(catalogue.characters[0], catalogue.characters[0]))
