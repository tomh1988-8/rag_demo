"""Source-span context sufficiency, separate from answer/model-quality review."""

import hashlib
from typing import Self

from pydantic import Field, model_validator

from ask_phil.evidence import Passage, Record, SourceSnapshot
from ask_phil.source_windows import resolve_span


class SpanExpectation(Record):
    source_id: str
    revision_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str
    sha256: str | None = None

    @model_validator(mode="after")
    def exact_quote(self) -> Self:
        if self.end - self.start != len(self.text) or (
            self.sha256 is not None
            and self.sha256 != hashlib.sha256(self.text.encode()).hexdigest()
        ):
            raise ValueError("Expected source span must match its quote and fingerprint.")
        return self


class ContextCoverage(Record):
    covered_facts: int
    required_facts: int
    coverage: float | None
    sufficient: bool


def score_text_context(
    snapshot: SourceSnapshot,
    required_spans: tuple[tuple[SpanExpectation, ...], ...],
    context: tuple[Passage, ...],
    *,
    answerable: bool,
) -> ContextCoverage:
    """Each fact requires all its labelled spans; adjacency can cover split source quotes.

    Labels describe selected sufficient source spans, not exhaustive passage relevance.
    Unknown/no factual denominator is unavailable, never a perfect factual score.
    """
    for passage in context:
        if resolve_span(snapshot, passage.evidence_id) != passage:
            raise ValueError("Scored context must resolve to this exact captured snapshot.")
    documents = {d.source_id: d for d in snapshot.imported.documents} if snapshot.imported else {}

    def covered(expected: SpanExpectation) -> bool:
        document = documents.get(expected.source_id)
        if (
            document is None
            or document.revision_id != expected.revision_id
            or document.text[expected.start : expected.end] != expected.text
            or not any(
                s.scope == "main_series" and s.start <= expected.start < expected.end <= s.end
                for s in document.spans
            )
        ):
            raise ValueError(
                "Expected sufficient spans must be admitted in this captured revision."
            )
        cursor = expected.start
        for start, end in sorted(
            (p.start, p.end)
            for p in context
            if p.location
            and p.location.source_id == expected.source_id
            and p.source
            and p.source.revision_id == expected.revision_id
        ):
            if start <= cursor:
                cursor = max(cursor, end)
            if cursor >= expected.end:
                return True
        return False

    if any(not spans for spans in required_spans):
        raise ValueError("Every required fact needs independently labelled sufficient spans.")
    count = sum(all(covered(span) for span in spans) for spans in required_spans)
    total = len(required_spans)
    return ContextCoverage(
        covered_facts=count,
        required_facts=total,
        coverage=count / total if total else None,
        sufficient=answerable and total > 0 and count == total,
    )
