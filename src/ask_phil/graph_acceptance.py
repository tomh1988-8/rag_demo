"""Retained graph acceptance through real HTTP/CLI, receipts and actual traces."""

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import httpx
import psycopg
import uvicorn
from mlflow import MlflowClient
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import TypeAdapter

from ask_phil.answering import application_fingerprint
from ask_phil.answers import AnswerReceipt, AskRequest
from ask_phil.api import create_app
from ask_phil.claim_projections import EventAudit, FamilyAudit, RelationshipAudit
from ask_phil.connection_evaluation import ConnectionReference
from ask_phil.connection_graph import ConnectionQuery
from ask_phil.evaluation import EvaluationRun
from ask_phil.event_graph import EventGraph, EventQuery
from ask_phil.evidence import SourceSnapshot
from ask_phil.family_graph import FamilyGraph, FamilyQuery
from ask_phil.parentage import ClaimBatch, ClaimReview
from ask_phil.relationship_graph import RelationshipGraph, RelationshipQuery
from ask_phil.relationships import RelationshipBatch
from ask_phil.storage import EvidenceStore
from ask_phil.story_events import EventBatch, EventReview

GraphQuery = FamilyQuery | RelationshipQuery | EventQuery | ConnectionQuery
Assessment = Callable[[dict[str, Any], SourceSnapshot, bytes | None], dict[str, Any]]


@dataclass(frozen=True)
class GraphCase:
    case_id: str
    question: str
    query: GraphQuery
    transport: Literal["api", "cli", "session"] = "api"
    assess: Assessment | None = None


@dataclass(frozen=True)
class GraphPhase:
    name: str
    kind: Literal["family", "relationships", "events", "connections"]
    snapshot: Path
    batch: Path
    reviews: Path
    cases: tuple[GraphCase, ...]
    typed_query: GraphQuery | None = None
    reference: Path | None = None


@dataclass(frozen=True)
class _Captured:
    receipt: AnswerReceipt
    elapsed_ms: float
    session_path: str | None = None
    session_headers: dict[str, str] | None = None


@contextmanager
def _serve(database_url: str, tracking_uri: str) -> Iterator[str]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(
            uvicorn.Config(create_app(database_url, tracking_uri=tracking_uri), log_level="error")
        )
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            if not server.started:
                raise RuntimeError("Acceptance HTTP server did not start.")
            yield f"http://127.0.0.1:{listener.getsockname()[1]}"
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("Acceptance HTTP server did not stop.")


def _code_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        # Packaged acceptance can retain the application fingerprint without a Git checkout.
        return None


class GraphAcceptanceRun:
    def __init__(self, database_url: str, *, tracking: MlflowClient) -> None:
        self._database_url = database_url
        self._tracking = tracking

    def run(
        self,
        output: Path,
        phases: Sequence[GraphPhase],
        *,
        metadata: dict[str, Any] | None = None,
        summarize: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if output.exists():
            raise FileExistsError("Choose a new output path; acceptance evidence is immutable.")
        if not phases or len({p.name for p in phases}) != len(phases):
            raise ValueError("Select unique graph acceptance phases.")
        inputs = tuple(
            dict.fromkeys(
                p
                for phase in phases
                for p in (phase.snapshot, phase.batch, phase.reviews, phase.reference)
                if p is not None
            )
        )
        frozen = {path: path.read_bytes() for path in inputs}
        snapshots = {
            phase.name: SourceSnapshot.model_validate_json(frozen[phase.snapshot])
            for phase in phases
        }
        references: list[dict[str, Any]] = []
        for phase in phases:
            if not phase.cases:
                raise ValueError("Each phase needs graph acceptance cases.")
            for case in phase.cases:
                request = AskRequest(
                    question=case.question,
                    snapshot_id=snapshots[phase.name].snapshot_id,
                    route="graph",
                    graph=case.query,
                )
                references.append(
                    {
                        "case_id": f"{phase.name}-{case.case_id}",
                        "phase": phase.name,
                        "domain_case_id": case.case_id,
                        "transport": case.transport,
                        "request": request.model_dump(mode="json"),
                    }
                )
        responses: list[dict[str, Any]] = []
        checks: list[dict[str, Any]] = []
        admissions: dict[str, Any] = {}
        identity = application_fingerprint()
        with tempfile.TemporaryDirectory(prefix="ask-phil-graph-acceptance-") as temporary:
            reference_path = Path(temporary) / "cases.json"
            reference_path.write_text(json.dumps({"cases": references}))
            evaluation = EvaluationRun(
                output,
                reference_path,
                tuple(r["case_id"] for r in references),
                artifacts=inputs,
                metadata={
                    **(metadata or {}),
                    "captured_at": datetime.now(UTC).isoformat(),
                    "code_revision": _code_revision(),
                    "application_sha256": identity,
                    "snapshot_sha256": snapshots[phases[0].name].fingerprint,
                    "frozen_input_sha256": {
                        str(path): hashlib.sha256(data).hexdigest() for path, data in frozen.items()
                    },
                    "responses": [],
                    "checks": [],
                    "admissions": {},
                    "paid_serving_calls": 0,
                    "serving_inference_usd": 0,
                },
            )
            with evaluation as run:
                if any(path.read_bytes() != data for path, data in frozen.items()):
                    raise ValueError("Frozen acceptance inputs changed before execution.")
                for phase in phases:
                    self._phase(
                        run,
                        phase,
                        snapshots[phase.name],
                        frozen,
                        identity,
                        responses,
                        checks,
                        admissions,
                    )
                if summarize:
                    summary = summarize(deepcopy(responses))
                    if {
                        "responses",
                        "checks",
                        "admissions",
                        "application_sha256",
                        "snapshot_sha256",
                        "code_revision",
                        "stage",
                        "current_case",
                    } & summary.keys():
                        raise ValueError("Domain summary cannot replace acceptance evidence.")
                    run.annotate(**summary)
                run.annotate(stage="complete", current_case=None)
        document: dict[str, Any] = json.loads(output.read_bytes())
        return document

    @contextmanager
    def _database(self) -> Iterator[str]:
        name = "ask_phil_acceptance_" + uuid4().hex
        with psycopg.connect(self._database_url, autocommit=True) as admin:
            admin.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
            )
            try:
                yield make_conninfo(self._database_url, dbname=name)
            finally:
                admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))

    def _phase(
        self,
        run: EvaluationRun,
        phase: GraphPhase,
        snapshot: SourceSnapshot,
        frozen: dict[Path, bytes],
        identity: str,
        responses: list[dict[str, Any]],
        checks: list[dict[str, Any]],
        admissions: dict[str, Any],
    ) -> None:
        run.annotate(stage="installing", current_phase=phase.name)
        with self._database() as database_url:
            EvidenceStore(database_url).load(snapshot)
            audit, endpoint, tool_name = self._install(database_url, phase, frozen)
            admissions[phase.name] = audit["admission"]
            run.annotate(admissions=admissions)
            if phase.kind == "family":
                run.annotate(admission=audit["admission"], graph_sha256=audit["graph_sha256"])
            captures: list[_Captured] = []
            with (
                _serve(database_url, self._tracking.tracking_uri) as url,
                httpx.Client(base_url=url, trust_env=False, timeout=30) as client,
            ):
                for case in phase.cases:
                    identifier = f"{phase.name}-{case.case_id}"
                    run.annotate(stage="capturing", current_case=identifier)

                    def execute(selected: GraphCase = case) -> dict[str, Any]:
                        captured = self._capture(client, url, snapshot.snapshot_id, selected)
                        captures.append(captured)
                        return {
                            "phase": phase.name,
                            "transport": (
                                "api" if selected.transport == "session" else selected.transport
                            ),
                            "response": captured.receipt.response.model_dump(mode="json"),
                            "capture_elapsed_ms": captured.elapsed_ms,
                            **(
                                {"http_elapsed_ms": captured.elapsed_ms}
                                if selected.transport == "api"
                                else {}
                            ),
                        }

                    def verify(
                        record: dict[str, Any], selected: GraphCase = case
                    ) -> dict[str, Any]:
                        captured = captures[-1]
                        run.annotate(stage="verifying")
                        checked = self._verify(
                            client,
                            record["response"],
                            snapshot,
                            identity,
                            selected.query.kind
                            if isinstance(selected.query, EventQuery)
                            else "relationship_history"
                            if isinstance(selected.query, RelationshipQuery)
                            else "family_graph"
                            if isinstance(selected.query, FamilyQuery)
                            else tool_name,
                        )
                        if selected.assess:
                            assessment = selected.assess(
                                deepcopy(record["response"]),
                                snapshot,
                                frozen[phase.reference] if phase.reference else None,
                            )
                            if (record.keys() | checked.keys()) & assessment.keys():
                                raise ValueError(
                                    "Domain assessment cannot replace acceptance evidence."
                                )
                            checked.update(assessment)
                        if captured.session_path:
                            reset = client.post(
                                captured.session_path + "/reset", headers=captured.session_headers
                            )
                            reset.raise_for_status()
                            if reset.json()["generation"] != 1 or reset.json()["history"]:
                                raise ValueError("Session reset did not clear graph references.")
                            checked["session_reset"] = True
                        return checked

                    try:
                        run.capture(identifier, execute, verify=verify)
                    finally:
                        # Preserve the established presentation from the retained journal,
                        # including a response whose verification just failed.
                        responses[:] = [
                            {
                                **{
                                    key: value
                                    for key, value in row.items()
                                    if key
                                    not in {
                                        "case_id",
                                        "reference",
                                        "reference_sha256",
                                        "response_sha256",
                                        "state",
                                        "failure_type",
                                    }
                                },
                                "case_id": row["reference"]["domain_case_id"],
                            }
                            for row in run.cases
                            if "response" in row
                        ]
                        run.annotate(responses=responses)
                run.annotate(stage="checking_graph")
                query = phase.typed_query or phase.cases[0].query
                typed = client.post(
                    f"/v1/snapshots/{snapshot.snapshot_id}/{endpoint}",
                    json=query.model_dump(mode="json"),
                )
                typed.raise_for_status()
                invalid = client.post(
                    "/v1/answers",
                    json={
                        "question": "Invalid mixed graph query",
                        "route": "graph",
                        **(
                            {"graph": {**query.model_dump(mode="json"), "direction": "ancestors"}}
                            if phase.kind != "family"
                            else {}
                        ),
                    },
                )
                if invalid.status_code != 422:
                    raise ValueError("An invalid graph request was accepted.")
                audit_path = (
                    "family-claims"
                    if phase.kind == "family"
                    else "relationship-claims"
                    if phase.kind == "relationships"
                    else "event-claims"
                )
                audit_paths = (
                    {
                        "family": "family-claims",
                        "relationship": "relationship-claims",
                        "event": "event-claims",
                    }
                    if phase.kind == "connections"
                    else {"single": audit_path}
                )
                for kind, path in audit_paths.items():
                    lookup = client.get(f"/v1/snapshots/{snapshot.snapshot_id}/{path}")
                    lookup.raise_for_status()
                    if lookup.json() != (audit if kind == "single" else audit[kind]):
                        raise ValueError("Retained graph audit differs from installed Claims.")
            run.annotate(stage="restarting")
            with (
                _serve(database_url, self._tracking.tracking_uri) as url,
                httpx.Client(base_url=url, trust_env=False, timeout=30) as client,
            ):
                for captured in captures:
                    receipt = captured.receipt
                    saved = client.get(
                        f"/v1/responses/{receipt.response.response_id}",
                        headers={"Authorization": f"Bearer {receipt.read_token}"},
                    )
                    saved.raise_for_status()
                    if saved.json() != receipt.response.model_dump(mode="json"):
                        raise ValueError("Original response changed after application restart.")
            check = {
                "phase": phase.name,
                "typed_tool": typed.json(),
                "invalid_mixed_query_http": 422,
                "audit_readback_matches": True,
                "original_response_survives_restart": True,
            }
            if any(c.transport == "session" for c in phase.cases):
                check.update(
                    event_session_and_reset=True, original_response_survives_api_restart=True
                )
            checks.append(check)
            run.annotate(checks=checks, stage="cleanup")
            if phase.kind == "family":
                run.annotate(
                    typed_tool=typed.json(),
                    invalid_pairing_http=422,
                    original_response_survives_restart=True,
                    traces=[
                        {
                            "trace_id": r["response"]["trace_id"],
                            "span_names": r["trace_span_names"],
                            "zero_inference": True,
                        }
                        for r in responses
                        if r["phase"] == phase.name
                    ],
                )

    def _install(
        self, database_url: str, phase: GraphPhase, frozen: dict[Path, bytes]
    ) -> tuple[dict[str, Any], str, str]:
        if phase.kind == "connections":
            reference = ConnectionReference.model_validate_json(frozen[phase.batch])
            reviews = json.loads(frozen[phase.reviews])
            common: dict[str, Any] = dict(
                snapshot_id=reference.snapshot_id,
                snapshot_sha256=reference.snapshot_sha256,
                catalogue=reference.catalogue,
                extractor="retained-reviewed-reference-composition",
            )
            family = FamilyGraph(database_url).install(
                ClaimBatch(**common, claims=reference.family_claims),
                TypeAdapter(tuple[ClaimReview, ...]).validate_python(reviews["family"]),
            )
            relationship = RelationshipGraph(database_url).install(
                RelationshipBatch(**common, claims=reference.relationship_claims),
                TypeAdapter(tuple[ClaimReview, ...]).validate_python(reviews["relationship"]),
            )
            event = EventGraph(database_url).install(
                EventBatch(
                    **common, claims=reference.event_claims, context_claims=reference.context_claims
                ),
                TypeAdapter(tuple[EventReview, ...]).validate_python(reviews["event"]),
            )
            audits: dict[str, FamilyAudit | RelationshipAudit | EventAudit] = {
                "family": family,
                "relationship": relationship,
                "event": event,
            }
            return (
                {
                    "admission": {
                        k: a.admission.model_dump(mode="json") for k, a in audits.items()
                    },
                    **{k: a.model_dump(mode="json") for k, a in audits.items()},
                },
                "connections",
                "connection_graph",
            )
        if phase.kind == "family":
            family = FamilyGraph(database_url).install(
                ClaimBatch.model_validate_json(frozen[phase.batch]),
                TypeAdapter(tuple[ClaimReview, ...]).validate_json(frozen[phase.reviews]),
            )
            return family.model_dump(mode="json"), "family", "family_graph"
        if phase.kind == "relationships":
            relationships = RelationshipGraph(database_url).install(
                RelationshipBatch.model_validate_json(frozen[phase.batch]),
                TypeAdapter(tuple[ClaimReview, ...]).validate_json(frozen[phase.reviews]),
            )
            return relationships.model_dump(mode="json"), "relationships", "relationship_history"
        events = EventGraph(database_url).install(
            EventBatch.model_validate_json(frozen[phase.batch]),
            TypeAdapter(tuple[EventReview, ...]).validate_json(frozen[phase.reviews]),
        )
        return events.model_dump(mode="json"), "events", "crime_history"

    def _capture(
        self, client: httpx.Client, url: str, snapshot_id: str, case: GraphCase
    ) -> _Captured:
        started = time.perf_counter()
        path, headers = None, None
        request = AskRequest(
            question=case.question, snapshot_id=snapshot_id, route="graph", graph=case.query
        )
        if case.transport == "cli":
            command = [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "--api-url",
                url,
                "ask",
                case.question,
                "--snapshot",
                snapshot_id,
                "--route",
                "graph",
                "--character",
                case.query.character_id,
            ]
            query = case.query
            if isinstance(query, ConnectionQuery):
                command += [
                    "--connect-to",
                    query.target_id,
                    "--depth",
                    str(query.max_depth),
                    "--max-paths",
                    str(query.max_paths),
                    "--max-expansions",
                    str(query.max_expansions),
                ]
            elif isinstance(query, EventQuery):
                command += ["--event-kind", query.kind, "--max-events", str(query.max_events)]
                if query.participant_id:
                    command += ["--participant", query.participant_id]
                if query.event_id:
                    command += ["--event", query.event_id]
            elif isinstance(query, RelationshipQuery):
                command += ["--history", "--max-events", str(query.max_events)]
                if query.partner_id:
                    command += ["--partner", query.partner_id]
            else:
                command += [
                    "--direction",
                    query.direction,
                    "--depth",
                    str(query.max_depth),
                    "--max-paths",
                    str(query.max_paths),
                ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
                env={**os.environ, "NO_PROXY": "127.0.0.1"},
            )
            receipt = AnswerReceipt.model_validate_json(result.stdout)
        else:
            if case.transport == "session":
                created = client.post("/v1/sessions")
                created.raise_for_status()
                session = created.json()
                path = f"/v1/sessions/{session['session']['session_id']}"
                headers = {"Authorization": f"Bearer {session['session_token']}"}
            response = client.post(
                path + "/turns" if path else "/v1/answers",
                headers=headers,
                json=request.model_dump(mode="json"),
            )
            response.raise_for_status()
            receipt = AnswerReceipt.model_validate(response.json())
        return _Captured(receipt, (time.perf_counter() - started) * 1000, path, headers)

    def _verify(
        self,
        client: httpx.Client,
        answer: dict[str, Any],
        snapshot: SourceSnapshot,
        identity: str,
        tool_name: str,
    ) -> dict[str, Any]:
        if (
            answer["application_sha256"] != identity
            or answer["snapshot_sha256"] != snapshot.fingerprint
            or answer["snapshot_id"] != snapshot.snapshot_id
            or answer["route"] != "graph"
        ):
            raise ValueError("Captured answer differs from the frozen application or source.")
        for citation in answer["citations"]:
            evidence = client.get(citation["resolve_path"])
            evidence.raise_for_status()
            matches = evidence.json()["matches"]
            if len(matches) != 1 or any(
                matches[0][k] != citation[k] for k in ("sha256", "text", "evidence_id")
            ):
                raise ValueError("A captured citation does not resolve to its retained passage.")
        trace = self._tracking.get_trace(answer["trace_id"], flush=True)
        if trace is None:
            raise ValueError("The captured answer trace is unavailable.")
        roots = [s for s in trace.data.spans if s.name == "graph"]
        tools = [s for s in trace.data.spans if s.name == tool_name]
        if len(roots) != 1 or roots[0].outputs != answer or len(tools) != 1:
            raise ValueError("Actual trace outputs differ from the captured graph answer.")
        if "graph" in answer:
            if tools[0].outputs != answer["graph"]:
                raise ValueError("Actual graph tool output differs from the captured result.")
        elif answer["execution"]["stop_reason"] != "context_limit":
            raise ValueError("A graph result is missing without its recorded context stop.")
        if answer["execution"]["model_calls"] != 0 or answer["execution"]["tool_calls"] != 1:
            raise ValueError("Graph acceptance requires one tool call and no inference.")
        return {
            "citations_resolve": True,
            "all_citations_resolve": True,
            "trace_output_matches": True,
            "trace_span_names": [s.name for s in trace.data.spans],
            "tool_output": tools[0].outputs,
        }
