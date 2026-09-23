# 11: Explain family and romantic histories

Status: approved and published as [GitHub #12](https://github.com/tomh1988-8/rag_demo/issues/12), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S18, S20, S21, S22, S30, S38, S39, S59, S60, S68, S72, S73, S77, S78, S79, S81, S86. Checklist evidence owner for: the extensions and rechecks below; primary ownership is recorded in the project register.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S18, S20, S21, S22, S30, S38, S39, S59, S60, S68, S72, S73, S77, S78, S79, S81, S86.

## What to build

Extend admitted claims and typed graph answers to social family and romantic relationship histories. A user can see step/adoptive ties, marriage, separation, divorce, reconciliation, remarriage and affairs with supported ordering and appropriate uncertainty, while biological tree queries retain their narrower meaning.

## Acceptance criteria

- [ ] Review source-backed examples before extending extraction. Preserve biological, adoptive, step-parent and ward roles distinctly; a ward is not inferred to be an adopted child.
- [ ] Keep current/former status and repeated relationships distinct. Separation does not establish divorce; reconciliation does not necessarily establish remarriage. Represent multiple episodes without collapsing them into one undated edge.
- [ ] Answer family/romantic history questions through the API and CLI using typed read-only results, supported timing/ordering and evidence for each asserted relationship. Unknown dates remain unknown.
- [ ] Retain underlying claims and explicit admission/hold outcomes; graph inclusion never erases provenance or turns an unresolved relationship into an established fact.
- [ ] Add unit counterexamples for exposed relationship meanings and direction, plus real database/query/API integration tests. A regression confirms that newly added social ties do not enter biological ancestry.
- [ ] Expand component extraction/value/grounding and graph-result cases and end-to-end answers for repeated marriages, affairs, separation/divorce and uncertain timing. Use reviewed matching and alternatives, report failures by relation type and retain actual execution evidence.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| RAG-04, EXT-02, EXT-03 | Reviewed relationship-history annotations, separated biological/social meanings and supported graph-answer results. |
| AD-06.3, AD-08.1 | Repeated-relationship and uncertain-timing counterexamples with component versus final-answer failures. |

Recheck when: Relationship taxonomy, temporal/status semantics, extraction/admission prompts or history-query behavior.

## Blocked by

- #11 — Answer biological family questions from admitted claims: The evidence-backed claim admission and graph-answer path is needed to extend relationship semantics.

