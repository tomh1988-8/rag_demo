# 10: Answer biological family questions from admitted claims

Status: approved and published as [GitHub #11](https://github.com/tomh1988-8/rag_demo/issues/11), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S17, S18, S19, S30, S34, S38, S39, S41, S49, S52, S58, S59, S60, S61, S62, S67, S68, S71, S72, S73, S75, S77, S78, S79, S81, S98. Checklist evidence owner for: AD-05.2, EXT-02, EXT-03.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S17, S18, S19, S30, S34, S38, S39, S41, S49, S52, S58, S59, S60, S61, S62, S67, S68, S71, S72, S73, S75, S77, S78, S79, S81, S98.

## What to build

Pilot LlamaIndex structured extraction on a small, independently reviewed parentage reference set. Preserve evidence-backed claims separately from their checked SQL-backed graph projection in PostgreSQL. A user can explicitly select the graph route for biological ancestry/descendant questions and inspect the supporting edges and source evidence.

## Acceptance criteria

- [ ] Before the extraction pilot, review source spans, normalized identities, relation direction, negation, uncertainty, timing and complete-enough reference labels for the selected material. Extend the existing seed rather than treating candidate questions as validated facts.
- [ ] Store extracted claims, arguments and evidence independently of graph projections. Apply explicit structure, support, identity, biological-meaning and contradiction checks; hold uncertain, conflicting or unsupported claims out of established graph relationships.
- [ ] Thoroughly audit the initial small batch and record admission/review outcomes. Automated admission and shared-source agreement are not labelled independent verification.
- [ ] Expose typed read-only ancestry/descendant tools with validated inputs, bounded traversal, defined no-result/failure outcomes and evidence-bearing results. Use explicit application SQL graph semantics, not a presumed pgvector graph adapter.
- [ ] Return biological paths/results through the API and CLI with edge citations, snapshot, visible route override and real measurements. Step-parent, adoptive and ward ties must not change the biological tree; unsupported ancestry produces an honest limited outcome.
- [ ] Add failing public/domain cases and real database/graph/API integration tests. Separately score schema validity, claim-value accuracy, evidence grounding and graph results. Define normalization, duplicate matching and annotation sufficiency before reporting extraction precision/recall/F1; include direction, identity and non-biological counterexamples.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-05.2, RAG-04 | Typed read-only graph contract, public ancestry/descendant outputs and path/edge/evidence tests. |
| EXT-02, EXT-03, EXT-04 | Reviewed extraction annotations, admission/audit outcomes and separate schema/value/grounding measurements with matching rules. |

Recheck when: Extraction/schema/normalization changes, identity or parentage evidence, admission rules, graph query semantics, source snapshot or tool contract.

## Blocked by

- #4 — Handle incomplete evidence and false premises: A complete text-answer path and honest missing-evidence outcomes must exist before graph answering.
- #5 — Import real sources with character identity and canon scope: Character identity, scoped source evidence and parsing retention must be established before semantic extraction.

