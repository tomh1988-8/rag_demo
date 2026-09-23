# 18: Validate Phil's voice without changing facts

Status: approved and published as [GitHub #19](https://github.com/tomh1988-8/rag_demo/issues/19), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S02, S03, S04, S30, S32, S33, S35, S36, S38, S43, S83, S84, S85, S86, S90, S91, S92. Checklist evidence owner for: the extensions and rechecks below; primary ownership is recorded in the project register.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S02, S03, S04, S30, S32, S33, S35, S36, S38, S43, S83, S84, S85, S86, S90, S91, S92.

## What to build

Refine and validate the persona already present in text answers. A viewer gets Phil-style speech even for facts Phil would dislike or not personally know, while the evidence appendix stays neutral. This ticket measures and improves a real response behavior; it does not defer factual integrity until the end of development.

## Acceptance criteria

- [ ] Review examples where supported facts contradict Phil's interests or personal knowledge. Any self-serving phrasing must still state the correct supported facts clearly and preserve their qualifications.
- [ ] Use reviewed serious-offence examples to check that neither the offence nor its harm is trivialised. Keep factual correctness, grounding, persona style and treatment of harm as distinct measures with independent critical failures.
- [ ] Preserve partial, abstention, clarification, conflicting-evidence and uncertain-date outcomes. Style must not change the evidence, introduce unsupported certainty or remove citations.
- [ ] Keep the appendix and detailed trace neutral and derived from actual records. Test the final API answer and CLI rendering, not only an intermediate neutral draft.
- [ ] Add failing persona/counterexample cases before prompt changes, use calibrated semantic judges where helpful and inspect disagreements against human-reviewed labels. Record prompt/judge settings and representative repeated-run variation.
- [ ] Compare before/after persona behavior on controlled source/model cases, retain factual regressions and report style gains separately from any changes in support or expense. Later graph/investigative coverage reuses these checks at integration.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-06.3, AD-08.2, RAG-03 | Reviewed persona cases, separate factual/harm/style scores and calibrated judge disagreement results. |
| AD-10.4 | Versioned persona limitations and regressions for factual distortion or minimisation. |

Recheck when: Persona prompt/model, serious-harm examples, response formatting or a new route/evidence shape.

## Blocked by

- #9 — Inspect calibrated quality comparisons: Calibrated factual and semantic evaluation is needed to distinguish persona quality from truth and harm treatment.

