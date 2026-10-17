# Captured-answer evaluation deepening

Implements recommendation 01 from the repo-wide architecture review accepted by
the user on 17 October 2026. The review starts at commit
d8e7d8d7245ec5391014c8c7320d79aabc808ea9.

## Accepted scope

Concentrate capture validity, evidence identity and recorded-run completion in
the evaluation module. Policy, corpus and conversation scripts retain their own
case preparation, actual answer/CLI execution and spending controls.

- Journal a selected case before execution, preserving attempted and failed work
  through provider failure or interruption.
- Complete a run only after all selected cases finish exactly once in order and
  configured MLflow publication succeeds. Keep unfinished publication explicit.
- Review complete captures against the exact frozen references. Reject duplicate
  cases, incomplete or missing responses, missing/duplicate reviews, and stale
  response/reference identities before creating a scored artifact.
- Retain compatibility with the existing policy, corpus and conversation captures
  and their separate quality dimensions.
- Keep review model calls and model spending at zero; associate a new review run
  with its original capture rather than regenerating answers.
- Preserve fresh output paths, private receipts, existing provider reservations
  and distinct serving/offline expenditure.

This is an enabling refactor for quality comparisons. It does not implement or
close issue #9, add calibrated judges, or alter answer prompts or retrieval.

## Module and test seam

**ask_phil.evaluation.EvaluationRun** owns the journal and optional MLflow
publication. Callers select frozen case IDs, supply execution through capture,
and retain measured metadata through annotate. The module owns state,
identifiers and fingerprints. Its EvaluationTracking value configures the
existing MLflow adapter, experiment and tags.

**review_capture** owns batch validation, independent review binding, scoring,
artifact hashes and review publication. The existing scoring functions remain
available. These tests use the evaluation/scorer seam already confirmed in
[the testing strategy](../../design/testing-and-evaluation.md).

New artifacts add selected case IDs, per-case reference/response fingerprints and
recorder_version: frozen-evaluation-run-v1. The existing capture shapes remain
readable. Each new review has its own run, zero review model usage and a
source_run_id when the capture recorded one. Reset outcomes remain in
conversation captures and are excluded from factual scoring.

Local journals use exclusive creation and atomic replacement. A caught failure
records its type without upstream exception text; an abrupt process death leaves
the last attempted case and a running/finalizing journal. Such a journal cannot
be reviewed as complete. Retain it for inspection and choose a fresh output path;
the module does not retry paid execution.

## Validation

Focused tests exercise all three score commands without model configuration,
real local MLflow results, unchanged retained artifacts, stale and incomplete
inputs, zero-denominator dimensions, attempt retention and failed/interrupted
publication. Strict mypy and Ruff pass.

Replaying retained captures reproduces every previously recorded quality
dimension: 13 policy cases from issue #4, 25 corpus cases from issue #7, and nine
conversation responses from issue #8. Replay uses zero answer-model calls.
These are compatibility checks, not a new model-quality assessment.

Final suite results and both review axes are recorded in
[validation.json](validation.json).

    uv run pytest tests/test_evaluation_runs.py tests/test_policy_evaluation.py -q
    uv run mypy
    uv run ruff check .
    docker compose --profile test run --build --rm test
