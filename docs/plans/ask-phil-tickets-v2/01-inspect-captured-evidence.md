# 01: Inspect captured source evidence locally

Status: completed and closed as [GitHub #2](https://github.com/tomh1988-8/rag_demo/issues/2) on 23 September 2026. Plan version: 2. Native and fresh Docker Compose acceptance passed: 17 tests in each environment, exact reviewed CLI results and evidence preserved through database/API restart. [Implementation evidence](../../implementation/issue-2/README.md). GitHub state and the completed body were read back and verified.

Spec stories: S06, S15, S38, S41, S42, S55, S58, S66, S67, S69, S71, S72, S73, S74, S75, S86, S87. Checklist evidence owner for: AD-02.4, AD-03.1, AD-04.1, AD-04.2, AD-06.1.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S06, S15, S38, S41, S42, S55, S58, S66, S67, S69, S71, S72, S73, S74, S75, S86, S87.

## What to build

A maintainer can load a small, permitted source fixture and ask for matching evidence through the CLI, shared FastAPI application, and PostgreSQL. Return the captured passage and provenance without generating a model answer. This is an evidence-inspection baseline for development, not a fourth production answer route. Establish the smallest complete local environment and independently reviewed seed cases before any model-driven work.

## Acceptance criteria

- [x] Inspect a representative real character passage and record its source/revision, main-series scope, capture date, demonstrated coverage and any gaps. The inspected seed includes an answerable question and a question whose expected evidence is absent; candidate demonstration questions are not accepted as gold without review.
- [x] Record stable case IDs, expected supporting spans/facts, acceptable alternatives, forbidden claims, answerability, reviewer notes and synthetic provenance where applicable. Reference labels are established by checking the source, not by accepting a generated answer.
- [x] Load the captured fixture, persist it in PostgreSQL, and retrieve deterministic matching excerpts through the same FastAPI boundary used by the CLI. An empty result reports the limits of this fixture. Source-supported is not presented as independently cross-checked.
- [x] A fresh local Docker Compose run exposes this behavior using documented configuration, with no paid model calls required. The source snapshot and evidence identifiers remain resolvable across restarts.
- [x] Start with a failing public behavior case. Unit-check exposed provenance/citation rules; integration-check real database persistence and API/CLI passage inspection, including missing evidence and restart. Keep external source retrieval controlled for routine tests.
- [x] Save the reference artifact, fixture version, actual deterministic baseline outputs and software-test results. Record this as baseline evidence, not as proof of generative-answer quality.
- [x] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

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

## Completion evidence — 23 September 2026

All seven acceptance criteria passed. Docker Engine 29.8.1 and Compose 5.5.1 are installed on the Ubuntu 24.04 development host. A fresh `ask-phil-issue2-acceptance` project built successfully, created its own PostgreSQL volume, loaded the reviewed seed and exposed healthy API/database services.

- Native suite: 17 passed. Container suite: 17 passed, no failures or skips; one upstream Starlette deprecation warning.
- Both exact reviewed CLI questions returned their expected evidence IDs. Citation lookup through the published API resolved the original passage and provenance.
- After restarting PostgreSQL and the API, both CLI responses and the citation response were identical. The seed did not run again.
- Standards review: 0 findings. Spec review: 0 findings. Typechecking, lint and installer syntax checks passed.

The application/configuration exercised is local commit `1748866`; 17 code/configuration/test/reference fingerprints, image digests, actual before/after responses, startup output and JUnit results are saved under `docs/implementation/issue-2/`. These are local repository artifacts; this acceptance work does not push commits to GitHub.

No paid model calls were used. This accepts the deterministic evidence-inspection slice only; generative quality, broad corpus coverage and complete-product acceptance remain for their tickets. Issues #3 and #5 can proceed from this completed dependency.
