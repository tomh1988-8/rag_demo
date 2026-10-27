# Graph acceptance and Source refresh deepening

The user selected both candidates from the 27 October 2026 architecture report
and requested implementation with TDD, review and a commit on the current branch.
The starting revision is `0ee405782b37d226ceec2cfad1dbde16d68e02a7`.

## Accepted scope

The graph acceptance module owns disposable PostgreSQL, application startup,
HTTP/CLI/session capture, durable progress, citation resolution, retained-response
readback after restart and exact agreement with actual MLflow outputs. Commands
retain their domain cases, scoring and raw-versus-reviewed distinctions. Preserve
historical artifacts and command options; retain captured answers when a later
verification fails. Reuse the existing retained evaluation-run implementation
where compatible rather than creating a second generic run engine.

The Source refresh journal owns the writer connection, progress transitions,
captured-source outcomes, partial/failed/interrupted records and final-record
consistency. Refresh and rollback no longer rebuild records or coordinate raw
database writes. Keep publication and its final record atomic, retain captures,
and preserve idempotency, recovery, source/index compatibility and pinned answers.

Use the already-confirmed evaluation, conversation and Source ingestion/refresh
seams in [the testing strategy](../../design/testing-and-evaluation.md). Tests use
real disposable PostgreSQL, temporary files, local MLflow/Prefect and loopback
HTTP; substitute only external source/model/tracking operations where needed.
The interface is the test surface. Keep existing domain-rule and recovery checks.

ADRs 0004–0007 remain in force. No new domain term or ADR is required. Preserve
source/reference inputs, historical evidence, private credentials, the shared
non-resetting spending ledger and pre-existing user work. No paid calls or new
product ticket are part of this change.

## Module interfaces

`GraphAcceptanceRun.run` accepts phases containing the frozen snapshot/Claim/review
paths and typed graph cases. Each case selects HTTP, CLI or a session and may
supply its own independent domain assessment. The module supplies assessments
with its parsed frozen snapshot and frozen reference bytes; commands do not
parse another copy before tracking setup. The module owns disposable
databases, startup, typed-tool/audit checks, receipt readback after restart and
exact actual trace comparison. Commands select cases and interpret domain scores.

The existing `EvaluationRun` journals each attempt before execution and the
captured answer before verification. Capture completion and verification are
distinct: a failed proof retains the returned answer and an explicit failed
verification, while the overall run remains failed. No read/session capabilities
are written to the artifact. Historical fields remain; run state and per-case
progress are additive. Existing output paths are never reused.

`refresh_journal` owns the writer connection and refresh outcome. `SourceRefresh`
keeps its `run` and `rollback` interface and the existing Prefect flows; callers
no longer construct `RefreshRun` copies or pass a connection into capture.
Captures and their source outcomes commit together. Publication and its final
record still commit in the existing PostgreSQL transaction. Ordinary failures
retain partial/failed outcomes; explicit interruptions are recorded immediately
and propagated. Abrupt process termination retains the existing next-writer
interruption recovery. The historical exception imports remain supported.

## Development checks

The refresh tracer first failed with `running` instead of `interrupted` after a
source interrupted capture, then passed. The existing refresh file passed all
17 checks, including the new tracer. A second check injects a real PostgreSQL
write failure and observes no orphan capture or source outcome and no pointer
change.

The graph tracer first failed because the deep interface did not exist, then
passed with two retained answers after a later tracking timeout. The family
command first failed its missing completion-state check, then passed with its
original nine outcomes and retained 2/3 reference-path recall. One development
run was correctly rejected after source edits changed its application fingerprint;
the fixed-source rerun passed. Relationship and event command migration removes
their imports from the family command and keeps the distinct case/scoring rules.

Independent Standards review found one reference-binding defect: a command could
parse a reference before the run froze newer bytes. A copied-reference regression
changes the labels during external tracking setup and first failed because old
labels were still scored. Assessments now consume the bytes frozen by the run.
The Spec review initially reported zero findings; final review readback follows
the focused regression. The Docker test stage includes the acceptance commands
and their existing reviewed Claim/review fixtures. Packaged runs without Git
retain the application fingerprint and explicitly record an unknown revision.

## Verification

The final full suite passed **395 tests**, with zero failures, errors or skips,
in **1121.27 seconds**. It ran once against the final source. Strict mypy passed
all **94 files**; Ruff lint and formatting passed. The independent Standards
and Spec reviews have **zero remaining findings**. See the
[software test report](software-tests.xml) and [review record](review.md).

Separate readback of the actual local MLflow storage verifies **61 graph
responses**: nine Family tree, 28 Character relationship and 24 Crime/Criminal
justice involvement outcomes. Root outputs and typed-tool outputs match their
captured results, including the reviewed context stop. Citations resolve and
original receipts survive application restart. All historical domain answers,
result sets and reference scores are preserved; the raw Family tree still has
2/3 reference-path recall. These are software and curated-capability checks,
not new model-quality or canon acceptance.

[Runtime evidence](runtime-verified.json) retains per-response identities and
hashes, actual readback comparisons and selected complete root/tool outputs.
[Validation](validation.json) binds the results to all 104 tested source and
dependency hashes. All **381 protected file hashes** match the starting state,
including source/reference inputs, historical evidence and pre-existing user
work. Credentials and the non-resetting spending ledger remain unchanged:
**$0.417335**, zero unsettled reservations. Validation required no paid calls.

To reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
.venv/bin/pytest -q -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
