# 13: Investigate with bounded text and graph tools

Draft for breakdown review; not approved or published.

Spec story references: 37, 40, 44, 45, 46, 47, 49, 53, 55, 68, 70, 82, 96.

## What to build

A viewer or demonstrator can explicitly select an investigative route for a reviewed question requiring several evidence-gathering steps. The system uses the available text and graph tools within one captured snapshot, then returns supported findings and a concise record of what it actually did.

## Acceptance criteria

- [ ] Use the existing text retrieval and typed graph tool contracts with validated arguments and actual recorded execution. No live-web browsing or unsupported graph capability is introduced.
- [ ] Bind the whole investigation to one source/claim/projection snapshot, including when refresh occurs, and preserve evidence from all steps needed for the final answer.
- [ ] Enforce setup-configured execution/API limits and stop honestly on exhausted limits, tool errors, or insufficient evidence, retaining supported partial findings where possible.
- [ ] Demonstrate a small reviewed multi-step task, a recoverable tool failure, and a limit-triggered partial or abstain outcome; do not require one exact internal sequence when alternative supported strategies succeed.
- [ ] Return text/graph evidence and a concise appendix assembled from actual tool calls, findings, fallbacks, elapsed time, and available cost/usage, through the shared API and CLI with a visible route override.
- [ ] Record the actual combined context for MLflow component and end-to-end scorers, including tool/argument validity, evidence acquisition, task success, recovery, limits, citations, and total serving expense.
- [ ] Compare the reviewed investigative cases with the existing text/graph options on the same snapshot and answer-model settings; complexity alone does not prove investigation adds value.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 02: Handle incomplete evidence and false premises
- 11: Trace evidenced connections between characters

