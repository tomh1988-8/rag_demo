"""Budgeted local HTTP demo: controlled serving, actual online provider and review.

Run once with --live. Existing artifacts and the shared provider ledger are retained.
The two explicit-subject support controls are demo traffic, not broad judge acceptance.
"""

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any
from uuid import uuid4

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
from ask_phil.execution import ExecutionPolicies
from ask_phil.feedback import FeedbackPolicy
from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.models import Models, ModelSettings
from ask_phil.online_evaluation import OnlinePolicy, OnlineReport
from ask_phil.online_review import OnlineReview, RegressionPromotion, ReportReview
from ask_phil.online_runtime import configured_online
from ask_phil.openrouter import Budget
from ask_phil.retrieval import TextRetriever
from ask_phil.storage import EvidenceStore


def write(path: Path, value: Any) -> None:
    with path.open("x") as destination:
        destination.write(json.dumps(value, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output: Path = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    initial_ledger = Budget().summary()
    write(
        output / "ledger-before.json",
        {"spent_usd": initial_ledger[0], "unsettled": initial_ledger[1]},
    )
    if initial_ledger[1]:
        raise ValueError(
            "Reconcile existing uncertain provider reservations before a new paid demo."
        )
    state = {"year": "1990"}

    def provider(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"model": "demo-answer", "digest": "a" * 64},
                        {"model": "demo-embedding", "digest": "b" * 64},
                    ]
                },
            )
        if request.url.path == "/api/embed":
            return httpx.Response(200, json={"embeddings": [[1.0, 0.0, 0.0]]})
        return httpx.Response(
            200,
            json={
                "model": "demo-answer",
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
        answer_model="demo-answer",
        answer_digest="a" * 64,
        embedding_model="demo-embedding",
        embedding_digest="b" * 64,
        embedding_dimensions=3,
    )
    models = Models(
        settings=settings,
        embedding=OllamaEmbedding(
            model_name="demo-embedding", client_kwargs={"transport": transport}
        ),
        llm=Ollama(
            model="demo-answer",
            context_window=4096,
            additional_kwargs={"num_predict": 256},
            client=Client(host="http://demo-model.invalid", transport=transport),
        ),
    )
    seed = SourceSnapshot.model_validate_json(Path("data/seed/phil-arrival-v1.json").read_bytes())
    EvidenceStore(args.database_url).load(seed)
    TextRetriever(args.database_url, models.embedding, settings.embedding_id, 3).prepare(
        seed.snapshot_id
    )
    tracking_path = Path("artifacts") / ("issue23-" + output.name + "-mlflow.db")
    tracking_path.parent.mkdir(parents=True, exist_ok=True)
    if tracking_path.exists():
        raise FileExistsError("Preserve the original demo tracking database.")
    uri = "sqlite:///" + str(tracking_path.resolve())
    private = Path(tempfile.mkdtemp(prefix="ask-phil-issue23-private-"))
    os.environ["ASK_PHIL_ONLINE_CALIBRATION"] = "docs/implementation/issue-9/judge-calibration.json"
    execution_path = output / "execution-policy.json"
    write(execution_path, ExecutionPolicies(online_enabled=True).model_dump(mode="json"))
    os.environ["ASK_PHIL_EXECUTION_POLICY"] = str(execution_path)
    policy = OnlinePolicy(
        background_rate=1, interval_seconds=0.5, max_judge_calls=2, max_judge_spend_usd=0.25
    )
    write(output / "online-policy.json", policy.model_dump(mode="json"))
    app = create_app(
        args.database_url,
        models=models,
        tracking_uri=uri,
        feedback_policy=FeedbackPolicy(delivery_interval_seconds=0.2),
        online_policy=policy,
    )
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
                raise RuntimeError("Demo API did not start.")
            with (
                httpx.Client(
                    base_url=f"http://127.0.0.1:{listener.getsockname()[1]}",
                    timeout=30,
                    trust_env=False,
                ) as client,
                configured_online(args.database_url, uri, policy=policy) as evaluation,
            ):

                def report() -> OnlineReport:
                    now = datetime.now(UTC)
                    return evaluation.report(
                        FeedbackCohort(
                            served_from=now - timedelta(hours=1),
                            served_until=now + timedelta(hours=1),
                            feedback_as_of=now,
                        )
                    )

                def answer(label: str) -> dict[str, Any]:
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
                    path = private / (label + ".json")
                    with os.fdopen(
                        os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
                    ) as saved:
                        saved.write(json.dumps(value))
                    return value

                def wait_scored(response: dict[str, Any]) -> None:
                    deadline = time.monotonic() + 90
                    while time.monotonic() < deadline:
                        trace = tracking.get_trace(response["trace_id"], flush=True)
                        if any(a.name == "online_context_support" for a in trace.info.assessments):
                            return
                        time.sleep(0.2)
                    raise TimeoutError("Automatic semantic assessment did not arrive.")

                def feedback(receipt: dict[str, Any], rating: str, comment: str) -> dict[str, Any]:
                    submission = {
                        "submission_id": str(uuid4()),
                        "policy_version": "feedback-v1",
                        "rating": rating,
                        "categories": ["facts"] if comment else [],
                        "comment": comment,
                    }
                    path = f"/v1/responses/{receipt['response']['response_id']}/feedback"
                    headers = {"Authorization": "Bearer " + receipt["read_token"]}
                    accepted = client.post(path, headers=headers, json=submission)
                    accepted.raise_for_status()
                    duplicate = client.post(path, headers=headers, json=submission)
                    if duplicate.json()["revision"] != accepted.json()["revision"]:
                        raise ValueError("Duplicate feedback created another revision.")
                    value: dict[str, Any] = accepted.json()
                    return value

                correct = answer("correct")
                wait_scored(correct["response"])
                feedback(
                    correct,
                    "not_helpful",
                    "Demo disagreement: please check the date. password=synthetic-demo-secret",
                )
                disagreement = report()
                write(output / "disagreement-report.json", disagreement.model_dump(mode="json"))
                review = OnlineReview(args.database_url)
                reviewed_disagreement = review.record(
                    ReportReview.model_validate(
                        {
                            "report_id": str(disagreement.report_id),
                            "reviewer": "Codex source-review agent",
                            "note": "Demo/test traffic; inspected the retained Wikipedia clause.",
                            "dispositions": [
                                {
                                    "response_id": correct["response"]["response_id"],
                                    "feedback_revision": 1,
                                    "response_sha256": document_fingerprint(correct["response"]),
                                    "disposition": "rejected",
                                    "note": "Source states February 1990, matching the answer; "
                                    "the negative factual report is rejected.",
                                }
                            ],
                        }
                    )
                )
                write(
                    output / "disagreement-review.json",
                    reviewed_disagreement.model_dump(mode="json"),
                )
                state["year"] = "1991"
                wrong = answer("wrong")
                wait_scored(wrong["response"])
                feedback(wrong, "not_helpful", "The retained source says February 1990, not 1991.")
                feedback(correct, "helpful", "")
                final = report()
                write(output / "report.json", final.model_dump(mode="json"))
                dispositions = []
                for item in final.required_reviews:
                    is_wrong = str(item.response_id) == wrong["response"]["response_id"]
                    original = wrong["response"] if is_wrong else correct["response"]
                    dispositions.append(
                        {
                            "response_id": str(item.response_id),
                            "feedback_revision": item.feedback_revision,
                            "response_sha256": document_fingerprint(original),
                            "disposition": "confirmed" if is_wrong else "rejected",
                            "note": "Checked source: February 1990. "
                            + (
                                "This answer's 1991 is unsupported."
                                if is_wrong
                                else "This answer matches the source; no factual error found."
                            ),
                        }
                    )
                recorded = review.record(
                    ReportReview.model_validate(
                        {
                            "report_id": str(final.report_id),
                            "reviewer": "Codex source-review agent",
                            "note": "Checked required demo items and the remaining helpful rating.",
                            "dispositions": dispositions,
                        }
                    )
                )
                write(output / "review.json", recorded.model_dump(mode="json"))
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
                    "review_note": "Expected date independently read from the captured clause.",
                    "synthetic_provenance": "Controlled wrong external-model output; "
                    "actual API/online judge and scripted demo feedback.",
                }
                promotion = review.promote(
                    RegressionPromotion.model_validate(
                        {
                            "review_id": str(recorded.review_id),
                            "response_id": wrong["response"]["response_id"],
                            "case": case,
                            "source_checks": [
                                {
                                    "fact": "Phil first arrived in February 1990.",
                                    "evidence_ids": [passage.evidence_id],
                                    "note": "Read Wikipedia revision 1375499431: "
                                    "first arrives in February 1990.",
                                }
                            ],
                        }
                    ),
                    output / "regression-v1.json",
                )
                write(output / "promotion.json", promotion.model_dump(mode="json"))
                state["year"] = "1990"
                fixed = answer("fixed")
                responses = {
                    "original-failure": wrong["response"],
                    "fixed-control": fixed["response"],
                }
                references = {
                    "cases": [{**case, "case_id": identifier} for identifier in responses]
                }
                reference_path = output / "offline.references.json"
                write(reference_path, references)
                capture_path = output / "offline.json"

                def verify(row: dict[str, Any]) -> dict[str, Any]:
                    response = row["response"]
                    trace = tracking.get_trace(response["trace_id"], flush=True)
                    roots = [s for s in trace.data.spans if s.parent_id is None]
                    if len(roots) != 1 or roots[0].outputs != response:
                        raise ValueError("Offline original response/trace mismatch.")
                    return {"original_trace_readback": True}

                with EvaluationRun(
                    capture_path,
                    reference_path,
                    list(responses),
                    tracking=EvaluationTracking(
                        tracking, "ask-phil-online-regression-demo", {"traffic": "demo-test"}
                    ),
                    artifacts=(Path(__file__), Path("uv.lock")),
                    metadata={
                        "expenditure_category": "offline_evaluation",
                        "cost_usd": 0,
                        "limitation": "Controlled external-model output correction; "
                        "no accepted application/model-quality fix is claimed.",
                    },
                ) as run:
                    for identifier, response in responses.items():
                        run.capture(
                            identifier,
                            partial(dict, response=response),
                            verify=verify,
                        )
                captured = CapturedAnswers(capture_path, reference_path, verified=True)
                annotations = []
                for identifier, response in responses.items():
                    supported = identifier == "fixed-control"
                    reference = next(c for c in references["cases"] if c["case_id"] == identifier)
                    annotations.append(
                        QualityReview(
                            case_id=identifier,
                            response_sha256=document_fingerprint(response),
                            reference_sha256=document_fingerprint(reference),
                            reviewer="Codex source-review agent",
                            rationale="Expected year read independently from source; demo traffic.",
                            claims=(
                                ClaimReview(
                                    claim=response["answer"],
                                    correct=supported,
                                    grounded=supported,
                                    citation_supported=supported,
                                ),
                            ),
                            required_facts=(
                                FactReview(
                                    fact="Phil first arrived in February 1990.", covered=supported
                                ),
                            ),
                            answerability=True,
                        )
                    )
                scores = captured.score(annotations)
                write(
                    output / "offline-reviewed.json",
                    {
                        "scores": {k: v.model_dump(mode="json") for k, v in scores.items()},
                        "reviewer_type": "agent; requires maintainer quality acceptance",
                        "capture_sha256": captured.fingerprint,
                    },
                )
                write(
                    output / "responses.json",
                    {
                        "correct": correct["response"],
                        "wrong": wrong["response"],
                        "fixed": fixed["response"],
                    },
                )
                write(
                    output / "assessments.json",
                    {
                        name: [
                            a.to_dictionary()
                            for a in tracking.get_trace(
                                response["trace_id"], flush=True
                            ).info.assessments
                        ]
                        for name, response in (
                            ("correct", correct["response"]),
                            ("wrong", wrong["response"]),
                        )
                    },
                )
                command = [sys.executable, "-m", "ask_phil.cli", "online-report"]
                environment = {
                    **os.environ,
                    "DATABASE_URL": args.database_url,
                    "MLFLOW_TRACKING_URI": uri,
                    "ASK_PHIL_ONLINE_POLICY": str(output / "online-policy.json"),
                }
                cli = subprocess.run(
                    command, env=environment, capture_output=True, text=True, check=True
                )
                cli_report = OnlineReport.model_validate_json(cli.stdout)
                write(output / "cli-report.json", cli_report.model_dump(mode="json"))
                cli_review = review.record(
                    recorded.model_copy(
                        update={
                            "report_id": cli_report.report_id,
                            "review_id": uuid4(),
                        }
                    )
                )
                write(output / "cli-review.json", cli_review.model_dump(mode="json"))
                write(
                    output / "manifest.json",
                    {
                        "traffic": "demo-test",
                        "serving_models": "controlled external HTTP boundary",
                        "online_judge": "actual paid calibrated provider; "
                        "narrow explicit-subject support pilot",
                        "code_revision": subprocess.check_output(
                            ["git", "rev-parse", "HEAD"], text=True
                        ).strip(),
                        "application_sha256": correct["response"]["application_sha256"],
                        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                        "report_id": str(final.report_id),
                        "review_id": str(recorded.review_id),
                        "source_revision": seed.source.revision_id,
                        "provider_ledger_before": initial_ledger,
                        "provider_ledger_after": Budget().summary(),
                        "new_serving_provider_calls": 0,
                        "new_online_judge_calls": final.online_judge_calls,
                        "offline_judge_calls": 0,
                        "limitation": "Scripted ratings and controlled serving; "
                        "source-supported agent review, not human canon or held-out acceptance.",
                    },
                )
        except BaseException as exc:
            write(
                output / "failure.json",
                {"failure": type(exc).__name__, "provider_ledger": Budget().summary()},
            )
            raise
        finally:
            server.should_exit = True
            thread.join(timeout=30)
    print(json.dumps({"output": str(output), "provider_ledger": Budget().summary()}))


if __name__ == "__main__":
    main()
