## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S17, S18, S20, S21, S22, S24, S25, S27, S28, S29, S34, S38, S39, S49, S52, S68, S72, S73, S81, S86.

## What to build

Compose the established relationship and event capabilities into a typed, bounded connection query. A user can inspect an evidenced path between characters, including derived connections, without accepting arbitrary graph proximity as an explanation.

## Acceptance criteria

- [x] Define permitted edge/role combinations, direction and traversal bounds. Preserve biological versus social relationships and event participant roles throughout a composed path.
- [x] Return a supported explanation, path and evidence for every asserted step through the API and CLI, with an explicit graph override and actual snapshot/trace. Derived meanings must follow from the path rather than being invented by prose generation.
- [x] Exclude connections based only on shared themes, co-appearance, unchecked/held claims or links to performers. Prevent cycles or repeated nodes from causing unbounded work.
- [x] Support acceptable alternative evidenced paths where the reference permits them. No path in the bounded captured graph is reported as limited coverage, not proof that no connection exists in the programme.
- [x] Begin with reviewed direct, multi-step, alternative-path, misleading-role, no-path and cycle cases. Unit-test exposed path semantics and integrate real SQL-backed traversal, provenance and API/CLI outputs.
- [x] Evaluate graph result correctness, path/edge meanings, provenance and final derived-answer support separately. Verify all four agreed graph families through their public contracts without requiring one exact internal traversal sequence.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

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

## Implemented and validated

[Published implementation and evidence](https://github.com/tomh1988-8/rag_demo/commit/3716f9c351b6b513bf2e25997ac7a0e0ab9107f8).
[Contract and runtime evidence](https://github.com/tomh1988-8/rag_demo/blob/3716f9c351b6b513bf2e25997ac7a0e0ab9107f8/docs/implementation/issue-16/README.md),
[validation](https://github.com/tomh1988-8/rag_demo/blob/3716f9c351b6b513bf2e25997ac7a0e0ab9107f8/docs/implementation/issue-16/validation.json),
and [separate independent reviews](https://github.com/tomh1988-8/rag_demo/blob/3716f9c351b6b513bf2e25997ac7a0e0ab9107f8/docs/implementation/issue-16/review.md)
record the completed scoped capability.

The explicit graph route composes admitted family edges, directed social ties,
historical romantic assertions and shared incident roles within finite depth,
path and expansion bounds. Biological history cannot bypass family admission.
Every step retains its Claims and source evidence; API/CLI/session answers expose
the actual snapshot and trace. Alternative, cycle, false-role, text-only exclusion,
held-claim and qualified no-path cases are covered.

The single final native suite passes 514 tests with zero failures, errors or skips;
strict mypy across 116 files and Ruff/formatting pass. All 33 focused checks pass.
The Docker test image builds and its four-family SQL/API/CLI/session contract passes.
All 17 final public responses pass result, step-meaning and provenance checks,
with exact actual MLflow readback, citations, reset and saved-response restart.
Independent source review passes eleven factual responses and six assertion-free
outcomes; factual/citation support is not applicable to those six.
One P2 admission-bypass finding was repaired; both review axes have zero remaining findings.

These are exposed curated capability cases, with transport repetitions preserved
as repeats. Existing extraction and ordinary text-quality failures are unchanged.
No new live false-account coverage, held-out accuracy or independent canon
corroboration is claimed. Broader checked graph coverage and release gates remain
Pending; register counts stay 35 Pass and 16 Pending. No paid model calls were made.
The shared ledger remains $0.464981 with zero unsettled reservations; original
data, private inputs and user workspace changes are preserved.
