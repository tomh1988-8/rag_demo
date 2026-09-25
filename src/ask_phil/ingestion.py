"""Explicit, revision-bound admission of captured source material into text evidence."""

import gzip
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from ask_phil.evidence import Passage, Source, SourceSnapshot
from ask_phil.source_records import CapturedSource as CapturedSource
from ask_phil.source_records import (
    ImportedSources,
    ImportIssue,
    ParsedSource,
    SourceLocation,
    SourceSpan,
    StructuredRecord,
)
from ask_phil.source_records import ScopeRule as ScopeRule
from ask_phil.source_records import SourceBatch as SourceBatch
from ask_phil.source_records import SourceRequest as SourceRequest
from ask_phil.source_records import WikipediaPolicy as WikipediaPolicy

USER_AGENT = "AskPhilResearch/0.1 (https://github.com/tomh1988-8/rag_demo)"


def read_batch(path: Path) -> SourceBatch:
    """Read a frozen UTF-8 batch, bounding decompression before validation."""
    with gzip.open(path, "rb") if path.suffix == ".gz" else path.open("rb") as source:
        content = source.read(25_000_001)
    if len(content) > 25_000_000:
        raise ValueError("Source batch exceeds the decoded file limit.")
    return SourceBatch.model_validate_json(content)


def capture_sources(
    requests: tuple[SourceRequest, ...], client: httpx.Client
) -> tuple[CapturedSource, ...]:
    """Capture a small batch once. HTTP failure never becomes an empty source record."""
    if not 1 <= len(requests) <= 20:
        raise ValueError("Capture batches contain 1–20 sources.")
    results: list[CapturedSource] = []
    total = 0
    for request in requests:
        try:
            with client.stream(
                "GET",
                str(request.url),
                headers={"User-Agent": USER_AGENT},
                follow_redirects=False,
                timeout=30,
            ) as response:
                if response.status_code != 200:
                    raise ValueError(
                        f"{request.source_id}: source returned HTTP {response.status_code}."
                    )
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    total += len(chunk)
                    if size > 5_000_000 or total > 20_000_000:
                        raise ValueError("Capture exceeds the per-source or batch byte limit.")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                results.append(
                    CapturedSource(
                        **request.model_dump(),
                        content=raw.decode("utf-8"),
                        sha256=hashlib.sha256(raw).hexdigest(),
                        captured_at=datetime.now(UTC),
                    )
                )
        except httpx.HTTPError as exc:
            raise ValueError(f"{request.source_id}: source transport failed.") from exc
    return tuple(results)


def parse_wikipedia(capture: CapturedSource, policy: WikipediaPolicy) -> ParsedSource:
    revision = re.search(r'"wgRevisionId"\s*:\s*(\d+)', capture.content)
    item = re.search(r'"wgWikibaseItemId"\s*:\s*"(Q\d+)"', capture.content)
    if revision is None or item is None:
        raise ValueError("Wikipedia capture lacks revision or character identity metadata.")
    if revision.group(1) != policy.revision_id:
        raise ValueError("Wikipedia scope policy requires its reviewed source revision.")
    soup = BeautifulSoup(capture.content, "html.parser")
    root = soup.select_one("#mw-content-text .mw-parser-output")
    if root is None:
        raise ValueError("Wikipedia capture lacks its article content container.")
    for ref in root.select("sup.reference"):
        ref.decompose()
    headings: list[tuple[int, str, str]] = []
    spans: list[SourceSpan] = []
    text = ""
    for node in root.find_all(["h2", "h3", "h4", "h5", "h6", "p"]):
        if node.find_parent(["table", "figure", "aside", "nav"]):
            continue
        value = " ".join(node.get_text().split())
        if node.name != "p":
            level = int(node.name[1])
            headings = [h for h in headings if h[0] < level]
            headings.append((level, value, str(node.get("id", ""))))
            continue
        if not value:
            continue
        section = tuple(h[1] for h in headings)
        candidates = [r for r in policy.rules if section[: len(r.section)] == r.section]
        rule = max(candidates, key=lambda r: len(r.section)) if candidates else None
        start = len(text)
        text += value + "\n\n"
        linked_titles: list[str] = []
        for anchor in node.find_all("a", href=True):
            link = urlsplit(urljoin(str(capture.url), str(anchor.get("href"))))
            if link.hostname == "en.wikipedia.org" and link.path.startswith("/wiki/"):
                linked_titles.append(unquote(link.path[6:]).replace("_", " "))
        spans.append(
            SourceSpan(
                ordinal=len(spans),
                section=section,
                section_id=headings[-1][2] if headings else "lead",
                start=start,
                end=start + len(value),
                text=value,
                sha256=hashlib.sha256(value.encode()).hexdigest(),
                scope=rule.scope if rule else "review_required",
                reason=rule.reason
                if rule
                else "Outside the reviewed narrative sections; retained for review.",
                linked_titles=tuple(dict.fromkeys(linked_titles)),
            )
        )
    if not spans:
        raise ValueError("Wikipedia capture contains no paragraphs.")
    return ParsedSource(
        source_id=capture.source_id,
        revision_id=revision.group(1),
        wikidata_id=item.group(1),
        text=text,
        spans=tuple(spans),
    )


def build_snapshot(batch: SourceBatch, snapshot_id: str) -> SourceSnapshot:
    """Prepare a complete immutable import before the store publishes anything."""
    characters = {c.character_id: c for c in batch.catalogue.characters}
    documents: list[ParsedSource] = []
    records: list[StructuredRecord] = []
    issues: list[ImportIssue] = []
    passages: list[Passage] = []
    for capture in batch.captures:
        if capture.kind != "wikipedia":
            parsed_records, parsed_issues = parse_records(capture, batch)
            records.extend(parsed_records)
            issues.extend(parsed_issues)
            continue
        document = parse_wikipedia(capture, batch.policies[capture.source_id])
        character = characters[str(capture.character_id)]
        if document.wikidata_id != character.wikidata_id:
            raise ValueError("Wikipedia identity does not match the reviewed character.")
        documents.append(document)
        for rule in batch.policies[capture.source_id].rules:
            if not any(s.section[: len(rule.section)] == rule.section for s in document.spans):
                issues.append(
                    ImportIssue(
                        source_id=capture.source_id,
                        code="missing_section",
                        detail=f"Reviewed section is absent: {' / '.join(rule.section)}.",
                    )
                )
        seen: set[str] = set()
        for span in document.spans:
            if span.sha256 in seen:
                issues.append(
                    ImportIssue(
                        source_id=capture.source_id,
                        code="duplicate_paragraph",
                        detail=f"Repeated paragraph at ordinal {span.ordinal}.",
                    )
                )
            seen.add(span.sha256)
            if span.scope != "main_series":
                continue
            links = {character.character_id}
            for title in span.linked_titles:
                resolution = batch.catalogue.resolve(title.removesuffix(" (EastEnders)"))
                if resolution.status == "resolved":
                    links.update(resolution.character_ids)
            source = Source(
                title=character.name,
                url=capture.url,
                revision_id=document.revision_id,
                revision_url=HttpUrl(
                    f"https://en.wikipedia.org/w/index.php?oldid={document.revision_id}"
                ),
                section=" / ".join(span.section),
                captured_at=capture.captured_at,
                capture_sha256=capture.sha256,
                scope="main_series",
                license_url=capture.usage.license_url,
                attribution=capture.usage.attribution,
                coverage="Reviewed narrative sections in this captured revision only.",
                gaps=(
                    "Partial canon coverage; other paragraphs remain excluded or awaiting review.",
                    "Identity and episode metadata do not independently corroborate story claims.",
                ),
            )
            # Preserve exact offsets in the full paragraph projection, including gaps.
            start = span.start
            while start < span.end:
                remaining = document.text[start : span.end]
                prefix = remaining.encode()[:1200].decode("utf-8", errors="ignore")
                if len(prefix) < len(remaining) and " " in prefix:
                    prefix = prefix[: prefix.rfind(" ") + 1]
                end = start + len(prefix)
                passages.append(
                    Passage(
                        evidence_id=f"{capture.source_id}-{span.ordinal:04d}-{start}",
                        text=prefix,
                        sha256=hashlib.sha256(prefix.encode()).hexdigest(),
                        start=start,
                        end=end,
                        source=source,
                        location=SourceLocation(
                            source_id=capture.source_id,
                            paragraph_ordinal=span.ordinal,
                            section_id=span.section_id,
                            character_ids=tuple(sorted(links)),
                        ),
                    )
                )
                start = end
    if not passages:
        raise ValueError("Import has no admitted main-series narrative evidence.")
    imported = ImportedSources(
        **batch.model_dump(),
        documents=tuple(documents),
        records=tuple(records),
        issues=tuple(issues),
    )
    assert passages[0].source is not None
    return SourceSnapshot(
        snapshot_id=snapshot_id,
        fixture_version=1,
        source=passages[0].source,
        passages=tuple(passages),
        imported=imported,
    )


def parse_records(
    capture: CapturedSource, batch: SourceBatch
) -> tuple[list[StructuredRecord], list[ImportIssue]]:
    """Identity and broadcast records are inspectable metadata, never story passages."""
    try:
        data = json.loads(capture.content)
    except ValueError as exc:
        raise ValueError(f"{capture.source_id}: malformed JSON.") from exc
    issues: list[ImportIssue] = []
    records: list[StructuredRecord] = []
    if capture.kind == "wikidata":
        character = next(
            c for c in batch.catalogue.characters if c.character_id == capture.character_id
        )
        if not isinstance(data, dict) or not isinstance(data.get("entities"), dict):
            raise ValueError(f"{capture.source_id}: malformed Wikidata entities.")
        entity = data["entities"].get(character.wikidata_id)
        if not isinstance(entity, dict) or "missing" in entity:
            issues.append(
                ImportIssue(
                    source_id=capture.source_id,
                    code="missing_record",
                    detail=f"Missing identity record {character.wikidata_id}.",
                )
            )
            return records, issues
        if entity.get("id") != character.wikidata_id or not isinstance(
            entity.get("lastrevid"), int
        ):
            raise ValueError(f"{capture.source_id}: missing or conflicting identity/revision.")
        records.append(
            StructuredRecord(
                source_id=capture.source_id,
                record_id=character.wikidata_id,
                role="identity_linkage",
                revision_id=str(entity["lastrevid"]),
                fields=entity,
            )
        )
        sitelinks = entity.get("sitelinks", {})
        if not isinstance(sitelinks, dict):
            raise ValueError(f"{capture.source_id}: malformed identity sitelinks.")
        if not sitelinks.get("enwiki"):
            issues.append(
                ImportIssue(
                    source_id=capture.source_id,
                    code="missing_field",
                    detail="Identity record has no enwiki sitelink.",
                )
            )
    else:
        if not isinstance(data, list):
            raise ValueError(f"{capture.source_id}: expected a TVmaze episode list.")
        if not data:
            issues.append(
                ImportIssue(
                    source_id=capture.source_id,
                    code="missing_record",
                    detail="No episode metadata returned for the requested date.",
                )
            )
        seen: dict[int, object] = {}
        for episode in data:
            if not isinstance(episode, dict) or not isinstance(episode.get("id"), int):
                raise ValueError(f"{capture.source_id}: episode lacks a stable identifier.")
            links = episode.get("_links", {})
            if not isinstance(links, dict) or not isinstance(links.get("show", {}), dict):
                raise ValueError(f"{capture.source_id}: malformed episode show linkage.")
            show = links.get("show", {}).get("href")
            if show != "https://api.tvmaze.com/shows/793":
                raise ValueError(
                    f"{capture.source_id}: episode does not identify main-series EastEnders."
                )
            if episode["id"] in seen:
                if seen[episode["id"]] != episode:
                    raise ValueError(f"{capture.source_id}: conflicting duplicate episode records.")
                issues.append(
                    ImportIssue(
                        source_id=capture.source_id,
                        code="duplicate_record",
                        detail=f"Repeated episode {episode['id']}; retained once.",
                    )
                )
                continue
            seen[episode["id"]] = episode
            records.append(
                StructuredRecord(
                    source_id=capture.source_id,
                    record_id=str(episode["id"]),
                    role="episode_metadata",
                    revision_id=capture.sha256,
                    fields=episode,
                )
            )
            for field in ("airdate", "summary"):
                if not episode.get(field):
                    issues.append(
                        ImportIssue(
                            source_id=capture.source_id,
                            code="missing_field",
                            detail=f"Episode {episode['id']} has no {field}.",
                        )
                    )
    return records, issues
