# 03: Handle incomplete evidence and false premises

Status: [GitHub #4](https://github.com/tomh1988-8/rag_demo/issues/4) remains open. Software implementation has 66 passing Docker tests, but local-model semantic acceptance has failed. The [implementation evidence](../../implementation/issue-4/README.md) and [validation record](../../implementation/issue-4/validation.json) preserve separate scores, independent reviews and a served critical citation-support regression. A stronger provider and locally configured capped credential are needed before acceptance can finish. Plan version: 2.

Spec stories: S10, S15, S30, S32, S33, S34, S35, S36, S38, S43, S71, S72, S79, S83, S84, S86, S92. Checklist evidence owner for: AD-01.2, AD-06.3, RAG-03.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S10, S15, S30, S32, S33, S34, S35, S36, S38, S43, S71, S72, S79, S83, S84, S86, S92.

## What to build

Make the existing text answer path respond honestly to insufficient, contradictory or misleading evidence. Decide among supported answer, clarification, partial answer and abstention through the public conversation contract. Preserve uncertainty, including uncertain dates, in Phil's response and the neutral appendix.

## Acceptance criteria

- [ ] Reviewed cases distinguish missing context, evidence that disproves a premise, unresolved source disagreement and explicit source evidence of a negative fact. Empty retrieval alone never becomes a claim that an event did not happen.
- [ ] Return supported portions and identify unanswered portions for multi-part questions; abstain when no part can be supported. Ask for clarification where user intent or identity cannot be resolved from available information.
- [ ] Expose conflicting passages with attribution and qualifications without inventing a resolution. Later structured correction/admission work may refine this behavior, but conflicting text must already be handled safely.
- [ ] Preserve exact, approximate, relative and unknown timing. Source dates or broadcast dates are not substituted for unsupported story-event dates.
- [ ] Before implementing each behavior, add independently reviewed positive and counterexample cases through the conversation API. Unit-test exposed outcome/citation rules and integration-test evidence retrieval and the resulting public response; check the CLI renders the outcomes.
- [x] Report correctness, groundedness, completeness, citation support and answerability separately. Turn observed critical false-premise, unsupported-negative or false-citation failures into reviewed regression cases.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-01.2, AD-06.3 | Reviewed response-outcome matrix and public counterexample/regression results. |
| RAG-03, AD-08.1 | Separate factual, support, citation and answerability results with missing/conflicting-evidence examples. |

Recheck when: Response policy, corpus conflicts, answer prompt/model, date handling, retrieval behavior or newly observed failure categories.

## Blocked by

- #3 — Generate a grounded Ask Phil answer: A real generated answer and its supporting evidence are needed to exercise answerability outcomes.
