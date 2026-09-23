# 07: Answer biological family questions from checked claims

Draft for breakdown review; not approved or published.

Spec story references: 17, 18, 39, 41, 49, 52, 57, 58, 59, 60, 61, 62, 67, 68, 71, 72, 73, 74, 75, 77, 78, 79, 81, 92, 95.

## What to build

A viewer can explicitly request a graph-backed biological family answer for a small reviewed set of characters and inspect the evidence for every asserted parent link. This first graph slice carries claim extraction, admission, storage, traversal, and response presentation through one narrow relationship family.

## Acceptance criteria

- [ ] Prepare reviewed parentage annotations and question outcomes before the extraction pilot, including biological, step/adoptive, ward, uncertain, and wrongly directed counterexamples. Thoroughly audit this initial extraction batch.
- [ ] Use LlamaIndex structured extraction to produce claims tied to source revisions/spans and stable character identities; retain the claims and evidence independently of their graph projections.
- [ ] Apply structure, source-support, identity, biological-meaning, and contradiction checks. Ambiguous or conflicting claims are held with an inspectable reason and do not become established biological edges; automation does not imply independent corroboration.
- [ ] Build explicit typed SQL-backed ancestry and descendant tools in PostgreSQL. Their graph results preserve direction, permitted relationship type, evidence, and configured traversal bounds; pgvector is not assumed to supply relationship traversal.
- [ ] Return the supported path or structured result with edge evidence through FastAPI and the CLI, reporting the actual graph route and visible override. An unavailable graph capability or empty result is qualified honestly.
- [ ] Ensure source records, admitted claims, and queried projections refer to the same recorded snapshot. Graph coverage can be narrower than the retrievable source text.
- [ ] Record schema validity separately from normalized extraction precision/recall/F1 where annotations support them, grounding, result/path correctness, and citation support. Compare reviewed graph answers with the text baseline using the same evidence and answer-model settings.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 03: Resolve characters and keep sources in scope

