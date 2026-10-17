# Issue #6 — refresh and recover a captured snapshot

The maintainer can run a reviewed source refresh through real Prefect, inspect
its outcomes, publish a complete source/text-index pair, and recover the previous
compatible pair. New answers and current inspection pin one publication before
retrieval. Old snapshots, source captures, evidence locators and saved answer
receipts remain readable after refresh and recovery.

## Manual workflow

Use the configured development PostgreSQL/pgvector database and model settings.
`DATABASE_URL` is required only for maintainer commands; reader commands use the
running HTTP API. `ASK_PHIL_MODELS` selects the model JSON and
`ASK_PHIL_OLLAMA_URL` selects the local embedding server, as in the existing demo.
Refresh verifies the configured embedding digest. It needs neither an installed
answer model nor answer-provider credentials and makes no answer-model calls.

```sh
uv run ask-phil refresh-sources data/sources/real-sources-v1.json.gz
uv run ask-phil publication
uv run ask-phil refresh-runs
uv run ask-phil refresh-runs RUN_UUID
uv run ask-phil refresh-runs RUN_UUID --captures
uv run ask-phil inspect 'signet ring'
uv run ask-phil publication --previous
uv run ask-phil rollback-snapshot
```

Replace `RUN_UUID` with the ID printed by refresh. An omitted `--snapshot` on
`inspect` or `ask` selects the current publication. Supplying it retains the
explicit-snapshot workflow, including the seed. `ask` invokes the configured
answer model and its existing provider/spending policy; the lifecycle acceptance
checks use controlled external-model responses instead.

For a new live capture, review the capture plan and its expected revision/scope
policy first, then run:

```sh
uv run ask-phil refresh-sources data/sources/real-sources-plan-v1.json --live
```

An unexpected Wikipedia revision needs a new explicit scope review. Capture or
validation failure preserves the active publication. Successful captures before
a later HTTP failure remain inspectable under the failed run. Fix the input or
provider and rerun the same command; it is not necessary to clear stored state.

Recovery reads and validates retained source and index artifacts without calling
the model server. Keep the prior embedding identity/dimensions in configuration;
an incompatible configuration fails recovery without changing the active pair.
Recovery withdraws the newer publication for new answers, while its evidence and
previously served responses remain available for explanation. A withdrawn input
cannot be silently republished: review corrected input for a new identity.

The API supplies read-only `/v1/publication`, `/v1/publication/previous`,
`/v1/refresh-runs`, `/v1/refresh-runs/{id}`, and
`/v1/refresh-runs/{id}/captures` inspection paths. Refresh/recovery remain explicit
maintainer CLI operations; there is no public upload or refresh endpoint.
Use the original snapshot-specific source/evidence routes for historical reads.

Rebuild the application/test images after this dependency/code change. Existing
already-running application containers do not acquire new code automatically.
The local Prefect flow creates or uses the configured Prefect backend. Its
parameters exclude database URLs and full capture bodies; result persistence is
disabled. The PostgreSQL journal is the durable maintainer inspection record.

## Publication and compatibility contract

`source-text-publication-v1` records the canonical input identity, immutable
snapshot fingerprint, source hashes/revisions/attribution, embedding identity and
dimensions, passage count, and hash of the exact retained vector artifacts.
Checks ensure each index entry resolves to its expected passage and has a usable
vector. A complete candidate is retained before one PostgreSQL transaction
activates it and records the terminal refresh outcome.

The input identity includes the reviewed catalogue, policies, source URLs and
capture hashes. Capture-check timestamps are excluded; identical bytes checked
later reuse the same logical snapshot/index and report the new check time on the
run. A changed policy/catalogue changes the identity even with unchanged bytes.
Import reports expose duplicate records separately from source outcomes. Reruns
of the already-active input reuse the saved index without advancing generation.
A reviewed source revert reactivates its retained, non-withdrawn compatible pair
and advances generation without duplicating artifacts.

The active pointer contains a monotonic generation. Future answer reuse must
match **both** `compatibility_id` and the current generation, using
`PublicationStore.is_current` or an equivalent atomic eligibility check. Refresh
and rollback advance that generation, preventing old cache entries from becoming
eligible merely because the same compatible artifacts are active again. This
ticket establishes eligibility metadata; #25 owns end-to-end cache behavior.

One PostgreSQL session advisory lock serializes refresh and rollback. A competing
maintainer fails as busy. Closing or killing its owner releases the lock. The next
writer marks unfinished journal entries interrupted and a retry removes orphan
vectors before rebuilding a complete candidate. A retained candidate is not an
answerable publication until activation succeeds.

Graph work must extend this contract with a **new immutable manifest version**:
include claim/projection/schema identities and graph artifact hashes, prepare and
validate every required artifact against the same source snapshot, then activate
or recover the entire compatible pair/set in one transaction. Keep source-text
v1 manifests unchanged. A reader must reject missing or incompatible required
graph artifacts rather than mix a current graph with older text. #15 supplies the
graph projection lifecycle; this ticket implements the source/text portion.

## Acceptance scope

[The pre-implementation plan](PLAN.md) fixes the baseline, reviewed lifecycle
counterexamples and agreed public seams. The fixtures are authored development
examples using official source formats; their blue/red workshop content is
synthetic and makes no EastEnders canon or model-quality claim. Tests use real
Prefect, PostgreSQL/pgvector, application interfaces and HTTP, with controlled
substitutes at external source/model boundaries. The interruption case kills a
real worker process while a later embedding is blocked.

Weekly scheduling and deployed monitoring remain the recorded deployment trigger
in AD-10.3. Full-roster ingestion, semantic corrections/graph projection, fusion
and caching retain their existing tickets. No paid answer-model call is required
for this ticket's acceptance.

To reproduce the recorded frozen-source lifecycle, point `DATABASE_URL` at an
empty disposable PostgreSQL/pgvector database and choose a new output path:

```sh
uv run python scripts/record_refresh_acceptance.py --output artifacts/refresh-acceptance.json
```

The recorder refuses an existing output or publication history. It publishes all
138 passages from the frozen eight-source sample, skips an unchanged rerun,
publishes a deliberate review-policy change, then recovers the original pair.
[Final lifecycle evidence](lifecycle.json) records four completed Prefect flows,
the manifests, generations 1 → 2 → 3, and successful HTTP reads of both retained
versions. Exact application/input/dependency hashes bind the record to its code.
[The earlier lifecycle capture](lifecycle-before-review.json) is retained as
pre-review development history and is superseded by the final record.
[A second capture](lifecycle-before-storage-fix.json) precedes restoration of the
existing reader API's empty-database 503 contract; it too is superseded.

## Acceptance failures and repairs

The first full Docker run is preserved in [its JUnit result](software-tests-first.xml).
It exposed the empty-database 404 regression; bootstrap handling now belongs only
to refresh and the reader API again returns storage-unavailable 503. Targeted
empty-database and new-database refresh checks passed after the fix. Later in that
run the disposable database exited with code 139, causing additional storage
failures. [The Docker event](infrastructure-first.json) records the observation;
its root cause is unknown. The final run uses the same pinned database image,
retains the database container for diagnostics, and allocates 256 MiB shared memory.

The non-root test image also exposed an unwritable default Prefect home.
`PREFECT_HOME=/app/artifacts/prefect` now uses the existing owned artifacts
directory. The [independent review](review.md) includes the final bootstrap and
container configuration changes. Earlier failing interruption, CLI and source
reversion cases and their repairs are recorded in [validation](validation.json).

## Final software result

On 17 October 2026 the rebuilt non-root Docker test image passed **131 tests**
with zero failures, errors or skips in 369.11 seconds. [Final JUnit](software-tests.xml)
and [validation identities](validation.json) record the exact image, application,
dependencies, test inputs and pinned PostgreSQL/pgvector image. The image's
application fingerprint matches the final lifecycle capture. Ruff and strict
mypy (37 files) pass; independent Standards and Spec reviews have zero remaining
findings. The staged secret scan passes. Source/document whitespace checks pass;
raw JUnit captures retain their original traceback whitespace.

The only final warning is the upstream Starlette/httpx test-client deprecation.
The earlier Prefect home warning is resolved. These software results establish
the source/text lifecycle and existing contract regressions; constant embeddings
and controlled external responses do not measure retrieval or answer quality.

## Publication

[Implementation 4080121](https://github.com/tomh1988-8/rag_demo/commit/408012156c55d040bc69a22bff034f87dd9a5dbd)
was published through the authorised GitHub connector. Its fetched tree exactly
matches local acceptance commit `ac3c5fd`; issue #6 was then closed as completed
with all eight criteria checked and read back. [The receipt](publication.json)
records this verification. The handoff and receipt follow in a documentation
commit. No later ticket was started.
