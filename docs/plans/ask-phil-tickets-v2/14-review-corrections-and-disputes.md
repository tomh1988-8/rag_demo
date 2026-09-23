# 14: Review corrected and disputed knowledge

Status: approved and published as [GitHub #15](https://github.com/tomh1988-8/rag_demo/issues/15), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S31, S32, S33, S41, S55, S58, S59, S60, S61, S62, S63, S64, S65, S72, S73, S77, S79, S86, S89. Checklist evidence owner for: EXT-04.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S31, S32, S33, S41, S55, S58, S59, S60, S61, S62, S63, S64, S65, S72, S73, S77, S79, S86, S89.

## What to build

Give a maintainer a narrow review path for ambiguous, conflicting and corrected claims, and show its consequences in user answers. Publish source, admitted-claim and graph versions coherently. Preserve earlier evidence and distinguish current supported interpretations from unresolved disputes without treating review itself as independent corroboration.

## Acceptance criteria

- [ ] Inspect a held claim with its source spans, identities, admission reasons and review history; record an explicit review outcome and rationale. Review actions are maintainer operations, not new answering-agent tools.
- [ ] Apply a supported correction while preserving earlier claims/evidence and the reason the interpretation changed. Current text and graph answers follow the corrected interpretation with suitable attribution.
- [ ] Leave unresolved disagreement visible in text explanations and outside established graph connections. Do not silently select one competing account or treat an in-story lie/belief as narrative fact.
- [ ] Publish/rebuild source, retrieval, claim and graph artifacts as a compatible snapshot. An answer pins that version; interrupted refresh/review/projection work preserves the last usable version and supports an inspected recovery.
- [ ] Define annotation/matching and review guidance, duplicate handling, uncertainty tolerances and reference completeness for extraction metrics. Thoroughly audit the small pilot, then define targeted review/sampling criteria for later coverage; passing automation is not labelled independent verification.
- [ ] Start from reviewed correction/conflict/failure cases. Unit-test public admission transitions and integrate real storage, refresh, review and API/CLI answers, checking actual resulting claims, graph membership, evidence integrity and recovery rather than only command success.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

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

