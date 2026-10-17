"""Whole source passages prepared and selected against their serialized context size."""

import hashlib
import json
from typing import TYPE_CHECKING, Literal

from ask_phil.evidence import Passage, Source
from ask_phil.source_records import SourceLocation, SourceSpan

if TYPE_CHECKING:
    from ask_phil.retrieval import RetrievedPassage

CONTEXT_BYTE_BUDGET = 1200
# Change this identity whenever passage preparation or its sizing policy changes.
PROJECTION_VERSION: Literal["html-context-fit-v2"] = "html-context-fit-v2"


def context_text(passages: tuple[Passage, ...]) -> str:
    return json.dumps(
        [
            {
                "evidence_id": p.evidence_id,
                "text": p.text,
                **({"source_title": p.source.title} if p.source else {}),
            }
            for p in passages
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )


def assemble_context(
    hits: tuple["RetrievedPassage", ...], byte_budget: int = CONTEXT_BYTE_BUDGET
) -> tuple[Passage, ...]:
    """Keep whole spans in retrieval order; a truncated excerpt cannot become a citation."""
    if byte_budget < 2:
        raise ValueError("Context budget must accommodate an empty JSON list.")
    selected: tuple[Passage, ...] = ()
    for hit in hits:
        candidate = (*selected, hit.passage)
        if len(context_text(candidate).encode()) <= byte_budget:
            selected = candidate
    return selected


def project_passages(
    span: SourceSpan, source: Source, location: SourceLocation
) -> tuple[Passage, ...]:
    """Preserve an admitted span as contiguous whole passages that each fit alone."""
    passages: list[Passage] = []
    start = span.start
    while start < span.end:
        remaining = span.text[start - span.start :]
        lower, upper = 1, min(len(remaining), CONTEXT_BYTE_BUDGET)
        fitted: Passage | None = None
        while lower <= upper:
            length = (lower + upper) // 2
            candidate = _passage(remaining[:length], start, source, location)
            if len(context_text((candidate,)).encode()) <= CONTEXT_BYTE_BUDGET:
                fitted = candidate
                lower = length + 1
            else:
                upper = length - 1
        if fitted is None:
            raise ValueError("Passage metadata leaves no room for text in the answer context.")
        if len(fitted.text) < len(remaining) and " " in fitted.text:
            fitted = _passage(fitted.text[: fitted.text.rfind(" ") + 1], start, source, location)
        passages.append(fitted)
        start = fitted.end
    return tuple(passages)


def _passage(text: str, start: int, source: Source, location: SourceLocation) -> Passage:
    return Passage(
        evidence_id=f"{location.source_id}-{location.paragraph_ordinal:04d}-{start}",
        text=text,
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        start=start,
        end=start + len(text),
        source=source,
        location=location,
    )
