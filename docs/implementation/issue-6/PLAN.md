# Issue #6 — refresh and recovery

Review baseline: `f4d2c6a808b2002d2ac66f19105a02d409f79006`.
Origin: GitHub #6 under the approved specification #1; #5 is complete.

Use the confirmed source ingestion/refresh, retrieval and conversation API/CLI
seams. No new service or test-seam approval is needed. Existing explicit seed
snapshot requests and saved responses must remain readable.

The maintainer workflow runs through real Prefect. It records its run and source
outcomes, retains an immutable candidate, prepares a complete pgvector index,
validates source/index artifacts, then atomically advances the active publication.
One PostgreSQL maintainer lock serializes refresh and rollback; its release after
a killed process permits a later run to mark unfinished work interrupted and retry.
Reads pin one publication before retrieval. Old evidence remains resolvable.

An immutable manifest identifies sources, snapshot and exact retrieval artifacts.
Its compatibility identity and the active generation are exposed for later cache
eligibility. Rollback withdraws the failed newer publication for new requests while
preserving its citations, and restores the prior compatible source/index pair.
Future graph artifacts must join the same manifest and atomic activation contract.

Reviewed cases before implementation (exposed development fixtures, not canon):

1. Authored official-format HTML changes a synthetic blue workshop to a red
   workshop in a new reviewed revision. New active inspection finds only red;
   the original snapshot still resolves blue with its original locator.
2. Exact input rerun, and a later check of unchanged raw content, reuse the same
   logical snapshot/index. Report unchanged sources and duplicate records without
   duplicating passages. A changed policy/catalogue is a different input identity.
3. A second source fails after a first capture succeeds; or a required record/
   section is missing. Record partial/failed work and retain the old publication.
4. An embedding response fails or the worker is killed during preparation. No
   incomplete candidate becomes active. A subsequent run records interruption,
   removes incomplete index artifacts on retry and publishes one usable version.
5. A request blocked at the external query-embedding boundary survives a concurrent
   publication: response, context, citations and manifest all use its initial pin.
6. Rollback restores the prior source/index pair and compatibility identity,
   advances the active generation, rejects the withdrawn version for new answers,
   and preserves prior served answers and citations. An incompatible model fails
   before answering.

Work vertically: failing public test, smallest implementation, focused checks.
Run strict typing regularly, full Docker suite once at the end, and independent
Standards/Spec reviews. Record source/code/config identities, failures and limits;
commit, publish through the authorised connector, verify its exact tree, then close.
No paid answer-model calls are needed. Weekly scheduling is a deployed-operation
trigger; full-roster coverage, graph projection, fusion and answer caching remain
their existing tickets.

Prefect references checked on 25 September 2026:
[flows](https://docs.prefect.io/v3/concepts/flows) and
[real orchestration test harness](https://docs.prefect.io/v3/how-to-guides/workflows/test-workflows).
The workflow has no credential or full-capture parameters/results in Prefect;
PostgreSQL retains the bounded maintainer outcome and source manifest.
