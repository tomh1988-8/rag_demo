"""Versioned local model settings and external LlamaIndex model clients."""

import asyncio
import hashlib
import os
from contextlib import nullcontext
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
import mlflow
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.llms.ollama import Ollama
from ollama import Client, ResponseError
from pydantic import Field, PrivateAttr

from ask_phil.evidence import Fingerprint, Record

QUERY_PREFIX = "task: search result | query:"
DOCUMENT_PREFIX = "title: none | text:"


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
                keep_alive=0,
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


class ModelSettings(Record):
    answer_model: str
    answer_digest: Fingerprint
    embedding_model: str
    embedding_digest: Fingerprint
    embedding_dimensions: int = Field(default=768, ge=1, le=2000)
    context_window: int = Field(default=4096, ge=4096, le=4096)
    output_tokens: int = Field(default=256, ge=256, le=512)
    temperature: float = Field(default=0, ge=0, le=0)
    request_timeout_seconds: int = Field(default=180, ge=1, le=180)
    seed: int = 17

    @property
    def embedding_id(self) -> str:
        identity = (
            f"{self.embedding_model}:{self.embedding_digest}:{self.embedding_dimensions}:"
            f"{QUERY_PREFIX}:{DOCUMENT_PREFIX}"
        )
        return hashlib.sha256(identity.encode()).hexdigest()


@dataclass(frozen=True)
class Models:
    settings: ModelSettings
    embedding: BaseEmbedding
    llm: Ollama

    @property
    def embedding_tokens(self) -> int | None:
        return self.embedding.input_tokens if isinstance(self.embedding, LocalEmbedding) else None

    def verify(self) -> None:
        """Reject mutable tags whose current content differs from the recorded configuration."""
        try:
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
        base_url = os.environ.get("ASK_PHIL_OLLAMA_URL", "http://127.0.0.1:11435")
        if urlparse(base_url).hostname not in {"localhost", "127.0.0.1", "::1", "ollama"}:
            raise ModelConfigurationError(
                "This development baseline requires a local Ollama server."
            )
        path = Path(os.environ.get("ASK_PHIL_MODELS", "config/local-models.json"))
        try:
            settings = ModelSettings.model_validate_json(path.read_text())
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
        models = cls(
            settings=settings,
            embedding=LocalEmbedding(
                model_name=settings.embedding_model,
                client=Client(
                    host=base_url,
                    timeout=settings.request_timeout_seconds,
                    trust_env=False,
                ),
            ),
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
