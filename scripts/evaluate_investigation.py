"""Capture paired, bounded investigator/text runs with exact public trace readback."""

import argparse
import hashlib
import json
import os
import socket
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from functools import partial
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx
import psycopg
import uvicorn
from fastapi import FastAPI
from mlflow import MlflowClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter

from ask_phil.answering import application_fingerprint
from ask_phil.answers import AnswerReceipt, AnswerRecord
from ask_phil.api import create_app
from ask_phil.connection_evaluation import ConnectionReference
from ask_phil.evaluation import (
    EvaluationRun,
    RetrievalReference,
    score_retrieval,
)
from ask_phil.event_graph import EventGraph
from ask_phil.evidence import SourceSnapshot
from ask_phil.execution import ExecutionLimits
from ask_phil.family_graph import FamilyGraph
from ask_phil.investigation_evaluation import score_investigation
from ask_phil.investigation_tools import TOOL_ARGUMENTS, TOOL_CONTRACT_SHA256
from ask_phil.models import Models, OpenRouterSettings
from ask_phil.openrouter import Budget
from ask_phil.parentage import ClaimBatch, ClaimReview
from ask_phil.publications import PublicationStore, RefreshRun
from ask_phil.relationship_graph import RelationshipGraph
from ask_phil.relationships import RelationshipBatch
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventReview

REFERENCES = Path("data/references/investigation-v1.json")
SNAPSHOT = Path("data/seed/connections-pilot-v1.json")
CLAIMS = Path("data/references/connections-v1.json")
REVIEWS = Path("docs/implementation/issue-16/claim-reviews.json")
LIMITS = ExecutionLimits(
    model_calls=8,
    tool_calls=4,
    http_calls=24,
    seconds=180,
    context_bytes=4000,
    spend_usd=Decimal("0.20"),
    concurrency=1,
)
TRIAL_START = Decimal("0.464981")
TRANCHE_CAP = Decimal("1.20")


@contextmanager
def database(admin_url: str) -> Iterator[str]:
    name = "ask_phil_investigation_" + uuid4().hex
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name)))
        try:
            yield make_conninfo(admin_url, dbname=name)
        finally:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


@contextmanager
def serve(app: FastAPI) -> Iterator[str]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and worker.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            if not server.started:
                raise RuntimeError("Local capture API did not start.")
            yield f"http://127.0.0.1:{listener.getsockname()[1]}"
        finally:
            server.should_exit = True
            worker.join(timeout=10)
            if worker.is_alive():
                raise RuntimeError("Local capture API did not stop.")


def install(database_url: str, models: Models) -> SourceSnapshot:
    snapshot = SourceSnapshot.model_validate_json(SNAPSHOT.read_bytes())
    reference = ConnectionReference.model_validate_json(CLAIMS.read_bytes())
    reviews = json.loads(REVIEWS.read_bytes())
    EvidenceStore(database_url).load(snapshot)
    common: dict[str, Any] = {
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_sha256": snapshot.fingerprint,
        "catalogue": reference.catalogue,
        "extractor": "retained-reviewed-reference-composition",
    }
    FamilyGraph(database_url).install(
        ClaimBatch(**common, claims=reference.family_claims),
        TypeAdapter(tuple[ClaimReview, ...]).validate_python(reviews["family"]),
    )
    RelationshipGraph(database_url).install(
        RelationshipBatch(**common, claims=reference.relationship_claims),
        TypeAdapter(tuple[ClaimReview, ...]).validate_python(reviews["relationship"]),
    )
    EventGraph(database_url).install(
        EventBatch(
            **common, claims=reference.event_claims, context_claims=reference.context_claims
        ),
        TypeAdapter(tuple[EventReview, ...]).validate_python(reviews["event"]),
    )
    index = TextRetriever(
        database_url,
        models.embedding,
        models.settings.embedding_id,
        models.settings.embedding_dimensions,
    ).prepare(snapshot.snapshot_id)
    publications = PublicationStore(database_url)
    run = RefreshRun(
        run_id=uuid4(),
        flow_run_id=uuid4(),
        started_at=datetime.now(UTC),
        status="running",
        action="review",
        input_sha256=snapshot.fingerprint,
    )
    with publications.writer() as conn:
        publications.publish(snapshot, index, run, conn)
    return snapshot


def verify(client: httpx.Client, answer: AnswerRecord, tracking: MlflowClient) -> dict[str, Any]:
    trace = tracking.get_trace(answer.trace_id, flush=True)
    if trace is None:
        raise ValueError("Actual answer trace is missing.")
    roots = [s for s in trace.data.spans if s.name == answer.route]
    if len(roots) != 1 or roots[0].outputs != answer.model_dump(mode="json"):
        raise ValueError("Actual trace and served response differ.")
    for citation in answer.citations:
        result = client.get(citation.resolve_path)
        result.raise_for_status()
        matches = result.json()["matches"]
        if (
            len(matches) != 1
            or matches[0]["text"] != citation.text
            or matches[0]["sha256"] != citation.sha256
        ):
            raise ValueError("A served citation does not resolve to its exact captured passage.")
    checked = 0
    if answer.investigation:
        for step in answer.investigation.steps:
            if step.result is None:
                continue
            arguments = TOOL_ARGUMENTS[step.tool].model_validate_json(step.arguments, strict=True)
            spans = [
                s
                for s in trace.data.spans
                if s.name == step.tool and s.inputs == arguments.model_dump(mode="json")
            ]
            if len(spans) != 1 or spans[0].outputs != step.result.model_dump(mode="json"):
                raise ValueError("Actual tool trace and investigation record differ.")
            checked += 1
    return {
        "trace_output_matches": True,
        "citations_resolve": True,
        "tool_results_checked": checked,
        "span_names": [s.name for s in trace.data.spans],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url", required=True, help="Disposable local PostgreSQL admin URL."
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--tracking-uri", default="sqlite:///artifacts/issue-17-mlflow.db")
    parser.add_argument("--models", type=Path, default=Path("config/openrouter-sol.json"))
    args = parser.parse_args()
    reference = json.loads(REFERENCES.read_bytes())
    selected = args.cases or [c["case_id"] for c in reference["cases"]]
    by_id = {c["case_id"]: c for c in reference["cases"]}
    if (
        args.output.exists()
        or not selected
        or len(set(selected)) != len(selected)
        or not set(selected) <= by_id.keys()
    ):
        parser.error("Select unique frozen cases and a new output path.")
    if (
        hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() != reference["snapshot_file_sha256"]
        or hashlib.sha256(CLAIMS.read_bytes()).hexdigest() != reference["claim_reference_sha256"]
    ):
        raise ValueError("Source/reference inputs changed after the development cases were frozen.")
    os.environ["ASK_PHIL_MODELS"] = str(args.models)
    models = Models.from_environment()
    if not isinstance(models.settings, OpenRouterSettings):
        raise ValueError("The live comparison requires the explicitly selected cloud profile.")
    identity = application_fingerprint()
    tracking = MlflowClient(tracking_uri=args.tracking_uri)
    shared = Budget()
    before, unsettled = shared.summary()
    if unsettled:
        raise ValueError("Resolve the existing unsettled billing before another live run.")
    receipts: list[AnswerReceipt] = []
    inputs = (
        SNAPSHOT,
        CLAIMS,
        REVIEWS,
        args.models,
        Path(__file__),
        *sorted(Path("src/ask_phil").glob("*.py")),
    )
    with (
        EvaluationRun(
            args.output,
            REFERENCES,
            selected,
            artifacts=inputs,
            metadata={
                "application_sha256": identity,
                "model_settings": models.settings.model_dump(mode="json"),
                "limits": LIMITS.model_dump(mode="json"),
                "tool_contract_sha256": TOOL_CONTRACT_SHA256,
                "shared_ledger_before_usd": before,
                "trial_start_usd": str(TRIAL_START),
                "additional_tranche_cap_usd": str(TRANCHE_CAP),
                "expenditure_category": "serving measurements in exposed development comparison",
                "offline_review_model_cost_usd": 0,
            },
        ) as run,
        database(args.database_url) as url,
    ):
        snapshot = install(url, models)
        app = create_app(
            url, models=models, tracking_uri=args.tracking_uri, execution_limits=LIMITS
        )
        with (
            serve(app) as api_url,
            httpx.Client(base_url=api_url, timeout=210, trust_env=False) as client,
        ):
            for case_id in selected:
                case = by_id[case_id]
                run.annotate(stage="capturing", current_case=case_id)

                def capture(
                    route: Literal["text_rag", "investigation"],
                    selected_case: dict[str, Any] = case,
                ) -> dict[str, Any]:
                    spent, unsettled = shared.summary()
                    if (
                        unsettled
                        or Decimal(str(spent)) + LIMITS.spend_usd > TRIAL_START + TRANCHE_CAP
                    ):
                        raise ValueError(
                            "The additional live tranche cannot cover another request."
                        )
                    print(f"Capturing {selected_case['case_id']} {route}", flush=True)
                    started = time.perf_counter()
                    result = client.post(
                        "/v1/answers",
                        json={
                            "snapshot_id": snapshot.snapshot_id,
                            "question": selected_case["question"],
                            "route": route,
                        },
                    )
                    elapsed = (time.perf_counter() - started) * 1000
                    result.raise_for_status()
                    receipt = AnswerReceipt.model_validate(result.json())
                    receipts.append(receipt)
                    return {
                        "response": receipt.response.model_dump(mode="json"),
                        "end_to_end_elapsed_ms": elapsed,
                        "final_support": "Pending independent source review.",
                    }

                def check_capture(
                    captured: dict[str, Any], selected_case: dict[str, Any] = case
                ) -> dict[str, Any]:
                    answer = AnswerRecord.model_validate(captured["response"])
                    if (
                        answer.application_sha256 != identity
                        or answer.snapshot_sha256 != snapshot.fingerprint
                    ):
                        raise ValueError(
                            "The captured application/source differs from the frozen run."
                        )
                    retrieval_reference = RetrievalReference.model_validate(
                        {
                            k: selected_case[k]
                            for k in (
                                "case_id",
                                "question",
                                "answerable",
                                "relevant_ids",
                                "required_facts",
                            )
                        }
                    )
                    context_score = score_retrieval(
                        retrieval_reference,
                        tuple(h.passage.evidence_id for h in answer.retrieved),
                        tuple(p.evidence_id for p in answer.context),
                        k=max(1, answer.retrieval_k),
                    )
                    return {
                        "context_scores": context_score.model_dump(mode="json"),
                        "readback": verify(client, answer, tracking),
                        "orchestration_scores": score_investigation(
                            answer.investigation,
                            answer.execution,
                            expected_stops=tuple(selected_case["expected_stops"]),
                        ).model_dump(mode="json")
                        if answer.investigation and answer.execution
                        else None,
                    }

                run.capture_pair(
                    case_id,
                    {
                        "text_rag": partial(capture, "text_rag"),
                        "investigation": partial(capture, "investigation"),
                    },
                    primary="investigation",
                    verify=check_capture,
                )
                run.annotate(shared_ledger_after_usd=shared.summary()[0])
        run.annotate(stage="application_recreation")
        with (
            serve(
                create_app(
                    url, models=models, tracking_uri=args.tracking_uri, execution_limits=LIMITS
                )
            ) as api_url,
            httpx.Client(base_url=api_url, timeout=10, trust_env=False) as client,
        ):
            for receipt in receipts:
                retained = client.get(
                    f"/v1/responses/{receipt.response.response_id}",
                    headers={"Authorization": f"Bearer {receipt.read_token}"},
                )
                retained.raise_for_status()
                if retained.json() != receipt.response.model_dump(mode="json"):
                    raise ValueError("The original response changed after application recreation.")
        after, unsettled = shared.summary()
        run.annotate(
            stage="complete",
            shared_ledger_after_usd=after,
            unsettled_reservations=unsettled,
            responses_survive_application_recreation=True,
        )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "paired_cases": len(selected),
                "shared_ledger_usd": shared.summary()[0],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
