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


## Implemented and measured — 5 November 2026

Published implementation/evidence: [06b5169](https://github.com/tomh1988-8/rag_demo/commit/06b51695e026dd0edb59ff2da2fd0ba6188b378b). [Evidence and limitations](https://github.com/tomh1988-8/rag_demo/blob/06b51695e026dd0edb59ff2da2fd0ba6188b378b/docs/implementation/issue-18/README.md), [validation](https://github.com/tomh1988-8/rag_demo/blob/06b51695e026dd0edb59ff2da2fd0ba6188b378b/docs/implementation/issue-18/validation.json), and [independent review](https://github.com/tomh1988-8/rag_demo/blob/06b51695e026dd0edb59ff2da2fd0ba6188b378b/docs/implementation/issue-18/review.md).

- 715 passing native software tests, ten passing Docker contracts, strict mypy across 183 files, Ruff/formatting for src/tests/scripts and Compose validation. Both review axes have zero remaining findings. All 301 frozen software inputs and 150 protected inputs verify; all 98 original data files remain unchanged.
- Conservative admitted-coverage rules select four graph query families. Actual text evidence controls at most one bounded investigation; supported partial answers and full stage expense survive failure. Explicit overrides and actual routing/check/fallback/stop records match original root outputs.
- 54 actual development responses: 44 on the 26-passage cohort and ten on the separate 147-passage ordered cohort. Legacy automatic baseline completes 7/7 tasks versus 6/7 for text; source-bound reviews retain four text completeness misses. Ordered baseline/fusion/automatic baseline complete 2/2 each; expansion and combined complete 1/2 each, retaining both expected-date losses. Baseline remains selected. Per-case changes, categories, uncertainty and full transport/stage expense are recorded; the two cohorts are not pooled.
- At 57 cumulative paid calls, the next optional ordered automatic-combined request cannot reserve its eight-call maximum under the original 64-call ceiling. Both optional responses are unexecuted and unscored; no limit is increased or reset. The required routed-versus-active-conventional comparison is retained across the other five paired ordered arms.
- Four interrupted ordered responses are checked against original PostgreSQL and MLflow records with explicitly labelled recovered readback and no repeated paid calls. The wrong ordered graph-eligibility label is versioned to reflect correctly held missing identities; original labels, source, failures and raw scores remain. All 44 legacy model messages, contexts and final outcomes reproduce through current code with recorded completions and zero paid inference.
- 57 paid calls report $0.137923 serving inference; conservative rounding advances the original ledger from $0.975588 to $1.113530, zero unsettled reservations. External indexing/offline review inference is $0; local infrastructure cost is unmeasured.

AD-02.2, AD-02.3, AD-05.4 and AD-09.3 pass within this scope, bringing the current register to 44 Pass / 7 Pending. Source annotations are agent development reviews, not human canon, held-out acceptance or release-threshold approval. The 4,000-byte comparison does not establish 1,200-byte default quality. Caching and full release remain #25/#21 obligations.
