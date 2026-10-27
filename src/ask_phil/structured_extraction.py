"""Schema-aligned Claim extraction through the existing capped provider adapter."""

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, cast

from llama_index.core.llms import ChatMessage, CompletionResponse, CustomLLM, LLMMetadata
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.program import LLMTextCompletionProgram
from pydantic import BaseModel, PrivateAttr

from ask_phil.evidence import Identifier, NonEmpty, Record, SourceSnapshot
from ask_phil.identity import IdentityCatalogue
from ask_phil.openrouter import OpenRouterChat
from ask_phil.parentage import ClaimBatch, ExtractedClaims
from ask_phil.relationships import ExtractedRelationships, RelationshipBatch
from ask_phil.story_events import EventBatch, EventExtractionOutput


class IncidentScope(Record):
    event_id: Identifier
    event_label: NonEmpty


class ClaimLLM(CustomLLM):
    """LlamaIndex completion protocol backed by the guarded strict-schema chat."""

    _chat: OpenRouterChat = PrivateAttr()
    _raw: str | None = PrivateAttr(default=None)
    _output_cls: type[BaseModel] = PrivateAttr()

    def __init__(self, chat: OpenRouterChat, output_cls: type[BaseModel] = ExtractedClaims) -> None:
        super().__init__()
        self._chat = chat
        # Keep the original standalone completion and ParentageLLM behavior. A typed
        # extraction supplies its own schema per invocation, without mutating the adapter.
        self._output_cls = output_cls

    @property
    def raw(self) -> str | None:
        return self._raw

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(
            context_window=16384,
            num_output=self._chat.profile.output_tokens,
            model_name=self._chat.profile.canonical_slug,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        output_cls: type[BaseModel] = kwargs.pop("output_cls", self._output_cls)
        try:
            result = self._chat.chat(
                [ChatMessage(role="user", content=prompt)], format=output_cls.model_json_schema()
            )
        finally:
            self._raw = self._chat.last_content
        return CompletionResponse(text=result.message.content or "")

    def stream_complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> Any:
        raise NotImplementedError("The extraction pilot uses one bounded non-streaming call.")


@dataclass(frozen=True)
class ClaimExtractor[
    Output: ExtractedClaims | ExtractedRelationships | EventExtractionOutput,
    Batch: ClaimBatch | RelationshipBatch | EventBatch,
]:
    """One extraction kind owns invocation, parsing, captured material and candidate identity."""

    name: str
    _output_cls: type[Output]
    _batch_cls: type[Batch]
    _prompt: str

    @property
    def prompt_sha256(self) -> str:
        return hashlib.sha256(self._prompt.encode()).hexdigest()

    @property
    def schema_sha256(self) -> str:
        return hashlib.sha256(
            json.dumps(self._output_cls.model_json_schema(), sort_keys=True).encode()
        ).hexdigest()

    def extract(
        self,
        snapshot: SourceSnapshot,
        catalogue: IdentityCatalogue,
        llm: ClaimLLM,
        incidents: dict[str, IncidentScope] | None = None,
    ) -> tuple[Batch, float]:
        started = time.perf_counter()
        scoped = self._output_cls is EventExtractionOutput
        if scoped and incidents is None:
            raise ValueError("Story event extraction requires incident scope.")
        # Preserve the existing parentage/relationship prompts, including their schema
        # copy. The event prompt omits that copy to stay within its provider input budget.
        parser = (
            PydanticOutputParser(output_cls=self._output_cls, pydantic_format_tmpl="")
            if scoped
            else PydanticOutputParser(output_cls=self._output_cls)
        )
        program = LLMTextCompletionProgram.from_defaults(
            output_cls=self._output_cls,
            output_parser=parser,
            prompt_template_str=self._prompt,
            llm=llm,
        )
        characters = (
            catalogue.model_dump_json()
            if self._output_cls is ExtractedClaims
            else [
                {
                    "character_id": c.character_id,
                    "name": c.name,
                    "aliases": c.aliases,
                    "performers": c.performers,
                }
                for c in catalogue.characters
            ]
        )
        material = [
            {
                "evidence_id": p.evidence_id,
                "text": p.text,
                **(
                    incidents[p.evidence_id].model_dump()
                    if scoped and incidents is not None
                    else {}
                ),
            }
            for p in snapshot.passages
        ]
        result = program(
            catalogue=characters,
            material=material,
            llm_kwargs={"output_cls": self._output_cls},
        )
        batch = self._batch_cls.model_validate(
            {
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_sha256": snapshot.fingerprint,
                "catalogue": catalogue,
                "claims": result.claims,
                "extractor": llm.metadata.model_name,
                **(
                    {"context_claims": result.context_claims}
                    if isinstance(result, EventExtractionOutput)
                    else {}
                ),
            }
        )
        return cast(Batch, batch), (time.perf_counter() - started) * 1000
