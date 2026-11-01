"""Local-only acceptance capture: controlled serving, no external judge or key access."""

import argparse
import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import threading
import time
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import uvicorn
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from mlflow import MlflowClient
from ollama import Client

from ask_phil.api import create_app
from ask_phil.evaluation import (
    CapturedAnswers,
    ClaimReview,
    EvaluationRun,
    EvaluationTracking,
    FactReview,
    QualityReview,
    document_fingerprint,
)
from ask_phil.evidence import SourceSnapshot
from ask_phil.feedback import FeedbackPolicy
from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.models import Models, ModelSettings
from ask_phil.online_evaluation import OnlinePolicy
from ask_phil.online_review import OnlineReview, RegressionPromotion, ReportReview
from ask_phil.online_workflow import OnlineEvaluation
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore


def write(path: Path, value: Any) -> None:
    with path.open("x") as destination:
        destination.write(json.dumps(value, indent=2) + "\n")


def ledger() -> tuple[float, int]:
    path = Path("artifacts/openrouter-budget.sqlite").resolve()
    with sqlite3.connect("file:" + str(path) + "?mode=ro", uri=True) as conn:
        row = conn.execute(
            "SELECT coalesce(sum(microdollars),0)/1000000.0, "
            "coalesce(sum(CASE WHEN settled=0 THEN 1 ELSE 0 END),0) FROM reservations"
        ).fetchone()
    return float(row[0]), int(row[1])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output: Path = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    initial = ledger()
    write(
        output / "started.json",
        {
            "traffic": "demo-test",
            "provider_ledger_before": initial,
            "external_judge": "disabled; no provider credentials or network used",
            "code_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
        },
    )
    os.environ.pop("ASK_PHIL_ONLINE_CALIBRATION", None)
    os.environ["ASK_PHIL_ONLINE_ENABLED"] = "true"
    state = {"year": "1991"}

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"model": "local-demo-answer", "digest": "a" * 64},
                        {"model": "local-demo-embedding", "digest": "b" * 64},
                    ]
                },
            )
        if request.url.path == "/api/embed":
            return httpx.Response(200, json={"embeddings": [[1.0, 0.0, 0.0]]})
        return httpx.Response(
            200,
            json={
                "model": "local-demo-answer",
                "done": True,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "status": "answered",
                            "answer": "Phil Mitchell first arrived in February "
                            + state["year"]
                            + ".",
                            "evidence_ids": ["phil-arrival-001"],
                            "unanswered": [],
                            "qualifications": [],
                        }
                    ),
                },
            },
        )

    transport = httpx.MockTransport(provider)
    settings = ModelSettings(
        answer_model="local-demo-answer",
        answer_digest="a" * 64,
        embedding_model="local-demo-embedding",
        embedding_digest="b" * 64,
        embedding_dimensions=3,
    )
    models = Models(
        settings=settings,
        embedding=OllamaEmbedding(
            model_name=settings.embedding_model, client_kwargs={"transport": transport}
        ),
        llm=Ollama(
            model=settings.answer_model,
            context_window=4096,
            additional_kwargs={"num_predict": 256},
            client=Client(host="http://local-model.invalid", transport=transport),
        ),
    )
    seed = SourceSnapshot.model_validate_json(Path("data/seed/phil-arrival-v1.json").read_bytes())
    EvidenceStore(args.database_url).load(seed)
    TextRetriever(args.database_url, models.embedding, settings.embedding_id, 3).prepare(
        seed.snapshot_id
    )
    uri = "sqlite:///" + str(Path("artifacts/issue23-local-mlflow.db").resolve())
    policy = OnlinePolicy(
        background_rate=1, interval_seconds=0.2, max_judge_calls=0, max_judge_spend_usd=0
    )
    app = create_app(
        args.database_url,
        models=models,
        tracking_uri=uri,
        feedback_policy=FeedbackPolicy(delivery_interval_seconds=0.2),
        online_policy=policy,
    )
    evaluation = OnlineEvaluation(args.database_url, uri, policy=policy)
    tracking = MlflowClient(tracking_uri=uri)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.05)
            if not server.started:
                raise RuntimeError("Local API did not start.")
            with httpx.Client(
                base_url=f"http://127.0.0.1:{listener.getsockname()[1]}",
                timeout=30,
                trust_env=False,
            ) as client:

                def ask(label: str) -> dict[str, Any]:
                    result = client.post(
                        "/v1/answers",
                        json={
                            "snapshot_id": seed.snapshot_id,
                            "question": "When did Phil Mitchell first arrive in Walford?",
                        },
                    )
                    result.raise_for_status()
                    value: dict[str, Any] = result.json()
                    write(output / (label + "-response.json"), value["response"])
                    return value

                def wait(response: dict[str, Any], human: bool = False) -> None:
                    deadline = time.monotonic() + 45
                    while time.monotonic() < deadline:
                        trace = tracking.get_trace(response["trace_id"], flush=True)
                        names = {a.name for a in trace.info.assessments}
                        if "online_evidence_checks" in names and (
                            not human or "human_helpfulness" in names
                        ):
                            return
                        time.sleep(0.1)
                    raise TimeoutError("Automatic local assessment was not exported.")

                def feedback(receipt: dict[str, Any], rating: str, comment: str) -> None:
                    response_id = receipt["response"]["response_id"]
                    path = f"/v1/responses/{response_id}/feedback"
                    headers = {"Authorization": "Bearer " + receipt["read_token"]}
                    submission = {
                        "submission_id": str(uuid4()),
                        "policy_version": "feedback-v1",
                        "rating": rating,
                        "categories": ["facts"] if comment else [],
                        "comment": comment,
                    }
                    accepted = client.post(path, headers=headers, json=submission)
                    accepted.raise_for_status()
                    duplicate = client.post(path, headers=headers, json=submission)
                    duplicate.raise_for_status()
                    assert duplicate.json()["revision"] == accepted.json()["revision"]
                    write(output / (response_id + "-feedback.json"), accepted.json())

                wrong = ask("wrong")
                wait(wrong["response"])
                feedback(wrong, "not_helpful", "Check the year. password=synthetic-local-secret")
                state["year"] = "1990"
                correct = ask("correct")
                feedback(correct, "helpful", "")
                unrated = ask("unrated")
                for receipt in (wrong, correct, unrated):
                    wait(receipt["response"], human=receipt is not unrated)
                identifiers = []
                for receipt in (wrong, correct, unrated):
                    trace = tracking.get_trace(receipt["response"]["trace_id"], flush=True)
                    check = next(
                        a for a in trace.info.assessments if a.name == "online_evidence_checks"
                    )
                    assert check.metadata is not None
                    identifiers.append(UUID(check.metadata["job_id"]))
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    if (
                        sum(
                            len(evaluation.inspect(identifier).triage) for identifier in identifiers
                        )
                        == 2
                    ):
                        break
                    time.sleep(0.2)
                else:
                    raise TimeoutError("Automatic feedback reconciliation did not finish.")
                now = datetime.now(UTC)
                cohort = FeedbackCohort(
                    served_from=now - timedelta(hours=1),
                    served_until=now + timedelta(hours=1),
                    feedback_as_of=now,
                )
                report = evaluation.report(cohort)
                write(output / "report.json", report.model_dump(mode="json"))
                assert (
                    report.feedback.counts.eligible,
                    report.feedback.counts.rated,
                    report.feedback.counts.positive,
                    report.feedback.counts.negative,
                ) == (3, 2, 1, 1)
                assert report.scored == 3 and report.support_scored == 0
                assert report.online_judge_calls == 0
                assert all(j.checks and j.checks.reference_correctness is None for j in report.jobs)
                review = OnlineReview(args.database_url)
                dispositions = []
                for item in report.required_reviews:
                    bad = str(item.response_id) == wrong["response"]["response_id"]
                    original = wrong["response"] if bad else correct["response"]
                    dispositions.append(
                        {
                            "response_id": str(item.response_id),
                            "feedback_revision": item.feedback_revision,
                            "response_sha256": document_fingerprint(original),
                            "disposition": "confirmed" if bad else "rejected",
                            "note": "Inspected original source: February 1990. "
                            + (
                                "The 1991 answer is unsupported."
                                if bad
                                else "No factual discrepancy found."
                            ),
                        }
                    )
                checked = review.record(
                    ReportReview.model_validate(
                        {
                            "report_id": str(report.report_id),
                            "reviewer": "Codex source-review agent",
                            "note": "Demo/test traffic; required items checked against source.",
                            "dispositions": dispositions,
                        }
                    )
                )
                write(output / "review.json", checked.model_dump(mode="json"))
                passage = seed.passages[0]
                case = {
                    "case_id": "online-phil-arrival-regression-v1",
                    "group_ids": ["mitchell-arrival-1990", "phil-arrival-february-1990"],
                    "split": "regression",
                    "category": "arrival-year",
                    "question": wrong["response"]["question"],
                    "snapshot_id": seed.snapshot_id,
                    "expected_status": "answered",
                    "required_facts": [
                        {
                            "fact": "Phil first arrived in February 1990.",
                            "sufficient_sets": [[passage.evidence_id]],
                        }
                    ],
                    "allowed_alternatives": [],
                    "forbidden_assertions": ["Phil arrived in 1991."],
                    "evidence": [
                        {
                            "evidence_id": passage.evidence_id,
                            "text": passage.text,
                            "source_revision": seed.source.revision_id,
                            "sha256": passage.sha256,
                        }
                    ],
                    "review_note": "Expected year independently read from the captured clause.",
                    "synthetic_provenance": "Controlled model outputs and scripted demo feedback; "
                    "no external model service.",
                }
                promotion = review.promote(
                    RegressionPromotion.model_validate(
                        {
                            "review_id": str(checked.review_id),
                            "response_id": wrong["response"]["response_id"],
                            "case": case,
                            "source_checks": [
                                {
                                    "fact": "Phil first arrived in February 1990.",
                                    "evidence_ids": [passage.evidence_id],
                                    "note": "Retained revision 1375499431 states February 1990.",
                                }
                            ],
                        }
                    ),
                    output / "regression-v1.json",
                )
                write(output / "promotion.json", promotion.model_dump(mode="json"))
                references = {
                    "cases": [
                        {**case, "case_id": name} for name in ("original-failure", "fixed-control")
                    ]
                }
                reference_path = output / "offline.references.json"
                write(reference_path, references)
                captured_path = output / "offline.json"
                responses = {
                    "original-failure": wrong["response"],
                    "fixed-control": correct["response"],
                }

                def verify(row: dict[str, Any]) -> dict[str, Any]:
                    response = row["response"]
                    trace = tracking.get_trace(response["trace_id"], flush=True)
                    roots = [span for span in trace.data.spans if span.parent_id is None]
                    assert len(roots) == 1 and roots[0].outputs == response
                    return {"original_trace_readback": True}

                with EvaluationRun(
                    captured_path,
                    reference_path,
                    list(responses),
                    tracking=EvaluationTracking(
                        tracking, "online-local-regression-demo", {"traffic": "demo-test"}
                    ),
                    artifacts=(Path(__file__), Path("uv.lock")),
                    metadata={
                        "expenditure_category": "offline_evaluation",
                        "cost_usd": 0,
                        "limitation": "Controlled reply correction; no real quality fix claimed.",
                    },
                ) as run:
                    for name, response in responses.items():
                        run.capture(name, partial(dict, response=response), verify=verify)
                captured = CapturedAnswers(captured_path, reference_path, verified=True)
                annotations = []
                for name, response in responses.items():
                    good = name == "fixed-control"
                    reference = next(r for r in references["cases"] if r["case_id"] == name)
                    annotations.append(
                        QualityReview(
                            case_id=name,
                            response_sha256=document_fingerprint(response),
                            reference_sha256=document_fingerprint(reference),
                            reviewer="Codex source-review agent",
                            rationale="Source says February 1990; synthetic demo outputs.",
                            claims=(
                                ClaimReview(
                                    claim=response["answer"],
                                    correct=good,
                                    grounded=good,
                                    citation_supported=good,
                                ),
                            ),
                            required_facts=(
                                FactReview(
                                    fact="Phil first arrived in February 1990.", covered=good
                                ),
                            ),
                            answerability=True,
                        )
                    )
                write(
                    output / "offline-reviewed.json",
                    {
                        name: score.model_dump(mode="json")
                        for name, score in captured.score(annotations).items()
                    },
                )
                write(
                    output / "assessments.json",
                    {
                        name: [
                            a.to_dictionary()
                            for a in tracking.get_trace(
                                receipt["response"]["trace_id"], flush=True
                            ).info.assessments
                        ]
                        for name, receipt in (
                            ("wrong", wrong),
                            ("correct", correct),
                            ("unrated", unrated),
                        )
                    },
                )
                assert ledger() == initial
                write(
                    output / "manifest.json",
                    {
                        "traffic": "demo-test",
                        "code_revision": subprocess.check_output(
                            ["git", "rev-parse", "HEAD"], text=True
                        ).strip(),
                        "application_sha256": wrong["response"]["application_sha256"],
                        "driver_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        "provider_ledger_before": initial,
                        "provider_ledger_after": ledger(),
                        "new_paid_calls": 0,
                        "online_judge_calls": 0,
                        "serving": "controlled external HTTP model boundary",
                        "actual_services": "localhost HTTP API, PostgreSQL, MLflow SDK, Prefect",
                        "limitation": "No live semantic judge, broad model quality, "
                        "human canon or held-out acceptance.",
                    },
                )
        except BaseException as exc:
            write(
                output / "failure.json",
                {"failure": type(exc).__name__, "provider_ledger": ledger()},
            )
            raise
        finally:
            server.should_exit = True
            thread.join(timeout=30)
    print(json.dumps({"output": str(output), "new_paid_calls": 0, "provider_ledger": ledger()}))


if __name__ == "__main__":
    main()
