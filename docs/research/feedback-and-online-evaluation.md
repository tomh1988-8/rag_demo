# User feedback and online evaluation

Research and product amendment: 23 September 2026. The user requires the finished Ask Phil product to collect feedback and use it in online evaluations. This extends the initial local demonstration; hosting remains a later decision.

## Findings from primary documentation

**Attach feedback to the actual interaction.** MLflow supports human assessments on an existing trace, including boolean ratings and comments, and distinguishes human, code and LLM-judge sources. This provides a suitable reporting model for the existing stack. [MLflow feedback collection](https://mlflow.org/docs/latest/genai/tracing/collect-user-feedback)

**Feedback and ground truth have different roles.** MLflow distinguishes assessments of an observed output from expectations defining a desired result. For Ask Phil, a helpfulness vote or proposed correction is a user report; source-checked adjudication is required before it becomes a factual reference. [MLflow expectations](https://mlflow.org/docs/latest/genai/assessments/expectations/)

**Online evaluation assesses served traffic.** LangSmith distinguishes automatic checks on production runs from offline experiments against datasets or historical runs. Its evaluator configuration can target feedback-bearing runs and sample eligible traffic. These are useful conventions, without introducing LangSmith as a project dependency. [Evaluation types](https://docs.langchain.com/langsmith/evaluation-types), [online evaluator filtering and sampling](https://docs.langchain.com/langsmith/online-evaluations-llm-as-judge)

**Check the actual MLflow execution contract.** Current native automatic evaluation is asynchronous and supports sampling, but its documented runner is for LLM judges using AI Gateway. It does not execute custom code scorers; its eligibility/re-evaluation rules do not guarantee processing later feedback, and failed evaluations are not automatically retried. Therefore a checkbox enabling native judges is insufficient evidence that this project's whole feedback loop works. [MLflow automatic evaluation](https://mlflow.org/docs/latest/genai/eval-monitor/automatic-evaluations/)

## Application to Ask Phil

The following are project design choices derived from the requirement and existing architecture, rather than claims that a vendor implements them automatically.

1. Offer optional helpful/not-helpful feedback for a selected response, optional reason categories and a bounded comment or proposed correction. The CLI remains usable without feedback; no account system or Shiny interface is required.
2. Preserve an opaque response identity resolving to the original answer, context/evidence, snapshot, route and model/prompt/application versions. Store feedback revisions and reliable delivery state in PostgreSQL; expose human-origin assessments on the original MLflow trace. Accepting feedback and completing a judge are separate events.
3. Start the evaluation workflow with the normal local stack. Use Prefect to orchestrate durable asynchronous checks and reconciliation, reusing the existing calibrated scorers and MLflow APIs. Native automatic judges may contribute where verified compatible, but they must not be the only path for late feedback or deterministic checks.
4. Every accepted current feedback item updates descriptive metrics and review priority. Evaluate a bounded feedback-directed selection plus a recorded random sample that includes unrated interactions. Assess the original served output; re-running the answer would evaluate a different product event.
5. Keep user satisfaction, reported factual errors, evidence grounding, automated findings and adjudicated correctness separate. Without reviewed references, mark reference-dependent metrics unavailable. Shield generic quality judges from the user's rating to reduce anchoring; feedback-aware triage is a separately named assessment.
6. Define counts and denominators, served-time windows and feedback-as-of cutoffs. Publish coverage, pending/error/budget-skipped counts and feedback-directed versus background samples separately. Because users choose whether to rate, rating proportions are not a census of accuracy; changing traffic or versions also prevents causal improvement claims from a simple trend.
7. Bound online evaluation expense, calls, retries, concurrency and lag independently from serving/offline budgets, while respecting the overall provider limit. Handle duplicate delivery, revisions, unavailable MLflow, worker restart and delayed feedback explicitly. A failed or unattempted score never counts as a pass.
8. Inspect reports and disagreements, record review dispositions, verify suggested factual corrections against sources and promote only adjudicated examples into versioned regression data. Preserve story/duplicate grouping and held-out separation. Do not automatically train models, edit canon, change prompts or switch routes based on raw feedback.
9. Explain data use, minimise identifying data, apply access/redaction/retention controls and treat comments as untrusted input. Evaluation records are not personal conversation memory and do not enter the retrieval corpus.

## Delivery and verification

Add two complete tickets: capture feedback and inspect live signals; then automatically evaluate and review served interactions. Amend response-trace identity, scorer contracts, execution budgets and final acceptance in the existing issues. Preserve the six existing public test boundaries.

Required evidence includes API/CLI behavior, real PostgreSQL/local MLflow integration, deterministic metric/sampling tests, reviewed scorer/judge cases, restart/failure/budget tests and one normal-use demonstration that reaches an online assessment and recorded review disposition. Label staged demonstration interactions as tests; do not present them as organic usage data.

This loop complements the fixed-corpus offline evaluations. Automatic scoring on normal local interactions is mandatory now; cloud monitoring infrastructure, on-call responsibilities and weekly deployed source refresh remain deferred.

