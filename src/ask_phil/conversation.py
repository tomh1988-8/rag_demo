"""Bounded character references; generated assertions never become reference state."""

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID

from pydantic import Field

from ask_phil.evidence import Record
from ask_phil.identity import IdentityCatalogue

MAX_CONTEXT_TURNS = 8
PRONOUNS = re.compile(r"\b(he|she|they|him|her|them|his|their)\b", re.IGNORECASE)
UNSUPPORTED_REFERENCE = re.compile(
    r"\bthe (?:former|latter)\b(?!\s+(?:wife|husband|partner|spouse|relationship|"
    r"owner|landlord|landlady|tenant|boss|job|home|house|flat)\b)|"
    r"\b(?:that|this) (?:character|person)\b",
    re.IGNORECASE,
)
PARTIAL_NAME_BOUNDARY = re.compile(
    r"^(?:['’]s\b|[?!.,]|$|\s+(?:arriv(?:e|ed|es)|first|marry|married|meet|met|open|opened|"
    r"leave|left|become|became|die|died|go|went|have|has|had|is|was|were|and|or|in|at|to|with|"
    r"before|after|ever|never)\b)",
    re.IGNORECASE,
)
POSSESSIVE_HER = re.compile(
    r"\s+(?:(?:first|second|former|current|biological|adoptive|older|younger|late|new)\s+)*"
    r"(?:father|mother|parents?|brother|sister|sons?|daughters?|children|husband|wife|partner|"
    r"family|name|age|arrival|departure|birth|death|story|marriage|career|history|relationship)\b",
    re.IGNORECASE,
)
RELATIONSHIP_REFERENCE = re.compile(
    r"\b(?:father|mother|parents?|brothers?|sisters?|sons?|daughters?|children|"
    r"husbands?|wives|wife|partners?|spouse)\b",
    re.IGNORECASE,
)


class ReferenceTurn(Record):
    turn_id: UUID
    character_ids: tuple[str, ...]
    pending_question: str | None = Field(default=None, max_length=1000)
    reference_barrier: bool = False


class ReferenceResolution(Record):
    question: str
    character_ids: tuple[str, ...]
    context_turn_id: UUID | None = None
    clarification: str | None = None
    followup_requires_name: bool = False


class TurnIdentity(Record):
    session_id: UUID
    turn_id: UUID
    turn_number: int
    generation: int


class ConversationReference(TurnIdentity):
    reference: ReferenceResolution


@dataclass(frozen=True)
class _NameMention:
    start: int
    end: int
    character_ids: tuple[str, ...]
    reviewed: bool


def _pattern(name: str) -> str:
    return r"(?<!\w)" + r"\s+".join(map(re.escape, name.split())) + r"(?!\w)"


def _mentions(question: str, catalogue: IdentityCatalogue) -> tuple[_NameMention, ...]:
    matches: dict[tuple[int, int, bool], list[str]] = {}
    performers = [
        m.span()
        for c in catalogue.characters
        for name in c.performers
        for m in re.finditer(_pattern(name), question, re.IGNORECASE)
    ]
    for character in catalogue.characters:
        for name in (character.name, *character.aliases):
            # Partial names propose a clarification; they do not silently create
            # an identity inside unknown full names, regardless of capitalization.
            for alias, reviewed in (
                (name, True),
                (name.split()[0], False),
                (name.split()[-1], False),
            ):
                for match in re.finditer(_pattern(alias), question, re.IGNORECASE):
                    if not reviewed and any(
                        a <= match.start() < match.end() <= b for a, b in performers
                    ):
                        continue
                    matches.setdefault((*match.span(), reviewed), []).append(character.character_id)
    selected: list[_NameMention] = []
    for (start, end, reviewed), ids in sorted(
        matches.items(), key=lambda item: (item[0][0], -(item[0][1] - item[0][0]), not item[0][2])
    ):
        if not selected or start >= selected[-1].end:
            selected.append(_NameMention(start, end, tuple(dict.fromkeys(ids)), reviewed))
    return tuple(selected)


def _possessive(match: re.Match[str], text: str) -> bool:
    word = match.group().casefold()
    return word in {"his", "their"} or (
        word == "her" and POSSESSIVE_HER.match(text[match.end() :]) is not None
    )


def _substitute(question: str, edits: list[tuple[int, int, str]]) -> str:
    for start, end, replacement in sorted(edits, reverse=True):
        question = question[:start] + replacement + question[end:]
    return question


def _multiple_reference_roles(question: str) -> bool:
    pronouns = list(PRONOUNS.finditer(question))
    families = {
        "male"
        if p.group().casefold() in {"he", "him", "his"}
        else "female"
        if p.group().casefold() in {"she", "her"}
        else "plural"
        for p in pronouns
    }
    # Distinct unnamed participants need explicit names. One selection must not
    # collapse a subject and its non-reflexive object into the same character.
    return len(families) > 1 or any(
        first.group().casefold() in {"he", "she", "they"}
        and second.group().casefold() in {"him", "her", "them"}
        and not _possessive(second, question)
        for index, first in enumerate(pronouns)
        for second in pronouns[index + 1 :]
    )


def resolve_reference(
    question: str, catalogue: IdentityCatalogue, history: tuple[ReferenceTurn, ...]
) -> ReferenceResolution:
    """Use reviewed names or a single retained antecedent, otherwise clarify.

    Full catalogue names/aliases resolve in free text. Unique partial names are
    accepted only as a bare clarification choice. Subject/possessive pronouns may
    refer to an explicit current subject; object pronouns require prior context.
    No gender or relationship is inferred from an assistant answer.
    """
    question = unicodedata.normalize("NFC", question)
    names = {c.character_id: c.name for c in catalogue.characters}
    mentions = _mentions(question, catalogue)
    bare = (
        len(mentions) == 1
        and question.strip(" .?!") == question[mentions[0].start : mentions[0].end]
    )
    if bare and len(mentions[0].character_ids) == 1 and history and history[-1].pending_question:
        chosen = mentions[0].character_ids[0]
        pending = history[-1].pending_question
        if _multiple_reference_roles(pending):
            return ReferenceResolution(
                question=pending,
                character_ids=(),
                context_turn_id=history[-1].turn_id,
                clarification="Please restate the question with a name for each character.",
            )
        edits = [
            (m.start, m.end, names[chosen])
            for m in _mentions(pending, catalogue)
            if chosen in m.character_ids
            and (
                len(m.character_ids) > 1
                or (not m.reviewed and PARTIAL_NAME_BOUNDARY.search(pending[m.end :]) is not None)
            )
        ]
        edits += [
            (m.start(), m.end(), names[chosen] + ("'s" if _possessive(m, pending) else ""))
            for m in PRONOUNS.finditer(pending)
        ]
        edits += [
            (m.start(), m.end(), names[chosen]) for m in UNSUPPORTED_REFERENCE.finditer(pending)
        ]
        if edits:
            resumed = resolve_reference(_substitute(pending, edits), catalogue, ())
            return resumed.model_copy(update={"context_turn_id": history[-1].turn_id})
        return ReferenceResolution(
            question=pending,
            character_ids=(),
            context_turn_id=history[-1].turn_id,
            clarification="Please repeat the question using the character's full name.",
        )

    edits = []
    ids: list[str] = []
    ambiguous_ids: list[str] = []
    missing = False
    for mention in mentions:
        if len(mention.character_ids) > 1:
            ambiguous_ids.extend(mention.character_ids)
        elif mention.reviewed or bare:
            character_id = mention.character_ids[0]
            ids.append(character_id)
            edits.append((mention.start, mention.end, names[character_id]))
        else:
            missing = True
    current = tuple(dict.fromkeys(ids))
    # An unresolved clarification is a barrier, even if no candidate survived;
    # do not revive an older identity across an unknown name or missing reference.
    previous = next(
        (
            t
            for t in reversed(history[-MAX_CONTEXT_TURNS:])
            if t.character_ids or t.pending_question is not None or t.reference_barrier
        ),
        None,
    )
    context_turn_id = None
    for pronoun in PRONOUNS.finditer(question):
        object_pronoun = pronoun.group().casefold() in {"him", "her", "them"} and not _possessive(
            pronoun, question
        )
        preceding = tuple(
            dict.fromkeys(
                c
                for m in mentions
                if m.reviewed and m.end <= pronoun.start() and len(m.character_ids) == 1
                for c in m.character_ids
            )
        )
        if preceding and RELATIONSHIP_REFERENCE.search(question[: pronoun.start()]):
            missing = True
            continue
        candidates = (
            preceding
            if preceding and not object_pronoun
            else (previous.character_ids if previous else ())
        )
        if not preceding or object_pronoun:
            context_turn_id = previous.turn_id if previous else None
        if (
            len(candidates) != 1
            or candidates[0] not in names
            or (object_pronoun and candidates == current)
        ):
            ambiguous_ids.extend(candidates)
            missing = missing or not candidates or (object_pronoun and candidates == current)
            continue
        ids.extend(candidates)
        edits.append(
            (
                pronoun.start(),
                pronoun.end(),
                names[candidates[0]] + ("'s" if _possessive(pronoun, question) else ""),
            )
        )
    performer = any(
        re.search(_pattern(p), question, re.IGNORECASE)
        for c in catalogue.characters
        for p in c.performers
    )
    missing = (
        missing
        or bool(UNSUPPORTED_REFERENCE.search(question))
        or (performer and not current)
        or _multiple_reference_roles(question)
    )
    clarification = None
    if missing or ambiguous_ids:
        choices = ", ".join(names[c] for c in dict.fromkeys(ambiguous_ids) if c in names)
        clarification = (
            f"Which character do you mean: {choices}?"
            if choices and not missing
            else (
                "Which character do you mean? Please give their full name; "
                "the reference is unresolved in the available context."
            )
        )
    resolved = _substitute(question, edits)
    if len(resolved) > 500 or len(resolved.encode()) > 1000:
        resolved = question
        clarification = "Please shorten the question and give the character's full name."
    return ReferenceResolution(
        question=resolved,
        character_ids=() if missing else tuple(dict.fromkeys((*ids, *ambiguous_ids))),
        context_turn_id=context_turn_id,
        clarification=clarification,
        followup_requires_name=bool(RELATIONSHIP_REFERENCE.search(question)),
    )
