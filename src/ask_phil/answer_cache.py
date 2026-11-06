"""Exact, publication-bound PostgreSQL reuse at the conventional text boundary."""

import hashlib
import os
import platform
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, Field

from ask_phil.answers import (
    SYSTEM_PROMPT,
    AnswerContent,
    AskRequest,
    Draft,
    cite_answer,
    context_text,
)
from ask_phil.cache_records import CacheDelivery
from ask_phil.classified_facts import ContextClaim
from ask_phil.conversation import (
    PRONOUNS,
    ReferenceResolution,
    ReferenceTurn,
    resolve_snapshot_reference,
)
from ask_phil.evaluation import document_fingerprint
from ask_phil.evidence import Fingerprint, Identifier, Passage, Record
from ask_phil.execution import ExecutionBudget
from ask_phil.models import ModelExecution, Models, ModelSettings, OpenRouterSettings, TokenUsage
from ask_phil.publications import PublicationStore
from ask_phil.retrieval import PinnedText
from ask_phil.routing import RoutingPolicy
from ask_phil.source_windows import resolve_span
from ask_phil.text_retrieval import QueryVariants, TextPipelineRecord, TextPolicy

_CONTEXT_DEPENDENT = re.compile(
    r"\b(that|this|those|these|again|also|more|previous|above|earlier|same)\b", re.IGNORECASE
)


class CachePolicy(Record):
    enabled: bool = True
    namespace: Identifier = "serving-v1"
    ttl_seconds: int = Field(default=3600, ge=1, le=86400)
    capacity: int = Field(default=256, ge=1, le=10000)

    @classmethod
    def from_environment(cls) -> "CachePolicy":
        path = os.environ.get("ASK_PHIL_CACHE_POLICY")
        return cls.model_validate_json(Path(path).read_bytes()) if path else cls()

    @property
    def enabled_now(self) -> bool:
        return self.enabled and os.environ.get("ASK_PHIL_CACHE_ENABLED", "true").lower() == "true"


class _ReusableText(Record):
    """Generation provenance without session, receipt capability or feedback."""

    generation_id: UUID
    draft: Draft
    context: tuple[Passage, ...]
    context_claims: tuple[ContextClaim, ...]
    pipeline: TextPipelineRecord
    model_settings: ModelSettings | OpenRouterSettings
    prompt_sha256: Fingerprint


class _Entry(Record):
    entry_id: UUID
    key: Fingerprint
    created_at: AwareDatetime
    expires_at: AwareDatetime
    origin_trace_id: str
    text: _ReusableText


@dataclass(frozen=True)
class CacheLookup:
    delivery: CacheDelivery
    key: str | None = None
    content: AnswerContent | None = None
    entry: _Entry | None = None


class AnswerCache:
    def __init__(
        self,
        database_url: str,
        application_sha256: str,
        *,
        policy: CachePolicy | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.database_url = database_url
        self.application_sha256 = application_sha256
        self.policy = policy or CachePolicy.from_environment()
        self.clock = clock
        self.runtime = {
            "python": platform.python_version(),
            **{
                name: version(name)
                for name in (
                    "pydantic",
                    "llama-index-core",
                    "llama-index-vector-stores-postgres",
                    "psycopg",
                    "httpx",
                )
            },
        }

    def _connect(self) -> psycopg.Connection[tuple[object, ...]]:
        # Optional work must not consume the normal answering timeout or reset it.
        return psycopg.connect(
            self.database_url,
            connect_timeout=1,
            options="-c statement_timeout=100 -c lock_timeout=50",
        )

    def _initialize(self, conn: psycopg.Connection[tuple[object, ...]]) -> None:
        if conn.execute("SELECT to_regclass('text_answer_cache')").fetchone() != (None,):
            return
        conn.execute("SELECT pg_advisory_xact_lock(728201)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS text_answer_cache (
                cache_key text PRIMARY KEY,
                generation_id uuid NOT NULL,
                expires_at timestamptz NOT NULL,
                last_used timestamptz NOT NULL,
                retired boolean NOT NULL DEFAULT false,
                document_sha256 text NOT NULL,
                document jsonb NOT NULL
            )
        """)

    def lookup(
        self,
        request: AskRequest,
        pinned: PinnedText,
        models: Models,
        policy: TextPolicy,
        reference: ReferenceResolution | None,
        history: tuple[ReferenceTurn, ...],
        budget: ExecutionBudget,
        *,
        category: str,
    ) -> CacheLookup:
        reason = None
        reference = reference or resolve_snapshot_reference(request.question, pinned.snapshot, ())
        if category != "serving":
            reason = "offline_evaluation"
        elif request.bypass_cache:
            reason = "request_bypass"
        elif not self.policy.enabled_now:
            reason = "disabled"
        elif history or reference.context_turn_id or _CONTEXT_DEPENDENT.search(request.question):
            reason = "context_dependent"
        elif (
            reference.clarification
            or not reference.character_ids
            or PRONOUNS.search(request.question)
        ):
            reason = "unresolved_or_contextual_identity"
        elif request.route not in {"auto", "text_rag"}:
            reason = "incompatible_route"
        elif pinned.publication is None:
            reason = "unpublished_snapshot"
        elif budget.remaining_seconds < 1:
            reason = "remaining_budget"
        if reason:
            return CacheLookup(CacheDelivery(status="bypass", reason=reason))
        publication = pinned.publication
        assert publication is not None
        key = document_fingerprint(
            {
                "version": "exact-text-cache-v1",
                "namespace": self.policy.namespace,
                "question": " ".join(unicodedata.normalize("NFC", request.question).split()),
                "effective_question": " ".join(
                    unicodedata.normalize("NFC", reference.question).split()
                ),
                "scope": "public-main-series-current-knowledge-v1",
                "source_support": pinned.snapshot.source.support_status,
                "snapshot": pinned.snapshot.fingerprint,
                "publication": publication.reference.model_dump(mode="json"),
                "text_policy": policy.model_dump(mode="json"),
                "route_override": request.route,
                "routing_policy": RoutingPolicy.from_environment().model_dump(mode="json"),
                "model": models.settings.model_dump(mode="json"),
                "prompt": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
                "output_schema": Draft.model_json_schema(),
                "limits": budget.limits.model_dump(mode="json"),
                "application": self.application_sha256,
                "runtime": self.runtime,
            }
        )
        try:
            if not PublicationStore(self.database_url).is_current(
                publication.compatibility_id, publication.generation
            ):
                return CacheLookup(CacheDelivery(status="bypass", reason="inactive_publication"))
            pinned.verify()
            with self._connect() as conn:
                self._initialize(conn)
                row = conn.execute(
                    "SELECT document, document_sha256 FROM text_answer_cache "
                    "WHERE cache_key=%s AND NOT retired AND expires_at > %s",
                    (key, self.clock()),
                ).fetchone()
                if row is None:
                    return CacheLookup(
                        CacheDelivery(status="miss", reason="absent", eligible=True), key
                    )
                try:
                    entry = _Entry.model_validate(row[0])
                    if (
                        entry.key != key
                        or document_fingerprint(entry.model_dump(mode="json")) != row[1]
                        or entry.expires_at <= self.clock()
                        or (self.clock() - entry.created_at).total_seconds()
                        >= self.policy.ttl_seconds
                        or any(
                            resolve_span(pinned.snapshot, p.evidence_id) != p
                            for p in entry.text.context
                        )
                    ):
                        raise ValueError("Invalid reusable evidence or entry.")
                    text = entry.text
                    citations = cite_answer(text.draft, text.context, pinned.snapshot.snapshot_id)
                    if text.draft.status != "answered" or not citations:
                        raise ValueError("Only complete, cited text can be reused.")
                except ValueError:
                    conn.execute(
                        "DELETE FROM text_answer_cache WHERE cache_key=%s AND document_sha256=%s",
                        (key, row[1]),
                    )
                    return CacheLookup(
                        CacheDelivery(status="miss", reason="invalid_entry", eligible=True), key
                    )
                conn.execute(
                    "UPDATE text_answer_cache SET last_used=%s WHERE cache_key=%s",
                    (self.clock(), key),
                )
            budget.context(len(context_text(text.context, text.context_claims).encode()))
            # Original timings, variant calls and retrieved rankings remain in the entry.
            # This delivery performed neither retrieval nor inference.
            pipeline = TextPipelineRecord(
                policy=policy,
                policy_sha256=policy.fingerprint,
                original_question=request.question,
                resolved_question=reference.question,
                variants=QueryVariants(queries=(), proposals=()),
                cache_enabled=True,
            ).with_final_context(text.context, text.context_claims)
            delivery = CacheDelivery(status="hit", reason="compatible_exact_match", eligible=True)
            return CacheLookup(
                delivery,
                key,
                AnswerContent(
                    generation_id=text.generation_id,
                    cache=delivery,
                    status=text.draft.status,
                    answer=text.draft.answer,
                    unanswered=text.draft.unanswered,
                    qualifications=text.draft.qualifications,
                    citations=citations,
                    context=text.context,
                    context_claims=text.context_claims,
                    text_pipeline=pipeline,
                    baseline_version="bounded-text-v1",
                    model_settings=text.model_settings,
                    prompt_sha256=text.prompt_sha256,
                    accounting=ModelExecution(
                        content=None,
                        usage=TokenUsage(input_tokens=0, output_tokens=0, embedding_tokens=0),
                        provider_usage=None,
                        failure_type=None,
                        estimated_api_cost_usd=0,
                        cost_scope="This cache delivery made no new model or embedding calls.",
                        limitation=(
                            "Source support is preserved; reuse is not independent verification."
                        ),
                    ),
                ),
                entry,
            )
        except (psycopg.Error, ValueError):
            return CacheLookup(CacheDelivery(status="bypass", reason="cache_error", eligible=True))

    def populate(
        self, lookup: CacheLookup, content: AnswerContent, trace_id: str, budget: ExecutionBudget
    ) -> AnswerContent:
        content = replace(content, cache=lookup.delivery)
        if content.text_pipeline is not None:
            content = replace(
                content,
                text_pipeline=content.text_pipeline.model_copy(
                    update={"cache_enabled": lookup.delivery.eligible}
                ),
            )
        if (
            lookup.key is None
            or content.status != "answered"
            or not content.citations
            or content.review_notices
            or content.text_pipeline is None
            or content.model_settings is None
            or budget.record().stop_reason
            or budget.remaining_seconds < 1
        ):
            return content
        pipeline = content.text_pipeline
        settings = content.model_settings
        generation_id = uuid4()
        content = replace(content, generation_id=generation_id)
        now = self.clock()
        try:
            draft = Draft(
                answer=content.answer,
                status="answered",
                evidence_ids=tuple(c.evidence_id for c in content.citations),
                unanswered=content.unanswered,
                qualifications=content.qualifications,
            )
        except ValueError:
            # Mandatory source annotations can make a valid final reply larger
            # than a model draft. Cache admission must not break that delivery.
            return replace(
                content,
                cache=CacheDelivery(
                    status="bypass",
                    reason="incompatible_output",
                    eligible=True,
                ),
            )
        entry = _Entry(
            entry_id=uuid4(),
            key=lookup.key,
            created_at=now,
            expires_at=now + timedelta(seconds=self.policy.ttl_seconds),
            origin_trace_id=trace_id,
            text=_ReusableText(
                generation_id=generation_id,
                draft=draft,
                context=content.context,
                context_claims=content.context_claims,
                pipeline=pipeline,
                model_settings=settings,
                prompt_sha256=content.prompt_sha256,
            ),
        )
        try:
            with self._connect() as conn:
                self._initialize(conn)
                conn.execute("SELECT pg_advisory_xact_lock(728201)")
                conn.execute(
                    "DELETE FROM text_answer_cache WHERE retired OR expires_at <= %s", (now,)
                )
                conn.execute(
                    "INSERT INTO text_answer_cache VALUES (%s,%s,%s,%s,false,%s,%s) "
                    "ON CONFLICT (cache_key) DO NOTHING",
                    (
                        entry.key,
                        generation_id,
                        entry.expires_at,
                        now,
                        document_fingerprint(entry.model_dump(mode="json")),
                        Jsonb(entry.model_dump(mode="json")),
                    ),
                )
                conn.execute(
                    "DELETE FROM text_answer_cache WHERE cache_key IN "
                    "(SELECT cache_key FROM text_answer_cache "
                    "ORDER BY last_used DESC, cache_key OFFSET %s)",
                    (self.policy.capacity,),
                )
        except (psycopg.Error, ValueError):
            content = replace(
                content,
                cache=CacheDelivery(status="bypass", reason="cache_write_error", eligible=True),
            )
        return content

    def retire(self, generation_id: UUID) -> int:
        """Maintainer retirement; raw user ratings never invoke this operation."""
        with self._connect() as conn:
            self._initialize(conn)
            return conn.execute(
                "UPDATE text_answer_cache SET retired=true WHERE generation_id=%s AND NOT retired",
                (generation_id,),
            ).rowcount
