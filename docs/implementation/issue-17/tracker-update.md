## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S15, S28, S35, S36, S37, S38, S39, S40, S41, S43, S44, S45, S46, S47, S49, S53, S55, S68, S70, S72, S73, S74, S79, S80, S81, S82, S83, S94, S96.

## What to build

A user or demonstrator can explicitly invoke bounded agentic RAG. The single investigator chooses among declared text and typed graph tools in one captured snapshot, gathers sufficient evidence where available and returns a supported response with its actual investigation record. It cannot browse the live web or create new authority by asking for it.

## Acceptance criteria

- [x] Version the investigator prompt/model and tool contracts. Validate tool arguments/results and permit only the declared read-only tools; no arbitrary SQL, shell, ingestion, source mutation or live-web tool is exposed.
- [x] Share one finite request budget across model calls, tool calls, checking, retries and context growth. Extend the established cancellation and failure handling to the full investigation; missing usage cannot silently remove the limit.
- [x] Pin text, claims and graph to one compatible snapshot and record retrieved results and assembled context. Assess multi-fact context sufficiency rather than stopping at the first relevant passage.
- [x] Return supported findings and clearly identify unresolved parts or stop reasons. The neutral appendix summarises actual tools/findings and paths/citations; it never invents an internal process or claims a tool ran when it did not.
- [x] Add reviewed multi-source, single-passage-sufficient, malformed-tool, repeated-call, insufficient-evidence, timeout/cancellation and budget-stop cases. Integrate the public API with real storage/tools and controlled external providers before budgeted live runs.
- [x] Evaluate tool eligibility/argument validity, recovery, stop behavior, task success and final support separately. Allow different valid strategies; do not grade exact internal call order. Compare representative development cases against the same-corpus/answer-model text baseline with complete serving cost and latency; preserve the held-out acceptance set for the frozen release comparison.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-05.2, AD-05.4, AD-07.1, AD-07.2, AD-07.4 | Actual investigation traces and public tool/authority/limit/recovery test results. |
| AD-08.1, AD-09.1, AD-09.3, RAG-02 | Context-sufficiency and final-answer evaluations with recorded tool findings and full investigation expenditure. |

Recheck when: Investigator prompt/model, tools, stop/retry policy, context assembly, budget accounting or snapshot handling.

## Blocked by

- #10 — Bound requests and enforce read-only execution: The programmatic authority, budget, retry and cancellation boundary must be verified before model-directed investigation.
- #16 — Trace evidenced connections between characters: The bounded, evidence-bearing text and full graph capabilities must be available to the investigator.

## Implementation and validation

Implemented in [000a866](https://github.com/tomh1988-8/rag_demo/commit/000a86681cf115dd1627c9eb87da015c5ca14e07); [implementation evidence](https://github.com/tomh1988-8/rag_demo/blob/000a86681cf115dd1627c9eb87da015c5ca14e07/docs/implementation/issue-17/README.md) and [criterion mapping](https://github.com/tomh1988-8/rag_demo/blob/000a86681cf115dd1627c9eb87da015c5ca14e07/docs/implementation/issue-17/acceptance-map.json).

- 550 passing tests, strict mypy across 125 files, Ruff/formatting and six Docker API/CLI/graph checks; native/container application fingerprints match.
- Both independent code-review axes have zero remaining findings after retaining and repairing the SQL-timeout receipt and oversized-stop failures.
- Three same-corpus/index/answer-model development pairs produce six actual API responses with exact root/tool/citation/recreation readback. Independent source review passes nine claims. Investigation covers 3/3 required facts; text covers 2/3 with honest partial and unsupported outcomes.
- Ten paid serving decisions report $0.0306264 inference charges. The shared non-resetting $5 ledger is $0.495612, with zero unsettled reservations. Offline source review/scoring makes no OpenRouter calls.

The actual live responses bind b599783; final software 13d38e0 repairs stop handling only, with unchanged prompt/model/tool contracts. Curated/exposed capability does not establish new extraction quality, independent canon corroboration or held-out release acceptance. Query drift, simpler-task overhead and the baseline context miss remain recorded. Routing, broader release and online checks remain Pending; checklist counts stay 35 Pass and 16 Pending. All original data, pre-existing workspace work and private inputs are preserved.

