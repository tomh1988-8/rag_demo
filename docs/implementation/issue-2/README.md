# Issue #2 implementation evidence

23 September 2026. [Ticket #2](https://github.com/tomh1988-8/rag_demo/issues/2)
is implemented and validated natively and in a fresh Docker Compose environment.
**All seven acceptance criteria now have evidence.** The container startup, CLI,
test suite and actual database/API restart passed on 23 September 2026.
GitHub issue #2 is closed as completed; its checked criteria and completion evidence
were read back and verified.

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
- [Machine-readable record](validation.json): commands, environment, restart identity
  and review outcomes, including the completed Docker checks below.

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

## Docker acceptance

The user authorised Docker installation and issue closure. The Ubuntu 24.04 host
now runs Docker Engine 29.8.1 with Compose 5.5.1, installed from Docker's official
apt repository using [the saved installer](../../../scripts/install-docker-ubuntu.sh).
The daemon is enabled and running. The `tom` account belongs to the Docker group;
the existing agent session used `sg docker -c` because group membership is refreshed
at login. Application code and configuration are unchanged from commit `1748866`.

- `docker compose -p ask-phil-issue2-acceptance up --build --wait --wait-timeout 180`
  built the images and created a fresh project, network and PostgreSQL volume.
  The seed exited successfully and both services became healthy.
  [Final startup transcript](compose-startup-output.txt).
- The exact two reviewed questions ran through the container CLI and shared API.
  Both produced their expected evidence IDs. The citation endpoint was also checked
  through the published host port.
- `docker compose -p ask-phil-issue2-acceptance --profile test run --build --name ask-phil-issue2-suite test pytest -q -p no:cacheprovider --junitxml=/tmp/compose-tests.xml`
  passed **17 tests, with no failures or skips**. One upstream Starlette deprecation
  warning remains. [JUnit](compose-tests.xml), [build/test output](compose-test-output.txt).
- `docker compose -p ask-phil-issue2-acceptance restart db api` preserved both CLI
  responses and the resolved evidence record exactly. The seed container's state
  and completion timestamp were unchanged: this checked persistence without reloading.

[Compose acceptance record](compose-acceptance.json) contains actual before/after
responses, commands, image digests and code/configuration/reference fingerprints.
The runtime used Python 3.12.14, PostgreSQL 18.6 and non-root application UID 10001.
These records supplement the earlier native baseline; they do not overwrite it.

The initial review's outstanding Docker criterion is now satisfied. A continuation
review compares the installation/evidence changes against `1748866`; its results
are recorded in `validation.json`.
Standards: zero findings. Spec: zero findings and no remaining acceptance blocker.
The acceptance containers and network were removed afterward; the named data volume
was retained and the Docker daemon remains enabled.

The complete product remains future work: generative text RAG, the other routes,
corpus expansion, conversational state, MLflow/Prefect and online feedback evaluation
are not claimed by this deterministic first slice.
