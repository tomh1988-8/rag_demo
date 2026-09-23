# 19: Demonstrate the complete evaluated Ask Phil workflow

Draft for breakdown review; not approved or published.

Spec story references: 5, 11, 15, 16, 37, 42, 43, 44, 45, 46, 47, 54, 55, 64, 69, 71, 72, 73, 74, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97.

## What to build

A portfolio reviewer can start the completed local Ask Phil demonstration, ask representative questions across the 20 core characters, inspect all three real retrieval routes, and reproduce the recorded test/evaluation evidence. This ticket integrates and checks the already delivered slices; it is not where missing extraction, routing, or evaluation capabilities are first built.

## Acceptance criteria

- [ ] Run the complete local workflow from reproducible startup and manual refresh to grounded conversation, clarification, follow-ups, partial/abstain outcomes, and reset across the agreed 20-character roster and relevant supporting characters.
- [ ] Demonstrate actual text, graph, and bounded-investigation execution with automatic routing plus explicit overrides; show appropriate excerpts, supported paths, or actual tools/findings and a neutral, accurate appendix.
- [ ] Re-run the full unit/integration suite against its confirmed public contracts, including real database behavior, failed/interrupted refresh, coherent snapshot use, evidence integrity, and execution limits. Associate results with the evaluated revision.
- [ ] Run component and end-to-end comparisons using frozen source/dataset artifacts, grouped reviewed cases, recorded model/prompt/schema/scorer settings, and thresholds chosen before inspecting the held-out candidate results.
- [ ] Compare the routed, graph-capable, and investigative policies with always-text-RAG using the same corpus/question set and controlled answer-model settings; include representative alternative eligible routes and targeted ablations.
- [ ] Report per-case failures, category coverage, sample sizes, paired differences, latency distributions, available cost/usage and appropriate uncertainty estimates. Repeated stochastic runs are not additional independent questions.
- [ ] Include extraction/retrieval/graph/routing and final persona/citation/answerability results, judge configuration and calibration evidence, and unresolved limitations. Critical factual, parentage, guilt, or citation failures must be resolved rather than averaged away.
- [ ] Inspect trace and combined-context completeness for graph and multi-step answers, separate serving from offline evaluation expense, and identify missing measurements without fabricated confidence.
- [ ] Provide a reproducible demonstration procedure and recorded evidence of the acceptance checks. No cloud deployment, R Shiny client, spoiler filters, extra personas, or programme-wide exhaustive rankings are required.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 05: Ground follow-ups and reset conversations
- 12: Keep Phil's voice faithful to the evidence
- 14: Route questions and escalate on evidence gaps
- 15: Cover the Mitchell and Watts core characters
- 16: Cover the Beale and Fowler core characters
- 17: Cover the Slater and Moon core characters
- 18: Cover the remaining connected core characters

