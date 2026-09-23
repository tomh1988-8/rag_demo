# 17: Route and escalate according to evidence

Status: approved and published as [GitHub #18](https://github.com/tomh1988-8/rag_demo/issues/18), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S37, S43, S44, S45, S46, S47, S48, S49, S50, S51, S52, S53, S54, S55, S70, S80, S82, S83, S89, S93, S94, S96. Checklist evidence owner for: AD-02.2, AD-02.3, AD-05.4, AD-09.3.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S37, S43, S44, S45, S46, S47, S48, S49, S50, S51, S52, S53, S54, S55, S70, S80, S82, S83, S89, S93, S94, S96.

## What to build

Make ordinary conversation select among conventional, graph and investigative routes according to supported capability and obtained evidence. Keep explicit overrides visible for demonstration. Use measurements to justify where model discretion is useful and where explicit eligibility/limit rules are sufficient.

## Acceptance criteria

- [ ] Check graph eligibility against the four supported query families and actual available coverage. Ineligible questions cannot receive invented structured answers; use the supported route/fallback behavior.
- [ ] Check obtained evidence and escalate only within the shared request budget when additional work may improve support. A complex-looking question with sufficient text evidence does not require investigation.
- [ ] Expose executed routes, overrides, checks, fallbacks, escalations and stop reasons in the public response and actual trace. Overrides do not bypass authority or execution limits and are visibly distinguished from automatic choices.
- [ ] Use reviewed routing tasks with capability eligibility, answerability, expected outcomes and allowed alternatives. Recognise multiple successful routes; route-label agreement is not a substitute for supported task success.
- [ ] Run a controlled development-set comparison with always-text RAG on the same corpus and answer model. Try other eligible routes on a representative subset, compare outcome quality and latency, and include router/checker/retry/investigation overhead in serving cost. Keep held-out acceptance labels out of routing-policy tuning.
- [ ] Start from failing eligibility/escalation cases; unit-test public routing rules and integrate real route tools through the API. Include sufficient-text, unsupported-graph, evidence-gap, exhausted-budget and failure-recovery cases, then run budgeted live evaluations with versioned settings.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-02.2, AD-02.3, AD-05.4 | Recorded workflow/model responsibilities and actual eligible-route/fallback/escalation behavior. |
| AD-09.3, AD-08.3 | Paired baseline and eligible-route counterfactual results with full serving overhead, separate offline expense and explicit missing usage. |

Recheck when: Routing/eligibility/evidence policy, available capabilities, graph coverage, route models/prompts or pricing/budget assumptions.

## Blocked by

- #17 — Investigate with bounded text and graph tools: All three working routes and the bounded investigation contract must exist before comparing or selecting them automatically.
