## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S23, S26, S27, S29, S30, S34, S38, S39, S58, S59, S60, S68, S72, S73, S77, S78, S79, S81, S86.

## What to build

Extend the working event-participant path to supported pregnancy and death events, and make the difference between an event type, a theme and an unclassified fact visible in answers. Retain useful scandals or unusual facts in text retrieval even where no checked graph category exists.

## Acceptance criteria

- [x] Review representative pregnancy/death evidence and required participant roles before extending extraction or graph answers. Preserve supported timing and uncertainty without inferring unmentioned parentage or inventing dates.
- [x] Keep topical themes, including domestic violence or the manosphere where supported, separate from event types. A theme shared by two characters or mere co-appearance does not create an asserted relationship or shared event.
- [x] Retain evidenced miscellaneous or unclassified facts with an explicit classification gap; the text route can explain them while graph results disclose their narrower coverage.
- [x] Return supported event participants and evidence through the API/CLI. Ineligible graph questions yield the documented limited outcome rather than invented classification; later automatic routing can use this capability contract.
- [x] Add failing event/theme/unclassified examples, unit checks of exposed classification/role rules and real extraction/storage/query/API integrations. Include no-result and unsupported-date counterexamples.
- [x] Extend extraction value/grounding metrics and end-to-end cases by event type and theme. A regression verifies that retaining unclassified text does not silently admit it as a graph edge.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| EXT-02, EXT-04, RAG-04 | Reviewed event/theme/classification cases with explicit text-versus-graph coverage and admission outcomes. |
| AD-06.3, RAG-03 | Public missing-category and unsupported-connection/date regressions. |

Recheck when: Classification system, event roles, thematic labels, source evidence or graph eligibility changes.

## Blocked by

- #13 — Explain crimes and criminal justice roles: The shared-event/participant query path must exist before extending it beyond crime and justice.

## Completion evidence — 27 October 2026

Implemented and published in [1df0a70](https://github.com/tomh1988-8/rag_demo/commit/1df0a70bb95eafe0522482a7c451fbe875f8ff57); a fresh native fetch confirms the remote revision and tree exactly match the intended local commit. [Implementation and evidence](https://github.com/tomh1988-8/rag_demo/blob/1df0a70bb95eafe0522482a7c451fbe875f8ff57/docs/implementation/issue-14/README.md) describe the public contract and its scope.

Pregnancy/death queries preserve supported roles, dates and uncertainty. Themes and unclassified facts remain source-bound text annotations, with explicit classification qualifications and no graph adjacency. The API and CLI expose typed life-event queries and limited outcomes for ineligible theme/unclassified queries. Existing crime-history and audit serialization contracts remain compatible.

[Final graph capture](https://github.com/tomh1988-8/rag_demo/blob/1df0a70bb95eafe0522482a7c451fbe875f8ff57/docs/implementation/issue-14/runtime-final.json) records 30 actual API/CLI/session outcomes, with exact MLflow root/tool readback, citation resolution, restart and reset checks. All five curated event meanings are supported; raw missing results and held candidates remain visible. [Live text review](https://github.com/tomh1988-8/rag_demo/blob/1df0a70bb95eafe0522482a7c451fbe875f8ff57/docs/implementation/issue-14/text-quality.json) passes two of three cases. The unsupported-manosphere case retains an incorrect answerability status and missing explicit coverage caveat; its incidental facts/citations are supported and it invents no theme or connection.

The frozen extraction pilot retains 4/5 exact event values, 3/5 resolvable event locators and 0/5 conservative full-span grounding; three shorter event quotes are source-supported and two malformed locators remain held. Context values match 1/2, with 2/2 resolvable locators and 1/2 full-span grounding. The date mismatch is literal wording, not an invented date. [Regressions](https://github.com/tomh1988-8/rag_demo/blob/1df0a70bb95eafe0522482a7c451fbe875f8ff57/docs/implementation/issue-14/regressions.json) preserve every failure separately from curated capability.

[Validation](https://github.com/tomh1988-8/rag_demo/blob/1df0a70bb95eafe0522482a7c451fbe875f8ff57/docs/implementation/issue-14/validation.json) records **414 passing tests**, zero failures/errors/skips, strict mypy across 99 files, Ruff lint/formatting and **zero implementation findings** from both independent Standards and Spec reviews. The final trace audit passed. All 34 original data files and 51 pre-existing workspace files remain unchanged. Software checks and live captures share the tested application fingerprint at `ef77ce8`.

One extraction and three serving calls cost **$0.0476445** in reported inference charges; the shared non-resetting $5 ledger is **$0.464981**, zero unsettled reservations. Scoped evidence leaves wider RAG-04, EXT-04 and release requirements Pending. These exposed development results are not a held-out, human-adjudicated or independent canon pass.
