# 02: Generate a grounded Ask Phil answer

Status: published as [GitHub #3](https://github.com/tomh1988-8/rag_demo/issues/3); feedback/online-evaluation amendment authorised by the user on 23 September 2026. Remote body and ready-for-agent label verified. Implementation has not started.

Spec stories: S01, S02, S03, S05, S06, S38, S41, S42, S43, S44, S45, S46, S47, S54, S66, S67, S69, S70, S71, S72, S73, S74, S79, S80, S89, S94, S95, S98, S102, S115.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S01, S02, S03, S05, S06, S38, S41, S42, S43, S44, S45, S46, S47, S54, S66, S67, S69, S70, S71, S72, S73, S74, S79, S80, S89, S94, S95, S98, S102, S115.

## What to build

Extend the evidence path to a complete conventional RAG answer using Python, LlamaIndex and PostgreSQL/pgvector. The CLI uses FastAPI and shared application behavior. Add basic Phil phrasing while retaining supported facts and a neutral evidence appendix. Run the reviewed seed through an always-text-RAG baseline before graph or investigative features are introduced.

## Acceptance criteria

- [ ] Select and record initial provider/model settings, prompts, context limits and compatible package versions. Configure conservative per-request limits and the provider/API spending control available at setup before paid calls; document what each limit can and cannot enforce.
- [ ] Retrieve from the captured fixture using pgvector and generate a sourced answer from the assembled context. Keep answering within the captured snapshot and make source spans resolvable. Latest captured facts have no spoiler filter.
- [ ] Return answer, citation excerpts, source snapshot, source-check versus demonstrated coverage information, executed text route, elapsed time and actual trace reference. Use Phil-style wording for the answer and neutral provenance/measurements.
- [ ] Instrument actual retrieval, assembled context, model calls and available token usage in MLflow. Label estimated model cost; missing usage remains missing. Separate serving and offline evaluation expenditure and avoid invented per-answer confidence.
- [ ] Use independently labelled relevant passages and required facts to measure retrieval coverage/ranking and context sufficiency separately. Define k, matching, denominators and sufficient evidence sets; do not claim corpus-wide quality from the small seed.
- [ ] Add failing public cases, exposed citation/context-rule unit tests and real PostgreSQL/pgvector/API integration checks. Substitute only external services in routine tests, then run a separately budgeted live-provider check and baseline with fixed corpus/answer-model settings.
- [ ] Assign each served outcome a stable client-visible response identifier resolving server-side to the original final persona answer, evidence/context, source snapshot, actual route and versioned model/prompt/application trace. Preserve that association for subsequent feedback without exposing arbitrary assessment-write authority; verify it through the API/CLI. Feedback submission is delivered by the separate feedback ticket.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

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

