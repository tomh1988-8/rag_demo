# Issue #2 implementation evidence

23 September 2026. [Ticket #2](https://github.com/tomh1988-8/rag_demo/issues/2)
is implemented and validated natively. **Acceptance remains pending the fresh
Docker Compose run.** Docker/Compose are absent on this machine and sudo requires
the user's password. No container run, image build or hosted deployment is claimed.
The issue remains open; its dependent work is not yet accepted as unblocked.

## What works

- The maintainer loads the reviewed fixture into real PostgreSQL atomically.
  Reimporting identical content is idempotent; an identifier cannot acquire new content.
- The CLI calls the shared FastAPI application over HTTP without database credentials.
  Search returns captured excerpts, revision/license/scope/coverage and explicit limitations.
- Missing evidence, unknown references, invalid requests and unavailable storage have
  distinct public outcomes. No model or embedding call is made.
- Saved evidence resolves by snapshot and evidence ID after application recreation.
  A separate actual PostgreSQL restart preserved the snapshot fingerprint and CLI result.

The [source record](../../../data/seed/README.md) and
[reference artifact](../../../data/references/phil-arrival-v1.json) record exact
evidence, reviewer identities, acceptable and forbidden outcomes, and synthetic
question provenance. A second agent independently inspected the downloaded source
and confirmed the clause, hashes, offsets, revision, license and labels. This is
source review by agents, not human review or independent corroboration of canon.

## Actual validation

- Full suite: **17 passed, 0 failed, 0 skipped**, with one upstream Starlette
  TestClient deprecation warning. [JUnit](tests.xml), [captured output](test-output.txt).
- Typechecking: mypy passed on 10 source/test/script files.
- Lint: `ruff check .` passed.
- [Baseline](baseline.json): both actual API outputs match the reviewed evidence-ID
  expectations: one arrival passage and one absent-evidence result. These two exposed
  development cases say nothing about generative or broad-corpus quality.
- [Machine-readable record](validation.json): commands, environment, restart identity,
  review outcomes and the explicitly unrun Docker checks.

`baseline.json` fingerprints the exercised code, locked dependencies, source fixture
and reference artifact. These identify the pre-commit revision without a circular
self-referential commit hash. The containing Git commit provides the revision link.
PostgreSQL 18.6 and Python 3.12.3 were used. No paid model call was required.

## TDD record and review

The existing agreed ingestion, retrieval/provenance and API/CLI seams were reused:

1. A public provenance test first failed because `ask_phil.evidence` did not exist;
   implementing the immutable validated records made the fingerprint rule pass.
2. The PostgreSQL/API passage case first failed because `ask_phil.api` did not exist;
   implementing fixture publication and deterministic inspection made it pass.
3. The real-HTTP CLI case first failed with `No module named ask_phil.cli`; the CLI
   client then passed without database credentials.
4. The citation/restart case first returned HTTP 404 for the missing resolution
   endpoint; evidence-by-ID resolution made it pass after reimport and application recreation.

Regression cases then checked source scope, capture timezone, unsupported corroboration,
span integrity, absence, immutable conflicts, invalid requests and storage errors.
Single files and typechecking ran during development; the full suite ran once after
the code review. No internal collaborators or PostgreSQL behavior were mocked.

The code-review skill ran Standards and Spec as independent parallel agents. There
was no existing Git commit, so the fixed comparison was the empty tree
`4b825dc642cb6eb9a060e54bf8d69288fbee4904`; a new-file diff covered the implementation.
Standards reported zero findings. Spec reported no implementation defects or scope
creep, and retained the unverified Docker criterion. The preexisting project design
documents were context, not newly implemented product behavior.

## Remaining acceptance work

Once Docker Engine and Compose v2 are available, run the documented fresh startup,
CLI answerable/absent cases, container test service and database/API restart from
the repository README. Record image IDs, commands and outcomes here. A native run
does not substitute for that check. Fix any container-specific failures before
closing #2 or declaring its dependents unblocked.

The complete product remains future work: generative text RAG, the other routes,
corpus expansion, conversational state, MLflow/Prefect and online feedback evaluation
are not claimed by this deterministic first slice.
