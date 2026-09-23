# 04: Refresh the corpus without losing provenance

Draft for breakdown review; not approved or published.

Spec story references: 42, 55, 58, 63, 64, 65, 73, 74, 89.

## What to build

A maintainer can refresh captured sources manually, inspect the outcome, and query the published version without mixing incompatible revisions. A viewer sees when the sources were checked and the limits of known storyline coverage. This slice establishes refresh behavior for the working text route; later graph work must preserve the same snapshot contract.

## Acceptance criteria

- [ ] Run the ingestion/refresh workflow through Prefect, reporting what was checked, changed, excluded, failed, or published. Manual execution is the local scope; document the agreed weekly cadence for a later deployment without deploying a scheduler now.
- [ ] Publish a coherent usable text snapshot; failed, interrupted, or partial imports have explicit outcomes and do not silently replace a usable snapshot with incompatible fragments.
- [ ] Rerunning unchanged input does not create duplicate usable passages or evidence identities. Retain earlier captured evidence and allow a recorded evaluation or query to be reproduced against its recorded revision.
- [ ] Bind each answer to one snapshot throughout execution, including when a refresh happens concurrently. The response identifies the selected version.
- [ ] Display source-check time separately from any evidenced storyline coverage date. A recent fetch must not imply complete current knowledge.
- [ ] Demonstrate an initial import, unchanged rerun, changed source, and interrupted refresh through observable workflow results and API/CLI answers; add real-database recovery and provenance regression cases.
- [ ] Keep source and projection publication requirements explicit so graph projections can be rebuilt against the matching evidence when introduced; handling corrected graph claims belongs to the disputed-claim slice.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 03: Resolve characters and keep sources in scope

