# Assessment publication deepening

The user selected the top recommendation from the 1 November 2026 architecture
report and requested implementation, TDD, review and a commit on the current
branch. The starting revision and review fixed point is
`e217853cb6f7c2a8e7a8dca70cf66c9c76127496` on `main`.
The originating report is `/tmp/architecture-review-20261101-181113-980946.html`.

## Accepted scope

Concentrate original-trace binding and idempotent MLflow assessment publication
in one deep module. Human helpfulness, evidence checks and context-support
assessments share stable assessment identity, missing-resource handling,
write/readback and exact payload/source validation. Exact readback includes the
superseded assessment for a revised human rating.

Keep assessment names, values, metadata, source kinds, identifiers and revision
lineage. Preserve workflow-specific queue transactions, retry policies, bounded
online cancellation/deadlines, durable scoring before export, judge accounting,
backend selection and retention cleanup. Remove online execution's dependency
on feedback delivery's private tracking helper. Reuse the existing MLflow
adapter rather than introduce a generic transport abstraction.

ADRs 0003, 0004, 0006 and 0007 remain in force. This changes no domain terminology
or factual interpretation. Preserve original answers, source/reference data,
historical evidence, private inputs and the shared paid-inference ledger.
Retained-cohort reporting, the second architecture candidate, is outside scope.
No paid inference, tracker mutation or remote publication is part of this work.

## Agreed test seams

The user-confirmed conversation/feedback and evaluation/scorer seams in
[the testing strategy](../../design/testing-and-evaluation.md) apply. Exercise
feedback acceptance/inspection/delivery and online processing/reporting with real
disposable PostgreSQL and local MLflow. Use the existing HTTP fault proxy and
controlled external model adapters. Assert retained outcomes and MLflow
assessments, not private methods or collaborator call order.

First reproduce incorrect supersession readback through a revised human rating,
then check recovery without changing the accepted revision. Preserve existing
missing-trace, outage and lost-acknowledgement cases. Characterize online support
export recovery and durable judge accounting through the evaluation interface.
Run focused files and strict typechecking during implementation, independent
Standards and Spec reviews, then the full suite once at the end.

## Implementation

`assessment_publication.AssessmentPublication` binds the original trace to one
retained answer and owns stable-identity publication and exact readback. The
comparison includes assessment/trace identity, name, feedback, source, metadata
and supersession. The same module owns bounded tracking configuration and
idempotent retention deletion through the existing MLflow adapter.

Feedback delivery constructs the human assessment and keeps revision ordering,
durable acceptance, retry scheduling and retention transactions. Online execution
constructs code/support assessments, retains scoring before export and reuses
the same publication for both assessments. Every online attempt binds the
original trace before judging or replaying an export. Cancellation and cycle
deadlines are checked before publication operations; replay does not rescore.
The online configuration fingerprint includes the shared implementation.

## Development checks

The existing feedback file passed all three baseline cases. The new revised-rating
regression then failed because delivery was marked complete after the HTTP proxy
omitted its supersession link. The shared implementation passed all four feedback
cases, including recovery with the same accepted revision and assessment identity.

Two online characterization cases passed before and after switching publication:
missing traces, outages and a lost acknowledgement on either the code or support
assessment preserve durable scoring and do not repeat the controlled judge charge.
The expanded recovery check also interrupts either export with cancellation.
All **43 focused cases** passed with zero failures, errors or skips. Strict mypy
passed all **164 files**; Ruff and formatting passed. The public OpenAPI matches
the starting revision exactly: **28 paths and 95 schemas**. Both independent
review axes have **zero findings**; see [the review](review.md).

- [Original supersession-readback failure](supersession-red.xml.gz)
- [Four passing feedback delivery checks](feedback-green.xml)
- [Focused feedback and online checks](focused-tests.xml)
- [Frozen software and configuration inputs](software-inputs.json)

Reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
PREFECT_HOME=/tmp/assessment-publication-verification PREFECT_SERVER_ANALYTICS_ENABLED=false MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/pytest -q -p no:cacheprovider --disable-warnings
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```

## Final verification

The full suite ran once against the final implementation and passed **658 tests**,
with zero failures, errors or skips, in **2246.43 seconds**. The process exited
successfully and reported 16 warnings. Prefect emitted the same closed-file
logging diagnostic seen in the characterization run during shutdown, after the
successful test result; it did not change the exit status.

All **176 frozen software/configuration inputs** match the tested bytes. All
**1,212 protected existing files**, including **97 existing data files** and the
user's pre-existing workspace changes, match the starting state. The shared
paid-inference ledger is byte-for-byte unchanged. These are controlled-model
software checks, not new model-quality or canon acceptance.

- [Full software test report](software-tests.xml) and [execution log](software-tests.log)
- [Validation and preservation record](validation.json)

Both independent review axes have **zero remaining findings**. The requested
commit contains the implementation, regressions and this evidence; remote
publication is outside the selected architecture task.
