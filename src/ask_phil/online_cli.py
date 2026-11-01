"""Maintainer-only online evaluation commands; database credentials stay local."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from uuid import UUID

from ask_phil.feedback_reporting import FeedbackCohort
from ask_phil.online_review import OnlineReview, RegressionPromotion, ReportReview
from ask_phil.online_runtime import configured_online, online_worker


def add_online_commands(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    commands.add_parser("online-process", help="Maintainer: run a bounded durable Prefect batch.")
    commands.add_parser(
        "online-worker", help="Maintainer: continuously process retained interactions."
    )
    report = commands.add_parser(
        "online-report", help="Maintainer: save a versioned quality report."
    )
    report.add_argument("--served-from", type=datetime.fromisoformat)
    report.add_argument("--served-until", type=datetime.fromisoformat)
    report.add_argument("--as-of", type=datetime.fromisoformat)
    inspect = commands.add_parser(
        "online-inspect", help="Maintainer: inspect original assessment evidence."
    )
    inspect.add_argument("job_id", type=UUID)
    review = commands.add_parser(
        "online-review", help="Maintainer: record immutable report dispositions."
    )
    review.add_argument("request", type=Path)
    history = commands.add_parser(
        "online-review-history", help="Maintainer: inspect report dispositions."
    )
    history.add_argument("report_id", type=UUID)
    response = commands.add_parser(
        "online-review-response", help="Maintainer: inspect any reported original response."
    )
    response.add_argument("report_id", type=UUID)
    response.add_argument("response_id", type=UUID)
    promotion = commands.add_parser(
        "online-promote", help="Maintainer: promote a source-checked regression."
    )
    promotion.add_argument("request", type=Path)
    promotion.add_argument("--output", type=Path, required=True)


def run_online_command(args: argparse.Namespace) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is required for maintainer evaluation commands.")
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///artifacts/mlflow.db")
    review = OnlineReview(database_url)
    if args.command == "online-review":
        print(
            review.record(
                ReportReview.model_validate_json(args.request.read_bytes())
            ).model_dump_json()
        )
    elif args.command == "online-review-response":
        import json

        from ask_phil.evaluation import document_fingerprint

        original = review.response(args.report_id, args.response_id).model_dump(mode="json")
        print(json.dumps({"response": original, "response_sha256": document_fingerprint(original)}))
    elif args.command == "online-review-history":
        from pydantic import TypeAdapter

        print(
            TypeAdapter(tuple[ReportReview, ...]).dump_json(review.history(args.report_id)).decode()
        )
    elif args.command == "online-promote":
        request = RegressionPromotion.model_validate_json(args.request.read_bytes())
        print(review.promote(request, args.output).model_dump_json())
    elif args.command == "online-worker":
        stop, wake = Event(), Event()
        try:
            online_worker(database_url, tracking_uri, stop, wake)
        finally:
            stop.set()
    else:
        with configured_online(database_url, tracking_uri) as evaluation:
            if args.command == "online-process":
                print(evaluation.process().model_dump_json())
            elif args.command == "online-inspect":
                print(evaluation.inspect(args.job_id).model_dump_json())
            else:
                now = datetime.now(UTC)
                cohort = FeedbackCohort(
                    served_from=args.served_from or now - timedelta(days=1),
                    served_until=args.served_until or now,
                    feedback_as_of=args.as_of or now,
                )
                print(evaluation.report(cohort).model_dump_json())
