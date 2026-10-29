# Core character coverage deepening

The user selected the top recommendation from the 29 October 2026 architecture
report and requested implementation with `/implement`. The starting revision and
review fixed point is `f69b7f8add0f28c8867de1b312eca7fbcc7174e8` on `main`.
The originating report is `/tmp/architecture-review-20261029-125916-479809.html`;
the scope below preserves the selected recommendation for review.

## Accepted scope

Concentrate reviewed coverage composition and checked inventory in the coverage
module. Its implementation owns frozen source/reference binding, retained raw
Claim provenance, translated Claim identities, content-bound explicit reviews,
three-family admission composition and consistent per-Core-character figures.
Commands retain argument parsing and output presentation without reconstructing
the evidence protocol. Preserve their arguments, stored formats, immutable
outputs and historical artifact compatibility.

Keep bounded extraction and its no-repeat/restart safeguards in the existing
coverage run, and keep each typed Claim admission rule in its existing module.
Preserve original candidates, annotations, review outcomes, correction links,
extraction scores, source identities, split groups and explicit coverage gaps.
The second report candidate, current Claim review reads, is outside this change.
ADRs 0004–0007 remain in force.

## Test seams

The already-confirmed Claim extraction/admission, evaluation and public-answer
seams in [the testing strategy](../../design/testing-and-evaluation.md) apply.
Observe retained artifacts, admission decisions and inventory through the
coverage interface, with temporary files. Retain CLI smoke checks and real
disposable PostgreSQL / local MLflow answer, citation and trace readback. Existing
controlled HTTP adapters verify extraction without paid model calls.

Characterize existing candidate/reference/admission drift rejection and the
same-marriage correction before restructuring. Preserve the original failures,
raw candidates and reviewed references. Compare historical composition bytes
and inventory records against retained issue #20 evidence. Tests exercise
observable behavior, not private helpers or internal collaborator call order.

The user's pre-existing workspace, private inputs and shared spending ledger are
protected. No paid inference or subsequent product-issue implementation is part
of this work.

## Implementation

`coverage.CoverageEvidence` owns reviewed composition and inventory. Each operation
reads one checked set of source, plan, references and retained extraction results.
The same preparation binds frozen file hashes and original snapshot identity for
both operations. Composition owns Claim identity translation, explicit raw and
reference review binding, typed admission and the four linked output artifacts.
Inventory derives profile figures from those same checked inputs and artifacts.
The two commands now parse arguments and delegate to this module.

The original source-drift regression first reproduced composition accepting a
changed scoped source file. Reporting previously rejected that drift later.
Shared preparation now rejects it before writing composition artifacts. Successful
historical outputs retain their original bytes and serialization order.

Most drift checks and the same-marriage correction now exercise the coverage
interface directly. The existing command-to-PostgreSQL graph answer check still
verifies actual CLI, citation, stored-response and MLflow trace results. Bounded
extraction resume and no-repeat checks retain their existing controlled provider.

## Verification

The full suite ran once against source `fd975bd` and passed **593 tests**, with
zero failures, errors or skips. Strict mypy passed all **140 files**; Ruff,
formatting and diff checks passed. Both independent review axes have **zero
findings**. The 16 warnings are existing Starlette/httpx and JUnit
`record_property` categories.

The focused checks passed **15 cases**: 11 composition/artifact checks plus four
real-publication and extraction-resume checks. Independent Spec verification
also passed historical replay and early source-drift rejection. The original
source-drift failure and passing regression are retained separately.

All four composition files reproduce the original issue #20 bytes exactly;
the complete **20-profile / 22-batch inventory** also matches. All **318 frozen
software/configuration/data/test inputs** still match the tested source. All
**1,062 protected existing files** outside the four intentional implementation
and test edits remain unchanged, including the user's pre-existing workspace,
**94 existing data files**, private inputs and shared spending ledger.
No paid model calls were made; the ledger remains **$0.911656**, with no unsettled
reservations.

- [Validation record](validation.json) and [frozen inputs](software-inputs.json)
- [Independent Standards and Spec reviews](review.md)
- [Historical compatibility](compatibility.json)
- [Full test report](software-tests.xml) and [execution log](software-tests.log)
- [Static checks](static-checks.log)
- [Original source-drift failure](source-drift-red.xml) and [passing regression](source-drift-green.xml)

Reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
PREFECT_HOME=/tmp/ask-phil-verification PREFECT_SERVER_ANALYTICS_ENABLED=false MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/pytest -v -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
