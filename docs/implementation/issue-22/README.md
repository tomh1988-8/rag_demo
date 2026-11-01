# Issue #22: response feedback and live signals

Implements [#22](https://github.com/tomh1988-8/rag_demo/issues/22) from
`ce0e27cc62a9933af38ec6efceafe42107570640` on `main`. The
[reviewed cases](cases.md) preceded implementation at the confirmed conversation
API/CLI and evaluation boundaries. See [usage and operating policy](../../feedback.md).

Published implementation: [25dbc82](https://github.com/tomh1988-8/rag_demo/commit/25dbc826a7ca34f2099dc597728f0a3b1b872c8d).
[The publication receipt](publication.json) verifies the exact remote tree,
all 251 frozen input blobs, nine checked criteria and completed tracker closure.
The receipt/handoff follow-up changes documentation only.

## Implemented behavior

Feedback is attached to an actual delivered response with a server-resolved
original answer, context, citations, turn/session, source/graph snapshot, actual
route and application/prompt/model trace versions. Session feedback uses the
existing expiring feedback capability; standalone feedback uses the response
capability. Reset preserves original identity and clears conversation references.

PostgreSQL commits immutable submission revisions before returning an acceptance
receipt. Exact retries reuse their revision; changed payloads conflict unless
given a new submission identity. Current ratings count once per delivered
interaction. Explicit skip and absent feedback remain unrated. Categories and
bounded comments/corrections are redacted and retained outside retrieval/memory.

A bounded API worker publishes minimal HUMAN assessments to the original local
MLflow trace. It reconciles missing traces, outages, restarts and a successful
write whose acknowledgement was lost. Stable assessment identities and readback
prevent duplicate writes. A newer revision overrides its earlier assessment.
The configured backend fingerprint is bound at serving time for export and
cleanup. Expired local payloads are purged; failed external deletion retains only
minimal cleanup identifiers. Original response/source retention is unchanged.

The private maintainer report defines served-time cohorts and feedback cutoffs,
counts every current item, exposes explicit denominators and paginates all review
priorities. Actual route/outcome/snapshot and application/prompt/model slices are
inspectable. Human helpfulness, reported errors and adjudicated correctness remain
separate. No user account, graphical client, automatic judge or canon edit is added.

## Evidence and scope

`runtime/` contains public API/CLI/MLflow readback from controlled-model executions
with scripted feedback. These are actual database, network and local MLflow
operations; they are not organic user data, new model-quality measurements or
independently adjudicated canon. All bearer capabilities are omitted. The graph
pilot explicitly returns partial ancestry coverage; the investigator completes
its supported arrival case. Their original outcomes and lineage remain unchanged.

The retention counterexample first reproduced false cleanup completion after a
backend switch. Backend binding repairs it while preserving pending cleanup and
recovery at the original backend. The HTTP case exercises hidden trace visibility,
an outage and a lost write acknowledgement, then recovers through a new API
instance. The read-only PostgreSQL case rejects acceptance without a saved receipt.
An independent review found that foreign-backend work could starve current export;
the one-item-batch regression now verifies both immediate current delivery and
subsequent recovery of retained foreign obligations. Receipt expiry also respects
the original session capability's earlier expiry.

[Validation](validation.json) records **616 passing tests**, zero failures/errors/
skips, strict mypy across **147 files**, Ruff/formatting and Compose validation.
The full suite ran once against the frozen source and exited successfully. The
16 warnings are existing Starlette/httpx and JUnit `record_property` categories.
All **251 frozen software/configuration/data inputs** verify, all four runtime
captures match application `cf505a333aa596d0af078edc5ec75e873638f7c38c21661d322bc17aa32f0a74`,
and both [independent review axes](review.md) have **zero remaining findings**.

All **1,079 pre-existing files** were checked, with changes confined to the
intentional implementation/configuration and evidence/handoff paths. All **94
existing data files**, the user's README changes, skills and private inputs are
preserved. No paid inference was made; the shared non-resetting provider ledger
remains **$0.911656**, with zero unsettled reservations.

ONLINE-01 passes this collection contract. Issue #23 owns automatic judging,
sampling, evaluator expense/lag and reviewed regression promotion; ONLINE-03 and
AD-10.4 remain Pending for those broader obligations. No organic-usage, model-quality
or held-out release pass is claimed.
