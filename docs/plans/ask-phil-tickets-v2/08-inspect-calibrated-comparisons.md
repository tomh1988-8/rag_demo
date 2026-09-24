# 08: Inspect calibrated quality comparisons

Status: published as [GitHub #9](https://github.com/tomh1988-8/rag_demo/issues/9); fusion/cache scope amendment requested on 23 September 2026. Publication readback is recorded in the manifest. Implementation has not started.

Spec stories: S71, S74, S79, S80, S83, S84, S86, S87, S88, S89, S90, S91, S92, S93, S94, S95, S97, S103, S106, S111, S115, S121, S127, S130.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S71, S74, S79, S80, S83, S84, S86, S87, S88, S89, S90, S91, S92, S93, S94, S95, S97, S103, S106, S111, S115, S121, S127, S130.

## What to build

Extend the baseline already running with the text-answer slice into a useful quality-comparison workflow. An evaluator can run actual conversation cases, inspect independent factual/support/answerability results and see where a calibrated semantic judge disagrees with reviewed labels. Build and validate scoring behavior against known answers, not an abstract evaluation framework.

## Acceptance criteria

- [ ] Maintain linked case artifacts containing evidence, expected facts, allowed alternatives, forbidden assertions, answerability, reviewer/adjudication notes and synthetic provenance. Group repeated events, near-duplicates, paraphrases and derivatives before separating development, judge-calibration, held-out comparison and regression uses.
- [ ] Exercise the public API and record factual correctness, grounding, completeness, relevance, citation support and answerability separately. Check retrieval/context outcomes separately from final-answer quality.
- [ ] Test deterministic scorers on independently reviewed successes, failures and missing-data examples. Never use the candidate output itself as the expected result; missing data and insufficient reference annotations remain explicit.
- [ ] Use LLM judges only for checks whose semantic rubric adds value. Calibrate against reviewed labels; inspect disagreements and false passes, check order/verbosity sensitivity, repeat representative cases and validate rubric changes on labels excluded from judge tuning.
- [ ] Store self-hosted-compatible MLflow artifacts and hashes for datasets/splits, source revisions, prompts, models/settings, context/retrieval configuration, scorer/rubric versions and code revision or available source identity. Associate separate software-test artifacts with the same evaluation.
- [ ] Produce a controlled development-set baseline/candidate comparison with per-case/category failures, sample sizes and variation limits. Distinguish serving from offline evaluation costs. Define the suite cadence and critical gates, and record the procedure for choosing numeric thresholds after baseline measurement but before held-out candidate results are inspected. Keep this development comparison separate from final held-out acceptance.
- [ ] Declare which scorer inputs require reviewed expectations and which checks can assess recorded responses/context alone. Reuse versioned/calibrated checks for later online evaluation; user helpfulness and unverified corrections are human reports, not factual answer keys. Include missing-reference and human/judge-disagreement fixtures, preserving held-out separation.
- [ ] Keep uncached single-query baseline results identifiable. Support versioned fusion/context configurations and stage-level measurements; the later fusion slice supplies the four ablations. Keep deliberate cold/warm cache experiments separate, with isolated run/partition state and no reuse of held-out labels or tuning answers.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-04.3, AD-04.4, AD-09.2 | Grouped split manifests, versioned run artifacts, metric definitions, critical gates and execution cadence. |
| AD-06.4, AD-08.1, AD-08.2 | Independent scorer tests, public API results and human-label/judge calibration with false-pass and sensitivity analysis. |

| ONLINE-02, ONLINE-04 | Versioned online-eligible scorer contracts and reviewed disagreement/missing-reference fixtures for the feedback branch. |
Recheck when: Reference labels/splits, metrics, scorers/judges, prompts/models, source snapshot, evaluation dependencies or acceptance policy.

## Blocked by

- #4 — Handle incomplete evidence and false premises: Real supported, partial, clarification and abstention outputs are needed to validate the scorers and judges.
