# 13: Explain life events, themes and unclassified facts

Status: approved and published as [GitHub #14](https://github.com/tomh1988-8/rag_demo/issues/14), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S23, S26, S27, S29, S30, S34, S38, S39, S58, S59, S60, S68, S72, S73, S77, S78, S79, S81, S86. Checklist evidence owner for: the extensions and rechecks below; primary ownership is recorded in the project register.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S23, S26, S27, S29, S30, S34, S38, S39, S58, S59, S60, S68, S72, S73, S77, S78, S79, S81, S86.

## What to build

Extend the working event-participant path to supported pregnancy and death events, and make the difference between an event type, a theme and an unclassified fact visible in answers. Retain useful scandals or unusual facts in text retrieval even where no checked graph category exists.

## Acceptance criteria

- [ ] Review representative pregnancy/death evidence and required participant roles before extending extraction or graph answers. Preserve supported timing and uncertainty without inferring unmentioned parentage or inventing dates.
- [ ] Keep topical themes, including domestic violence or the manosphere where supported, separate from event types. A theme shared by two characters or mere co-appearance does not create an asserted relationship or shared event.
- [ ] Retain evidenced miscellaneous or unclassified facts with an explicit classification gap; the text route can explain them while graph results disclose their narrower coverage.
- [ ] Return supported event participants and evidence through the API/CLI. Ineligible graph questions yield the documented limited outcome rather than invented classification; later automatic routing can use this capability contract.
- [ ] Add failing event/theme/unclassified examples, unit checks of exposed classification/role rules and real extraction/storage/query/API integrations. Include no-result and unsupported-date counterexamples.
- [ ] Extend extraction value/grounding metrics and end-to-end cases by event type and theme. A regression verifies that retaining unclassified text does not silently admit it as a graph edge.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| EXT-02, EXT-04, RAG-04 | Reviewed event/theme/classification cases with explicit text-versus-graph coverage and admission outcomes. |
| AD-06.3, RAG-03 | Public missing-category and unsupported-connection/date regressions. |

Recheck when: Classification system, event roles, thematic labels, source evidence or graph eligibility changes.

## Blocked by

- #13 — Explain crimes and criminal justice roles: The shared-event/participant query path must exist before extending it beyond crime and justice.

