# 14: Route questions and escalate on evidence gaps

Draft for breakdown review; not approved or published.

Spec story references: 44, 48, 49, 50, 51, 52, 53, 54, 82, 93, 94, 96.

## What to build

A viewer asks an ordinary question without choosing a retrieval technique. The application selects an eligible route, checks the obtained evidence, and escalates only within the configured limits when that may help. Demonstrators retain explicit overrides and can inspect the route actually executed.

## Acceptance criteria

- [ ] Select among the implemented text, graph, and bounded-investigation capabilities using their real eligibility and coverage; reject or qualify unsupported tool requests.
- [ ] Check evidence adequacy and return a supported answer, escalate, clarify, give a partial answer, or abstain as appropriate. Preserve all existing configured execution and API limits across selection, checking, retries, and investigation.
- [ ] Report actual routing, overrides, fallback/escalation, evidence, and measurements through API/CLI output and traces; do not generate a fictional explanation of unperformed work.
- [ ] Evaluate supported task success before cost/latency and recognise multiple valid routes. A complex-looking question with sufficient direct passage evidence need not invoke investigation.
- [ ] On a reviewed subset, execute other eligible routes with the same snapshot and answer-model settings; compare missed/unnecessary escalation and resulting quality with the always-text baseline.
- [ ] Measure selection/checking/retry overhead in serving totals, keep offline evaluation expenditure separate, and label unavailable usage honestly.
- [ ] Demonstrate a direct answer, a suitable graph answer, useful escalation, and an unsuccessful bounded attempt; add component and end-to-end regression cases for each outcome.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 13: Investigate with bounded text and graph tools

