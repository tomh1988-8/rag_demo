"""Bounded conversation references; generated assertions are never reference state."""

import re
import unicodedata
from uuid import UUID

from pydantic import Field

from ask_phil.evidence import Record
from ask_phil.identity import IdentityCatalogue

MAX_CONTEXT_TURNS = 8
REFERENCE_WORDS = re.compile(
    r"\b(he|she|they|him|her|them|his|their|former|latter)\b|\b(?:that|this) character\b",
    re.IGNORECASE,
)


class ReferenceTurn(Record):
    turn_id: UUID
    character_ids: tuple[str, ...]
    pending_question: str | None = Field(default=None, max_length=1000)


class ReferenceResolution(Record):
    question: str
    character_ids: tuple[str, ...]
    context_turn_id: UUID | None = None
    clarification: str | None = None


class TurnIdentity(Record):
    session_id: UUID
    turn_id: UUID
    turn_number: int
    generation: int


class ConversationReference(TurnIdentity):
    reference: ReferenceResolution


def resolve_reference(
    question: str, catalogue: IdentityCatalogue, history: tuple[ReferenceTurn, ...]
) -> ReferenceResolution:
    """Resolve names/aliases and singular follow-ups using only reviewed identities."""
    question = unicodedata.normalize("NFC", question)
    names = {c.character_id: c.name for c in catalogue.characters}
    mentions: list[tuple[int, int, str]] = []
    for character in catalogue.characters:
        for alias in (
            character.name,
            *character.aliases,
            *character.name.split()[:1],
            character.name.split()[-1],
        ):
            pattern = r"(?<!\w)" + r"\s+".join(map(re.escape, alias.split())) + r"(?!\w)"
            for match in re.finditer(pattern, question, re.IGNORECASE):
                mentions.append((match.start(), match.end(), character.character_id))
    # A complete name wins over its overlapping first name or surname. Preserve
    # multiple identities sharing the exact same mention instead of picking one.
    selected: list[tuple[int, int, tuple[str, ...]]] = []
    for start, end, _ in sorted(mentions, key=lambda m: (m[0], -(m[1] - m[0]))):
        if selected and start < selected[-1][1]:
            continue
        candidates = tuple(dict.fromkeys(m[2] for m in mentions if m[:2] == (start, end)))
        selected.append((start, end, candidates))
    ids = tuple(dict.fromkeys(c for _, _, candidates in selected for c in candidates))
    resolved = question
    ambiguous = any(len(candidates) != 1 for _, _, candidates in selected)
    # A short known name inside an unreviewed full name must not silently turn
    # that unknown person into the catalogue's character (e.g. Cindy Williams).
    if any(
        len(question[start:end].split()) == 1 and re.match(r"\s+[A-Z][\w-]+", question[end:])
        for start, end, _ in selected
    ):
        ambiguous = True
        ids = ()
    for start, end, candidates in reversed(selected):
        if len(candidates) == 1:
            resolved = resolved[:start] + names[candidates[0]] + resolved[end:]
    if (
        len(selected) == 1
        and len(ids) == 1
        and not ambiguous
        and history
        and history[-1].pending_question
        and question.strip(" .?!") == question[selected[0][0] : selected[0][1]]
    ):
        pending = history[-1].pending_question
        # A bare identity is an answer to the pending clarification. Only the
        # retained user question is resumed; no generated assertion is consulted.
        if REFERENCE_WORDS.search(pending):
            selection = resolve_reference(
                pending, catalogue, (ReferenceTurn(turn_id=history[-1].turn_id, character_ids=ids),)
            )
            return selection
    context_turn_id = None
    if REFERENCE_WORDS.search(question):
        previous = next(
            (t for t in reversed(history[-MAX_CONTEXT_TURNS:]) if t.character_ids), None
        )
        if previous:
            ids = tuple(dict.fromkeys((*ids, *previous.character_ids)))
            context_turn_id = previous.turn_id
        ambiguous = ambiguous or len(ids) != 1 or any(c not in names for c in ids)
        if not ambiguous:

            def replace(match: re.Match[str]) -> str:
                possessive = match.group().lower() in {"his", "their"} or (
                    match.group().lower() == "her"
                    and re.match(r"\s+\w", question[match.end() :]) is not None
                )
                return names[ids[0]] + ("'s" if possessive else "")

            resolved = REFERENCE_WORDS.sub(replace, question)
    clarification = None
    if ambiguous:
        choices = ", ".join(names[c] for c in ids if c in names)
        clarification = (
            f"Which character do you mean: {choices}?"
            if choices
            else "Which character do you mean? Please give their name; "
            "earlier context is unavailable."
        )
    if len(resolved) > 500 or len(resolved.encode()) > 1000:
        resolved = question
        clarification = "Please shorten the question and give the character's full name."
    return ReferenceResolution(
        question=resolved,
        character_ids=ids,
        context_turn_id=context_turn_id,
        clarification=clarification,
    )
