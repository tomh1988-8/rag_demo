"""Shared HTTP interface for evidence inspection; fixture loading is maintainer-only."""

import asyncio
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import StringConstraints

from ask_phil.answering import AnswerService
from ask_phil.answers import AnswerReceipt, AnswerRecord, AskRequest
from ask_phil.conversation import ReferenceTurn, TurnIdentity
from ask_phil.evidence import Identifier, Inspection
from ask_phil.execution import ExecutionBudget, ExecutionLimits, ExecutionPolicies, ExecutionStopped
from ask_phil.family_graph import FamilyAudit, FamilyGraph, FamilyQuery, FamilyResult
from ask_phil.identity import IdentityResolution
from ask_phil.models import ModelConfigurationError, Models
from ask_phil.openrouter import ProviderError
from ask_phil.publications import (
    ActivePublication,
    PublicationNotFound,
    PublicationStore,
    RefreshRun,
)
from ask_phil.relationship_graph import (
    RelationshipAudit,
    RelationshipGraph,
    RelationshipQuery,
    RelationshipResult,
)
from ask_phil.responses import ResponseLedger
from ask_phil.retrieval import IndexNotReady
from ask_phil.sessions import ConversationSessions, SessionNotFound, SessionReceipt, SessionState
from ask_phil.source_records import CapturedSource, ImportedSources, ImportSummary, SourceInspection
from ask_phil.storage import EvidenceStore, SnapshotNotFound

SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


def create_app(
    database_url: str | None = None,
    *,
    models: Models | None = None,
    tracking_uri: str | None = None,
    execution_limits: ExecutionLimits | None = None,
    session_clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
    database_url = database_url or os.environ["DATABASE_URL"]
    answer_tracking_uri = tracking_uri or os.environ.get(
        "MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db"
    )
    store = EvidenceStore(database_url)
    publications = PublicationStore(database_url)
    sessions = ConversationSessions(database_url, clock=session_clock)
    policies = ExecutionPolicies.from_environment()
    if execution_limits is not None:
        policies = policies.model_copy(update={"serving": execution_limits})
    app = FastAPI(title="Ask Phil evidence inspection", version="0.1.0")
    service = (
        AnswerService(database_url, models, answer_tracking_uri, policies=policies)
        if models
        else None
    )
    service_lock = threading.Lock()

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "loc": error["loc"][:1],
                        "type": error["type"],
                        "msg": "Invalid request value.",
                    }
                    for error in exc.errors()
                ]
            },
        )

    @app.exception_handler(SessionNotFound)
    async def session_missing(request: Request, exc: SessionNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.post("/v1/sessions", status_code=201)
    def start_session() -> SessionReceipt:
        return sessions.create()

    @app.get("/v1/sessions/{session_id}")
    def inspect_session(
        session_id: UUID,
        authorization: Annotated[str | None, Header()] = None,
    ) -> SessionState:
        return sessions.get(session_id, bearer_token(authorization))

    @app.post("/v1/sessions/{session_id}/reset")
    def reset_session(
        session_id: UUID,
        authorization: Annotated[str | None, Header()] = None,
    ) -> SessionState:
        return sessions.reset(session_id, bearer_token(authorization))

    @app.post("/v1/sessions/{session_id}/turns")
    async def conversation_turn(
        session_id: UUID,
        request: AskRequest,
        http_request: Request,
        authorization: Annotated[str | None, Header()] = None,
    ) -> AnswerReceipt:
        budget = ExecutionBudget(policies.serving)
        return await connected_answer(
            http_request,
            budget,
            partial(
                sessions.ask,
                session_id,
                bearer_token(authorization),
                request,
                answer=partial(answer, execution=budget),
            ),
        )

    @app.exception_handler(PublicationNotFound)
    async def publication_missing(request: Request, exc: PublicationNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/v1/publication")
    def active_publication() -> ActivePublication:
        return publications.active()

    @app.post("/v1/snapshots/{snapshot_id}/family")
    def family_query(snapshot_id: Identifier, query: FamilyQuery) -> FamilyResult:
        budget = ExecutionBudget(policies.serving)
        try:
            with budget.activate():
                publications.pin(snapshot_id)
                return FamilyGraph(database_url).query(snapshot_id, query)
        except SnapshotNotFound as exc:
            raise HTTPException(status_code=404, detail="Snapshot not found.") from exc
        except (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable) as exc:
            raise HTTPException(status_code=503, detail="Family graph query timed out.") from exc
        except ExecutionStopped as exc:
            raise HTTPException(status_code=503, detail=f"Family graph stopped: {exc}.") from exc
        except IndexNotReady as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/v1/snapshots/{snapshot_id}/family-claims")
    def family_claims(snapshot_id: Identifier) -> FamilyAudit:
        audit = FamilyGraph(database_url).audit(snapshot_id)
        if audit is None:
            raise HTTPException(
                status_code=404, detail="No reviewed family graph for this snapshot."
            )
        return audit

    @app.post("/v1/snapshots/{snapshot_id}/relationships")
    def relationship_query(snapshot_id: Identifier, query: RelationshipQuery) -> RelationshipResult:
        budget = ExecutionBudget(policies.serving)
        try:
            with budget.activate():
                publications.pin(snapshot_id)
                return RelationshipGraph(database_url).query(snapshot_id, query)
        except SnapshotNotFound as exc:
            raise HTTPException(status_code=404, detail="Snapshot not found.") from exc
        except (psycopg.errors.QueryCanceled, psycopg.errors.LockNotAvailable) as exc:
            raise HTTPException(status_code=503, detail="Relationship query timed out.") from exc
        except ExecutionStopped as exc:
            raise HTTPException(
                status_code=503, detail=f"Relationship graph stopped: {exc}."
            ) from exc
        except IndexNotReady as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/v1/snapshots/{snapshot_id}/relationship-claims")
    def relationship_claims(snapshot_id: Identifier) -> RelationshipAudit:
        audit = RelationshipGraph(database_url).audit(snapshot_id)
        if audit is None:
            raise HTTPException(
                status_code=404, detail="No reviewed relationship graph for this snapshot."
            )
        return audit

    @app.get("/v1/publication/previous")
    def previous_publication() -> ActivePublication:
        return publications.previous()

    @app.get("/v1/refresh-runs")
    def refresh_runs(limit: Annotated[int, Query(ge=1, le=100)] = 20) -> tuple[RefreshRun, ...]:
        return publications.runs(limit)

    @app.get("/v1/refresh-runs/{run_id}")
    def refresh_run(run_id: UUID) -> RefreshRun:
        return publications.run(run_id)

    @app.get("/v1/refresh-runs/{run_id}/captures")
    def refresh_captures(run_id: UUID) -> tuple[CapturedSource, ...]:
        return publications.captures(run_id)

    @app.get("/v1/inspect")
    def inspect_current(
        query: Annotated[SearchText, Query()], limit: Annotated[int, Query(ge=1, le=20)] = 10
    ) -> Inspection:
        pinned = publications.active()
        result = store.inspect(pinned.manifest.snapshot_id, query, limit)
        return result.model_copy(update={"publication": pinned.reference})

    @app.post("/v1/answers")
    async def standalone_answer(request: AskRequest, http_request: Request) -> AnswerReceipt:
        budget = ExecutionBudget(policies.serving)
        return await connected_answer(
            http_request, budget, partial(answer, request, execution=budget)
        )

    async def connected_answer(
        request: Request, budget: ExecutionBudget, operation: Callable[[], AnswerReceipt]
    ) -> AnswerReceipt:
        def run() -> AnswerReceipt:
            with budget.activate():
                return operation()

        worker = asyncio.create_task(asyncio.to_thread(run))
        try:
            while not worker.done():
                if await request.is_disconnected():
                    budget.cancellation.set()
                await asyncio.sleep(0.02)
            return await worker
        finally:
            if not worker.done():
                budget.cancellation.set()
                # Retain the terminal trace/receipt even if the HTTP task is cancelled.
                await asyncio.shield(worker)

    def answer(
        request: AskRequest,
        turn: TurnIdentity | None = None,
        history: tuple[ReferenceTurn, ...] = (),
        *,
        execution: ExecutionBudget,
    ) -> AnswerReceipt:
        nonlocal service
        try:
            with service_lock:
                if service is None:
                    Path("artifacts").mkdir(exist_ok=True)
                    service = AnswerService(
                        database_url,
                        models,
                        answer_tracking_uri,
                        policies=policies,
                    )
            return service.ask(
                request,
                turn=turn,
                history=history,
                execution=execution,
            )
        except (ModelConfigurationError, ProviderError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except SnapshotNotFound as exc:
            raise HTTPException(status_code=404, detail="Snapshot not found.") from exc
        except IndexNotReady as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/v1/responses/{response_id}")
    def original_response(
        response_id: UUID,
        authorization: Annotated[str | None, Header()] = None,
    ) -> AnswerRecord:
        token = authorization.removeprefix("Bearer ") if authorization else ""
        original = ResponseLedger(database_url).get(response_id, token)
        if original is None:
            raise HTTPException(status_code=404, detail="Response not found.")
        return original

    @app.exception_handler(psycopg.Error)
    async def database_unavailable(request: Request, exc: psycopg.Error) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": "Evidence storage is unavailable."})

    @app.get("/v1/snapshots/{snapshot_id}/inspect")
    def inspect(
        snapshot_id: Identifier,
        query: Annotated[SearchText, Query()],
        limit: Annotated[int, Query(ge=1, le=20)] = 10,
    ) -> Inspection:
        try:
            return store.inspect(snapshot_id, query, limit)
        except SnapshotNotFound as exc:
            raise HTTPException(status_code=404, detail="Snapshot not found.") from exc

    def imported_sources(snapshot_id: str) -> ImportedSources:
        try:
            imported = store.snapshot(snapshot_id).imported
        except SnapshotNotFound as exc:
            raise HTTPException(status_code=404, detail="Snapshot not found.") from exc
        if imported is None:
            raise HTTPException(status_code=404, detail="Snapshot has no source import record.")
        return imported

    @app.get("/v1/snapshots/{snapshot_id}/sources")
    def source_report(snapshot_id: Identifier) -> ImportSummary:
        return imported_sources(snapshot_id).report()

    @app.get("/v1/snapshots/{snapshot_id}/sources/{source_id}")
    def inspect_source(snapshot_id: Identifier, source_id: Identifier) -> SourceInspection:
        try:
            return imported_sources(snapshot_id).inspect(source_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail="Source not found.") from exc

    @app.get("/v1/snapshots/{snapshot_id}/identities")
    def resolve_character(
        snapshot_id: Identifier, name: Annotated[SearchText, Query()]
    ) -> IdentityResolution:
        return imported_sources(snapshot_id).catalogue.resolve(name)

    @app.get("/v1/snapshots/{snapshot_id}/evidence/{evidence_id}")
    def resolve(snapshot_id: Identifier, evidence_id: Identifier) -> Inspection:
        try:
            snapshot = store.snapshot(snapshot_id)
        except SnapshotNotFound as exc:
            raise HTTPException(status_code=404, detail="Snapshot not found.") from exc
        matches = tuple(p for p in snapshot.passages if p.evidence_id == evidence_id)
        if not matches:
            raise HTTPException(status_code=404, detail="Evidence not found in this snapshot.")
        return Inspection(
            snapshot_id=snapshot.snapshot_id,
            snapshot_sha256=snapshot.fingerprint,
            source=snapshot.source,
            query=None,
            matches=matches,
            method="evidence_id_lookup_v1",
        )

    return app


def bearer_token(authorization: str | None) -> str:
    return authorization.removeprefix("Bearer ") if authorization else ""
