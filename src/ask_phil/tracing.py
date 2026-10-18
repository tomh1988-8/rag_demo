"""Shared MLflow experiment naming and artifact location for serving and evaluation."""

from pathlib import Path

from mlflow import MlflowClient


def experiment_for(tracking: MlflowClient, category: str) -> str:
    name = f"ask-phil-{category}"
    experiment = tracking.get_experiment_by_name(name)
    return (
        experiment.experiment_id
        if experiment
        else tracking.create_experiment(
            name, artifact_location=str(Path("artifacts/mlflow").resolve().as_uri())
        )
    )
