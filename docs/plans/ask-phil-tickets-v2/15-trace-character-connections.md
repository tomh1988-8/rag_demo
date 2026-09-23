# 15: Trace evidenced connections between characters

Status: approved and published as [GitHub #16](https://github.com/tomh1988-8/rag_demo/issues/16), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S17, S18, S20, S21, S22, S24, S25, S27, S28, S29, S34, S38, S39, S49, S52, S68, S72, S73, S81, S86. Checklist evidence owner for: RAG-04.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S17, S18, S20, S21, S22, S24, S25, S27, S28, S29, S34, S38, S39, S49, S52, S68, S72, S73, S81, S86.

## What to build

Compose the established relationship and event capabilities into a typed, bounded connection query. A user can inspect an evidenced path between characters, including derived connections, without accepting arbitrary graph proximity as an explanation.

## Acceptance criteria

- [ ] Define permitted edge/role combinations, direction and traversal bounds. Preserve biological versus social relationships and event participant roles throughout a composed path.
- [ ] Return a supported explanation, path and evidence for every asserted step through the API and CLI, with an explicit graph override and actual snapshot/trace. Derived meanings must follow from the path rather than being invented by prose generation.
- [ ] Exclude connections based only on shared themes, co-appearance, unchecked/held claims or links to performers. Prevent cycles or repeated nodes from causing unbounded work.
- [ ] Support acceptable alternative evidenced paths where the reference permits them. No path in the bounded captured graph is reported as limited coverage, not proof that no connection exists in the programme.
- [ ] Begin with reviewed direct, multi-step, alternative-path, misleading-role, no-path and cycle cases. Unit-test exposed path semantics and integrate real SQL-backed traversal, provenance and API/CLI outputs.
- [ ] Evaluate graph result correctness, path/edge meanings, provenance and final derived-answer support separately. Verify all four agreed graph families through their public contracts without requiring one exact internal traversal sequence.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| RAG-04, AD-05.2 | Bounded connection contract and reviewed path/result/role/provenance checks across the four graph families. |
| AD-06.3, AD-08.1 | Alternative-path, cycle, false-connection and no-result regressions plus separate final-answer results. |

Recheck when: Allowed edges/roles, direction or traversal bounds, query implementation, provenance rules or source/claim changes.

## Blocked by

- #12 — Explain family and romantic histories: Connection paths need correctly distinguished family and romantic relationships.
- #14 — Explain life events, themes and unclassified facts: Connection paths also need the supported shared-event/participant capabilities and theme exclusions.

