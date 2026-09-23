# 12: Explain crimes and criminal justice roles

Status: approved and published as [GitHub #13](https://github.com/tomh1988-8/rag_demo/issues/13), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implementation has not started.

Spec stories: S24, S25, S29, S30, S33, S34, S38, S39, S58, S59, S60, S61, S68, S72, S73, S77, S78, S79, S81, S86. Checklist evidence owner for: the extensions and rechecks below; primary ownership is recorded in the project register.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S24, S25, S29, S30, S33, S34, S38, S39, S58, S59, S60, S61, S68, S72, S73, S77, S78, S79, S81, S86.

## What to build

Introduce a narrow shared-event/participant query through a reviewed crime and criminal-justice case. A user can ask what happened and who was involved without treating accusation or conviction as proof of actual guilt. This supplies the event-participant path later life-event and connection questions can extend.

## Acceptance criteria

- [ ] Review realistic source claims for actual commission, allegation/accusation, arrest, trial, conviction, acquittal, imprisonment and release, using distinct event and participant roles. Include false accusation or false confession counterexamples.
- [ ] Require narrative support for actual commission independent of whether the character was caught or punished. Being charged, convicted, jailed, acquitted or present at court alone is not substituted for an assertion of guilt or innocence.
- [ ] Keep events, roles, timing and evidence linked. Distinguish exact/approximate/relative/unknown dates and supported changing accounts; ambiguous claims are held or qualified.
- [ ] Return shared-event participants and a supported crime/justice explanation through the API and CLI, with typed graph results and citations. An empty legal-history result never establishes that a character did not commit a crime.
- [ ] Begin with failing guilt/role counterexamples. Unit-check public role and admission rules and integrate real stored claims, graph queries and user responses. Preserve respectful factual wording for serious harm.
- [ ] Report extraction errors by identity, role, direction, negation and timing separately from schema validity and grounding; evaluate final answers for the forbidden guilt conflations. Link reviewed failures to regressions and actual trace artifacts.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| EXT-02, EXT-03, RAG-04 | Independently reviewed crime/justice roles and supported shared-event graph results. |
| AD-06.3, AD-08.4 | False-accusation/confession and guilt-versus-legal-outcome regression results with critical failures explicit. |

Recheck when: Crime/justice role definitions, new evidence/corrections, extraction/admission rules or shared-event queries.

## Blocked by

- #11 — Answer biological family questions from admitted claims: Claim admission, identity and typed graph answers must exist before introducing role-sensitive event answers.

