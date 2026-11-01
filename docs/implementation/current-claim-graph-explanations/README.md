# Current Claim reads and graph explanations

The user selected both candidates from the 1 November 2026 architecture report
and requested implementation, TDD at existing seams, independent review and a
commit on the current branch. The starting revision and review fixed point is
`44cdaad4d399509d66b6508b5eab591c50950fb8` on `main`.
The originating report is `/tmp/architecture-review-20261101-130536-133729.html`.

## Accepted scope

Concentrate current Claim interpretation and story classifications within one
pinned operation. Current notices use the current retained audits and complete
connected correction groups, without traversing maintainer inspection history.
Text retrieval, graph answers and bounded investigation share that implementation.
Keep full history inspection and its diagnostics separately available. Preserve
legacy snapshots, immutable original Claims and evidence, publication pinning,
source qualifications and context/stop limits.

Concentrate graph explanation preparation for Family tree, Character relationship,
Story event and Character connection results. One module owns query-family wording
metadata and result interpretation for direct answers and investigation findings.
Preserve their distinct prose, factual roles, supported timing, synthetic labels,
wording versions, citations and trace results. Graph execution, admission,
review-evidence preparation and investigation context accumulation retain their
existing responsibilities.

ADRs 0003–0007 remain in force. No new domain concept or ADR is required. Preserve
the user's pre-existing workspace, private inputs, source/reference data,
historical evidence and shared spending ledger. No paid inference, new product
issue, publication or tracker mutation is part of this work.

## Test seams

The existing confirmed seams in
[the testing strategy](../../design/testing-and-evaluation.md) apply: retrieval
and typed graph tools, bounded investigation, and public answer/inspection
interfaces. Exercise real disposable PostgreSQL, local MLflow and controlled
external model adapters. Observe notices, classifications, complete citations,
retained answers, wording and recorded model context through those interfaces.
Do not mock internal readers or assert collaborator call order.

Reproduce current serving's dependency on an unreadable archived review record
before changing its implementation. Retain full-history inspection's diagnostic
failure while verifying that the valid current interpretation still answers.
Characterize existing graph wording and investigation findings before moving
their implementation. Run focused files and strict typechecking during the work,
independent Standards and Spec reviews, then the full suite once at the end.

## Implementation

`review_notes.ReviewedClaims` owns the current interpretation for one pinned
operation. It reuses its retained Story event audit for classifications and
notices, derives notices from current audits and captured passages, and keeps
connected corrections complete. Each text pin owns a reader; investigation
shares that reader across text and graph tools. Direct graph answers own a
reader for their pinned snapshot. Full maintainer inspection is unchanged.
The existing `knowledge_review.review_notices` import remains supported.
The retained `EventAudit` owns admitted-classification selection, shared by the
existing graph read and the pinned reader.

`graph_wording.GraphExplanation` owns query-family metadata, evidence presence
and result rendering. Direct answers retain span recording, citations,
conversation state and execution accounting. Investigation retains tool
execution and context accumulation. Relationship wording moved unchanged;
Story event and Character connection renderers retain their existing modules.

## Development checks

The archived-review regression first failed during a current text answer because
serving parsed the damaged ancestor through full inspection. With current reads,
both text and graph answers return the supported dispute and resolvable citations,
while full history inspection still raises its original diagnostic. The focused
review, classification and recovery files passed all **20 cases**.

Four graph-family characterization cases check actual findings submitted to a
controlled model, including biological parentage, adoption, pregnancy timing and
connection direction. They passed before moving the wording implementation.
Relationship rendering has identical syntax structure and both moved wording
version strings retain their original bytes. Strict mypy passed all **149 files**;
Ruff and formatting passed before independent review.

The four-case characterization produced a passing JUnit report, but its reporting
shutdown stalled and termination was requested. The subsequent **78-case** graph
and investigation run exited successfully. Independent Spec verification also
ran all four findings cases plus both current-dispute variants and exited
successfully. The full-suite result below is the final software check.

## Verification

The full suite ran once against the final source and passed **618 tests**, with
zero failures, errors or skips, in **1803.92 seconds**. The process exited
successfully. It reported 16 warnings. All **154 frozen software/configuration
inputs** still match the tested bytes. Strict mypy passed all **149 files**;
Ruff, formatting and diff checks passed. Both independent review axes have
**zero remaining findings**.

All **1,100 protected existing files** outside the eight intentional source/test
edits match the starting state, including all **94 original data files** and the
user's pre-existing workspace changes. No paid model calls were made. These
checks establish software behavior with controlled models, not new model-quality
or canon acceptance.

- [Full software test report](software-tests.xml) and [execution log](software-tests.log)
- [Validation record](validation.json) and [frozen software inputs](software-inputs.json)
- [Independent Standards and Spec review](review.md)
- [Original current-read failure, losslessly compressed](current-read-red.xml.gz) and [passing focused checks](current-read-green.xml)
- [Graph and investigation checks](graph-tests.xml), [classification review checks](classification-review-tests.xml) and [wording compatibility](wording-compatibility.json)

Reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
PREFECT_HOME=/tmp/claim-graph-verification PREFECT_SERVER_ANALYTICS_ENABLED=false MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/pytest -q -p no:cacheprovider --disable-warnings
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
