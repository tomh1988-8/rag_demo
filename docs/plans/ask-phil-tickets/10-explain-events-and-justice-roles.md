# 10: Explain story events, crimes, and justice roles

Draft for breakdown review; not approved or published.

Spec story references: 23, 24, 25, 26, 27, 29, 30, 39, 41, 77, 78, 81.

## What to build

A viewer can ask what happened and who was involved in a supported story event, including a crime or court proceeding, and receive an answer that preserves each participant's role. The same path retains pregnancy/death events, topical themes, and evidenced facts that do not fit the classification.

## Acceptance criteria

- [ ] Extract and admit a small reviewed set of story events and participant roles covering pregnancy, death, crime, and criminal-justice stages, using the existing claim/evidence checks.
- [ ] Distinguish actual commission from accusation, arrest, trial, conviction, acquittal, imprisonment, and release; an accused or convicted person is not automatically the established perpetrator.
- [ ] Expose supported shared-event/participant queries through the typed graph tools, API, and CLI with event meaning, role, timing precision, and source evidence.
- [ ] Keep event types distinct from themes such as domestic abuse or the manosphere. A shared theme or mere co-appearance does not create a character connection.
- [ ] Retain source-supported unclassified facts for text retrieval and show the classification gap; do not force them into an invented graph category.
- [ ] Demonstrate reviewed false-accusation/conviction-versus-guilt and uncertain-date cases. Candidate Lucy/Max/Bobby scenarios require checked source revisions and legal terminology before adoption as gold.
- [ ] Report event/role extraction and grounding errors separately from schema validity, graph results, and answer correctness; critical guilt mistakes cannot be hidden by aggregate scores.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 07: Answer biological family questions from checked claims

