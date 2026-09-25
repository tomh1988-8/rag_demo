"""A bounded local-provider development smoke run, not a representative quality benchmark."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from ask_phil.answering import AnswerService, application_fingerprint
from ask_phil.answers import AskRequest
from ask_phil.evaluation import RetrievalReference, score_retrieval
from ask_phil.models import Models, OpenRouterSettings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-cases", type=int, choices=[1, 2], default=2)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Choose a new output path; baseline artifacts must not be overwritten.")
    references = Path("data/references/phil-arrival-rag-v1.json")
    dataset = json.loads(references.read_text())
    models = Models.from_environment()
    if isinstance(models.settings, OpenRouterSettings):
        raise ValueError(
            "Cloud baselines use scripts/evaluate_answer_policy.py and its spend ledger."
        )
    Path("artifacts").mkdir(exist_ok=True)
    service = AnswerService(
        os.environ["DATABASE_URL"],
        models,
        os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db"),
    )
    rows = []
    for raw in dataset["cases"][: args.max_cases]:
        reference = RetrievalReference.model_validate(raw)
        receipt = service.ask(
            AskRequest(
                snapshot_id=dataset["snapshot_id"],
                question=reference.question,
            ),
            category="offline_evaluation",
        )
        response = receipt.response
        score = score_retrieval(
            reference,
            tuple(hit.passage.evidence_id for hit in response.retrieved),
            tuple(p.evidence_id for p in response.context),
            k=response.retrieval_k,
        )
        trace = service.tracking.get_trace(response.trace_id, flush=True)
        rows.append(
            {
                "reference": reference.model_dump(),
                "response": response.model_dump(mode="json"),
                "retrieval_and_context": score.model_dump(),
                "trace": trace.to_dict(),
            }
        )
        print(f"{reference.case_id}: {response.status}, {response.elapsed_ms:.0f} ms", flush=True)
    experiment = service.tracking.get_experiment_by_name("ask-phil-offline_evaluation")
    assert experiment is not None
    run = service.tracking.create_run(
        experiment.experiment_id,
        tags={
            "kind": "local-development-smoke",
            "expenditure_category": "offline_evaluation",
        },
    )
    run_id = run.info.run_id
    artifact = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "kind": "local-development-smoke",
        "limitation": dataset["scoring"]["limitation"],
        "evaluation_run_id": run_id,
        "application_sha256": application_fingerprint(),
        "reference_sha256": hashlib.sha256(references.read_bytes()).hexdigest(),
        "lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "model_settings": models.settings.model_dump(),
        "budget": {
            "maximum_answer_calls": args.max_cases,
            "output_tokens_per_call": models.settings.output_tokens,
            "paid_api_calls": 0,
            "retries": 0,
        },
        "packages": {
            name: importlib.metadata.version(name)
            for name in (
                "llama-index-core",
                "llama-index-vector-stores-postgres",
                "llama-index-llms-ollama",
                "ollama",
                "mlflow",
                "psycopg",
                "pgvector",
            )
        },
        "cases": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, ensure_ascii=True) + "\n")
    for name, value in models.settings.model_dump().items():
        service.tracking.log_param(run_id, name, value)
    service.tracking.log_param(run_id, "reference_sha256", artifact["reference_sha256"])
    service.tracking.log_param(run_id, "application_sha256", artifact["application_sha256"])
    service.tracking.log_metric(run_id, "case_count", len(rows))
    service.tracking.log_metric(run_id, "estimated_api_cost_usd", 0.0)
    service.tracking.log_artifact(run_id, str(args.output))
    service.tracking.set_terminated(run_id)
    print(f"Saved {len(rows)} actual outcomes and traces to {args.output}; MLflow run {run_id}")


if __name__ == "__main__":
    main()
