# 19: Establish checked graph coverage across the core roster

Status: approved and published as [GitHub #20](https://github.com/tomh1988-8/rag_demo/issues/20), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S11, S12, S13, S15, S16, S17, S18, S20, S21, S22, S23, S24, S25, S26, S27, S29, S30, S31, S32, S39, S41, S42, S58, S59, S60, S61, S62, S64, S75, S76, S77, S78, S79, S81, S86, S87, S88, S89, S92. Checklist evidence owner for: the extensions and rechecks below; primary ownership is recorded in the project register.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S11, S12, S13, S15, S16, S17, S18, S20, S21, S22, S23, S24, S25, S26, S27, S29, S30, S31, S32, S39, S41, S42, S58, S59, S60, S61, S62, S64, S75, S76, S77, S78, S79, S81, S86, S87, S88, S89, S92.

## What to build

Apply the existing claim extraction, review and graph publication workflow to the already captured 20-character corpus. A maintainer can inspect what was admitted, held, unclassified or missing; users can ask representative supported family, relationship and shared-event questions across that coverage. Expand data using the existing behavior rather than inventing family-specific features.

## Acceptance criteria

- [ ] Process the agreed 20 profiles through bounded, restartable batches under the configured API limits. Keep supporting characters needed by sourced relationships/events, stable identities and relevant pre-1990 history.
- [ ] For each core profile, record source/text coverage, evaluated extraction coverage, admitted graph capabilities, unresolved claims and known gaps. Demonstrate reviewed questions or an explicitly supported coverage limitation; do not manufacture claims to fill a roster quota.
- [ ] Use the pilot's manual audit and annotation guidance, then targeted review and sampling informed by ambiguity, contradictions and observed errors. Inspect representative biological/social ties, repeated relationships, crime/justice roles, life events and unknown dates.
- [ ] Build reviewed reference expansions before evaluating each new batch; preserve reviewer notes, synthetic labels, cross-source check status and story/duplicate groups across splits. Report precision/recall/F1 only on material with suitable reference completeness.
- [ ] Demonstrate family, relationship-history and shared-event answers through the API/CLI against a coherent source/claim/graph snapshot. Check value accuracy, evidence support and graph results separately; preserve unclassified facts for text answers.
- [ ] Run relevant real database/public-boundary integrations and component/end-to-end regressions, inspect category failures, preserve corrected claims and generate budgeted live results. Deliver a reusable coverage process and reviewed cases for future notable-character expansion without claiming exhaustive canon.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

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

