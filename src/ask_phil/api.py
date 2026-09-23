"""Shared HTTP interface for evidence inspection; fixture loading is maintainer-only."""

import os
from typing import Annotated

import psycopg
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import StringConstraints

from ask_phil.evidence import Identifier, Inspection
from ask_phil.storage import EvidenceStore, SnapshotNotFound

SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


def create_app(database_url: str | None = None) -> FastAPI:
    store = EvidenceStore(database_url or os.environ["DATABASE_URL"])
    app = FastAPI(title="Ask Phil evidence inspection", version="0.1.0")

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
