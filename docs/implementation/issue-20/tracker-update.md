## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S11, S12, S13, S15, S16, S17, S18, S20, S21, S22, S23, S24, S25, S26, S27, S29, S30, S31, S32, S39, S41, S42, S58, S59, S60, S61, S62, S64, S75, S76, S77, S78, S79, S81, S86, S87, S88, S89, S92.

## What to build

Apply the existing claim extraction, review and graph publication workflow to the already captured 20-character corpus. A maintainer can inspect what was admitted, held, unclassified or missing; users can ask representative supported family, relationship and shared-event questions across that coverage. Expand data using the existing behavior rather than inventing family-specific features.

## Acceptance criteria

- [x] Process the agreed 20 profiles through bounded, restartable batches under the configured API limits. Keep supporting characters needed by sourced relationships/events, stable identities and relevant pre-1990 history.
- [x] For each core profile, record source/text coverage, evaluated extraction coverage, admitted graph capabilities, unresolved claims and known gaps. Demonstrate reviewed questions or an explicitly supported coverage limitation; do not manufacture claims to fill a roster quota.
- [x] Use the pilot's manual audit and annotation guidance, then targeted review and sampling informed by ambiguity, contradictions and observed errors. Inspect representative biological/social ties, repeated relationships, crime/justice roles, life events and unknown dates.
- [x] Build reviewed reference expansions before evaluating each new batch; preserve reviewer notes, synthetic labels, cross-source check status and story/duplicate groups across splits. Report precision/recall/F1 only on material with suitable reference completeness.
- [x] Demonstrate family, relationship-history and shared-event answers through the API/CLI against a coherent source/claim/graph snapshot. Check value accuracy, evidence support and graph results separately; preserve unclassified facts for text answers.
- [x] Run relevant real database/public-boundary integrations and component/end-to-end regressions, inspect category failures, preserve corrected claims and generate budgeted live results. Deliver a reusable coverage process and reviewed cases for future notable-character expansion without claiming exhaustive canon.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| RAG-01, RAG-04, EXT-01, EXT-02, EXT-03, EXT-04 | Core-roster coverage/audit report, versioned annotations, per-category extraction/grounding/graph results and public supported answers. |
| AD-03.4, AD-04.3, AD-08.4 | Cross-profile duplicate/split checks, sampled review decisions and critical-failure regressions. |

Recheck when: Roster expansion, new captured snapshot, extraction/admission/classification changes or changed review/reference labels.

## Blocked by

- #7 — Answer from all 20 core character profiles: The complete core roster must already have reproducible text/source coverage.
- #12 — Explain family and romantic histories: Relationship-history meanings and extraction must be working.
- #14 — Explain life events, themes and unclassified facts: Life-event and crime/justice meanings and extraction must be working.
- #15 — Review corrected and disputed knowledge: Review, correction and coherent graph publication must be available before scaling admitted claims.

## Implementation evidence

[Checked coverage and reproducible workflow](https://github.com/tomh1988-8/rag_demo/blob/main/docs/implementation/issue-20/README.md) now cover all 20 captured core profiles at reviewed source revision `eec703391b486b1b300b165a905861fde7363010`.

- Twenty-two bounded, restartable paid extraction attempts preserve 32 actual candidates and exact root trace readback. All 794 original passages remain in the 816-passage snapshot; all 45 pre-existing tracked data files remain byte-identical.
- Pre-frozen labels cover 29 structured source assertions and two text classifications. Full candidate review preserves malformed locators, the out-of-catalogue Laura record, literal/policy-sensitive time mismatches and uncertainty. Per-family precision/recall/F1 apply only to fully annotated selected excerpts; no corpus-wide recall or independent canon acceptance is claimed.
- The coherent reviewed projection admits 28 structured source assertions and two text classifications, retaining originals, correction links and supporting identity Den. Explicit content-bound review consolidates Martin/Stacey’s same marriage without weakening the episode safeguard or changing raw scores. Both original source accounts and the initial failure remain recorded.
- Twenty-five actual graph API/CLI/session outcomes pass separate result-set, typed-value, locator/citation and exact root/tool trace checks plus audit/reset/restart readback. Independent final-prose review passes 29 factual groups and all 25 outcomes. The actual full-index text answer passes 2/2 source-supported claims and required facts while preserving the tape revelation as unclassified.
- Both independent review axes have zero remaining findings after retaining and repairing false graph-value passes, changed-report-input acceptance, scope/ownership accounting and inaccurate audit notes. All eight final Docker public-boundary/scorer checks pass; strict mypy checks 140 files and Ruff/formatting pass.
- Final software verification passes all 586 original test identities exactly once across two isolated disjoint selections (320 + 266), with zero failures/errors/skips. The original 585-pass/1-failure run is preserved; a reviewed test-only provider-readiness repair fixes its scheduling precondition. The original trace confirms safe cancellation before any model operation. No application or paid result changed.
- Reported incremental inference is $0.238023 across 22 extraction calls and one text answer. The shared non-resetting $5 ledger is $0.911656, with zero unsettled reservations and no repeated paid work. Offline reviews made no provider calls.
- RAG-04 passes for checked graph contracts; register counts are 36 Pass and 15 Pending. Representative variation, original model-quality failures, human/canon adjudication, routing and broader release/online obligations remain pending. The per-profile inventory, grouped regressions and reusable commands support later character expansion.

Publication: [Verified implementation and evidence commit 99d4b4a](https://github.com/tomh1988-8/rag_demo/commit/99d4b4ae47a0361c46576f54d2cc392ed7587bd5)
