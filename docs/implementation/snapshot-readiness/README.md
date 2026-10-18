# Source snapshot readiness deepening

Implements candidate 01 from the architecture review, selected by the user on
18 October 2026. The starting revision is
`22870fc3f353d55d719b731b0523665c86ea6d51`. The user authorized implementation,
review, a commit on the current branch and publication to GitHub.

## Accepted scope

Concentrate source snapshot readiness in the text retrieval module so answering,
recovery and corpus evaluation share version selection and compatibility rules.

- Pin the publication and captured source once per operation. Preserve explicit
  legacy snapshots, unpublished candidate rejection and withdrawn-publication
  rejection.
- Verify the configured embedding identity, source identity, index manifest and
  retained index artifacts before using a published snapshot. Preserve full
  artifact verification and the existing ranking and context-selection behavior.
- Keep a pinned source inspectable before index verification so a deadline during
  verification still produces the existing saved stop outcome and MLflow trace.
- Normalize direct and vector-adapter index/retrieval timeouts inside the module.
  Callers do not compare index manifests or interpret database adapter errors.
- Recovery validates the previous publication before changing the active pointer.
  A failed recovery preserves the current publication and retains a failed run.
- Retain source/citation/receipt identities, public HTTP/CLI contracts, execution
  accounting, request limits, bounded read-only access and historical evidence.

The comparison metadata mismatch and refresh journal deepening are separate
architecture candidates. This change retains the existing passage-context,
conversation-turn, evaluation-run and model-execution depth.

## Test seams

Use the existing confirmed text retrieval, source refresh/recovery and public
conversation/HTTP seams in [the testing strategy](../../design/testing-and-evaluation.md).
PostgreSQL/pgvector, Prefect and local MLflow remain real. Substitute only external
source/model adapters. The first tracer exercises a pinned legacy snapshot through
retrieval; subsequent slices cover publication compatibility and public outcomes.
Tests assert returned passages, publication identity, retained evidence and explicit
failure results. ADRs 0004, 0006 and 0007 continue to apply.

## Module and interface

`TextRetriever.pin` selects the publication and loads its source once. Its
`PinnedText` exposes the retained source and publication as read-only properties.
`verify` owns source/index compatibility and complete artifact verification;
`retrieve` enforces that verification before returning passages. Each pin belongs
to one operation and verifies published artifacts afresh; verification is retained
only within that pin, with no shared readiness or answer cache.

The two phases preserve tracing behavior: answer execution can retain the source
identity before bounded index verification, then save the same explicit timeout
outcome as before. Source selection failures retain the existing public errors.
Explicit legacy snapshots retain source-only clarification and their existing
prepared-index requirement when retrieving.

`TextRetriever.previous` validates the prior source/index pair before recovery can
restore its publication. The corpus evaluation script uses the same pin while
retaining its separate frozen-reference checks. Database timeout normalization
belongs to the retrieval implementation; answering no longer imports database
adapter errors or compares index manifests. Existing PostgreSQL, embedding and
external model adapters remain in place.

## Verification

The first pinned-retrieval tracer failed because the interface did not exist,
then passed after implementation. The next tracer showed changed vectors being
accepted; it passed once published artifact verification moved into the module.
Counterexamples also reject a publication's mismatched index and source identity
before model work. Existing lifecycle tests now exercise unpublished and withdrawn
snapshot rejection through the deepened retrieval interface.

The final full suite passed **285 tests**, with zero failures, errors or skips,
in 622.72 seconds. It ran once after the two independent reviews. Strict mypy
passed all 59 source files; Ruff and formatting checks passed. Both review axes
have zero findings. All 17 public HTTP paths and 45 OpenAPI schemas match the
starting revision; all 207 frozen source, fixture, retained-evidence and dependency
inputs match the final tested implementation. The suite reports the existing
Starlette/httpx deprecation and JUnit record-property warnings.

Focused runs passed seven retrieval checks, ten public execution-limit checks and
six affected refresh/recovery/concurrent-pinning checks. They retain incompatible
embedding rejection, complete index-artifact verification, saved timeout outcomes,
interrupted/failed refresh recovery, withdrawn-source inspection and pinning during
a concurrent refresh. A separate execution of the actual corpus-evaluation command
returned the three retained fixture passages using real PostgreSQL/pgvector and a
controlled local embedding server.

No paid model calls, live source captures or model-quality evaluations were needed.
The private key, shared trial ledger and pre-existing user work remain unchanged.
The retained answer-quality regressions and the other architecture candidates
continue to require their own work.

The [validation record](validation.json) binds these results to implementation
commit `5b567959b1812a2b9b1f526516918bf0e2c1b744` and its unchanged source hashes.
The [full test report](software-tests.xml), [independent reviews](review.md) and
[controlled corpus probe](corpus-probe.json) retain the supporting evidence.
The final evidence commit changes documentation only.

To reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
.venv/bin/pytest -q -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
