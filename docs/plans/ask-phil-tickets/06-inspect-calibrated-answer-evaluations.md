# 06: Inspect calibrated evaluations of chat answers

Draft for breakdown review; not approved or published.

Spec story references: 75, 79, 80, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 97.

## What to build

A developer can run a reviewed set of real chat questions, inspect which answers fail correctness, evidence, completeness, or answerability checks, and examine how calibrated LLM judges compare with human-reviewed labels. Extend the small working baseline from the first slice; do not wait for this ticket to begin testing or evaluation.

## Acceptance criteria

- [ ] Execute selected versioned cases through the application and record the actual answer, assembled context, expected facts, citations, source snapshot, configuration, and individual scorer results in MLflow with inspectable failure reasons.
- [ ] Keep correctness, groundedness, completeness/relevance, citation resolution/support/coverage, and answerability distinct. Validate deterministic scorers against independently reviewed successes, failures, and missing measurements.
- [ ] Calibrate narrow evidence-aware semantic judge rubrics against reviewed labels; record model/settings and rubric versions, inspect disagreements and false passes, and validate on labels excluded from judge tuning.
- [ ] Measure representative repeat variation and sensitivity to answer order and verbosity where applicable. Judge output is an estimate and cannot turn style or source-supported statements into verified truth.
- [ ] Store stable case IDs, evidence revisions/spans, expected and forbidden facts, acceptable alternatives, answerability, reviewer notes, and synthetic provenance. Review model-generated candidate labels before gold use.
- [ ] Group overlapping story events, near-duplicate passages, paraphrases, and synthetic derivatives before splitting development, calibration, held-out, and regression uses. Held-out labels stay out of tuning even when supporting passages remain retrievable.
- [ ] Freeze case artifacts/hashes and scorer/model/prompt/retrieval configurations using self-hosted-compatible storage. Version corrections and rerun baseline/candidate fairly; software-test results remain separate from model evaluation.
- [ ] Record the selected metric variants and reference requirements, choose informed thresholds before the held-out comparison used to accept a candidate, and keep evaluation/judge expenditure separate from serving cost.
- [ ] Demonstrate a supported answer that passes its applicable checks and a fluent but unsupported or wrongly cited answer that fails. Later domain and route slices extend this working reporting path with their own cases.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 02: Handle incomplete evidence and false premises

