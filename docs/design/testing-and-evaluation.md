# Testing and evaluation strategy

Status: the user has confirmed this strategy and its public test boundaries as part of the complete design. The first deterministic slice now has 17 passing tests in both native and Docker environments, plus recorded baseline outputs; [issue #2 evidence](../implementation/issue-2/README.md) describes the scope and successful restart checks. Generative/component quality evaluation remains future work.

## Development approach

Testing and evaluation are part of each development slice, starting with a small reviewed reference set before the first extraction pilot. The larger benchmark grows as coverage and understanding improve.

1. Define an observable behavior at an agreed public boundary and an independently established expected result.
2. Add the failing deterministic test or reviewed evaluation case that exposes the missing behavior or quality problem.
3. Make the smallest implementation, prompt, schema, or retrieval change that addresses that case.
4. Run the relevant unit and integration tests, component evaluations, and affected end-to-end regressions.
5. Compare with the recorded baseline, inspect failures, and retain useful failure cases as reviewed regressions.

Use one behavior slice at a time. Avoid writing a large speculative test suite before implementing its public behavior. Expected results must not be calculated by reusing the implementation under test or accepted directly from the model being evaluated.

For stochastic components, a passing example is preliminary evidence. Use held-out comparisons and repeated representative cases to establish whether improvements persist. Keep code, model/prompt, schema, retriever, and corpus changes attributable by changing one factor at a time where practical.

## Confirmed public test boundaries

The user has confirmed these boundaries, satisfying the repository's [TDD skill](../../.agents/skills/tdd/SKILL.md) requirement to agree them before writing tests. Define each implementation slice's public contract within these boundaries; test observable results rather than internal methods or collaborator call order. Existing confirmed boundaries do not require renewed approval; a genuinely new boundary should be agreed before tests are added there.

| Boundary | Observable behavior to test |
| --- | --- |
| Source ingestion and refresh | Captured revisions, retained content, main-series filtering, reproducible reruns, usable published snapshots, and explicit failure outcomes. |
| Claim extraction and admission | Structured claims, identities, roles, timing, evidence links, and admission or review outcomes. |
| Text retrieval and typed graph tools | Returned passages, result sets, relationship paths, evidence, coverage limitations, and empty-result behavior. |
| Routing and bounded investigation | Eligible route selection, supported final outcomes, fallback, recorded execution, and enforcement of externally visible limits. |
| Conversation API and CLI | Grounded answers, citations, neutral appendix, partial/abstain/clarify responses, follow-ups, reset, and consistent transport behavior. |
| Evaluation scorers | Correct scoring on independently reviewed examples, including known failures and missing measurements. |

## Software tests

### Unit tests

Use fast deterministic tests for exposed rules such as identity/alias normalization, relation direction, biological-only ancestry, event/date precision, crime versus criminal-justice roles, claim admission decisions, citation formatting, and budget arithmetic. These rules should have meaningful public interfaces before testing them.

Test important invariants and worked examples, including counterexamples. Do not assert private implementation structure, reproduce the same algorithm in the expected value, or turn one generated answer into the reference for itself.

### Integration tests

Exercise real PostgreSQL/pgvector, application interfaces, and ingestion/query orchestration using small controlled fixtures. Cover snapshot publication and revision provenance, idempotent ingestion, claim-to-evidence links, graph queries, API/CLI responses, conversation reset, and observable recovery from failed or interrupted operations.

Use controlled substitutes at external source/model-service boundaries for routine reproducible runs. Prefer a real test database over mocking internal repositories. Separately run budgeted live-provider integration checks; passing a substituted-provider test does not establish model quality or live-provider compatibility.

Evaluate multi-step behavior through public results and recorded external execution. A tool-call limit is a behavioral contract; one exact internal sequence of calls is not generally the only correct implementation.

## Component evaluation matrix

The following are candidate measures selected for this project's failure modes. Choose and document the precise metric variants and reference requirements; not every metric needs to run on every dataset.

| Component | Checks and metrics | Required reference or observation |
| --- | --- | --- |
| Document ingestion/parsing | Retained relevant sections and records, missed or duplicated content, exclusion errors, correct revision and section/span locators. | Saved HTML/JSON fixtures with reviewed content expectations. OCR and PDF-layout scores are added only if such inputs enter scope. |
| Entity, relationship, and event extraction | Schema validity separately from normalized value/identity accuracy; entity/relation/event precision, recall, and F1; role/direction, negation, uncertainty, date-precision, duplicate and invented-record errors. | Reviewed structured annotations and explicit matching rules. Recall claims require sufficiently complete annotation of the evaluated passages. |
| Extraction grounding | Resolvable provenance and whether the supplied evidence actually supports the extracted claim in context. | Source revisions, spans and reviewed support judgments; matching a correct value alone is insufficient. |
| Text retrieval | Recall@k and Hit@k initially; precision@k, MRR, or nDCG where they answer a useful ranking question. | Relevant evidence spans/passages, alternative sufficient evidence sets, and graded judgments when required by the chosen variant. |
| Context assembly | Relevant context, coverage of required facts, sufficiency of combined evidence, and evidence lost through truncation. | Question, actual assembled context, and required answer facts or sufficient evidence sets. |
| Graph retrieval | Correct result sets and relationship meaning, allowed edge types/directions, valid supported paths, evidence coverage, cycle/bound handling, and qualified empty results. | Reviewed graph fixtures, expected outcomes, acceptable paths and underlying edge evidence. |
| Router | Capability eligibility, answer quality attained, missed or unnecessary escalation, and cost/latency compared with other eligible routes. | Known capabilities, acceptable outcomes, actual traces, and comparative runs on a subset. Multiple routes can be valid. |
| Investigator | Task completion, tool/argument validity, evidence acquired, recovery, adherence to limits, and supported partial/abstain outcomes. | Reviewed tasks and outcomes, tool contracts, configured limits, and execution traces. |
| Answer generation | Correctness against reviewed references, required-fact completeness, relevance, groundedness in supplied evidence, and appropriate clarification or abstention. | Expected facts and acceptable alternatives, actual evidence, and answerability labels. |
| Citations | Citation resolution, evidence availability, claim-to-citation support, and coverage of factual claims. | Actual citation mappings/passages and reviewed support labels. |
| Persona and appendix | Factual/uncertainty preservation, separate style quality, respectful handling of serious harm, and exact agreement between the appendix and recorded execution. | Neutral factual expectations, a persona rubric, and actual route/tool/measurement records. |

### Metric interpretation

- Hit@k and MRR can pass after retrieving one useful passage while missing another passage necessary to answer the question. Evaluate sufficient evidence for questions requiring several supporting facts.
- Groundedness or faithfulness concerns support in supplied context; correctness concerns agreement with a reviewed reference. Neither alone establishes that a source account is independently true.
- Schema validity does not establish factual correctness. A valid record that confuses an accused person with the actual perpetrator fails the domain check.
- Citation presence and URL resolution do not establish citation support or coverage.
- Specify normalization, duplicate handling, top-k denominators, relevance labels, and matching tolerances. Metrics with similar names can implement different definitions; record the exact library version and scorer configuration.
- Report results by event/relation type and difficult-case category as well as aggregates. A good average must not conceal systematic parentage, guilt, or citation errors.

These conventions draw on [LlamaIndex retrieval metrics](https://raw.githubusercontent.com/run-llama/llama_index/main/llama-index-core/llama_index/core/evaluation/retrieval/metrics.py), [Ragas faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/), [reference-based factual correctness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/), and [citation evaluation research](https://aclanthology.org/2023.emnlp-main.398/). Extraction measures adapt the separation of values, grounding, and record completeness in [ExtractBench](https://github.com/run-llama/ExtractBench#metrics); its enterprise-document results do not establish performance on this narrative corpus.

## Custom datasets

Create a small reviewed seed set before the first extraction/model-driven slice, then expand it from observed failures, underrepresented event types, and new corpus coverage. No existing dataset has yet been adopted as ground truth.

Maintain distinct but linked datasets for saved source fixtures, extracted-claim annotations, retrieval relevance, graph questions, routing/investigation tasks, and end-to-end conversations. A case may include:

- Stable case ID, purpose/category, question and relevant conversation history.
- Frozen source/corpus revision and evidence spans or structured source records.
- Expected claims, entities and roles; acceptable alternatives; forbidden unsupported assertions.
- Expected answerability, partial-answer requirements, and required ambiguity or conflict handling.
- Relevant or sufficient evidence sets and route eligibility where useful.
- Labels, reviewer/adjudication notes, split, and whether the example is synthetic.

Cover ordinary successes and targeted failures: biological versus step/adoptive relationships, wards versus adopted children, character versus performer, repeated marriages, separation versus divorce, false confession, actual guilt versus conviction, approximate dates, corrected or conflicting accounts, unsupported themes, incomplete graph coverage, and conversational references.

Cross-check reference facts against the agreed trusted-source policy and record the actual checks. Model-generated questions or labels may propose candidates; review them before treating them as gold. Keep synthetic examples marked and evaluate realistic source material separately.

### Splits and reproducibility

- Separate development, judge-calibration, held-out comparison, and regression uses. Keep held-out labels out of prompt/scorer tuning.
- Group repeated story events, near-duplicate passages, paraphrases, and synthetic derivatives across character pages before assigning splits. Record source lineage so the same story does not masquerade as several independent tests.
- Supporting source evidence may remain retrievable for held-out RAG questions. Holding out questions and labels is different from testing unseen-document generalization.
- Freeze dataset artifacts and hashes, split assignments, source snapshots, extraction/normalization rules, prompts, models and settings, retrieval configuration, scorer/rubric versions, and code revision where available.
- Version reference corrections and rerun both baseline and candidate on the same corrected data. Do not silently change labels to make a candidate pass.

[MLflow's dataset guidance](https://mlflow.org/docs/latest/genai/datasets/) supports problem-specific reviewed examples. For the planned self-hosted setup, store explicit frozen artifacts: the current [dataset API](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.genai.html#mlflow.genai.datasets.get_dataset) marks immutable version retrieval as Databricks-only. Grouping and leakage checks are domain-specific applications of [research on overlapping NLP evaluation data](https://aclanthology.org/2021.eacl-main.113/).

## LLM-as-judge evaluations

Use deterministic checks when expectations can be checked directly. Use LLM judges for semantic support, completeness, ambiguity handling, or persona quality where a rubric adds value.

- Give each judge an explicit, narrow rubric, relevant evidence, allowed answer variants, and an uncertainty/adjudication option where appropriate.
- Judge factual support and completeness separately from Phil-like style. Style scores cannot compensate for wrong claims or minimisation of serious harm.
- Calibrate against reviewed human labels. Inspect disagreements and false passes; validate judge changes on labels excluded from judge tuning.
- Record judge model/settings, rubric/prompt version, input evidence, decisions, and concise assessment reasons. A judge score is an estimate with known limitations, not independent proof of canon.
- For pairwise comparisons, vary answer order and inspect order sensitivity. Check verbosity and style sensitivity, and repeat a representative sample to estimate variation.
- Route unresolved or consequential disagreements to review. Low temperature or use of a different model does not guarantee a reliable judge.

See [MLflow scorer development](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/) and [research on LLM-judge strengths and biases](https://arxiv.org/abs/2306.05685).

## End-to-end comparisons and MLflow

Run representative questions and multi-turn conversations through the public application path, assessing the final persona answer and evidence appendix. Include all three routes, routing decisions, partial/abstain/clarify cases, reset, unsupported premises, ambiguous names, and representative limit/failure cases.

- Compare always-text-RAG with the graph-capable, investigative, and routed policies on the same frozen corpus and question set. Keep answer-model settings fixed when isolating retrieval-policy changes.
- On a representative subset, try other eligible routes to identify multiple successful strategies and their quality/cost differences. Route-label accuracy is a diagnostic, not the main objective.
- Use targeted ablations where practical, such as graph access, reranking, escalation, or persona rendering. Report component changes alongside final-answer effects.
- Record per-case results, failure categories, sample sizes, paired changes, appropriate uncertainty estimates, and latency distributions. Repeated runs estimate stochastic variation; they are not additional independent questions.
- Include routing, checking, retries, and investigation in serving measurements. Record online and offline evaluation/judge expenditure separately, and label model cost estimates and missing usage honestly.

Use MLflow for run comparison, artifacts, datasets, traces, and custom offline scorers. Keep ordinary software-test results in the test runner/CI artifacts and associate them with the evaluated revision; MLflow does not replace the unit/integration test runner.

[Custom MLflow scorers](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/custom/) can inspect outputs, expectations, and traces. Built-in [RAG judges](https://mlflow.org/docs/latest/genai/eval-monitor/scorers/llm-judge/rag/) require retrieval spans; sufficiency also needs expected facts. For graph and multi-step routes, supply the actual combined evidence and add custom scorers where a built-in judge does not match the required contract.

## User feedback and online evaluation

Required for the initial local demo. Use the existing conversation API/CLI and evaluation/scorer boundaries, with actual database/MLflow integration and Prefect orchestration; the confirmed six seams are unchanged.

- Keep the existing six public boundaries. Feedback submission is exercised through the conversation API/CLI; background evaluation and its public results use the existing evaluation/scorer and orchestration contracts. No separate service boundary or new design-seam approval is required.
- Before implementing feedback, review cases for helpful/not-helpful/skip, optional comments, invalid or other-session references, duplicate submission, changed rating, reset, delayed trace export and MLflow failure. Verify the original response/trace association, durable receipt, access rules, minimal logging and retention behavior with real PostgreSQL and local MLflow integrations.
- Before enabling automatic evaluation, test the complete normal-use path: serve an answer, submit feedback, process it automatically and inspect its online metrics/assessments and review state. Include delayed feedback after prior scoring, feedback on partial/abstain/clarification outcomes, all three routes and a follow-up/reset interaction.
- Check metric/scorer arithmetic against independent fixtures, including no feedback, zero denominators, duplicate/revised votes, unrated interactions and failed or budget-skipped evaluations. Check sampling/eligibility deterministically in routine tests and show feedback-directed and background samples separately. No score is silently manufactured for missing context or reference labels.
- Integration-test restart/recovery, bounded retries, cancellation/disable, slow or failing judges, unavailable MLflow, redaction and hostile feedback text. Assert actual persisted feedback/jobs/assessments and unchanged served answers, not one internal execution sequence. The app remains usable when evaluation is unavailable.
- Validate online judges against reviewed labels and inspect user/judge disagreements; promote a reviewed live failure into a grouped/versioned regression case without leaking it into an existing held-out split. Record monitoring cadence, reviewer responsibility and pending/unresolved dispositions.
- Run a separately budgeted live local-demo evaluation and report latency to assessment, sample/feedback coverage, measurement gaps and online expense. This complements the fixed-corpus offline baseline; online observational results do not replace held-out acceptance.


### Online metric contract

- Identify the served-interaction cohort and report feedback as of a stated cutoff; distinguish event volume from current per-interaction ratings.
- Show eligible interactions, rated interactions, helpful/not-helpful counts and response coverage. An unrated interaction is not a positive or negative rating.
- Show selected, completed, valid-score, failed, budget-skipped, pending and ineligible counts. Each reported rate names its denominator; zero or missing denominators produce an unavailable result.
- Keep feedback-directed and random-background selections identifiable, record selection probabilities/policy and break down by route/outcome/version only where sample sizes support interpretation.
- Use reference-dependent factual, recall and completeness checks only with reviewed expectations. Raw correction text is not such an expectation. Generic support judges see the original evidence without the rating; feedback-aware triage has a separate labelled rubric.
- Record original answer/context/snapshot identity, feedback revision, evaluation configuration/version, timestamps, lag and online expense. Evaluate preserved served outputs, not a fresh candidate response.
- Demonstrate independent arithmetic cases: six eligible interactions, three current ratings and two positive ratings give feedback coverage 3/6 and rated helpfulness 2/3; neither number establishes factual accuracy. A failed judge is excluded from valid-score averages and included in the failure/coverage report. Retries and revised votes do not increase the count of distinct interactions.
- The project owner/maintainer reviews reports and disagreements, records dispositions and promotes checked examples with grouping/split controls. Measure unresolved report/backlog counts instead of implying every report has been resolved.

The [research review](../research/feedback-and-online-evaluation.md) records MLflow compatibility constraints. Use application-managed orchestration for the full feedback lifecycle rather than assuming native automatic judges process code checks or arbitrary delayed feedback.

## Execution cadence and acceptance

- Run fast deterministic unit/integration tests and relevant fixture-based scorer regressions during normal development.
- During normal local use, automatically process accepted feedback and the configured sample of served traces within the recorded lag/budget policy. Enable this workflow in the acceptance demonstration; disabling it or showing only a manual historical run does not complete the requirement.
- Run budgeted real-model component and end-to-end evaluations when prompts, models, schemas, retrieval/routing policies, or relevant corpus content change, and before accepting a demonstration build.
- Use a wider reviewed holdout periodically and at release checkpoints. Reserve its labels from routine tuning.
- Fix and rerun deterministic contract failures. Require the reviewed demonstration cases to satisfy factual, citation, domain, and expected-answerability checks; inspect and resolve critical failures rather than hiding them in averages.
- Set numerical quality/cost/latency thresholds, k values, dataset sizes, and repeat counts after the initial baseline and before using the held-out comparison to judge a candidate.
- Publish the suite configuration, reviewed coverage, measured results, and known limitations with the portfolio demonstration. Per-answer citations/traces and aggregate evaluation reports serve different purposes; aggregate scores are not per-answer confidence estimates.

The [candidate demo cases](demo-cases.md) seed case design after review. They are a small part of this suite, not the entire evaluation strategy.
