# 18: Cover the remaining connected core characters

Draft for breakdown review; not approved or published.

Spec story references: 11, 12, 13, 14, 15, 16, 19, 58, 61, 62, 86, 87, 88, 89.

## What to build

A viewer can explore the supported histories of Pat Butcher, Janine Butcher, Dot Cotton, Denise Fox, Max Branning, and Linda Carter. This cohort completes the named roster alongside the other coverage tickets while using the same repeatable ingestion and evaluation process.

## Acceptance criteria

- [ ] Capture and process the six named main-series profiles, relevant earlier history, and evidenced supporting characters without importing out-of-scope source sections.
- [ ] Review and sample applicable biological, social/romantic, event, crime/justice, and unclassified claims; retain unresolved conflicts and classification gaps explicitly.
- [ ] Preserve existing cohorts and canonical identities in the combined snapshot and deduplicate shared accounts/events without treating repeated narratives as independent corroboration.
- [ ] Demonstrate representative sourced relationship and event answers, including a false-accusation or justice-role distinction where the reviewed sources support one.
- [ ] Add reviewed annotations and questions with evidence revisions, sufficient evidence/alternatives, answerability, actual cross-checking status, and grouped dataset uses.
- [ ] Make cohort coverage and source-check information inspectable together with parsing/extraction, graph, and final-answer results; do not describe roster inclusion as exhaustive character coverage.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 08: Review disputed claims and explain corrections
- 09: Explain family and romantic relationship histories
- 10: Explain story events, crimes, and justice roles

