"""Source-reviewed subjects and classification gaps, kept outside event adjacency."""

import hashlib
from collections.abc import Iterable
from typing import Literal, Self

from pydantic import Field, model_validator

from ask_phil.evidence import Identifier, NonEmpty, Record
from ask_phil.parentage import ClaimEvidence

Theme = Literal["domestic_abuse", "manosphere"]


class ContextClaim(Record):
    claim_id: Identifier
    kind: Literal["theme", "unclassified"]
    character_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=8)
    theme: Theme | None
    classification_gap: NonEmpty | None
    evidence: tuple[ClaimEvidence, ...] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def classification(self) -> Self:
        if len(set(self.character_ids)) != len(self.character_ids):
            raise ValueError("Text subjects must be distinct characters.")
        if self.kind == "theme":
            if self.theme is None or self.classification_gap is not None:
                raise ValueError("A theme names a subject, not a missing event category.")
        elif self.theme is not None or not self.classification_gap:
            raise ValueError("An unclassified fact needs an explicit classification gap.")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()

    @property
    def assertion(self) -> tuple[object, ...]:
        return (
            self.kind,
            tuple(sorted(self.character_ids)),
            self.theme,
            tuple(sorted({e.evidence_id for e in self.evidence})),
        )

    @property
    def qualification(self) -> str:
        if self.theme:
            return (
                f"Theme: {self.theme.replace('_', ' ')}. A shared theme establishes neither "
                "a shared event nor a character relationship."
            )
        return f"Classification gap: {self.classification_gap} This fact remains text-only."


def context_for(
    claims: tuple[ContextClaim, ...], evidence_ids: Iterable[str]
) -> tuple[ContextClaim, ...]:
    retained = set(evidence_ids)
    return tuple(c for c in claims if {e.evidence_id for e in c.evidence} <= retained)
