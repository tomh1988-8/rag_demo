# Comparison completion and Character reference deepening

The user selected both candidates from the 5 November architecture report and
requested implementation with `/implement`: TDD at agreed seams, typechecking,
independent code review and a commit on the current branch. The starting revision
and review fixed point is `dcf2b5e2d53f9e82033dee1eceefd3098e3acbaa` on `main`.
The report is `/tmp/architecture-review-20261105-180543-647666.html`.

## Accepted scope

1. The comparison module owns the complete frozen arm/case plan, retained
   observations, missing or failed work and continuation completeness. Capture,
   continuation and scoring use the same plan. A stopped experiment cannot become
   complete merely because all files that happen to exist are complete. Preserve
   the existing per-arm capture, source/review binding, historical artifacts,
   expense controls and distinct recovery lineage. Never repeat paid work as part
   of this change.
2. The Character reference module owns interpretation across automatic route
   changes. Selection, text and investigation reuse one reviewed interpretation
   within the pinned snapshot. Preserve source identity admission, ambiguity and
   reset barriers, generated-claim exclusion, explicit graph override behavior,
   tracing, response schemas and shared execution/accounting.

The existing evaluation/scorer, conversation and routing seams in
[the testing strategy](../../design/testing-and-evaluation.md) apply. Verify
comparison outcomes through temporary capture/report files, and follow-ups
through real PostgreSQL, local MLflow and controlled external model adapters.
Tests observe returned outcomes and saved receipts rather than private methods
or internal call order. Work one failing regression at a time, run focused files
and strict typechecking during implementation, complete both review axes, and
run the full suite once at the end.

ADRs 0003–0007 remain in force. Existing domain terminology is sufficient. This
work does not execute another product issue, paid inference, tracker mutation or
remote publication. Preserve the user's existing workspace changes and data.

## Implementation

`ComparisonPlan` owns the full frozen arm/case matrix, durable plan/progress,
pending-work selection, immutable continuation inputs and completion across
disjoint capture chunks. Failed or unverified attempts require recovery rather
than automatic repetition. Complete arms still use `CapturedAnswers` for source
and review binding. Archived captures remain readable with their original
response identity. Continuation records retain source paths and fingerprints,
so subsequent reads need only the latest directory and reject later rewrites
or additions to its prior inputs.

`CapturedAnswers.retained` reuses the existing strict row validator for completed
and verified observations in a partially attempted failed phase. The original
journal stays failed and remains unavailable to ordinary whole-run review.
Full-attempt finalization/publication failures and running journals do not become
eligible through this read. Phase progress also blocks a continuation before its
prior phase closes, including before a request or between arms; blocked phases
retain their prior lineage.

Routing capture, continuation and scoring share one plan declaration. Text
ablations use the same completion module, and isolated routing recovery reports
the rest of the experiment as pending. Budget stops retain expense readback,
including already-received responses whose verification failed. Monetary and
call ceilings are unchanged; no command performs an automatic paid retry.

`resolve_snapshot_reference` owns catalogue authority: an imported snapshot uses
its captured catalogue; a legacy snapshot can use reviewed graph names. Answer
execution interprets explicit conversational text/investigation once. Automatic
selection interprets once and supplies the same result to text, graph fallback
and investigation. Original request text remains in receipts, while resolved
questions reach the models and retained conversation reference. Explicit graph
override barriers and session transactions keep their existing behavior.
Standalone requests use their original question and normal draft validation;
conversation turns apply the shared reviewed interpretation.

## Development checks

The empty-comparison tracer first returned success with zero observations; it
now rejects scoring. Additional regressions exposed missing continuation
lineage, unreadable lossless archives, silently accepted unplanned arms and
later additions to frozen prior inputs. They now exercise plan completeness,
retention through failure, recovery requirements and source binding.

The serving tracer first returned clarification after a prior Ben Mitchell
question. It now retains that reviewed Character reference across text and
investigation, preserves ambiguous-relative barriers and matches saved receipts
and actual MLflow outputs. A later test assertion incorrectly assumed MLflow's
serialized chat messages exposed a `content` field; the test now reads that
message through its actual `ChatMessage` interface.

Read-only compatibility checks validate all 44 retained legacy routing responses
across eight arms and all 16 archived text-ablation responses across four arms.
They do not regenerate answers or claim a model-quality improvement.

The first full-suite attempt exposed five standalone HTTP/CLI regressions and
was interrupted after 150 passes. Conversation clarification had been applied
to requests without a turn. Applying the shared interpretation only to
conversation turns restores those existing standalone outcomes and their draft
validation. The original log, interrupted XML, 303-input manifest and the two
changed runtime sources remain in `full-suite-initial.*`,
`software-inputs-initial.json` and `initial-runtime-source/`.

The next complete run passed 732 of 733 cases. Its interactive CLI failure was
the shared test-server fixture's five-second shutdown wait, shorter than the
application's existing two 15-second worker-drain allowances. The fixture now
waits at most 35 seconds and still asserts that the server stops. Application
request limits and worker-drain allowances are unchanged. The original complete
run and its input manifest remain in `full-suite-shutdown-failure.*.gz` and
`software-inputs-before-fixture-repair.json`.

The following complete run again passed 732 cases. Its network-cancellation
test reached the request deadline during snapshot/tracing setup, before the
controlled provider received a chat request. The test now allows three seconds
instead of 1.2 before timing out a provider that holds I/O for ten seconds. All
timeout, actual connection-close, MLflow terminal-trace and empty-result
assertions remain. Production limits are unchanged. Both timeout/disconnect
cases pass in `network-deadline-repair.xml`; the original full run and its
input manifest remain in `full-suite-deadline-failure.*.gz` and
`software-inputs-before-deadline-repair.json`.

Final verification passes all **733 tests**, with zero failures, errors or skips
and process exit code zero. Strict mypy, Ruff and formatting checks pass across
185 files; Standards and Spec reviews each have zero remaining findings.
All 303 frozen software/data inputs and 107 protected files match, including the
shared budget ledger and the user's existing work. Public OpenAPI remains
identical across 28 paths and 111 schemas. No paid inference ran.
[The validation record](validation.json) binds these results to the exact inputs.
The raw final log/XML retain 16 warnings and a Prefect console logging error at
process shutdown; the test results and successful exit remain intact.

## Reproduction

Use a disposable PostgreSQL/pgvector admin connection with permission to create
test databases. External model transports in these software checks are controlled.

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
PREFECT_HOME=/tmp/architecture-verification PREFECT_SERVER_ANALYTICS_ENABLED=false MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/pytest -q -p no:cacheprovider --test-database-url "$ASK_PHIL_TEST_DATABASE_URL"
.venv/bin/mypy src tests scripts
.venv/bin/ruff check src tests scripts
.venv/bin/ruff format --check src tests scripts
```
