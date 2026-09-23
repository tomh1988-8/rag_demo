# 05: Refresh and recover a captured snapshot

Status: approved and published as [GitHub #6](https://github.com/tomh1988-8/rag_demo/issues/6), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S05, S31, S42, S55, S58, S63, S64, S65, S69, S73, S74, S89. Checklist evidence owner for: AD-03.3.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S05, S31, S42, S55, S58, S63, S64, S65, S69, S73, S74, S89.

## What to build

A maintainer can refresh captured sources manually through Prefect, publish a usable version for evidence inspection and restore the prior usable snapshot. Record changed, skipped, duplicate, partial and failed imports. Establish the snapshot contract that later graph projections must join; this ticket verifies the source/text lifecycle.

## Acceptance criteria

- [ ] Give each published snapshot an identifiable source manifest and retrieval artifacts. Requests pin one published version so a concurrent refresh cannot mix evidence revisions within a response.
- [ ] Expose refresh success, changes and failures through a maintainer inspection path. Retry/rerun the same input without duplicate logical records or broken evidence links.
- [ ] Withhold publication of incomplete or unusable results, retaining the prior usable snapshot. Preserve earlier source revisions and explain which version an answer or baseline used.
- [ ] Demonstrate recovery to the previous compatible source/retrieval snapshot and a reproducible rerun; define how later graph projections join this publication/recovery contract.
- [ ] Use reviewed changed-source, repeated-run, partial-failure and interrupted-run cases before implementation. Integrate real Prefect/application/database boundaries with controlled sources, and verify resulting persisted state and usable API/CLI evidence rather than only scheduler success.
- [ ] Document manual refresh for the local demo. Weekly scheduling and deployed monitoring remain a recorded future trigger, not an unimplemented requirement claimed complete here.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-03.3, AD-09.2 | Versioned source/retrieval manifests and request records resolving to the same captured snapshot. |
| AD-06.2, AD-10.2 | Idempotence, interruption, failed-publication and successful recovery results through real storage/orchestration. |

Recheck when: Refresh/publication logic, source versions, retrieval indexes, storage compatibility or new graph projection lifecycle.

## Blocked by

- #5 — Import real sources with character identity and canon scope: Real source adapters and identity/provenance handling are needed to test changed and failed imports.

