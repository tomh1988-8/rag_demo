# Reusable agent development checklist

Version: 1.1, 23 September 2026. Version 1.0 was approved; this revision adds the ONLINE module to cover the user's explicit feedback and online-evaluation requirement. Apply it through a project profile and evidence register; approval of the checklist does not imply that implementation checks have passed.

Purpose: guide development of LLM applications, workflows, and agents across projects, regardless of language, framework, model provider, or who implements the work. The [research comparison](../research/agent-development-checklists.md) explains the source selection and its limits. This checklist is our synthesis, not a published industry standard.

## How to use it

Create a project profile with its intended release (local demonstration, pilot, or production), enabled capabilities, accountable owner, and applicable checks. Review all ten core areas and select conditional modules when their capabilities exist. Evidence can be a reviewed decision during design and executable results once behavior is implemented.

Revisit affected checks during each working slice. Establish reviewed examples and a baseline early, then grow the suite with failures and new capabilities. Existing valid evidence can be referenced again; a change should trigger the relevant rechecks rather than a complete restart.

Track each applicable item as Pending, In progress, Pass, Fail, Deferred, or N/A. Pass needs evidence for the relevant revision. Deferred needs a reason, owner, and future trigger; N/A needs an applicability reason. A failed requirement for the current release remains blocking. Future deployment work may be deferred for a local demo.

A check records an engineering obligation, not an automatic request for user confirmation. Any action-approval rules come from the project's actual authority requirements. Critical failures stay visible rather than being hidden in an overall percentage.

## AD-01: Define the outcome

- [ ] **AD-01.1** Name the users, their intended outcome, the scope, and the person accountable for acceptance.
- [ ] **AD-01.2** Describe acceptable responses or actions, including clarification, partial success, and inability to complete a task.
- [ ] **AD-01.3** Define quality goals and resource limits; set acceptance thresholds before judging the held-out candidate results.
- [ ] **AD-01.4** Identify important failure consequences, user interaction needs, assumptions, and explicit exclusions.

Evidence: a short outcome brief with worked examples and acceptance measures. Informed by [Géron's problem-framing checklist](https://github.com/ageron/handson-ml3/blob/main/ml-project-checklist.md).

## AD-02: Establish the simplest useful baseline

- [ ] **AD-02.1** Make an appropriate existing/manual, deterministic, or simple LLM solution available as a comparison.
- [ ] **AD-02.2** Explain which decisions need model discretion and which can remain an explicit workflow.
- [ ] **AD-02.3** Compare added complexity against the baseline using task outcomes, latency, and total cost.
- [ ] **AD-02.4** Choose a small first behavior that can work through the complete application and be demonstrated.

Evidence: a baseline run and a brief architectural decision. [Anthropic's agent-design guidance](https://www.anthropic.com/engineering/building-effective-agents) supports choosing complexity according to demonstrated need.

## AD-03: Understand inputs, data, and context

- [ ] **AD-03.1** Inspect representative real tasks and inputs; record difficult cases, missing information, and coverage gaps.
- [ ] **AD-03.2** Identify data sources, permitted uses, sensitivity, access constraints, and relevant freshness requirements.
- [ ] **AD-03.3** Preserve the versions and provenance needed to investigate an answer, action, or evaluation result.
- [ ] **AD-03.4** Check relevant quality issues: duplicates, inconsistent meanings, missing fields, stale material, and unrepresentative samples.

Evidence: input/source inventory, exploratory findings, and reviewed fixtures. See [DC-Check](https://www.vanderschaar-lab.com/dc-check/) and [Microsoft's ML Fundamentals](https://microsoft.github.io/code-with-engineering-playbook/ml-and-ai-projects/ml-fundamentals-checklist/).

## AD-04: Define evaluation cases before expanding behavior

- [ ] **AD-04.1** Prepare a small independently reviewed seed set before model-driven development; expand it with observed failures.
- [ ] **AD-04.2** Record expected outcomes, acceptable alternatives, forbidden results, and the evidence or state that determines correctness.
- [ ] **AD-04.3** Separate development, calibration, held-out, and regression uses; group related or duplicated cases before splitting.
- [ ] **AD-04.4** Specify component and end-to-end measures, critical failure conditions, and when each suite should run.

Evidence: versioned reference cases, split assignments, and an evaluation plan. [Microsoft's checklist](https://microsoft.github.io/code-with-engineering-playbook/ml-and-ai-projects/ml-fundamentals-checklist/) connects available labels and metrics to success criteria; [NeurIPS](https://neurips.cc/public/guides/PaperChecklist) supplies the evidence and reproducibility discipline.

## AD-05: Define model, tool, and state contracts

- [ ] **AD-05.1** Record model/configuration choices and version prompts, output contracts, and context-construction rules.
- [ ] **AD-05.2** Give each tool clear input, output, failure, and side-effect semantics; validate arguments and results.
- [ ] **AD-05.3** Specify context limits, conversation state, reset behavior, and any memory lifetime or isolation requirements.
- [ ] **AD-05.4** Make routing, fallback, escalation, and stopping behavior observable through the public application contract.

Evidence: compact interface descriptions and worked success/failure examples. Tool-contract checks draw on [Anthropic's tool-design guidance](https://www.anthropic.com/engineering/writing-tools-for-agents); the other checks specify the application's own configuration and state contracts.

## AD-06: Build and test a working slice

- [ ] **AD-06.1** Add a failing behavioral test or reviewed evaluation case, then implement the smallest useful complete behavior.
- [ ] **AD-06.2** Test exposed rules and real integrations, using controlled substitutes at external-service boundaries when reproducibility requires them.
- [ ] **AD-06.3** Include counterexamples and meaningful input variations; assert outcomes at public boundaries rather than private implementation structure.
- [ ] **AD-06.4** Exercise the complete user path and relevant component evaluations, including failures; validate scoring code against independent expectations.

Evidence: runnable unit/integration tests, component and end-to-end cases, and a demonstration. [CheckList](https://aclanthology.org/2020.acl-main.442/) informs behavioral variations; [ML Test Score](https://storage.googleapis.com/gweb-research2023-media/pubtools/4156.pdf) complements ordinary software tests with ML-specific checks.

## AD-07: Enforce authority and execution limits

- [ ] **AD-07.1** Restrict available tools, resources, and data to the task's authority; enforce boundaries outside model instructions.
- [ ] **AD-07.2** Exercise relevant cases where retrieved content or tool output contains misleading instructions or malformed data.
- [ ] **AD-07.3** Protect credentials and sensitive context in model requests, tool calls, storage, and logs as applicable.
- [ ] **AD-07.4** Enforce finite call/time/spending limits, bounded retries, cancellation, and explicit failure or handoff outcomes.

Evidence: executable boundary and limit checks for the enabled capabilities. [OWASP's agent guidance](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) supplies relevant scope and input-boundary considerations.

## AD-08: Evaluate improvements and inspect failures

- [ ] **AD-08.1** Assess component behavior and final task outcomes separately, including actual external state when actions change it.
- [ ] **AD-08.2** Use deterministic graders where suitable; when using semantic LLM judges, calibrate against reviewed labels and inspect disagreements.
- [ ] **AD-08.3** Compare baseline and candidate on controlled versions/settings; report quality, latency, and cost separately.
- [ ] **AD-08.4** Review failures by meaningful category, estimate variation where needed, and resolve critical failures before acceptance.

Evidence: a comparison report with per-case results and scorer configuration. [Anthropic's agent-evaluation guide](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) informs outcome grading and judge selection; [Microsoft's production checklist](https://microsoft.github.io/code-with-engineering-playbook/ml-and-ai-projects/ml-model-checklist/) informs baseline and resource trade-offs.

## AD-09: Make execution inspectable and reproducible

- [ ] **AD-09.1** Record observable inputs, outputs, context, tool results, routes, errors, and stop reasons with appropriate redaction.
- [ ] **AD-09.2** Link runs to code, data, prompts, models, tool contracts, configuration, and scorer versions.
- [ ] **AD-09.3** Measure complete-request latency and cost, including retries/routing; distinguish offline evaluation expenditure and missing measurements.
- [ ] **AD-09.4** Provide a repeatable run procedure; describe provider variability and other limits to exact reproduction.

Evidence: linked traces, run metadata, artifacts, and reproduction instructions. [NeurIPS](https://neurips.cc/public/guides/PaperChecklist) informs reproducibility reporting; [AWS's MLOps components](https://docs.aws.amazon.com/prescriptive-guidance/latest/mlops-checklist/mlops-checklist-components.html) cover observability and experiment management.

## AD-10: Release, monitor, and improve at the intended scale

- [ ] **AD-10.1** Demonstrate reproducible setup and execution in the intended environment with documented configuration and limits.
- [ ] **AD-10.2** Apply the release's acceptance checks and define recovery from changed code, prompts, data, or stored state.
- [ ] **AD-10.3** For a deployed service, assign monitoring, response, refresh, and retirement responsibilities with appropriate operating checks.
- [ ] **AD-10.4** Record known limitations and turn reviewed user failures into improvements and regressions; re-evaluate relevant dependency changes.

Evidence: release record, run/recovery instructions, and an operating plan proportionate to the target. See [ML Test Score](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/), [Microsoft's production checklist](https://microsoft.github.io/code-with-engineering-playbook/ml-and-ai-projects/ml-model-checklist/), and [AWS's MLOps guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/mlops-checklist/introduction.html).

## Conditional modules

Select these by actual capability. They do not imply that every application needs retrieval, extraction, persistent memory, multiple agents, or model training.

### RAG: External knowledge or structured retrieval

- [ ] **RAG-01** Check source scope, freshness, coverage, provenance, and applicable access restrictions.
- [ ] **RAG-02** Measure retrieval coverage/ranking and assembled-context sufficiency using explicit relevance expectations and metric definitions.
- [ ] **RAG-03** Check answer correctness, source support, citation coverage, and behavior on missing or conflicting evidence separately.
- [ ] **RAG-04** For graph/structured retrieval, validate identities, relationship meanings, allowed paths/results, and evidence behind derived answers.

Evidence: reviewed retrieval and answer cases with their actual context. [LlamaIndex's evaluation documentation](https://developers.llamaindex.ai/python/framework/module_guides/evaluating/) supports evaluating retrieval and responses separately; structured-query checks extend that principle to the application's own semantics.

### EXT: Document or structured-claim extraction

- [ ] **EXT-01** Measure retained source content separately from extracted semantic values; add layout/OCR measures only for relevant inputs.
- [ ] **EXT-02** Check normalized values, entities, roles, dates, duplicates, and missing/invented records separately from schema validity.
- [ ] **EXT-03** Require resolvable evidence for extracted claims; measure value correctness and grounding separately.
- [ ] **EXT-04** Define annotation/matching rules, admission/review outcomes, and uncertainty handling; report precision/recall/F1 only where references support them.

Evidence: reviewed documents, annotations, matching rules, and component results. [ExtractBench](https://github.com/run-llama/ExtractBench#metrics) provides a useful value/grounding distinction; these checks adapt it to the project's input types.

### ACT: Actions that change external state

- [ ] **ACT-01** Define preauthorised actions and any consequential actions requiring specific confirmation; enforce the configured authority.
- [ ] **ACT-02** Test retries, duplicate requests, partial completion, and recovery so the same action is not unintentionally repeated.
- [ ] **ACT-03** Verify actual resulting state and report incomplete actions accurately.

Evidence: action-contract and recovery tests, informed by [OWASP's action-integrity guidance](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html).

### MEM: Persistent memory

- [ ] **MEM-01** Define what may persist, its provenance, lifetime, and user/session isolation.
- [ ] **MEM-02** Test correction, deletion, expiration, and conflicting or untrusted memories.
- [ ] **MEM-03** Compare usefulness and factual reliability with memory disabled on representative tasks.

Evidence: memory behavior cases and a comparison run. Isolation considerations draw on [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html); the comparison is a proposed application of the baseline principle.

### MULTI: Multiple cooperating agents

- [ ] **MULTI-01** Define role, handoff, authority, and shared-state contracts.
- [ ] **MULTI-02** Check coordination failures, cancellation, and total limits across all workers.
- [ ] **MULTI-03** Compare final quality and expense against the simpler system on equivalent tasks.

Evidence: handoff/failure cases and comparison runs. [Anthropic's multi-agent research-system account](https://www.anthropic.com/engineering/built-multi-agent-research-system) illustrates coordination and resource trade-offs; the checks remain application-specific.

### TUNE: Model training or fine-tuning

- [ ] **TUNE-01** Review training data suitability, permitted use, lineage, and separation from evaluation labels.
- [ ] **TUNE-02** Record the reproducible training configuration and evaluate important task/data categories against the existing model.
- [ ] **TUNE-03** Retain compatible artifacts and a recovery path; measure training expense separately from serving.

Evidence: data review, training record, and model comparison. Applicable background: [Géron's checklist](https://github.com/ageron/handson-ml3/blob/main/ml-project-checklist.md) and [DC-Check](https://www.vanderschaar-lab.com/dc-check/).

### ONLINE: User feedback and evaluation during normal use

Apply when users interact with a running product and their feedback or served interactions are used for ongoing quality evaluation. This includes an interactive local demo; cloud hosting is not a prerequisite.

- [ ] **ONLINE-01** Capture optional feedback against the exact served interaction with source attribution, receipt/revision semantics, appropriate access and data handling; distinguish user reports from verified expectations.
- [ ] **ONLINE-02** Automatically use feedback and actual served traces in asynchronous evaluation, combining recorded feedback-directed and background sampling; handle delayed feedback without replacing the original output.
- [ ] **ONLINE-03** Define eligible inputs, metric denominators, version/cohort lineage, missing/failed/skipped states, processing lag and bounded evaluation expense separately from serving and offline work.
- [ ] **ONLINE-04** Review feedback and evaluator disagreements, record dispositions and promote only checked examples into regression/reference data with leakage controls; raw feedback must not autonomously change application behavior.

Evidence: a normal-use interaction-to-feedback-to-assessment demonstration, reliable delivery/failure tests, interpretable online reports and a reviewed improvement/regression record. The [feedback and online-evaluation review](../research/feedback-and-online-evaluation.md) documents primary sources and the distinction from offline acceptance.

## Evidence register and future ticket structure

Use one shared register so decisions and results can be referenced rather than copied into every ticket.

| Check ID | Applicability / release | Status | Evidence and revision | Owner | Recheck trigger |
| --- | --- | --- | --- | --- | --- |
| Selected item | Current / later / N/A, with reason | Pending / In progress / Pass / Fail / Deferred / N/A | Decision, test, dataset, trace, or report | Responsible person or role | Relevant change or milestone |

Each ticket should state its user-visible outcome, applicable checklist IDs, evidence needed for completion, genuine blockers, and any justified deferrals. Checklist sections can group the backlog; several checks can be satisfied by one working slice. Project-level decisions can be inherited until changed.

For each slice, identify affected checks, add or update reference cases, implement the behavior, run the appropriate checks, and record the result. Keep capability exploration, routine regressions, and held-out acceptance comparisons distinguishable.

The checklist is agreed for reuse. Applying it to a project preserves that project's agreed domain decisions, technology choices, test boundaries, and deployment scope unless a separate change is explicitly agreed.
