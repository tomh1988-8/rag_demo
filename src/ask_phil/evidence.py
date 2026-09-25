"""Public captured-source and citation contracts (no generated answers)."""

import hashlib
import json
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

from ask_phil.source_records import ImportedSources, SourceLocation

Identifier = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")]
Fingerprint = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
NonEmpty = Annotated[str, Field(min_length=1, max_length=4000)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Source(Record):
    title: NonEmpty
    url: HttpUrl
    revision_id: NonEmpty
    revision_url: HttpUrl
    section: NonEmpty
    captured_at: AwareDatetime
    capture_sha256: Fingerprint
    scope: Literal["main_series"]
    license_url: HttpUrl
    attribution: NonEmpty
    coverage: NonEmpty
    gaps: tuple[NonEmpty, ...] = Field(min_length=1)
    support_status: Literal["source_supported", "synthetic_fixture"] = "source_supported"


class Passage(Record):
    evidence_id: Identifier
    text: Annotated[str, Field(min_length=1, max_length=20000)]
    sha256: Fingerprint
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    # Omit absent overrides so published v1 snapshots and receipts retain their identity.
    source: Source | None = Field(default=None, exclude_if=lambda value: value is None)
    location: SourceLocation | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        if hashlib.sha256(self.text.encode()).hexdigest() != self.sha256:
            raise ValueError("passage fingerprint does not match retained text")
        if self.end - self.start != len(self.text):
            raise ValueError("span must cover the retained text in Unicode characters")
        return self


class SourceSnapshot(Record):
    snapshot_id: Identifier
    fixture_version: Literal[1]
    source: Source
    passages: tuple[Passage, ...] = Field(min_length=1, max_length=1000)
    imported: ImportedSources | None = Field(default=None, exclude_if=lambda value: value is None)

    @model_validator(mode="after")
    def unique_evidence(self) -> Self:
        if len({p.evidence_id for p in self.passages}) != len(self.passages):
            raise ValueError("evidence identifiers must be unique within a snapshot")
        if self.imported is not None:
            documents = {d.source_id: d for d in self.imported.documents}
            captures = {c.source_id: c for c in self.imported.captures}
            characters = {c.character_id for c in self.imported.catalogue.characters}
            for passage in self.passages:
                location = passage.location
                if location is None or location.source_id not in documents:
                    raise ValueError("Imported evidence needs its captured document locator.")
                document = documents[location.source_id]
                capture = captures[location.source_id]
                if location.paragraph_ordinal >= len(document.spans):
                    raise ValueError("Imported evidence must reference an admitted paragraph.")
                span = document.spans[location.paragraph_ordinal]
                if (
                    span.scope != "main_series"
                    or span.section_id != location.section_id
                    or not span.start <= passage.start < passage.end <= span.end
                    or document.text[passage.start : passage.end] != passage.text
                ):
                    raise ValueError(
                        "Imported evidence must match its admitted paragraph and span."
                    )
                if (
                    passage.source is None
                    or passage.source.capture_sha256 != capture.sha256
                    or passage.source.revision_id != document.revision_id
                    or passage.source.captured_at != capture.captured_at
                    or passage.source.url != capture.url
                    or not set(location.character_ids) <= characters
                ):
                    raise ValueError("Imported evidence provenance does not match its capture.")
        return self

    @property
    def fingerprint(self) -> str:
        canonical = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


class Inspection(Record):
    snapshot_id: Identifier
    snapshot_sha256: Fingerprint
    source: Source
    query: str | None
    matches: tuple[Passage, ...]
    method: Literal["postgresql_english_all_terms_v1", "evidence_id_lookup_v1"] = (
        "postgresql_english_all_terms_v1"
    )
    limitation: str = (
        "Matching excerpts from this captured fixture only; this is not a generated answer. "
        "No match does not establish that an event never happened. "
        "Source-supported does not mean independently cross-checked."
    )
