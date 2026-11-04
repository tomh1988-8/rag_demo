## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S117, S118, S119, S120, S121.

## What to build

A user receives a conventional text-RAG answer based on multiple faithful retrieval queries and relevant surrounding source context, with checkable citations and a measured comparison to the original text baseline. This fixed pipeline stays inside the captured snapshot and is neither graph traversal nor an autonomous investigation loop.

## Acceptance criteria

- [x] Extend reviewed real-source cases with questions needing several passages or surrounding qualifications. Label sufficient spans and query fidelity independently; include wrong-character/date/negation variants and cases where expansion must not add out-of-scope text.
- [x] Retain the original/resolved question, generate a bounded number of distinct faithful variants, retrieve ranked candidates per query and merge with reciprocal rank fusion. Record rank convention, fusion constant, candidate limits and deterministic ties; deduplicate by evidence identity and prevent repeated variants from overweighting evidence. Start with multi-query vector retrieval; a lexical retriever is optional.
- [x] Expand selected hits to bounded neighbouring sentences in the same captured revision and allowed canon scope. Preserve original and added span locators, merge overlapping windows and apply a total context budget. Never substitute model-generated background or live-web facts. Keep parent-passage/auto-merging expansion optional unless a measured input need justifies it.
- [x] Generate against the original/resolved question and actual final context. Through CLI/API, expose supporting spans and an honest text-route appendix; traces retain variants, ranked lists, fused candidates, added context, truncation, fallback and actual model/call/token expense. Expanded facts cite their supporting expanded spans.
- [x] Enforce request-wide fan-out, token, latency and spending bounds. Invalid, drifting or failed variant generation uses visible bounded original-query fallback; empty evidence and exhausted limits preserve the existing partial/abstain behavior.
- [x] Start with failing public fusion/context cases and independent expected rank examples. Integrate real PostgreSQL/pgvector and citation resolution through API/CLI; cover duplicates, overlap, incorrect revision/scope, missing qualifiers, truncation, failure and budget limits. Substitute only external model/source boundaries in routine tests.
- [x] Run budgeted baseline, fusion-only, expansion-only and combined comparisons with fixed corpus/questions/answer model and comparable final-context budgets, with caching disabled. Report candidate and fused-ranking quality, context sufficiency after truncation, final answer quality and total latency/cost separately. Select and version the conventional-text policy from measured development results; keep holdout separate and report negative results honestly.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

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

## Completion evidence

Implemented and verified at [a737c7f](https://github.com/tomh1988-8/rag_demo/commit/a737c7fa6bcb0a30b785c04acb70be339d35e337). The native fast-forward publication was read back with the exact commit and tree before closure.

- [Evidence and operating instructions](https://github.com/tomh1988-8/rag_demo/blob/a737c7fa6bcb0a30b785c04acb70be339d35e337/docs/implementation/issue-24/README.md), [acceptance map](https://github.com/tomh1988-8/rag_demo/blob/a737c7fa6bcb0a30b785c04acb70be339d35e337/docs/implementation/issue-24/acceptance-map.json) and [project register](https://github.com/tomh1988-8/rag_demo/blob/a737c7fa6bcb0a30b785c04acb70be339d35e337/docs/checklists/ask-phil-profile.md) bind the executed criteria to retained artifacts.
- The full suite passes **679 tests**, with zero failures, errors or skips. Strict mypy checks **172 files**; Ruff, formatting and Compose validation pass. Independent Standards and Spec reviews have **zero remaining findings**. All 184 frozen software/verification inputs match.
- Bounded faithful multi-query vector retrieval uses one-based RRF with constant 60, evidence deduplication and deterministic ties before SQL top-k. Same-revision, admitted-scope sentence windows merge overlap and obey the serialized context ceiling. CLI/API citations resolve the actual original and added spans; traces retain the actual question, context, rankings, fallbacks and per-call usage.
- Four uncached development ablations retain **16 responses and 24 paid calls**, costing **$0.061936**. Baseline/fusion retain 6/6 context facts and finish 4/4 tasks; expansion/combined retain 5/6 facts and finish 3/4 tasks. All **31 asserted story claims** pass source-based grounding/citation review. Literal completeness is 5/6, 6/6, 4/6 and 4/6. Original Stella-label sensitivity and both Ben-window losses remain failures rather than being relabelled.
- **Baseline remains the selected default**. Optional versioned policies expose fusion, expansion and combined modes. The common 4,000-byte comparison ceiling differs from the preserved 1,200-byte default. These exposed development results are not held-out acceptance, human canon adjudication or evidence of a broad quality improvement.
- Actual paid captures bind checkpoint `8c7dd56`. The later date-fidelity, retained-evidence appendix and citation-capacity stop repairs preserve all sixteen captured query/context decisions under deterministic replay; no additional paid generation is claimed.
- The initial full run's source-validation anomaly remains unexplained and preserved. Unchanged-source probes, the isolated 16-case conversation rerun and final complete 679-case retry pass; no source rewrite or validator relaxation was used.
- The non-resetting $5 ledger is **$0.975588**, with zero unsettled reservations. All 97 original data files and pre-existing/private workspace inputs are preserved. Global checklist counts remain **40 Pass / 11 Pending**; routing/cache and owner-accepted release/holdout obligations remain subsequent work.

Issue #18 is next; #25 is also unblocked. No further issue implementation was started.
