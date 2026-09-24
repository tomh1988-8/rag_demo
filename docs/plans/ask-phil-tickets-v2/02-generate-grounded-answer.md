# 02: Generate a grounded Ask Phil answer

Status: completed and closed as [GitHub #3](https://github.com/tomh1988-8/rag_demo/issues/3), 24 September 2026. [Implementation and acceptance evidence](../../implementation/issue-3/README.md) includes 32 passing tests, actual local-model traces, corrected token accounting and restart checks.

Spec stories: S01, S02, S03, S05, S06, S38, S41, S42, S43, S44, S45, S46, S47, S54, S66, S67, S69, S70, S71, S72, S73, S74, S79, S80, S89, S94, S95, S98, S102, S115.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S01, S02, S03, S05, S06, S38, S41, S42, S43, S44, S45, S46, S47, S54, S66, S67, S69, S70, S71, S72, S73, S74, S79, S80, S89, S94, S95, S98, S102, S115.

## What to build

Extend the evidence path to a complete conventional RAG answer using Python, LlamaIndex and PostgreSQL/pgvector. The CLI uses FastAPI and shared application behavior. Add basic Phil phrasing while retaining supported facts and a neutral evidence appendix. Run the reviewed seed through an always-text-RAG baseline before graph or investigative features are introduced.

## Acceptance criteria

- [x] Select and record initial provider/model settings, prompts, context limits and compatible package versions. Configure conservative per-request limits and the provider/API spending control available at setup before paid calls; document what each limit can and cannot enforce.
- [x] Retrieve from the captured fixture using pgvector and generate a sourced answer from the assembled context. Keep answering within the captured snapshot and make source spans resolvable. Latest captured facts have no spoiler filter.
- [x] Return answer, citation excerpts, source snapshot, source-check versus demonstrated coverage information, executed text route, elapsed time and actual trace reference. Use Phil-style wording for the answer and neutral provenance/measurements.
- [x] Instrument actual retrieval, assembled context, model calls and available token usage in MLflow. Label estimated model cost; missing usage remains missing. Separate serving and offline evaluation expenditure and avoid invented per-answer confidence.
- [x] Use independently labelled relevant passages and required facts to measure retrieval coverage/ranking and context sufficiency separately. Define k, matching, denominators and sufficient evidence sets; do not claim corpus-wide quality from the small seed.
- [x] Add failing public cases, exposed citation/context-rule unit tests and real PostgreSQL/pgvector/API integration checks. Substitute only external services in routine tests, then run a separately budgeted live-provider check and baseline with fixed corpus/answer-model settings.
- [x] Assign each served outcome a stable client-visible response identifier resolving server-side to the original final persona answer, evidence/context, source snapshot, actual route and versioned model/prompt/application trace. Preserve that association for subsequent feedback without exposing arbitrary assessment-write authority; verify it through the API/CLI. Feedback submission is delivered by the separate feedback ticket.
- [x] Preserve this slice as a versioned single-query, uncached text-RAG baseline. Record retrieval and final context distinctly so the later fusion/context-expansion slice can compare against it without rewriting baseline results. Do not implement the later fusion or cache here.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-02.1, AD-05.1 | Versioned always-text-RAG baseline, model/prompt/context contracts and setup limits. |
| AD-06.2, RAG-02 | Real vector/database integration results plus independently labelled retrieval and context-sufficiency results. |
| AD-09.1, AD-09.3 | Actual MLflow traces, citation appendix, complete request measurements and missing-usage example. |

Recheck when: Answer model, prompt, embedding/retrieval configuration, context construction, citations, dependencies or provider usage contract changes.

## Blocked by

- #2 — Inspect captured source evidence locally: The reviewed evidence fixture, baseline and working CLI/API/database path must exist before adding a model.

## Implementation result — 24 September 2026

Completed single-query, uncached text RAG through the CLI/FastAPI, LlamaIndex and PostgreSQL/pgvector, with pinned local Gemma 4 E2B QAT/EmbeddingGemma models, resolvable citations, actual MLflow traces and private original-response lookup.

- 32 Docker tests passed; lint, formatting and strict type checking passed.
- Final local-model baseline answers the reviewed arrival case in first person and declines the unsupported parentage question. Retrieval/context labels are independent of the model output.
- Actual token accounting was corrected and regression-tested. Saved response, citation and trace remained available after PostgreSQL/API/MLflow restart. Complete CLI wall time was 30.384 seconds in the serving smoke check.
- Independent Standards and Spec reviews have zero remaining findings. Failed persona/accounting attempts and transient test/readiness failures are retained.
- Five initial text-slice checks gain scoped Pass evidence: 13 Pass, 38 Pending overall. Broader routing/online accounting remains Pending.

[Implementation evidence](https://github.com/tomh1988-8/rag_demo/blob/main/docs/implementation/issue-3/README.md), [validation](https://github.com/tomh1988-8/rag_demo/blob/main/docs/implementation/issue-3/validation.json), [separate review axes](https://github.com/tomh1988-8/rag_demo/blob/main/docs/implementation/issue-3/review.md).

The local model is a development/smoke convenience only, as the user requested. Move to a more capable model before broad-roster quality acceptance (#7), representative comparisons (#9), or substantive extraction (#11 onward), or sooner if its limits prevent useful progress. Record a new model baseline and conservative key/account/request controls before paid calls. No paid API calls occurred here. This one-passage exposed seed does not establish deployment readiness or general quality.
