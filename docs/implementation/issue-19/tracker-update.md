## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S02, S03, S04, S30, S32, S33, S35, S36, S38, S43, S83, S84, S85, S86, S90, S91, S92.

## What to build

Refine and validate the persona already present in text answers. A viewer gets Phil-style speech even for facts Phil would dislike or not personally know, while the evidence appendix stays neutral. This ticket measures and improves a real response behavior; it does not defer factual integrity until the end of development.

## Acceptance criteria

- [x] Review examples where supported facts contradict Phil's interests or personal knowledge. Any self-serving phrasing must still state the correct supported facts clearly and preserve their qualifications.
- [x] Use reviewed serious-offence examples to check that neither the offence nor its harm is trivialised. Keep factual correctness, grounding, persona style and treatment of harm as distinct measures with independent critical failures.
- [x] Preserve partial, abstention, clarification, conflicting-evidence and uncertain-date outcomes. Style must not change the evidence, introduce unsupported certainty or remove citations.
- [x] Keep the appendix and detailed trace neutral and derived from actual records. Test the final API answer and CLI rendering, not only an intermediate neutral draft.
- [x] Add failing persona/counterexample cases before prompt changes, use calibrated semantic judges where helpful and inspect disagreements against human-reviewed labels. Record prompt/judge settings and representative repeated-run variation.
- [x] Compare before/after persona behavior on controlled source/model cases, retain factual regressions and report style gains separately from any changes in support or expense. Later graph/investigative coverage reuses these checks at integration.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-06.3, AD-08.2, RAG-03 | Reviewed persona cases, separate factual/harm/style scores and calibrated judge disagreement results. |
| AD-10.4 | Versioned persona limitations and regressions for factual distortion or minimisation. |

Recheck when: Persona prompt/model, serious-harm examples, response formatting or a new route/evidence shape.

## Blocked by

- #9 — Inspect calibrated quality comparisons: Calibrated factual and semantic evaluation is needed to distinguish persona quality from truth and harm treatment.


## Implementation evidence

Implemented on the current branch and published at SOFTWARE_COMMIT_LINK.
Full software validation: 567 passing tests, strict mypy across 131 files,
Ruff/formatting and zero remaining findings on both independent review axes.

[Issue #19 evidence](https://github.com/tomh1988-8/rag_demo/blob/main/docs/implementation/issue-19/README.md)
contains 72 actual API responses across baseline, first candidate and final
prompts. All final answer/CLI/actual trace/citation records agree. The controlled
comparison improves neutral appendices from 21/24 to 24/24, removes the mandatory
opener, and preserves separate voice/harm/outcome results of 24/24, 8/8 and 24/24.
The unsupported-absence regression and comparison-integrity repair are retained.

These are exposed source-based agent labels. Human-approved issue #9 support
calibration is unchanged; application agrees with 9/10 new agent labels, with one
foreman-role interpretation still requiring human adjudication. The over-specified
Jane reference retains one conservative coverage miss, not a wrong-killer result.
No human canon, broad judge or held-out acceptance is claimed. Register counts
remain 35 Pass and 16 Pending.

There were 72 paid answer calls and ten support-judge calls, reporting $0.1779852.
The original shared non-resetting $5 ledger is $0.673627 with zero unsettled
reservations. Existing data, user work and private inputs remain preserved.

Next: #20. #22 and #24 are also unblocked; #18 waits for #24. Wait for the user's
next implementation instruction before another ticket.
