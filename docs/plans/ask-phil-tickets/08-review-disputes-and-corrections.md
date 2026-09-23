# 08: Review disputed claims and explain corrections

Draft for breakdown review; not approved or published.

Spec story references: 31, 32, 33, 41, 59, 60, 61, 62, 63, 64, 86, 92.

## What to build

A maintainer can inspect a disputed or ambiguous extracted claim and record a supported review outcome. A viewer sees the current supported interpretation, can inspect earlier evidence, and is told about unresolved disagreement. Demonstrate this on a narrow corrected relationship or false account rather than adding a separate review application.

## Acceptance criteria

- [ ] Expose held claims, source spans, competing interpretations, and admission reasons through a minimal maintainer workflow; record actual review decisions without marking unchecked claims independently verified.
- [ ] On supported correction, retain earlier claims/evidence and rebuild the affected projection so text and graph answers identify the supported current interpretation with its qualification.
- [ ] Preserve unresolved conflicts visibly and exclude unsettled connections from established graph facts; uncertain evidence can support a qualified explanation.
- [ ] Pin queries and evaluations to coherent source/claim/projection versions during refresh and review, with reproducible older results and explicit failed or interrupted publication outcomes.
- [ ] Demonstrate a source-supported correction and an unresolved disagreement through the API and CLI, including why a previous account differs and where the evidence comes from.
- [ ] Use independently reviewed cases for lies, false beliefs or retractions and for genuine source disagreement. Check current-versus-previous interpretation, provenance retention, admission outcomes, and final-answer uncertainty separately.
- [ ] Keep review practical: thorough initial audit and targeted review/sampling thereafter, with coverage and review status visible.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 04: Refresh the corpus without losing provenance
- 07: Answer biological family questions from checked claims

