# 09: Explain family and romantic relationship histories

Draft for breakdown review; not approved or published.

Spec story references: 18, 20, 21, 22, 30, 39, 78, 81.

## What to build

A viewer can ask about a character's family or romantic relationships and receive an evidenced history that distinguishes biological ties from social ties and current relationships from former ones. Extend the existing claim-to-answer path with a small reviewed history before wider roster ingestion.

## Acceptance criteria

- [ ] Extract and admit supported adoptive, step-parent, partner, marriage, separation, divorce, and affair claims as distinguishable meanings; a ward or guardianship is not automatically adoption.
- [ ] Preserve repeated marriages, changing relationship status, and exact, approximate, relative, or unknown timing. Separation does not automatically establish divorce.
- [ ] Expose a typed family/romantic-history query and answer through the API and CLI, returning the relevant ordered or partially ordered facts, unresolved timing, and evidence for each assertion.
- [ ] Keep social family ties outside the biological family-tree results, while allowing their own relationship answers and later connection queries.
- [ ] Retain underlying evidence and ambiguous claims without inventing status, dates, or a relationship just because characters share a theme or appear together.
- [ ] Add reviewed extraction, history-result, timing, grounding, and final-answer cases, including an appropriate repeated-marriage example whose source premises are checked before gold use.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 07: Answer biological family questions from checked claims

