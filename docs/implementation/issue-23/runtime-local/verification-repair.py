"""Verify the original local capture without generating or judging another answer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from functools import partial
from pathlib import Path
from typing import Any

from mlflow import MlflowClient

from ask_phil.evaluation import (
    CapturedAnswers,
    ClaimReview,
    EvaluationRun,
    EvaluationTracking,
    FactReview,
    QualityReview,
    ReviewedAnswers,
    document_fingerprint,
)


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def write(path: Path, value: Any) -> None:
    with path.open("x") as destination:
        destination.write(json.dumps(value, indent=2) + "\n")


def main() -> None:
    output = Path(__file__).resolve().parent
    original = read(output / "offline.json")
    report = read(output / "report.json")
    references = output / "offline.references.json"
    responses = {row["case_id"]: row["response"] for row in original["cases"]}
    tracking_uri = "sqlite:///" + str(Path("artifacts/issue23-local-mlflow.db").resolve())
    tracking = MlflowClient(tracking_uri=tracking_uri)
    environment = {
        **os.environ,
        "DATABASE_URL": "postgresql://ask_phil:local-demo-only@127.0.0.1:55432/"
        "ask_phil_issue23_local_v1",
        "MLFLOW_TRACKING_URI": tracking_uri,
    }

    def verify(row: dict[str, Any]) -> dict[str, Any]:
        response = row["response"]
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ask_phil.cli",
                "online-review-response",
                report["report_id"],
                response["response_id"],
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        cli = json.loads(result.stdout)
        if cli["response"] != response or cli["response_sha256"] != document_fingerprint(response):
            raise ValueError("Maintainer CLI response differs from the original capture.")
        trace = tracking.get_trace(response["trace_id"], flush=True)
        roots = [span for span in trace.data.spans if span.parent_id is None]
        if len(roots) != 1 or roots[0].outputs != response:
            raise ValueError("Original trace differs from the preserved answer.")
        return {"cli_response": cli["response"], "trace_response": roots[0].outputs}

    capture_path = output / "offline-verified.json"
    with EvaluationRun(
        capture_path,
        references,
        list(responses),
        tracking=EvaluationTracking(
            tracking, "ask-phil-online-regression-local-repair", {"traffic": "demo-test"}
        ),
        artifacts=(Path(__file__), output / "offline.json", output / "failure.json"),
        metadata={
            "expenditure_category": "offline_evaluation",
            "cost_usd": 0,
            "model_calls": 0,
            "repair": "Actual maintainer CLI and original root-trace readback of saved responses.",
            "limitation": "No new agent generation, provider call or factual example.",
        },
    ) as run:
        for identifier, response in responses.items():
            run.capture(identifier, partial(dict, response=response), verify=verify)
    capture = CapturedAnswers(capture_path, references, verified=True)
    annotations = []
    for identifier, row in capture.cases.items():
        response = row["response"]
        supported = identifier == "fixed-control"
        annotations.append(
            QualityReview(
                case_id=identifier,
                response_sha256=document_fingerprint(response),
                reference_sha256=document_fingerprint(row["reference"]),
                reviewer="Codex source-review agent",
                rationale="Retained source clause states February 1990; scripted demo answers.",
                claims=(
                    ClaimReview(
                        claim=response["answer"],
                        correct=supported,
                        grounded=supported,
                        citation_supported=supported,
                    ),
                ),
                required_facts=(
                    FactReview(fact="Phil first arrived in February 1990.", covered=supported),
                ),
                answerability=True,
            )
        )
    scores = capture.score(annotations)
    review_path = output / "offline-reviewed.json"
    write(
        review_path,
        {
            "state": "complete",
            "capture_path": str(capture_path.relative_to(Path.cwd())),
            "capture_sha256": capture.fingerprint,
            "reviewer_type": "agent; requires maintainer quality acceptance",
            "cases": [
                {"case_id": identifier, **score.model_dump(mode="json")}
                for identifier, score in scores.items()
            ],
        },
    )
    ReviewedAnswers(review_path, capture_path, verified=True)
    write(
        output / "verification-repair.json",
        {
            "original_failure": "failure.json",
            "original_capture": "offline.json",
            "repaired_capture": "offline-verified.json",
            "review": "offline-reviewed.json",
            "verified_cli_and_original_trace": True,
            "new_agent_generations": 0,
            "new_provider_calls": 0,
            "local_run_ledger_before_and_after": [0.911656, 0],
            "limitation": "The shared ledger later changed in the separate approved paid pilot.",
        },
    )
    print(json.dumps({"verified": list(scores), "new_provider_calls": 0}))


if __name__ == "__main__":
    main()
