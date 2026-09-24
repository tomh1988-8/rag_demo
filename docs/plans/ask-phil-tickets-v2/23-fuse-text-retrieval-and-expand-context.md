# 23: Answer with fused retrieval and wider source context

Status: published as [GitHub #24](https://github.com/tomh1988-8/rag_demo/issues/24) for the user-requested fusion/cache amendment. Implementation has not started; runtime evidence is Pending.

Spec stories: S117, S118, S119, S120, S121.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S117, S118, S119, S120, S121.

## What to build

A user receives a conventional text-RAG answer based on multiple faithful retrieval queries and relevant surrounding source context, with checkable citations and a measured comparison to the original text baseline. This fixed pipeline stays inside the captured snapshot and is neither graph traversal nor an autonomous investigation loop.

## Acceptance criteria

- [ ] Extend reviewed real-source cases with questions needing several passages or surrounding qualifications. Label sufficient spans and query fidelity independently; include wrong-character/date/negation variants and cases where expansion must not add out-of-scope text.
- [ ] Retain the original/resolved question, generate a bounded number of distinct faithful variants, retrieve ranked candidates per query and merge with reciprocal rank fusion. Record rank convention, fusion constant, candidate limits and deterministic ties; deduplicate by evidence identity and prevent repeated variants from overweighting evidence. Start with multi-query vector retrieval; a lexical retriever is optional.
- [ ] Expand selected hits to bounded neighbouring sentences in the same captured revision and allowed canon scope. Preserve original and added span locators, merge overlapping windows and apply a total context budget. Never substitute model-generated background or live-web facts. Keep parent-passage/auto-merging expansion optional unless a measured input need justifies it.
- [ ] Generate against the original/resolved question and actual final context. Through CLI/API, expose supporting spans and an honest text-route appendix; traces retain variants, ranked lists, fused candidates, added context, truncation, fallback and actual model/call/token expense. Expanded facts cite their supporting expanded spans.
- [ ] Enforce request-wide fan-out, token, latency and spending bounds. Invalid, drifting or failed variant generation uses visible bounded original-query fallback; empty evidence and exhausted limits preserve the existing partial/abstain behavior.
- [ ] Start with failing public fusion/context cases and independent expected rank examples. Integrate real PostgreSQL/pgvector and citation resolution through API/CLI; cover duplicates, overlap, incorrect revision/scope, missing qualifiers, truncation, failure and budget limits. Substitute only external model/source boundaries in routine tests.
- [ ] Run budgeted baseline, fusion-only, expansion-only and combined comparisons with fixed corpus/questions/answer model and comparable final-context budgets, with caching disabled. Report candidate and fused-ranking quality, context sufficiency after truncation, final answer quality and total latency/cost separately. Select and version the conventional-text policy from measured development results; keep holdout separate and report negative results honestly.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

Use the existing public retrieval, conversation and evaluation seams. The implementer records results; the project owner accepts scope and measured release thresholds. New requirements remain Pending until executed and evidenced.

| Checks | Evidence required for completion |
| --- | --- |
| RAG-02, RAG-03, AD-05.1, AD-06.1, AD-06.2 | Reviewed query/context cases, independent rank expectations and real CLI/API/storage regressions. |
| AD-02.1, AD-08.3, AD-09.1, AD-09.3 | Four versioned text ablations, stage-level traces and complete serving measurements. |

Recheck when: Source/index snapshot, public behavior, retrieval/context policy, model/prompts, cache identity or eligibility, evaluation dataset/splits, limits or supported environment changes.

## Blocked by

- #4 — Handle incomplete evidence and false premises: The working text baseline from #3 and supported partial/clarify/abstain behavior must exist before fusion extends them.
- #5 — Import real sources with character identity and canon scope: Expansion needs ordered, revision-linked and scope-filtered source passages.
