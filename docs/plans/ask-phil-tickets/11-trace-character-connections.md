# 11: Trace evidenced connections between characters

Draft for breakdown review; not approved or published.

Spec story references: 28, 34, 39, 52, 68, 81.

## What to build

A viewer can ask how two characters are connected and inspect a bounded relationship/event path rather than an unexplained association. Compose the already working relationship-history and event-participant capabilities without creating connections from themes, co-appearance, or unchecked claims.

## Acceptance criteria

- [ ] Provide a typed bounded two-character connection query using the supported relationship and shared-event types, preserving direction and participant meaning.
- [ ] Return a valid path or qualified empty result through the API and CLI. Include the evidence for every asserted step and identify the graph/snapshot coverage and configured bounds.
- [ ] Exclude unadmitted claims and theme-only or co-appearance-only links. A path through an accusation must not imply the accused committed the crime.
- [ ] Handle cycles, multiple valid paths, supporting characters, and incomplete graph coverage without claiming global completeness or a unique connection when alternatives are valid.
- [ ] Use independently reviewed graph fixtures with acceptable alternative paths, counterexamples, and evidence expectations, then demonstrate one actual connection answer.
- [ ] Measure result validity, required meaning, supported-edge coverage, bounded execution, and final-answer support separately from path length or retrieval similarity.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 09: Explain family and romantic relationship histories
- 10: Explain story events, crimes, and justice roles

