## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S37, S43, S44, S45, S46, S47, S48, S49, S50, S51, S52, S53, S54, S55, S70, S80, S82, S83, S89, S93, S94, S96, S117, S120, S121.

## What to build

Make ordinary conversation select among conventional, graph and investigative routes according to supported capability and obtained evidence. Keep explicit overrides visible for demonstration. Use measurements to justify where model discretion is useful and where explicit eligibility/limit rules are sufficient.

## Acceptance criteria

- [x] Check graph eligibility against the four supported query families and actual available coverage. Ineligible questions cannot receive invented structured answers; use the supported route/fallback behavior.
- [x] Check obtained evidence and escalate only within the shared request budget when additional work may improve support. A complex-looking question with sufficient text evidence does not require investigation.
- [x] Expose executed routes, overrides, checks, fallbacks, escalations and stop reasons in the public response and actual trace. Overrides do not bypass authority or execution limits and are visibly distinguished from automatic choices.
- [x] Use reviewed routing tasks with capability eligibility, answerability, expected outcomes and allowed alternatives. Recognise multiple successful routes; route-label agreement is not a substitute for supported task success.
- [x] Run a controlled development-set comparison with always-text RAG on the same corpus and answer model. Try other eligible routes on a representative subset, compare outcome quality and latency, and include router/checker/retry/investigation overhead in serving cost. Keep held-out acceptance labels out of routing-policy tuning.
- [x] Start from failing eligibility/escalation cases; unit-test public routing rules and integrate real route tools through the API. Include sufficient-text, unsupported-graph, evidence-gap, exhausted-budget and failure-recovery cases, then run budgeted live evaluations with versioned settings.
- [x] Compare routing against the selected and versioned fused/context-expanded conventional-text policy as well as the preserved single-query baseline. Treat fusion/expansion as text-route stages, not agent tool steps; include their full overhead and keep answer caching disabled for route-quality comparisons.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-02.2, AD-02.3, AD-05.4 | Recorded workflow/model responsibilities and actual eligible-route/fallback/escalation behavior. |
| AD-09.3, AD-08.3 | Paired baseline and eligible-route counterfactual results with full serving overhead, separate offline expense and explicit missing usage. |

Recheck when: Routing/eligibility/evidence policy, available capabilities, graph coverage, route models/prompts or pricing/budget assumptions.

## Blocked by

- #17 — Investigate with bounded text and graph tools: All three working routes and the bounded investigation contract must exist before comparing or selecting them automatically.
- #24 — Answer with fused retrieval and wider source context: The final conventional-text policy must exist before judging routing against it.


## Completed after reopening — 5 November 2026

The initial closure was premature: two comparison runs promised by the frozen ordered protocol were unfinished and incorrectly described as optional. That completion declaration is superseded. Issue #18 was reopened; both missing automatic-routing-with-fusion-and-expansion runs are now executed, reviewed and published in [51f43ce](https://github.com/tomh1988-8/rag_demo/commit/51f43ce3622a868f9b277312da42bc1b0f8045da).

[Current evidence](https://github.com/tomh1988-8/rag_demo/blob/51f43ce3622a868f9b277312da42bc1b0f8045da/docs/implementation/issue-18/README.md), [comparison v2](https://github.com/tomh1988-8/rag_demo/blob/51f43ce3622a868f9b277312da42bc1b0f8045da/docs/implementation/issue-18/comparison-v2.json), [validation v2](https://github.com/tomh1988-8/rag_demo/blob/51f43ce3622a868f9b277312da42bc1b0f8045da/docs/implementation/issue-18/validation-v2.json) and [follow-up review](https://github.com/tomh1988-8/rag_demo/blob/51f43ce3622a868f9b277312da42bc1b0f8045da/docs/implementation/issue-18/review-v2.md).

- All six planned ordered arms have both observations: baseline, fusion, expansion, combined, automatic baseline and automatic combined. The full comparison has 56 actual responses, preserving all 54 previous records, seven unique exposed questions and five overlapping story groups. The legacy 26-passage and ordered 147-passage cohorts remain separate. Caching stays disabled.
- The two missing requests use five paid calls/$0.0243161. Parentage succeeds; the date answer stays partial after text search reaches the context limit and initial cited support is retained. Strict task success for that arm is 1/2. This is an executed quality failure, not unfinished measurement or an exhausted monetary allowance. Baseline remains selected.
- All 56 original root outputs/archives and original or explicitly labelled recovered CLI readbacks match. All twelve ordered responses share the same publication/index. Model, source, application, prompt, question, policy and per-request limits match the previous ordered arms. Versioned eligibility labels preserve the original reference error; no identity or source validator is weakened.
- Cumulative serving expense is 62 paid calls/$0.1622391 reported. The unchanged non-resetting $5 ledger advances to $1.137848, zero unsettled reservations. The original $0.75 ticket ceiling stays unchanged. The agent-set call allowance was explicitly revised from 64 to 73 for only these two requests, carrying all prior counts forward; actual cumulative use is 62. No earlier paid work is repeated. External indexing/offline-review inference costs $0; local infrastructure cost is unmeasured.
- All 301 previously tested software inputs remain byte-identical, so the successful 715 native tests and ten Docker contracts remain applicable. The archived recorder passes strict mypy, Ruff and formatting with the project roots (184 files). Independent Standards and Spec reviews have zero remaining findings. All 98 original data files and 150 protected inputs retain hashes.

The original closure, stop, damaged exports, wrong eligibility label and source-quality failures are preserved with explicit historical status. Four legacy text completeness misses and three ordered date losses remain regressions. AD-02.2, AD-02.3, AD-05.4 and AD-09.3 have complete scoped evidence; the register remains 44 Pass / 7 Pending. Agent source review is not human canon, held-out acceptance or full-release approval. Caching and complete-product acceptance remain #25/#21; no planned #18 comparison request remains unexecuted.
