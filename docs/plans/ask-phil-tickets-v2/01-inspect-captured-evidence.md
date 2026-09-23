# 01: Inspect captured source evidence locally

Status: approved and published as [GitHub #2](https://github.com/tomh1988-8/rag_demo/issues/2), labelled ready-for-agent; body and label verified on 23 September 2026. Plan version: 2. Implemented and validated natively on 23 September 2026; [implementation evidence](../../implementation/issue-2/README.md) records 17 passing tests. Fresh Docker Compose acceptance remains pending; GitHub #2 is still open.

Spec stories: S06, S15, S38, S41, S42, S55, S58, S66, S67, S69, S71, S72, S73, S74, S75, S86, S87. Checklist evidence owner for: AD-02.4, AD-03.1, AD-04.1, AD-04.2, AD-06.1.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S06, S15, S38, S41, S42, S55, S58, S66, S67, S69, S71, S72, S73, S74, S75, S86, S87.

## What to build

A maintainer can load a small, permitted source fixture and ask for matching evidence through the CLI, shared FastAPI application, and PostgreSQL. Return the captured passage and provenance without generating a model answer. This is an evidence-inspection baseline for development, not a fourth production answer route. Establish the smallest complete local environment and independently reviewed seed cases before any model-driven work.

## Acceptance criteria

- [ ] Inspect a representative real character passage and record its source/revision, main-series scope, capture date, demonstrated coverage and any gaps. The inspected seed includes an answerable question and a question whose expected evidence is absent; candidate demonstration questions are not accepted as gold without review.
- [ ] Record stable case IDs, expected supporting spans/facts, acceptable alternatives, forbidden claims, answerability, reviewer notes and synthetic provenance where applicable. Reference labels are established by checking the source, not by accepting a generated answer.
- [ ] Load the captured fixture, persist it in PostgreSQL, and retrieve deterministic matching excerpts through the same FastAPI boundary used by the CLI. An empty result reports the limits of this fixture. Source-supported is not presented as independently cross-checked.
- [ ] A fresh local Docker Compose run exposes this behavior using documented configuration, with no paid model calls required. The source snapshot and evidence identifiers remain resolvable across restarts.
- [ ] Start with a failing public behavior case. Unit-check exposed provenance/citation rules; integration-check real database persistence and API/CLI passage inspection, including missing evidence and restart. Keep external source retrieval controlled for routine tests.
- [ ] Save the reference artifact, fixture version, actual deterministic baseline outputs and software-test results. Record this as baseline evidence, not as proof of generative-answer quality.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-02.1, AD-02.4 | Runnable deterministic passage baseline and one complete CLI/API/database demonstration. |
| AD-03.1, AD-04.1, AD-04.2 | Reviewed real-source seed with explicit expected, alternative and forbidden results; source and review records. |
| AD-06.1, AD-06.2, AD-10.1 | Failing-to-passing public behavior check, real database integration results and fresh local setup transcript. |

Recheck when: Source fixture, expected facts, evidence identity, public request/response contract or local environment changes.

## Blocked by

None (can start immediately).

