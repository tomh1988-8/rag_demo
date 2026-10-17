# Issue #7 implementation contract

Baseline: `2d559ad6bf70c1520745bb876cfc0b5de115a258` on `main`.
Specification: GitHub #7 and parent #1; #3 and #6 are completed prerequisites.

Use the six already confirmed seams in `docs/design/testing-and-evaluation.md`.
TDD slices exercise source capture/resumption and source coverage through ingestion,
HTTP and CLI; deterministic external transports remain separate from live quality.
The review compares the completed implementation with this baseline.

Deliver one generic import of the agreed 20 Wikipedia character profiles, with
revision-specific scope reviews, retained payloads and evidenced supporting
identities. Preserve the prominence-based roster and explicit partial-history
limitations. Extend source inspection with per-character retention/gap inventories
and exact duplicate paragraph groups. Semantic cross-page consistency review is
recorded evidence, not an automatic claim based on matching identifiers.

Add opt-in durable capture checkpoints so a failed bounded batch can resume without
discarding successful captures. Validate reused captures against the exact plan,
retain the existing source/count/byte limits and refuse an existing final output.
Refresh/index/publication continue through the existing generic pipeline.

Before model calls, freeze source-based questions, sufficient passage sets and
story-event groups. Keep all initial cases in development; no held-out comparison
or calibration is claimed. Demonstrate one sourced case per core character plus
cross-profile and missing-evidence cases through HTTP and CLI. Record actual
retrieval/context scores and separately review factual/citation/outcome behavior;
retain unsuccessful attempts and gaps.

Use the existing Sol profile and shared non-resetting $5 trial ledger. Initial
live budget: at most 30 answer calls, no automatic retries, at most $1 additional
inference credits for this ticket. Stop before that local slice cap; the existing
provider and persistent reservation controls remain authoritative. Embeddings use
the already pinned local embedding model. No graph, fusion, cache or follow-up
features are added. Broad calibrated acceptance remains #9.

Run strict mypy and focused tests during implementation, the full suite at the end,
then independent Standards and Spec reviews under the code-review skill. Fix all
material findings, scan staged files for secrets, commit only this ticket's files,
and publish/verify the exact tree before closing #7.
