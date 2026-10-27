# Claim admission and projection deepening

The user selected both candidates from the 27 October 2026 architecture report
and instructed implementation. The starting revision is
`1e670e9d089aeccdf5566bf81bd334d44804d76a` on `main`.

## Accepted scope

Concentrate shared Claim admission obligations: source snapshot binding, reviewed
Character catalogue agreement, unique review membership, exact evidence spans
and content-bound support reviews. Keep biological ancestry, relationship episodes,
Story event roles, Crime commission support and text-only classifications distinct.
Preserve admitted/held decisions, their reason order and existing public records.

Concentrate immutable Claim projection installation: derivation fingerprints,
credential checks, transaction ownership, locking, idempotent replay, conflict
rejection and retained audits with atomic projection writes. Keep the existing
PostgreSQL tables, typed queries, version prefixes and historical fingerprints.
Earlier audits and raw/held Claims remain readable. A failed installation must
leave no partial projection, and a retry must remain usable.

This does not implement issue #15's correction workflow or coherent publication
of source, index and graph versions. Preserve existing prompts, source/reference
data, credentials, shared spending ledger and the user's pre-existing work.

## Test seams

The already-confirmed Claim extraction/admission and typed graph-tool seams in
[the testing strategy](../../design/testing-and-evaluation.md) apply. Tests call
the existing typed admission functions and graph install/audit/query operations.
Use real disposable PostgreSQL databases for installation, concurrency and recovery;
observe retained audits and query results rather than internal collaborators.
Keep existing domain-rule and conversation/CLI regressions.

Because these are behavior-preserving refactors, first characterize the existing
contracts, then use those checks during each implementation slice. Do not invent
new product behavior merely to make a refactoring test fail.

## Implementation

`claims.ClaimAdmission` owns batch/source agreement, captured catalogue binding,
review membership, passage resolution and content-bound support checks. Typed
admission functions retain their existing arguments, result records and semantic
rules. The common Claim records now live with that implementation; the original
parentage imports remain available for existing callers.

`claim_projections.install_projection` owns source loading, typed admission,
derivation identity, credential checks, locking, immutable replay and one
transaction for all retained records and graph rows. Its private projection
descriptions retain the three existing schemas and distinct biological edges,
relationship assertions and Story event participant rows. Callers supply their
existing typed batch and reviews; they do not supply SQL, callbacks or lock order.
The graph modules retain typed queries and their existing public audit imports.

Common projection tests now replace repeated sequential replay/conflict checks in
the three graph test files. They also cover concurrent first installation and
recovery after an external PostgreSQL constraint rejects a later projection row.
Assertions use audit/query results; SQL is used only to arrange the database fault.

## Verification

The final full suite passed **454 tests**, with zero failures, errors
or skips, in 1225.971 seconds. It ran once after the review fix. Strict mypy
passed all 104 files; Ruff, formatting and the staged secret scan passed.
Both independent review axes have zero remaining findings; see [the review](review.md).
The suite reports the existing Starlette/httpx deprecation and JUnit record-property
warning categories.

Focused checks passed during implementation: 49 admission checks initially,
44 graph/answer checks after projection deepening, 32 expanded shared admission
checks, and 49 admission/projection checks after the shared test-fixture fix.

[Runtime readback](runtime-verified.json) compares the archived starting application
with both replay of existing projections and fresh installation using the final
application. All seven historical raw/reviewed audits, derivation fingerprints,
27 typed graph query outcomes and six text classifications match exactly. Raw
extraction failures and held Claims retain their original status and evidence.
Public schemas also match exactly: 23 HTTP paths, 71 records and three extraction
schemas. These checks establish software compatibility, not improved model quality.

All 421 protected files match their starting hashes, including source/reference
inputs, historical evidence, credentials, the shared spending ledger and the user's
pre-existing work. No paid calls were required. All 159 pinned source, test and
configuration/data inputs match the final tested files.

The [validation record](validation.json) binds the checks to their exact inputs;
the [full test report](software-tests.xml) retains individual test outcomes.

To reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/pytest -q -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
