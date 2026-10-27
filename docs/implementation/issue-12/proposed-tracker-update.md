## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S18, S20, S21, S22, S30, S38, S39, S59, S60, S68, S72, S73, S77, S78, S79, S81, S86.

## What to build

Extend admitted claims and typed graph answers to social family and romantic relationship histories. A user can see step/adoptive ties, marriage, separation, divorce, reconciliation, remarriage and affairs with supported ordering and appropriate uncertainty, while biological tree queries retain their narrower meaning.

## Acceptance criteria

- [x] Review source-backed examples before extending extraction. Preserve biological, adoptive, step-parent and ward roles distinctly; a ward is not inferred to be an adopted child.
- [x] Keep current/former status and repeated relationships distinct. Separation does not establish divorce; reconciliation does not necessarily establish remarriage. Represent multiple episodes without collapsing them into one undated edge.
- [x] Answer family/romantic history questions through the API and CLI using typed read-only results, supported timing/ordering and evidence for each asserted relationship. Unknown dates remain unknown.
- [x] Retain underlying claims and explicit admission/hold outcomes; graph inclusion never erases provenance or turns an unresolved relationship into an established fact.
- [x] Add unit counterexamples for exposed relationship meanings and direction, plus real database/query/API integration tests. A regression confirms that newly added social ties do not enter biological ancestry.
- [x] Expand component extraction/value/grounding and graph-result cases and end-to-end answers for repeated marriages, affairs, separation/divorce and uncertain timing. Use reviewed matching and alternatives, report failures by relation type and retain actual execution evidence.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| RAG-04, EXT-02, EXT-03 | Reviewed relationship-history annotations, separated biological/social meanings and supported graph-answer results. |
| AD-06.3, AD-08.1 | Repeated-relationship and uncertain-timing counterexamples with component versus final-answer failures. |

Recheck when: Relationship taxonomy, temporal/status semantics, extraction/admission prompts or history-query behavior.

## Blocked by

- #11 — Answer biological family questions from admitted claims: The evidence-backed claim admission and graph-answer path is needed to extend relationship semantics.


## Implementation acceptance — 27 October 2026

Implemented and reviewed in [published commit 0740146](https://github.com/tomh1988-8/rag_demo/commit/074014676d17b40cfa098c279e1e31da90357467); [revision-linked evidence](https://github.com/tomh1988-8/rag_demo/blob/074014676d17b40cfa098c279e1e31da90357467/docs/implementation/issue-12/README.md) records the public contract, source reviews, raw pilot, corrected references, actual runtime and validation.

- Software: 340 tests pass with real PostgreSQL 18.6/pgvector 0.8.6; strict mypy across 79 files, Ruff and formatting pass. Both independent review axes have zero remaining findings after four fixes.
- Runtime: 28 actual API/CLI outcomes; exact MLflow root/tool output, citation, audit and restart readback. Biological ancestry stays separate from social relationships.
- Quality remains limited: corrected raw extraction precision 5/12, recall 5/13 and F1 0.4; locator/strict grounding 2/12; all twelve raw candidates held. The curated projection admits thirteen source assertions describing twelve semantic assertions while retaining all raw holds. Twelve labels predate inference; one documented source correction followed independent review. Original v1 labels/pilot remain unchanged. This is curated capability, not successful automatic extraction or held-out/human canon acceptance.
- The one offline model call cost $0.025226; serving inference is zero. Shared non-resetting $5 ledger: $0.386799, zero unsettled reservations. All original tracked data and unrelated user work are preserved.
- Scoped RAG-04, EXT-02/03, AD-06.3 and AD-08.1 evidence is recorded. Wider graph, corrections, routing and final release obligations retain their project status. #13 is next.
