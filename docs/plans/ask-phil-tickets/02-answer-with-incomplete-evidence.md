# 02: Handle incomplete evidence and false premises

Draft for breakdown review; not approved or published.

Spec story references: 30, 33, 34, 35, 36, 37, 84, 86.

## What to build

A viewer asking an unsupported, partly supported, or misleading question receives a useful, qualified response through the same API and CLI. The system distinguishes what its evidence supports from what remains unknown, instead of turning missing retrieval results or a fluent guess into a fact.

## Acceptance criteria

- [ ] Demonstrate supported, partial, and abstain outcomes on independently reviewed questions; retain citations for supported portions and state which requested facts remain unresolved.
- [ ] An empty retrieval establishes only that no supporting evidence was found in the available coverage, not that the event or relationship never existed.
- [ ] Challenge a false premise only when the captured evidence supports the correction; otherwise explain the uncertainty without asserting an alternative as fact.
- [ ] Preserve exact, approximate, relative, and unknown timing. An unsupported request for an exact date must not be satisfied with a broadcast, publication, or refresh date.
- [ ] An ambiguous character reference can return a clarification outcome instead of guessing. Consistent alias resolution and conversational clarification handling are extended by their own slices.
- [ ] Provider failures or configured execution limits produce an honest observable outcome with supported findings retained where available; the appendix must agree with the actual execution.
- [ ] Add reviewed answerability and forbidden-assertion cases to the baseline, evaluating factual support, completeness, uncertainty, and citation support separately.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 01: Answer one sourced question locally

