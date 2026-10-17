"""Versioned local model settings and external LlamaIndex model clients."""

import asyncio
import hashlib
import os
from collections.abc import Sequence
from contextlib import nullcontext
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import mlflow
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.llms import ChatMessage
from llama_index.llms.ollama import Ollama
from ollama import Client, ResponseError
from pydantic import Field, PrivateAttr, TypeAdapter

from ask_phil.evidence import Fingerprint, Record
from ask_phil.openrouter import Budget, OpenRouterChat, OpenRouterProfile, ProviderUsage, read_key

QUERY_PREFIX = "task: search result | query:"
DOCUMENT_PREFIX = "title: none | text:"
LOCAL_COST_SCOPE = "Local Ollama API only; hardware, electricity and hosting are unmeasured."
LOCAL_LIMITATION = (
    "Source-supported is not independently cross-checked. Coverage is limited to the "
    "captured snapshot. Local-model results are development smoke evidence, not a "
    "deployment or representative quality assessment."
)


class ModelConfigurationError(RuntimeError):
    pass


class LocalEmbedding(BaseEmbedding):
    """LlamaIndex embedding boundary retaining provider usage and forbidding silent truncation."""

    _client: Client = PrivateAttr()
    _input_tokens: ContextVar[int | None] = PrivateAttr(
        default_factory=lambda: ContextVar[int | None]("embedding_input_tokens", default=None)
    )

    def __init__(self, model_name: str, client: Client) -> None:
        super().__init__(model_name=model_name, embed_batch_size=1)
        self._client = client

    @property
    def input_tokens(self) -> int | None:
        return self._input_tokens.get()

    def verify(self, digest: str) -> None:
        installed = {m.model: m.digest for m in self._client.list().models}
        if installed.get(self.model_name) != digest:
            raise ModelConfigurationError(
                "Installed embedding digest differs; review and rebaseline."
            )

    def _embed(self, text: str, prefix: str, span_name: str) -> list[float]:
        self._input_tokens.set(None)
        if len(text.encode()) > 1800:
            raise ValueError("Text exceeds the embedding input budget.")
        tracing = (
            mlflow.start_span(span_name, span_type="EMBEDDING")
            if mlflow.get_current_active_span()
            else nullcontext()
        )
        with tracing as span:
            formatted = f"{prefix} {text.strip()}"
            if span:
                span.set_inputs({"model": self.model_name, "text": formatted, "truncate": False})
            result = self._client.embed(
                model=self.model_name,
                input=formatted,
                # Reuse the small embedding model across an import; unload after
                # five idle minutes rather than reload for every roster passage.
                keep_alive=300,
                truncate=False,
            )
            self._input_tokens.set(result.prompt_eval_count)
            vector = list(result.embeddings[0])
            if span:
                span.set_outputs(
                    {"dimensions": len(vector), "input_tokens": result.prompt_eval_count}
                )
                if result.prompt_eval_count is not None:
                    span.set_attribute(
                        "mlflow.chat.tokenUsage",
                        {
                            "input_tokens": result.prompt_eval_count,
                            "total_tokens": result.prompt_eval_count,
                        },
                    )
            return vector

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._embed(query, QUERY_PREFIX, "query_embedding")

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._embed(text, DOCUMENT_PREFIX, "passage_embedding")

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return await asyncio.to_thread(self._get_query_embedding, query)


class EmbeddingSettings(Record):
    embedding_model: str
    embedding_digest: Fingerprint
    embedding_dimensions: int = Field(default=768, ge=1, le=2000)

    @property
    def embedding_id(self) -> str:
        identity = (
            f"{self.embedding_model}:{self.embedding_digest}:{self.embedding_dimensions}:"
            f"{QUERY_PREFIX}:{DOCUMENT_PREFIX}"
        )
        return hashlib.sha256(identity.encode()).hexdigest()


def _local_ollama_url() -> str:
    base_url = os.environ.get("ASK_PHIL_OLLAMA_URL", "http://127.0.0.1:11435")
    if urlparse(base_url).hostname not in {"localhost", "127.0.0.1", "::1", "ollama"}:
        raise ModelConfigurationError("This development baseline requires a local Ollama server.")
    return base_url


def embedding_from_environment() -> tuple[EmbeddingSettings, LocalEmbedding]:
    """Configure maintainer retrieval without requiring an answer model or its credentials."""
    base_url = _local_ollama_url()
    path = Path(os.environ.get("ASK_PHIL_MODELS", "config/local-models.json"))
    try:
        settings = EmbeddingSettings.model_validate_json(path.read_text(), extra="ignore")
    except (OSError, ValueError) as exc:
        raise ModelConfigurationError("The embedding configuration could not be loaded.") from exc
    if "cloud" in settings.embedding_model.lower():
        raise ModelConfigurationError("Refresh requires the configured local embedding model.")
    return settings, LocalEmbedding(
        model_name=settings.embedding_model,
        client=Client(host=base_url, timeout=180, trust_env=False),
    )


class ModelSettings(EmbeddingSettings):
    answer_model: str
    answer_digest: Fingerprint
    context_window: int = Field(default=4096, ge=4096, le=4096)
    output_tokens: int = Field(default=256, ge=256, le=512)
    temperature: float = Field(default=0, ge=0, le=0)
    request_timeout_seconds: int = Field(default=180, ge=1, le=180)
    seed: int = 17


class OpenRouterSettings(OpenRouterProfile, EmbeddingSettings):
    pass


class TokenUsage(Record):
    input_tokens: int | None = None
    output_tokens: int | None = None
    embedding_tokens: int | None = None


class ModelExecution(Record):
    """One call's content and accounting, including failed or skipped inference."""

    content: str | None
    usage: TokenUsage
    provider_usage: ProviderUsage | None
    failure_type: str | None
    estimated_api_cost_usd: float | None
    cost_scope: str
    limitation: str

    @property
    def usage_complete(self) -> bool:
        return all(value is not None for value in self.usage.model_dump().values())

    @property
    def trace_attributes(self) -> dict[str, Any]:
        attributes: dict[str, Any] = {"observed_usage": self.usage.model_dump()}
        available = {
            name: value
            for name, value in {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
            }.items()
            if value is not None
        }
        if self.usage.input_tokens is not None and self.usage.output_tokens is not None:
            available["total_tokens"] = self.usage.input_tokens + self.usage.output_tokens
        if available:
            attributes["mlflow.chat.tokenUsage"] = available
        if self.provider_usage is not None:
            attributes["provider_usage"] = self.provider_usage.model_dump(mode="json")
        return attributes


@dataclass(frozen=True)
class Models:
    settings: ModelSettings | OpenRouterSettings
    embedding: BaseEmbedding
    llm: Ollama | OpenRouterChat

    @property
    def _embedding_tokens(self) -> int | None:
        return self.embedding.input_tokens if isinstance(self.embedding, LocalEmbedding) else None

    def skipped_answer(self) -> ModelExecution:
        """Report zero answer tokens without reading accounting from a previous call."""
        return self._execution(
            TokenUsage(input_tokens=0, output_tokens=0, embedding_tokens=self._embedding_tokens)
        )

    def generate_answer(
        self, messages: Sequence[ChatMessage], *, schema: dict[str, Any]
    ) -> ModelExecution:
        """Keep provider failures and their measured or unknown spend in the same result."""
        content = None
        usage = TokenUsage(embedding_tokens=self._embedding_tokens)
        failure_type = None
        provider_usage = None
        try:
            result = self.llm.chat(messages, format=schema)
            content = result.message.content
            if not isinstance(self.llm, OpenRouterChat):
                raw = result.raw if isinstance(result.raw, dict) else {}
                usage = TokenUsage(
                    input_tokens=raw.get("prompt_eval_count"),
                    output_tokens=raw.get("eval_count"),
                    embedding_tokens=self._embedding_tokens,
                )
        except (ValueError, ResponseError, httpx.HTTPError, ConnectionError) as exc:
            failure_type = type(exc).__name__
        if isinstance(self.llm, OpenRouterChat):
            provider_usage = self.llm.last_call
            if provider_usage is not None:
                usage = TokenUsage(
                    input_tokens=provider_usage.input_tokens,
                    output_tokens=provider_usage.output_tokens,
                    embedding_tokens=self._embedding_tokens,
                )
        return self._execution(
            usage, content=content, provider_usage=provider_usage, failure_type=failure_type
        )

    def _execution(
        self,
        usage: TokenUsage,
        *,
        content: str | None = None,
        provider_usage: ProviderUsage | None = None,
        failure_type: str | None = None,
    ) -> ModelExecution:
        cloud = isinstance(self.llm, OpenRouterChat)
        return ModelExecution(
            content=content,
            usage=usage,
            provider_usage=provider_usage,
            failure_type=failure_type,
            estimated_api_cost_usd=(
                provider_usage.cost_usd
                if provider_usage is not None
                else (None if cloud and failure_type is not None else 0.0)
            ),
            cost_scope=(
                "OpenRouter reported inference credits only. Null means unknown cost; "
                "the local budget retains a reservation. Credit purchase fees, tax, "
                "local embeddings and hosting are excluded."
                if cloud
                else LOCAL_COST_SCOPE
            ),
            limitation=(
                "Source-supported is not independently cross-checked. Coverage is limited "
                "to the captured snapshot; this provider baseline is not deployment approval."
                if cloud
                else LOCAL_LIMITATION
            ),
        )

    def verify(self) -> None:
        """Reject mutable tags whose current content differs from the recorded configuration."""
        try:
            if isinstance(self.settings, OpenRouterSettings):
                if not isinstance(self.embedding, LocalEmbedding):
                    raise ModelConfigurationError(
                        "Cloud profiles require verified local embeddings."
                    )
                self.embedding.verify(self.settings.embedding_digest)
                return
            if not isinstance(self.llm, Ollama):
                raise ModelConfigurationError("Local settings require the local answer client.")
            installed = {m.model: m.digest for m in self.llm.client.list().models}
        except (httpx.HTTPError, ResponseError, ConnectionError) as exc:
            raise ModelConfigurationError("The local model server is unavailable.") from exc
        for name, digest in (
            (self.settings.answer_model, self.settings.answer_digest),
            (self.settings.embedding_model, self.settings.embedding_digest),
        ):
            if installed.get(name) != digest:
                raise ModelConfigurationError(
                    "Installed model digest differs from configuration; review and rebaseline."
                )

    @classmethod
    def from_environment(cls) -> "Models":
        base_url = _local_ollama_url()
        path = Path(os.environ.get("ASK_PHIL_MODELS", "config/local-models.json"))
        try:
            settings: ModelSettings | OpenRouterSettings = TypeAdapter(
                ModelSettings | OpenRouterSettings
            ).validate_json(path.read_text())
        except (OSError, ValueError) as exc:
            raise ModelConfigurationError(
                "The local model configuration could not be loaded."
            ) from exc
        if any(
            "cloud" in name.lower() for name in (settings.answer_model, settings.embedding_model)
        ):
            raise ModelConfigurationError(
                "Cloud models require a separate provider/spending setup."
            )
        embedding = LocalEmbedding(
            model_name=settings.embedding_model,
            client=Client(host=base_url, timeout=settings.request_timeout_seconds, trust_env=False),
        )
        if isinstance(settings, OpenRouterSettings):
            models = cls(
                settings,
                embedding,
                OpenRouterChat(
                    settings,
                    read_key(),
                    Budget(),
                    httpx.Client(
                        timeout=settings.request_timeout_seconds,
                        trust_env=False,
                        follow_redirects=False,
                    ),
                ),
            )
            models.verify()
            return models
        models = cls(
            settings=settings,
            embedding=embedding,
            llm=Ollama(
                model=settings.answer_model,
                base_url=base_url,
                temperature=settings.temperature,
                context_window=settings.context_window,
                request_timeout=settings.request_timeout_seconds,
                keep_alive=0,
                thinking=False,
                additional_kwargs={"num_predict": settings.output_tokens, "seed": settings.seed},
                client=Client(
                    host=base_url,
                    timeout=settings.request_timeout_seconds,
                    trust_env=False,
                ),
            ),
        )
        models.verify()
        return models
