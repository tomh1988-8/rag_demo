# 24: Reuse eligible text answers with a versioned cache

Status: published as [GitHub #25](https://github.com/tomh1988-8/rag_demo/issues/25) for the user-requested fusion/cache amendment. Implementation has not started; runtime evidence is Pending.

Spec stories: S122, S123, S124, S125, S126, S127, S128, S129, S130.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S122, S123, S124, S125, S126, S127, S128, S129, S130.

## What to build

A user can repeat an eligible standalone text question and receive a supported cached answer with original citations, a new delivery identity and truthful measurements. Changed evidence/configuration or a context-dependent request goes through normal answering. Feedback and automatic online evaluation work for cached deliveries.

## Acceptance criteria

- [ ] Start with exact matches after documented conservative normalization; preserve names, dates, negation and relationship intent. Cache only successful supported standalone conventional-text answers. Follow-ups, history-dependent requests, unresolved identities, graph/investigative routes, incompatible overrides and failure/clarification/unsupported outcomes bypass reuse or population.
- [ ] Use PostgreSQL initially and key eligibility by effective request, canon/access scope, active source/index revision, retrieval/fusion/context policy, model/settings, prompts/persona, output/validation policy and relevant application version. Retain answer, source spans, original assembled context and generation lineage. Resolve supporting evidence and compatibility before serving a hit; TTL alone is insufficient.
- [ ] Implement expiry, bounded capacity/eviction, explicit retirement and disable/bypass. Snapshot publication/rollback, corrected/withdrawn evidence and configuration changes prevent incompatible reuse immediately. On a cache failure or invalid entry, run normal answering within the existing request budget. Do not let raw feedback rewrite source facts or mark a cached answer verified.
- [ ] Issue a new response ID and serving trace for every cache delivery, linked internally to the reusable entry and original evidence/generation. Preserve citations and support status while reporting hit/miss/bypass, current elapsed time and actual new model usage. Never replay old cost/latency or expose another session, feedback or private trace.
- [ ] Accept feedback on the new response and automatically assess the served cached answer against its original context. Include hit/fresh-generation cohorts in metrics and sampling, reconcile delayed/revised feedback, and retain shared generation lineage so repeated deliveries are not treated as independent factual evidence.
- [ ] Start from failing repeat/invalidation cases. Integrate real database persistence and API/CLI feedback/evaluation behavior; verify changed snapshots/configuration, rollback, expiry, retired citations, normalization near-misses, session isolation, follow-up bypass, restart, disable and cache-error fallback.
- [ ] Report deliberate cold/warm workload results: eligible requests and hits, all-request coverage, misses, stale/incorrect reuse, supported-answer quality and end-to-end latency/cost with explicit denominators. Disable/isolate caches for retrieval/model-quality comparisons and segregate dataset partitions; never warm held-out evaluations from tuning answers or labels.
- [ ] Record that semantic paraphrase matching is a later opt-in extension. Its enablement requires reviewed paraphrase/near-miss data, hard compatibility filters and calibrated false-hit gates covering character/date/negation and relationship/criminal-role distinctions. No Redis service or semantic matching implementation is required to accept this first cache.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

Use the existing public retrieval, conversation and evaluation seams. The implementer records results; the project owner accepts scope and measured release thresholds. New requirements remain Pending until executed and evidenced.

| Checks | Evidence required for completion |
| --- | --- |
| AD-05.3, AD-06.1, AD-06.2, AD-09.1, AD-09.3, RAG-03 | Eligibility/invalidation/isolation regressions, preserved evidence and cold/warm quality/cost measurements. |
| ONLINE-01, ONLINE-02, ONLINE-03, ONLINE-04 | New-delivery feedback, automatic original-context assessment, truthful cohorts and reviewed shared-lineage failures. |

Recheck when: Source/index snapshot, public behavior, retrieval/context policy, model/prompts, cache identity or eligibility, evaluation dataset/splits, limits or supported environment changes.

## Blocked by

- #24 — Answer with fused retrieval and wider source context: The selected text policy and context lineage define what can be reused.
- #6 — Refresh and recover a captured snapshot: Actual publication/rollback is needed to verify invalidation.
- #23 — Evaluate live answers with feedback and close the review loop: Cache-hit feedback and online assessment must extend a working delivered-response loop.
