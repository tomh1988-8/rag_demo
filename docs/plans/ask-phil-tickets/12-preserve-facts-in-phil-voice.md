# 12: Keep Phil's voice faithful to the evidence

Draft for breakdown review; not approved or published.

Spec story references: 2, 3, 4, 43, 85, 90, 91.

## What to build

A viewer receives recognisably Phil-like wording without losing factual accuracy, uncertainty, or a respectful account of serious offences. Extend the existing basic persona with reviewed counterexamples and the calibrated answer-evaluation path; evidence and measurements remain neutral.

## Acceptance criteria

- [ ] Demonstrate answers drawn from the full supported corpus, including facts Phil would not personally know or willingly admit; his voice must not restrict factual access.
- [ ] Permit self-serving phrasing only when it preserves the supported facts and qualifications; serious offences and their harm must not be minimised.
- [ ] Preserve partial/abstain/clarify outcomes and uncertainty through persona rendering, and keep citations, graph/tool evidence, and measurements neutral.
- [ ] Evaluate neutral expected facts, evidence support, uncertainty preservation, and serious-harm handling separately from a calibrated style rubric; style scores cannot offset factual failures.
- [ ] Use reviewed ordinary, self-incriminating, uncertain, and serious-harm examples. Inspect judge disagreement and verbosity/style sensitivity rather than treating an LLM style score as proof of correctness.
- [ ] Demonstrate the finished wording through the public API and CLI and include the actual persona-generation work in traces and cost; do not require an extra generation step if the same contract can be met without it.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 06: Inspect calibrated evaluations of chat answers

