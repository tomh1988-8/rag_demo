"""Captured inputs and ordered scope decisions retained with an imported snapshot."""

import hashlib
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    model_validator,
)

from ask_phil.identity import Character, IdentityCatalogue, IdentityResolution

Scope = Literal["main_series", "other_media", "production", "review_required"]


class ImportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceUse(ImportRecord):
    role: Literal["narrative", "identity_linkage", "episode_metadata"]
    license_url: HttpUrl
    attribution: str


_SOURCE_USE = {
    "wikipedia": SourceUse(
        role="narrative",
        license_url=HttpUrl("https://creativecommons.org/licenses/by-sa/4.0/"),
        attribution="Wikipedia contributors; markup removed and whitespace normalized.",
    ),
    "wikidata": SourceUse(
        role="identity_linkage",
        license_url=HttpUrl("https://creativecommons.org/publicdomain/zero/1.0/"),
        attribution="Wikidata contributors; structured identity data.",
    ),
    "tvmaze": SourceUse(
        role="episode_metadata",
        license_url=HttpUrl("https://creativecommons.org/licenses/by-sa/4.0/"),
        attribution="TVmaze, https://www.tvmaze.com/shows/793/eastenders; broadcast metadata.",
    ),
}


class SourceRequest(ImportRecord):
    source_id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,39}$")]
    kind: Literal["wikipedia", "wikidata", "tvmaze"]
    character_id: str | None = None
    url: HttpUrl

    @property
    def usage(self) -> SourceUse:
        return _SOURCE_USE[self.kind]

    @model_validator(mode="after")
    def official_source(self) -> Self:
        hosts = {
            "wikipedia": "en.wikipedia.org",
            "wikidata": "www.wikidata.org",
            "tvmaze": "api.tvmaze.com",
        }
        if (
            self.url.scheme != "https"
            or self.url.host != hosts[self.kind]
            or self.url.username
            or self.url.password
            or self.url.port != 443
        ):
            raise ValueError(
                "Use the official HTTPS source host without credentials or custom ports."
            )
        return self


class CapturedSource(SourceRequest):
    captured_at: AwareDatetime
    content: Annotated[str, Field(min_length=1, max_length=5_000_000)]
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]

    @model_validator(mode="after")
    def check_capture(self) -> Self:
        if hashlib.sha256(self.content.encode()).hexdigest() != self.sha256:
            raise ValueError("Capture fingerprint does not match its retained UTF-8 content.")
        return self


class ScopeRule(ImportRecord):
    section: tuple[str, ...] = Field(min_length=1)
    scope: Scope
    reason: str = Field(min_length=1, max_length=4000)


class WikipediaPolicy(ImportRecord):
    revision_id: str = Field(pattern=r"^[1-9][0-9]*$")
    reviewer: str = Field(min_length=1, max_length=4000)
    rules: tuple[ScopeRule, ...]

    @model_validator(mode="after")
    def unique_rules(self) -> Self:
        if len({rule.section for rule in self.rules}) != len(self.rules):
            raise ValueError("Each reviewed section can have only one scope rule.")
        return self


class SourceSpan(ImportRecord):
    ordinal: int = Field(ge=0)
    section: tuple[str, ...]
    section_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str
    sha256: str
    scope: Scope
    reason: str
    linked_titles: tuple[str, ...] = ()


class ParsedSource(ImportRecord):
    source_id: str
    revision_id: str
    wikidata_id: str
    text: str
    spans: tuple[SourceSpan, ...]


class ImportPlan(ImportRecord):
    format_version: Literal[1]
    catalogue: IdentityCatalogue
    policies: dict[str, WikipediaPolicy]


class CapturePlan(ImportPlan):
    requests: tuple[SourceRequest, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def unique_requests(self) -> Self:
        if len({r.source_id for r in self.requests}) != len(self.requests):
            raise ValueError("Capture request identifiers must be unique.")
        return self


class SourceBatch(ImportPlan):
    captures: tuple[CapturedSource, ...] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def check_sources(self) -> Self:
        source_ids = {c.source_id for c in self.captures}
        if len(source_ids) != len(self.captures):
            raise ValueError("Capture source identifiers must be unique.")
        if set(self.policies) != {c.source_id for c in self.captures if c.kind == "wikipedia"}:
            raise ValueError("Every Wikipedia capture needs exactly one reviewed scope policy.")
        character_ids = {c.character_id for c in self.catalogue.characters}
        for capture in self.captures:
            if capture.kind != "tvmaze" and capture.character_id not in character_ids:
                raise ValueError("Source must refer to a reviewed character identity.")
        for character in self.catalogue.characters:
            if not character.evidence_sources or not set(character.evidence_sources) <= source_ids:
                raise ValueError("Character identity needs retained source evidence.")
        return self


class StructuredRecord(ImportRecord):
    source_id: str
    record_id: str
    role: Literal["identity_linkage", "episode_metadata"]
    revision_id: str
    fields: dict[str, JsonValue]


class ImportIssue(ImportRecord):
    source_id: str
    code: Literal[
        "missing_record",
        "missing_field",
        "missing_section",
        "duplicate_record",
        "duplicate_paragraph",
    ]
    detail: str


class SourceLocation(ImportRecord):
    source_id: str
    paragraph_ordinal: int = Field(ge=0)
    section_id: str
    character_ids: tuple[str, ...]


class SourceSummary(SourceUse):
    source_id: str
    url: HttpUrl
    revision_id: str
    captured_at: AwareDatetime
    sha256: str
    paragraphs: int
    admitted_paragraphs: int
    excluded_paragraphs: int
    review_required_paragraphs: int
    structured_records: int


class CharacterCoverage(ImportRecord):
    character: Character
    identity_resolution: IdentityResolution
    primary_source_ids: tuple[str, ...]
    mentioned_in_source_ids: tuple[str, ...]
    admitted_paragraphs: int
    excluded_paragraphs: int
    review_required_paragraphs: int
    retained_narrative_characters: int
    admitted_sections: tuple[tuple[str, ...], ...]
    gaps: tuple[str, ...]


class ParagraphLocation(ImportRecord):
    source_id: str
    paragraph_ordinal: int


class DuplicateParagraphs(ImportRecord):
    sha256: str
    locations: tuple[ParagraphLocation, ...]


class ImportSummary(ImportRecord):
    parser_version: str
    sources: tuple[SourceSummary, ...]
    catalogue: IdentityCatalogue
    issues: tuple[ImportIssue, ...]
    characters: tuple[CharacterCoverage, ...] = ()
    duplicate_paragraphs: tuple[DuplicateParagraphs, ...] = ()
    limitation: str = (
        "Counts describe captured paragraphs and metadata, not extracted claims or canon accuracy. "
        "Unreviewed paragraphs stay outside retrieval. Capture time is not storyline coverage. "
        "Identity and episode metadata do not independently corroborate narrative facts."
    )


class SourceInspection(ImportRecord):
    summary: SourceSummary
    capture: CapturedSource
    document: ParsedSource | None
    records: tuple[StructuredRecord, ...]


class ImportedSources(SourceBatch):
    # Keep the legacy default so loading retained snapshots preserves their fingerprints.
    parser_version: Literal["html-paragraphs-v1", "html-context-fit-v2"] = "html-paragraphs-v1"
    documents: tuple[ParsedSource, ...]
    records: tuple[StructuredRecord, ...]
    issues: tuple[ImportIssue, ...]

    def report(self) -> ImportSummary:
        sources: list[SourceSummary] = []
        for capture in self.captures:
            document = next((d for d in self.documents if d.source_id == capture.source_id), None)
            records = [r for r in self.records if r.source_id == capture.source_id]
            spans = document.spans if document else ()
            sources.append(
                SourceSummary(
                    source_id=capture.source_id,
                    role=capture.usage.role,
                    url=capture.url,
                    revision_id=document.revision_id
                    if document
                    else (records[0].revision_id if records else capture.sha256),
                    captured_at=capture.captured_at,
                    sha256=capture.sha256,
                    license_url=capture.usage.license_url,
                    attribution=capture.usage.attribution,
                    paragraphs=len(spans),
                    admitted_paragraphs=sum(s.scope == "main_series" for s in spans),
                    excluded_paragraphs=sum(
                        s.scope in {"production", "other_media"} for s in spans
                    ),
                    review_required_paragraphs=sum(s.scope == "review_required" for s in spans),
                    structured_records=len(records),
                )
            )
        paragraphs: dict[str, list[ParagraphLocation]] = {}
        for document in self.documents:
            for span in document.spans:
                paragraphs.setdefault(span.sha256, []).append(
                    ParagraphLocation(source_id=document.source_id, paragraph_ordinal=span.ordinal)
                )
        return ImportSummary(
            parser_version=self.parser_version,
            sources=tuple(sources),
            catalogue=self.catalogue,
            issues=self.issues,
            characters=tuple(self.character_coverage(c) for c in self.catalogue.characters),
            duplicate_paragraphs=tuple(
                DuplicateParagraphs(sha256=sha256, locations=tuple(locations))
                for sha256, locations in paragraphs.items()
                if len(locations) > 1
            ),
        )

    def character_coverage(self, character: Character) -> CharacterCoverage:
        primary = tuple(
            c.source_id
            for c in self.captures
            if c.character_id == character.character_id and c.kind == "wikipedia"
        )
        spans = tuple(s for d in self.documents if d.source_id in primary for s in d.spans)
        admitted = tuple(s for s in spans if s.scope == "main_series")
        mentioned = tuple(
            d.source_id
            for d in self.documents
            if any(
                character.character_id
                in self.catalogue.resolve(title.removesuffix(" (EastEnders)")).character_ids
                for s in d.spans
                if s.scope == "main_series"
                for title in s.linked_titles
            )
        )
        return CharacterCoverage(
            character=character,
            identity_resolution=self.catalogue.resolve(character.name),
            primary_source_ids=primary,
            mentioned_in_source_ids=mentioned,
            admitted_paragraphs=len(admitted),
            excluded_paragraphs=sum(s.scope in {"production", "other_media"} for s in spans),
            review_required_paragraphs=sum(s.scope == "review_required" for s in spans),
            retained_narrative_characters=sum(len(s.text) for s in admitted),
            admitted_sections=tuple(dict.fromkeys(s.section for s in admitted)),
            gaps=(
                *(("No admitted primary narrative history.",) if not admitted else ()),
                "Partial captured history; unreviewed sections are excluded from retrieval.",
                "Capture time does not establish current storyline completeness.",
                "Matching identities and repeated accounts do not independently corroborate facts.",
            ),
        )

    def inspect(self, source_id: str) -> SourceInspection:
        capture = next((c for c in self.captures if c.source_id == source_id), None)
        if capture is None:
            raise LookupError("Source not found in this snapshot.")
        return SourceInspection(
            summary=next(s for s in self.report().sources if s.source_id == source_id),
            capture=capture,
            document=next((d for d in self.documents if d.source_id == source_id), None),
            records=tuple(r for r in self.records if r.source_id == source_id),
        )
