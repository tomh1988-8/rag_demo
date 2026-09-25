"""Reviewed character identities, without inferring identities from performers."""

import unicodedata
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator


def normalize_name(name: str) -> str:
    """Ignore case and spacing, preserving punctuation and meaningful name differences."""
    return " ".join(unicodedata.normalize("NFC", name).casefold().split())


class Character(BaseModel, frozen=True, extra="forbid"):
    character_id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    aliases: tuple[str, ...] = ()
    performers: tuple[str, ...] = ()
    coverage: Literal["core", "supporting"]
    wikidata_id: Annotated[str, Field(pattern=r"^Q[1-9][0-9]*$")]
    review_note: Annotated[str, Field(min_length=1, max_length=4000)]
    evidence_sources: tuple[str, ...] = ()


class IdentityResolution(BaseModel, frozen=True, extra="forbid"):
    status: Literal["resolved", "ambiguous", "performer", "unknown"]
    character_ids: tuple[str, ...] = ()


class IdentityCatalogue(BaseModel, frozen=True, extra="forbid"):
    characters: tuple[Character, ...]

    @model_validator(mode="after")
    def unique_characters(self) -> Self:
        for key in ("character_id", "wikidata_id"):
            if len({getattr(c, key) for c in self.characters}) != len(self.characters):
                raise ValueError("Character and Wikidata identifiers must be unique.")
        return self

    def resolve(self, name: str) -> IdentityResolution:
        normalized = normalize_name(name)
        matches = tuple(
            character.character_id
            for character in self.characters
            if normalized in {normalize_name(n) for n in (character.name, *character.aliases)}
        )
        if matches:
            return IdentityResolution(
                status="resolved" if len(matches) == 1 else "ambiguous", character_ids=matches
            )
        if any(
            normalized == normalize_name(performer)
            for character in self.characters
            for performer in character.performers
        ):
            return IdentityResolution(status="performer")
        return IdentityResolution(status="unknown")
