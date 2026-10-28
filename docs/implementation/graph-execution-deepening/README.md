# Reviewed graph execution deepening

The user selected the top recommendation from the 28 October 2026 architecture
report and requested implementation. The starting revision and fixed point for
the code review is `71218a24bcd6805b79a28c0c0dacf0a1a78ab4b8` on `main`.

## Accepted scope

Concentrate the shared reviewed graph query lifecycle: execution budget use,
publication pinning, snapshot selection, typed dispatch and stop accounting.
Direct HTTP queries and graph answers use the same module. HTTP status translation
and answer wording remain caller responsibilities. Preserve each typed query's
domain rules, publication verification, retained Claims, evidence, citations,
saved responses, trace identities and observable execution limits.

The speculative Claim review history candidate is outside this change. Existing
source/reference inputs, credentials, the shared spending ledger and pre-existing
workspace changes must remain intact. No paid model calls or issue implementation
are required. ADRs 0004–0007 continue to apply.

## Implementation

`graph_execution.GraphExecution` pins a publication and selects its snapshot,
activates one request budget for query work, dispatches typed queries and records
database timeouts and execution stops. A caller may supply its already-consumed
budget; the module never resets it. Direct queries supply their serving limits
and receive a fresh request budget. Captured passages are loaded lazily for
answers, avoiding an extra source read for direct typed queries.

The existing typed graph modules retain their PostgreSQL implementation and
publication checks. The HTTP adapter retains its error text in one translation
helper. Graph answering retains its wording, review preparation and trace spans,
while delegating query execution to the shared module.

## Test seams

The already-confirmed typed graph-tool, bounded-investigation and HTTP/answer
seams in [the testing strategy](../../design/testing-and-evaluation.md) apply.
Use disposable PostgreSQL databases and local MLflow. Verify returned evidence,
retained stops and actual traces through these interfaces; do not mock internal
collaborators or test dispatch structure.

Before restructuring, the broadened limit checks across all four query families
and the consumed-caller-budget check passed: **5 checks**. These characterize
existing behavior rather than introducing an artificial failing requirement.

## Verification

All 25 Character connection checks and 38 family, relationship, Story event and
bounded-execution checks passed after restructuring. The authority cases also
check that allowing other graph capabilities cannot authorize the selected one.
Strict mypy passed all 118 files; Ruff and formatting passed. All 25 HTTP paths
and 84 response schemas exactly match the starting revision.

The independent [Standards and Spec reviews](review.md), including follow-up
reviews of the final per-capability checks, have no findings.

The final full suite ran once and passed **518 tests**, with zero failures,
errors or skips, in **1328.58 seconds**. The 16 warnings are the existing
Starlette/httpx deprecation and JUnit `record_property` categories. The
[test report](software-tests.xml), [full log](software-tests.log) and
[focused checks](focused-tests.log) retain the outcomes.

All **170 frozen software, configuration and data inputs** still match their
[recorded hashes](software-inputs.json). All **716 protected existing files**
outside the five planned edits remain unchanged, including pre-existing workspace
changes, source/reference inputs and private files. No paid model calls were made.
The shared ledger matches its earlier preservation hash and remains **$0.464981**
with zero unsettled reservations.
The [validation record](validation.json) binds these checks to the tested inputs.

To reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
PREFECT_HOME=/tmp/graph-execution-prefect PREFECT_SERVER_ANALYTICS_ENABLED=false MLFLOW_DISABLE_AGENT_HINT=1 .venv/bin/pytest -v -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
