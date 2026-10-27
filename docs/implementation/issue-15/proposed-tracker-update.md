## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S31, S32, S33, S41, S55, S58, S59, S60, S61, S62, S63, S64, S65, S72, S73, S77, S79, S86, S89.

## What to build

Give a maintainer a narrow review path for ambiguous, conflicting and corrected claims, and show its consequences in user answers. Publish source, admitted-claim and graph versions coherently. Preserve earlier evidence and distinguish current supported interpretations from unresolved disputes without treating review itself as independent corroboration.

## Acceptance criteria

- [x] Inspect a held claim with its source spans, identities, admission reasons and review history; record an explicit review outcome and rationale. Review actions are maintainer operations, not new answering-agent tools.
- [x] Apply a supported correction while preserving earlier claims/evidence and the reason the interpretation changed. Current text and graph answers follow the corrected interpretation with suitable attribution.
- [x] Leave unresolved disagreement visible in text explanations and outside established graph connections. Do not silently select one competing account or treat an in-story lie/belief as narrative fact.
- [x] Publish/rebuild source, retrieval, claim and graph artifacts as a compatible snapshot. An answer pins that version; interrupted refresh/review/projection work preserves the last usable version and supports an inspected recovery.
- [x] Define annotation/matching and review guidance, duplicate handling, uncertainty tolerances and reference completeness for extraction metrics. Thoroughly audit the small pilot, then define targeted review/sampling criteria for later coverage; passing automation is not labelled independent verification.
- [x] Start from reviewed correction/conflict/failure cases. Unit-test public admission transitions and integrate real storage, refresh, review and API/CLI answers, checking actual resulting claims, graph membership, evidence integrity and recovery rather than only command success.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| EXT-04, AD-03.3 | Review/adjudication records, metric annotation rules, retained corrections and coherent snapshot manifests. |
| AD-06.2, AD-10.2, RAG-03 | Corrected/disputed public answers plus failed-projection and recovery results over real persisted state. |

Recheck when: Admission/review policy, source correction/conflict, graph projection, snapshot publication or recovery changes.

## Blocked by

- #6 — Refresh and recover a captured snapshot: Refresh and recovery need a working source snapshot lifecycle.
- #11 — Answer biological family questions from admitted claims: There must be admitted/held claims and a graph projection to inspect and correct.


## Completion evidence — 27 October 2026

Implemented and published in [d4d5564](https://github.com/tomh1988-8/rag_demo/commit/d4d5564929964766b3f1547ef1f6137968d0022e). A fresh native fetch verifies exact local/remote tree agreement and all 166 frozen tested input hashes.

Maintainers can inspect held Claims, exact source spans, identities, admission reasons and chronological reviews through the read-only API/CLI. The separate maintainer review command publishes explicit, content-bound outcomes and optional new assertions without overwriting prior Claims or evidence. Corrections retain original links and follow current replacement accounts, including later corrections and disputes. Connected competing groups remain visible even when retrieval initially finds only a predecessor with a mistaken identity.

Publication binds source, retrieval, all claim/graph families and review identity. Failed projection and interrupted indexing retain the last usable version; exact retry and inspected rollback work, withdrawn snapshots reject new answers, and already-pinned work completes on its original version. Unchanged source refresh preserves reviewed interpretations.

The final runtime records nineteen actual API/CLI/session responses with exact MLflow/saved-response readback, citation resolution, three restarts, resets and compatible rollbacks. Independent source review passes all twelve current corrected/disputed answers: the actual Peggy locator repair, a deliberately authored biological-to-adoptive correction, and an explicitly synthetic two-account dispute. Two intentionally wrong parentage baseline/rollback answers remain recorded factual failures and are excluded from the passing quality denominator. No answer-model calls or new extraction were used.

The evidence includes frozen annotation/matching rules, duplicate and uncertainty handling, reference-completeness boundaries, targeted later review/sampling, the initial text-context failure and both fixed independent-review findings. Original raw candidates, references and extraction/ordinary-text failures remain unchanged. EXT-04 now has scoped implementation evidence; wider graph coverage, full code/prompt recovery and representative release gates remain Pending.

All **480 software tests** pass with zero failures/errors/skips, as do strict mypy across 109 files and Ruff lint/formatting. Both independent code-review axes have zero remaining findings. All 166 frozen implementation inputs, 37 original data files, 51 pre-existing workspace files, the private key and shared ledger remain unchanged. No paid model calls were made; the shared non-resetting $5 ledger remains **$0.464981**, zero unsettled reservations.

[Implementation/evidence](https://github.com/tomh1988-8/rag_demo/blob/d4d5564929964766b3f1547ef1f6137968d0022e/docs/implementation/issue-15/README.md), [validation](https://github.com/tomh1988-8/rag_demo/blob/d4d5564929964766b3f1547ef1f6137968d0022e/docs/implementation/issue-15/validation.json), [actual answer quality](https://github.com/tomh1988-8/rag_demo/blob/d4d5564929964766b3f1547ef1f6137968d0022e/docs/implementation/issue-15/answer-quality.json), [review reports](https://github.com/tomh1988-8/rag_demo/blob/d4d5564929964766b3f1547ef1f6137968d0022e/docs/implementation/issue-15/review.md), [criterion-to-evidence map](https://github.com/tomh1988-8/rag_demo/blob/d4d5564929964766b3f1547ef1f6137968d0022e/docs/implementation/issue-15/acceptance-map.json), and [project register](https://github.com/tomh1988-8/rag_demo/blob/d4d5564929964766b3f1547ef1f6137968d0022e/docs/checklists/ask-phil-profile.md) retain the concrete results and limitations.
