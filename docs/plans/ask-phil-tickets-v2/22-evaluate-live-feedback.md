# 22: Evaluate live answers with feedback and close the review loop

Status: published as [GitHub #23](https://github.com/tomh1988-8/rag_demo/issues/23); fusion/cache scope amendment requested on 23 September 2026. Publication readback is recorded in the manifest. Implementation has not started.

Spec stories: S103, S104, S105, S106, S107, S108, S109, S110, S111, S112, S113, S114, S115, S116, S126, S127.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S103, S104, S105, S106, S107, S108, S109, S110, S111, S112, S113, S114, S115, S116, S126, S127.

## What to build

Normal local Ask Phil use automatically turns feedback and a configured sample of served interactions into online quality assessments and a reviewable report. A maintainer inspects a reported problem against the original evidence, records a disposition and promotes a checked failure into the regression suite. Keep this distinct from manually rerunning historical questions or treating a vote as factual truth.

## Acceptance criteria

- [ ] Start a durable asynchronous workflow with the local stack using the existing Prefect orchestration and self-hosted-compatible MLflow APIs. New served traces and feedback events/revisions lead to the appropriate work within a configured processing window; judging does not block chat or the feedback receipt. Assess the preserved answer/context/snapshot, without re-running the agent.
- [ ] Use every accepted current feedback item in descriptive metrics/triage. Prioritise reported factual/evidence/harm problems in a bounded feedback-directed evaluation sample, plus a recorded random background sample of eligible interactions including those without ratings. Preserve selection reasons/rates and keep these cohorts identifiable.
- [ ] Apply validated code checks and calibrated semantic judges only where their input contracts are satisfied. Keep user helpfulness, reported errors, automated evidence/support/persona findings and adjudicated correctness separate. No reviewed expectations means reference-based correctness/recall/completeness is unavailable. Generic quality judges do not see the vote; feedback-aware triage uses a separately named rubric.
- [ ] Handle delayed feedback after an earlier score, revised votes, duplicate delivery, missing traces and restart without duplicate active counts or unintended repeated model charges. Track feedback/evaluator/configuration revisions and assessment provenance separately. Test the selected MLflow version; do not assume native automatic judges run code scorers, retry failures or revisit arbitrary late feedback.
- [ ] Enforce configured call/time/spend/concurrency/retry bounds and a disable control. Persist and inspect pending, completed, failed, ineligible and budget-skipped states plus backlog age/assessment lag. Separate online judge expense from serving and offline evaluation, respecting the overall provider cap and reporting missing usage honestly.
- [ ] Provide a maintainer report with eligible/rated/selected/scored counts and explicit denominators, positive/negative feedback, category/outcome/route/version slices where counts allow, sample coverage and failures/lag/cost. Define served-time windows and feedback-as-of cutoffs; self-selected ratings are not unbiased accuracy and observed trends are not causal proof.
- [ ] Review each report with a category/comment and a documented sample of remaining ratings; inspect user/judge disagreement and record unresolved, confirmed, rejected or other explicit dispositions with evidence. Verify suggested corrections against trusted sources before promoting a case; do not automatically change canon, prompts, routing or weights.
- [ ] Promote a checked live failure into versioned regression/reference data with original interaction/evidence lineage, independent expected facts, reviewer notes, story/duplicate grouping and held-out contamination checks. Re-evaluate a fix using the established offline process; do not make held-out labels available to tuning.
- [ ] Start with independently reviewed workflow/scorer cases and test real PostgreSQL/local MLflow/Prefect through the public conversation/evaluation boundaries. Include late feedback, unrated sampling, revised/duplicate events, zero denominators, missing references/context, outage/recovery, disabled/failed/limited judges, redaction and hostile comments. Demonstrate normal interaction-to-feedback-to-automatic-assessment-to-review on a budgeted live local run, labelled as demo/test traffic.
- [ ] Update the checklist evidence register with revision-linked results, failures and limitations. Required runtime evidence remains Pending until demonstrated.

- [ ] Keep served-interaction identity distinct from shared generation lineage so the later cache slice can evaluate cached deliveries against original context. Cache integration and hit/fresh-generation cohort checks belong to that slice; repeated reuse must not become independent factual examples or duplicate original model cost.

## Checklist evidence

The ticket implementer owns runtime evidence; the project owner/maintainer owns quality review and acceptance. Preserve the six confirmed public test boundaries.

| Checks | Evidence required for completion |
| --- | --- |
| ONLINE-02, ONLINE-03 | Actual automatic workflow, delayed-feedback reconciliation, bounded execution and versioned sampled reports with denominators and missing/failure states. |
| ONLINE-04, AD-08.2, AD-10.4 | User/judge disagreement review and recorded dispositions, calibrated online checks and source-checked regression promotion with split controls. |
| AD-06.4, AD-09.2, AD-09.3 | Independent metric/scorer tests, real public-path integration, lineage/lag reports and separate serving/online/offline expense. |

Recheck when: Feedback/selection policy, metric denominators, scorer/judge versions, workflow/MLflow behavior, budgets, redaction, source/reference corrections or release scope.

## Blocked by

- #22 — Real submitted feedback, original response linkage and live summaries must exist before online scoring and review can use them.
- #9 — Validated scorer/judge contracts and calibration must exist before automatically evaluating normal-use interactions.
