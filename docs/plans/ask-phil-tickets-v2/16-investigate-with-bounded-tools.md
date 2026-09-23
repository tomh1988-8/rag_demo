# 16: Investigate with bounded text and graph tools

Status: approved and published as [GitHub #17](https://github.com/tomh1988-8/rag_demo/issues/17), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S15, S28, S35, S36, S37, S38, S39, S40, S41, S43, S44, S45, S46, S47, S49, S53, S55, S68, S70, S72, S73, S74, S79, S80, S81, S82, S83, S94, S96. Checklist evidence owner for: the extensions and rechecks below; primary ownership is recorded in the project register.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S15, S28, S35, S36, S37, S38, S39, S40, S41, S43, S44, S45, S46, S47, S49, S53, S55, S68, S70, S72, S73, S74, S79, S80, S81, S82, S83, S94, S96.

## What to build

A user or demonstrator can explicitly invoke bounded agentic RAG. The single investigator chooses among declared text and typed graph tools in one captured snapshot, gathers sufficient evidence where available and returns a supported response with its actual investigation record. It cannot browse the live web or create new authority by asking for it.

## Acceptance criteria

- [ ] Version the investigator prompt/model and tool contracts. Validate tool arguments/results and permit only the declared read-only tools; no arbitrary SQL, shell, ingestion, source mutation or live-web tool is exposed.
- [ ] Share one finite request budget across model calls, tool calls, checking, retries and context growth. Extend the established cancellation and failure handling to the full investigation; missing usage cannot silently remove the limit.
- [ ] Pin text, claims and graph to one compatible snapshot and record retrieved results and assembled context. Assess multi-fact context sufficiency rather than stopping at the first relevant passage.
- [ ] Return supported findings and clearly identify unresolved parts or stop reasons. The neutral appendix summarises actual tools/findings and paths/citations; it never invents an internal process or claims a tool ran when it did not.
- [ ] Add reviewed multi-source, single-passage-sufficient, malformed-tool, repeated-call, insufficient-evidence, timeout/cancellation and budget-stop cases. Integrate the public API with real storage/tools and controlled external providers before budgeted live runs.
- [ ] Evaluate tool eligibility/argument validity, recovery, stop behavior, task success and final support separately. Allow different valid strategies; do not grade exact internal call order. Compare representative development cases against the same-corpus/answer-model text baseline with complete serving cost and latency; preserve the held-out acceptance set for the frozen release comparison.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

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
