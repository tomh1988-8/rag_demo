"""Revision-bound sentence windows with independently resolvable captured spans."""

import hashlib
import re
from dataclasses import dataclass

from ask_phil.evidence import Passage, Record, SourceSnapshot
from ask_phil.passage_context import assemble_context, context_text
from ask_phil.retrieval import RetrievedPassage

SENTENCE_VERSION = "captured-sentences-v1"


class ExpansionWindow(Record):
    original_evidence_ids: tuple[str, ...]
    source_evidence_ids: tuple[str, ...]
    spans: tuple[Passage, ...]
    added_span_ids: tuple[str, ...] = ()
    selected: bool = True


class ContextExpansion(Record):
    context: tuple[Passage, ...]
    windows: tuple[ExpansionWindow, ...]
    byte_budget: int
    truncated: bool = False
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class _Sentence:
    passage: Passage
    run: int


def _sentences(snapshot: SourceSnapshot) -> tuple[_Sentence, ...]:
    if snapshot.imported is None:
        return ()
    fingerprint = snapshot.fingerprint
    paragraphs = {
        (p.location.source_id, p.location.paragraph_ordinal): p
        for p in snapshot.passages
        if p.location
    }
    result: list[_Sentence] = []
    run = 0
    for document in snapshot.imported.documents:
        previous_section: tuple[str, ...] | None = None
        run += 1
        for index, paragraph in enumerate(document.spans):
            exemplar = paragraphs.get((document.source_id, index))
            if paragraph.scope != "main_series" or exemplar is None:
                previous_section = None
                run += 1
                continue
            if previous_section != paragraph.section:
                run += 1
            previous_section = paragraph.section
            if (
                exemplar.source is None
                or exemplar.location is None
                or exemplar.source.revision_id != document.revision_id
                or document.text[paragraph.start : paragraph.end] != paragraph.text
                or hashlib.sha256(paragraph.text.encode()).hexdigest() != paragraph.sha256
                or paragraph.ordinal != index
            ):
                raise ValueError("Sentence windows require intact admitted source locators.")
            for match in re.finditer(r"\S.*?(?:[.!?](?=\s|$)|$)", paragraph.text, re.DOTALL):
                text = match.group()
                start = paragraph.start + match.start()
                end = paragraph.start + match.end()
                identity = (
                    f"{SENTENCE_VERSION}:{fingerprint}:{document.source_id}:"
                    f"{document.revision_id}:{start}:{end}"
                )
                result.append(
                    _Sentence(
                        passage=Passage(
                            evidence_id="sent-"
                            + hashlib.sha256(identity.encode()).hexdigest()[:40],
                            text=text,
                            sha256=hashlib.sha256(text.encode()).hexdigest(),
                            start=start,
                            end=end,
                            source=exemplar.source,
                            location=exemplar.location,
                        ),
                        run=run,
                    )
                )
    return tuple(result)


def resolve_span(snapshot: SourceSnapshot, evidence_id: str) -> Passage | None:
    """Resolve canonical originals or derived sentences using only the named snapshot."""
    original = next((p for p in snapshot.passages if p.evidence_id == evidence_id), None)
    if original is not None or not evidence_id.startswith("sent-"):
        return original
    return next(
        (s.passage for s in _sentences(snapshot) if s.passage.evidence_id == evidence_id), None
    )


def expand_context(
    snapshot: SourceSnapshot,
    hits: tuple[RetrievedPassage, ...],
    *,
    byte_budget: int,
    neighbours: int = 1,
) -> ContextExpansion:
    """Merge intersecting windows; original hits and added spans retain their locators."""
    if not 0 <= neighbours <= 3 or byte_budget < 2 or len(hits) > 20:
        raise ValueError("Sentence expansion requires bounded neighbours and a JSON budget.")
    originals = {p.evidence_id: p for p in snapshot.passages}
    if any(originals.get(h.passage.evidence_id) != h.passage for h in hits):
        raise ValueError("Expansion hits must belong to this exact captured snapshot.")
    sentences = _sentences(snapshot)
    if not sentences:
        return ContextExpansion(
            context=assemble_context(hits, byte_budget),
            windows=(),
            byte_budget=byte_budget,
            truncated=len(assemble_context(hits, byte_budget)) < len(hits),
            unavailable_reason="source_has_no_ordered_sentences",
        )
    groups: list[tuple[list[str], set[int]]] = []
    for hit in hits:
        anchor = hit.passage
        matching = [
            i
            for i, sentence in enumerate(sentences)
            if sentence.passage.location == anchor.location
            and sentence.passage.start < anchor.end
            and sentence.passage.end > anchor.start
        ]
        if not matching:
            continue
        first, last = matching[0], matching[-1]
        window = {
            i
            for i in range(max(0, first - neighbours), min(len(sentences), last + neighbours + 1))
            if sentences[i].run == sentences[first].run
        }
        identifiers = [anchor.evidence_id]
        overlapping = [group for group in groups if group[1] & window]
        for group in overlapping:
            identifiers = list(dict.fromkeys((*group[0], *identifiers)))
            window |= group[1]
            groups.remove(group)
        groups.append((identifiers, window))
    priority = {h.passage.evidence_id: i for i, h in enumerate(hits)}
    groups.sort(key=lambda group: min(priority[eid] for eid in group[0]))
    windows = tuple(
        ExpansionWindow(
            original_evidence_ids=tuple(identifiers),
            source_evidence_ids=tuple(
                p.evidence_id
                for p in snapshot.passages
                if any(
                    p.location == sentences[i].passage.location
                    and p.start < sentences[i].passage.end
                    and p.end > sentences[i].passage.start
                    for i in indices
                )
            ),
            spans=tuple(sentences[i].passage for i in sorted(indices)),
            added_span_ids=tuple(
                sentences[i].passage.evidence_id
                for i in sorted(indices)
                if not any(
                    h.passage.location == sentences[i].passage.location
                    and h.passage.start <= sentences[i].passage.start
                    and h.passage.end >= sentences[i].passage.end
                    for h in hits
                    if h.passage.evidence_id in identifiers
                )
            ),
        )
        for identifiers, indices in groups
    )
    context: tuple[Passage, ...] = ()
    selected_windows = []
    for prepared_window in windows:
        selected = len(context_text((*context, *prepared_window.spans)).encode()) <= byte_budget
        if selected:
            context = (*context, *prepared_window.spans)
        selected_windows.append(prepared_window.model_copy(update={"selected": selected}))
    return ContextExpansion(
        context=context,
        windows=tuple(selected_windows),
        byte_budget=byte_budget,
        truncated=any(not w.selected for w in selected_windows),
    )
