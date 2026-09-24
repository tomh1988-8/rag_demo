# Ask Phil: checklist profile and evidence register

Profile version: 1.1, 23 September 2026. Applies [reusable checklist v1.1](agent-development.md) to the [agreed Ask Phil specification](../specs/ask-phil.md). The user approved [ticket breakdown v2](../plans/ask-phil-tickets-v2/README.md) on 23 September 2026. The user subsequently required feedback collection and online evaluation; this scope amendment is integrated into the current release. The deterministic inspection and initial text-RAG slices have runtime evidence; later product capabilities remain pending.

## Release, capabilities and owners

**Intended release:** the complete local portfolio demonstration: all 20 core characters, three actual RAG routes, automatic routing and visible overrides, factual Phil persona, evidence appendix, grounded follow-ups/reset, reproducible refresh, optional response feedback, automatic online evaluation and a unit/integration/component/end-to-end evaluation workflow. A text-only intermediate slice is not completion.

**Capabilities:** captured HTML/JSON source ingestion; claim extraction/admission/review; biological and other typed SQL-backed graph queries; text/graph retrieval; one bounded investigator; a session-based CLI through FastAPI; durable feedback capture and asynchronous evaluation of actual served interactions. Use the agreed Python, LlamaIndex, PostgreSQL/pgvector, Prefect, MLflow and Docker Compose stack.

**Accountable acceptance owner:** the project owner (Tom). **Evidence owner:** the implementer of the primary ticket below; actual dataset/reference reviewers and adjudication notes are recorded with the cases. **Current feedback/evaluation review owner:** the project owner/maintainer; ticket implementers supply evidence and the online workflow exposes report/disagreement dispositions, cadence and backlog. **Future operational owner:** the project owner assigns deployment responsibilities when hosting enters scope. “Owner” here assigns responsibility for evidence; it does not reopen settled design decisions or create extra permission requirements.

Preserve the six confirmed public test boundaries and all accepted ADRs. R Shiny, Azure/Posit Connect deployment, a dedicated graph database, persistent personal memory, agent write tools, multiple cooperating agents and model training are not introduced by this checklist mapping.

## Applicability and current state

| Classification | Count | Meaning |
| --- | --- | --- |
| Current | 51 | 39 core checks plus four RAG, four extraction and four ONLINE checks |
| Deferred | 1 | AD-10.3: deployed operations, including weekly refresh |
| N/A | 12 | ACT, MEM, MULTI and TUNE modules for this release |
| Total reviewed | 64 | Every checklist item has an applicability decision |

Of the 51 current checks, **13 Pass**: three on design evidence, five for the deterministic inspection slice, and five for the initial text-RAG slice (AD-02.1, AD-05.1, AD-06.2, AD-09.1, RAG-02). **38 remain Pending**. The [issue #2 evidence](../implementation/issue-2/README.md) and [issue #3 evidence](../implementation/issue-3/README.md) record scoped results. Issue #3 has 32 passing Docker tests, real local-model traces, independent retrieval/context labels, and a versioned development smoke baseline. These results do not establish broad model quality, corpus coverage or complete-product acceptance. The local model must be replaced before serious evaluation or deployment.

Design Pass records below concern the approved design, including the user's feedback/online-evaluation and fusion/cache amendments, captured by specification SHA-256 `a82e93bd170be20c253415606fcb9a6ab082f7a9a7c991d56ca5e757ca728c53`. Runtime Pass records link to the exact scoped slice artifacts below; other runtime evidence remains prospective. On implementation, add artifact/run links and source/code/configuration identities before changing a check to Pass. Update affected checks to Pending, In progress or Fail when their evidence is invalidated. A current-release failure cannot be turned into a deployment deferral merely to complete a ticket.

Primary ownership is an index into a continuing evidence obligation, not a licence to postpone all work to that ticket. For example, caps and basic traces start in 02, stronger failure enforcement is proved in 09, and every tool extension rechecks the affected constraints. Source claims are reviewed before their extraction pilot. Per-slice tests and evaluations start in 01/02; final acceptance in 20 reuses their results.

## Current evidence register

All rows apply to the current local release. Runtime evidence owners are ticket implementers, with the project owner accountable for design scope and acceptance thresholds.

| Check | Status | Primary ticket | Existing or required evidence | Recheck trigger |
| --- | --- | --- | --- | --- |
| AD-01.1 | Pass | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) / project owner | [Spec: problem and scope](../specs/ask-phil.md#problem-statement) and this profile's owner assignment; design evidence only. Agreed spec names viewers, demonstrators and maintainers; this profile names the project owner as acceptance owner. | Users, release scope or accountable owner changes. |
| AD-01.2 | Pass | [03](../plans/ask-phil-tickets-v2/03-handle-incomplete-evidence.md) / project owner | [Spec: conversation and evidence contracts](../specs/ask-phil.md#conversation-and-evidence-contracts); design evidence only. Agreed response contract describes supported, clarification, partial and abstention outcomes; runtime verification belongs to ticket 03. | Response outcome policy or user interaction changes. |
| AD-01.3 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) / project owner | Setup caps, measured baseline and quality/latency/cost thresholds recorded before held-out candidate inspection. | Limits, release criteria, baseline or acceptance dataset changes. |
| AD-01.4 | Pass | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) / project owner | [Spec: testing decisions](../specs/ask-phil.md#testing-decisions) and [exclusions](../specs/ask-phil.md#out-of-scope); design evidence only. Agreed spec records factual/guilt/biological/citation failures, CLI interaction and explicit exclusions. | Important failure consequences, assumptions or exclusions change. |
| AD-02.1 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Deterministic baseline](../implementation/issue-2/baseline.json) and [single-query uncached text baseline](../implementation/issue-3/text-baseline-v4.json), pinned to snapshot, package, model, prompt and application identities. Pass covers the exposed seed only; future fusion/route comparisons must retain this baseline. | Source snapshot, answer model or comparison task changes. |
| AD-02.2 | Pending | [17](../plans/ask-phil-tickets-v2/17-route-and-escalate.md) | Implemented eligibility/workflow rules and documented scope of model discretion in investigation/routing. | Tool capabilities, routing policy or model responsibilities change. |
| AD-02.3 | Pending | [17](../plans/ask-phil-tickets-v2/17-route-and-escalate.md) | Same-corpus baseline/candidate and eligible-route comparisons with quality, full latency and cost. | Any added route, model, retrieval or orchestration complexity. |
| AD-02.4 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [Issue #2 acceptance evidence](../implementation/issue-2/README.md): complete captured-passage inspection through real CLI/HTTP, FastAPI and PostgreSQL; stable evidence survives reimport/application recreation and an actual database restart. Fresh Docker startup and database/API restart also passed; AD-10.1 remains Pending for the complete product. | First-slice scope or public contract changes. |
| AD-03.1 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [Real-source seed and gaps](../../data/seed/README.md), with source-reviewed answerable and absent-evidence cases. Pass covers initial inspected input; expand and recheck for the new sources/categories/roster in 06 and 19. | New task category, source type or roster expansion. |
| AD-03.2 | Pending | [04](../plans/ask-phil-tickets-v2/04-import-real-sources.md) | Source roles, permitted uses, attribution/access constraints, sensitivity and freshness inventory. | Source, access/usage rules or captured-data scope changes. |
| AD-03.3 | Pending | [05](../plans/ask-phil-tickets-v2/05-refresh-and-recover-snapshot.md) | Resolvable source/snapshot/revision evidence and compatible refresh manifests; graph extension in 14. | Capture/publication/projection or evidence identity changes. |
| AD-03.4 | Pending | [06](../plans/ask-phil-tickets-v2/06-cover-core-text-profiles.md) | Per-profile missing, stale, duplicate and conflicting-content checks; semantic expansion in 19. | Source refresh, roster, parsing or normalization changes. |
| AD-04.1 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [Reviewed seed](../../data/references/phil-arrival-v1.json) established from source inspection before model work, independently checked by the Spec review agent. New behavior/graph labels must be reviewed before their pilots; no human or independent-canon verification claimed. | New behavior, corpus category or reviewed failure. |
| AD-04.2 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [Frozen development cases](../../data/references/phil-arrival-v1.json) record stable IDs, source/span expectations, acceptable alternatives, forbidden assertions, answerability, grouping, synthetic provenance and actual review notes. | Reference correction, evidence revision or new outcome. |
| AD-04.3 | Pending | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | Versioned event/near-duplicate groups and separate development, calibration, held-out and regression manifests. | New cases, source overlap, synthetic derivatives or split changes. |
| AD-04.4 | Pending | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | Metric definitions, component/e2e separation, critical gates and routine/offline/online execution cadence with declared reference requirements. | Capability, metric, failure category or acceptance policy changes. |
| AD-05.1 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Issue #3 configuration and bounds](../implementation/issue-3/README.md#bounds-and-truthful-measurements): pinned model digests/settings, versioned prompt/schema, whole-span context and per-call bounds. Zero local API charge excludes hardware/hosting; paid-provider controls and a new baseline precede migration. | Prompt, model, context construction or output contract changes. |
| AD-05.2 | Pending | [10](../plans/ask-phil-tickets-v2/10-answer-biological-family.md) | Typed tool input/output/failure/side-effect contracts and validation; extended in 15 and 16. | Any new or changed tool or graph capability. |
| AD-05.3 | Pending | [07](../plans/ask-phil-tickets-v2/07-ground-followups-and-reset.md) | Finite context, isolated session lifetime and reset/misleading-history results. | Conversation persistence, truncation or reference resolution changes. |
| AD-05.4 | Pending | [17](../plans/ask-phil-tickets-v2/17-route-and-escalate.md) | Actual eligible-route, fallback, escalation and stop records through the API/CLI. | Routing/evidence policy, limits or tool availability changes. |
| AD-06.1 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [TDD record and actual results](../implementation/issue-2/README.md): failing public provenance, API, CLI and citation-resolution cases followed by minimal working changes. Reopen/extend this evidence for each later behavior change. | Every behavior change. |
| AD-06.2 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Issue #3 tests and acceptance](../implementation/issue-3/validation.json): 32 passing Docker tests, exposed context/citation/scorer rules, real PostgreSQL/pgvector, API/CLI and MLflow, with external-model HTTP substitutes only. Separate actual local-model baseline and restart checks complement them; extend for every later integration. | Affected rule, integration, dependency or provider contract changes. |
| AD-06.3 | Pending | [03](../plans/ask-phil-tickets-v2/03-handle-incomplete-evidence.md) | Public counterexamples and meaningful variations, including unsupported negatives and false premises. | New failure mode or changed public behavior. |
| AD-06.4 | Pending | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | Independent scorer tests plus full-path and component results; expanded conversations and routes by their tickets. | Scorer, public capability or failure behavior changes. |
| AD-07.1 | Pending | [09](../plans/ask-phil-tickets-v2/09-enforce-execution-boundaries.md) | Programmatic read-only answering capabilities and permitted resources, extended to all tools in 16. | New tool/resource, privileges or agent-triggered action. |
| AD-07.2 | Pending | [09](../plans/ask-phil-tickets-v2/09-enforce-execution-boundaries.md) | Retrieved-instruction and malformed-tool-output cases with observed enforced boundaries. | New source/tool format, validation or model context policy. |
| AD-07.3 | Pending | [09](../plans/ask-phil-tickets-v2/09-enforce-execution-boundaries.md) | Credential/context handling and redacted request, tool, error and trace examples. | Credential, logging, tracing or sensitive context handling changes. |
| AD-07.4 | Pending | [09](../plans/ask-phil-tickets-v2/09-enforce-execution-boundaries.md) | Finite call/time/spend/context limits, retries, cancellation and partial failure outcomes; global extension in 16. | Budget accounting, provider, retry or cancellation policy changes. |
| AD-08.1 | Pending | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | Separate component/final outcomes; storage-state verification for ingestion/review in 05 and 14. | Component, task success definition or persistent-state behavior changes. |
| AD-08.2 | Pending | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | Known-outcome scorer tests and reviewed judge calibration, false passes, sensitivity and variation. | Judge/model/rubric, scorers or reference label changes. |
| AD-08.3 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Frozen baseline/candidate settings, paired route comparisons and ablations with quality/latency/cost separated. | Candidate configuration, dataset, snapshot or comparison protocol changes. |
| AD-08.4 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Category failures, sample/variation reporting and explicit resolution of critical failures. | New release candidate or critical failure. |
| AD-09.1 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Actual local-model baseline traces](../implementation/issue-3/text-baseline-v4.json) and [serving trace](../implementation/issue-3/docker-serving-trace.json): actual retrieval, assembled context, model usage, versioned original response and resolvable citations. Read tokens are excluded. Pass is scoped to text RAG; later tools extend it. | Trace/evidence construction, tool or error handling changes. |
| AD-09.2 | Pending | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | Run-to-code/data/source/prompt/model/tool/config/scorer lineage and self-hosted-compatible artifacts. | Any recorded execution or evaluation dependency changes. |
| AD-09.3 | Pending | [17](../plans/ask-phil-tickets-v2/17-route-and-escalate.md) | [Issue #3](../implementation/issue-3/README.md) records serving/offline separation, available/null usage, scoped application latency and complete client-observed CLI latency. Full routing/retry and online expense remain Pending; ONLINE-03 owns live evaluation accounting. | Routing, retry, provider/pricing or measurement changes. |
| AD-09.4 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Repeatable local evaluation/demo procedure and documented provider variability limits. | Runtime, dependency, provider or evaluation procedure changes. |
| AD-10.1 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Fresh Docker Compose startup, configuration/limits and complete local workflow demonstration. First-slice Docker startup and restart passed; acceptance evidence is in [issue #2](../implementation/issue-2/README.md); later-slice/full-release requirements remain open. | Setup/runtime/dependency or intended environment changes. |
| AD-10.2 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Release gates plus verified compatible code/prompt/data recovery, building on 05 and 14. | Release candidate, snapshot/schema, prompt or recovery changes. |
| AD-10.4 | Pending | [22](../plans/ask-phil-tickets-v2/22-evaluate-live-feedback.md) | Actual feedback/disagreement dispositions and checked regression promotion, with known limitations and dependency re-evaluation verified again in final acceptance. | User feedback, observed failure, dependency or corpus change. |
| RAG-01 | Pending | [06](../plans/ask-phil-tickets-v2/06-cover-core-text-profiles.md) | Source roles, scope, freshness and 20-profile coverage/access inventory; checked graph coverage in 19. | New sources, snapshot, roster, canon or access constraints. |
| RAG-02 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Independent passage/fact labels](../../data/references/phil-arrival-rag-v1.json), tested scorer arithmetic, and [actual results](../implementation/issue-3/text-baseline-v4.json) define k, matching, denominators and sufficient sets. Negative-case retrieval metrics remain null and context is insufficient. One passage cannot demonstrate rank discrimination; later corpus/routes/fusion recheck this obligation. | Retrieval/context policy, embeddings, corpus or task distribution changes. |
| RAG-03 | Pending | [03](../plans/ask-phil-tickets-v2/03-handle-incomplete-evidence.md) | Separate correctness/grounding/citation/answerability results for missing, conflicting and supported evidence. | Answer prompt/model, evidence, corpus conflicts or output policy changes. |
| RAG-04 | Pending | [15](../plans/ask-phil-tickets-v2/15-trace-character-connections.md) | Reviewed identities, meanings, allowable paths and derived-answer evidence for four graph families. | Graph relations/roles, path logic, claims or provenance changes. |
| EXT-01 | Pending | [04](../plans/ask-phil-tickets-v2/04-import-real-sources.md) | HTML/JSON retained-content, missing/duplicate and provenance measures separate from semantic extraction. | Source format/filter/parser or proposed PDF/OCR inputs change. |
| EXT-02 | Pending | [10](../plans/ask-phil-tickets-v2/10-answer-biological-family.md) | Normalized entity/value/role/direction/date checks separate from validity; expanded by 11–13 and 19. | Schema, extraction/model, taxonomy, normalization or source changes. |
| EXT-03 | Pending | [10](../plans/ask-phil-tickets-v2/10-answer-biological-family.md) | Resolvable claim-to-span evidence and independent value-accuracy versus grounding results. | Evidence mapping, extracted claims, source revisions or scorer changes. |
| EXT-04 | Pending | [14](../plans/ask-phil-tickets-v2/14-review-corrections-and-disputes.md) | Annotation/matching, uncertainty/admission/review guide; PRF restricted to sufficiently annotated material. | Annotation policy, review criteria, category or reference completeness changes. |
| ONLINE-01 | Pending | [21](../plans/ask-phil-tickets-v2/21-capture-response-feedback.md) | Optional CLI/API feedback, durable receipt/revisions, original response/trace identity and real storage/MLflow access/retention results. | Feedback/session/response contract, storage/export, privacy or retention changes. |
| ONLINE-02 | Pending | [22](../plans/ask-phil-tickets-v2/22-evaluate-live-feedback.md) | Automatic normal-use evaluation using preserved outputs, feedback-directed and background samples, late/revised-feedback reconciliation. | Sampling/eligibility, evaluator input, orchestration or trace/feedback lifecycle changes. |
| ONLINE-03 | Pending | [22](../plans/ask-phil-tickets-v2/22-evaluate-live-feedback.md) | Versioned live report with explicit counts/denominators, missing/failure/lag states and bounded online expense. | Metric/cohort definitions, evaluator versions, retry/budget policy or measurement changes. |
| ONLINE-04 | Pending | [22](../plans/ask-phil-tickets-v2/22-evaluate-live-feedback.md) | Evidence-based report/disagreement dispositions and a checked case promoted with story-group/split controls. | Review/source policy, reference correction, regression or held-out group changes. |

## Deferred work

| Check | Status | Reason and current substitute | Owner | Trigger and required evidence |
| --- | --- | --- | --- | --- |
| AD-10.3 | Deferred | No deployed service in this release. Manual refresh, local recovery/limits and the feedback/online workflow are current obligations. Only hosted-service operating responsibilities are deferred. | Project owner | Before a hosted pilot on Azure, Posit Connect or another target: assign monitoring, incident/response, weekly refresh, recovery and retirement responsibilities; implement and check them for that environment. |

This is the deployed portion of spec story 65, not a deferral of local refresh or online evaluation. ONLINE-01–04 are required now even before hosting. Choosing a hosting provider is still open.

## Not applicable to this release

| Check | Status | Applicability reason | Owner and reconsideration trigger |
| --- | --- | --- | --- |
| ACT-01 | N/A | Answering tools are read-only; no agent-triggered action changes external systems. | Project owner: Agent gains a write/action tool or can trigger ingestion/refresh. |
| ACT-02 | N/A | No autonomous external action retry exists. Maintainer import/review reruns and recovery are still tested in 05/14 under AD-06.2 and AD-10.2. | Project owner: Agent gains a write/action tool or can trigger ingestion/refresh. |
| ACT-03 | N/A | No agent-produced external action outcome exists. Persisted import/review state is verified in 05/14, not inferred from command success. | Project owner: Agent gains a write/action tool or can trigger ingestion/refresh. |
| MEM-01 | N/A | Only bounded conversation/session context is used for answering; retained feedback/evaluation records are separate and do not become personal memory. AD-05.3 remains current. | Project owner: Persistent user memory is introduced. |
| MEM-02 | N/A | No persistent memory correction/expiry lifecycle; session reset/isolation is covered in 07. | Project owner: Persistent user memory is introduced. |
| MEM-03 | N/A | No persistent-memory candidate to compare; follow-ups are evaluated as conversation behavior. | Project owner: Persistent user memory is introduced. |
| MULTI-01 | N/A | One investigator/controller may use several tools/routes; no cooperating agent team exists. | Project owner: Specialist agents with handoffs/shared state are introduced. |
| MULTI-02 | N/A | No agent coordination lifecycle; total single-request budgets and cancellation remain current. | Project owner: Specialist agents with handoffs/shared state are introduced. |
| MULTI-03 | N/A | No multi-agent candidate exists; route complexity is still compared to the text baseline. | Project owner: Specialist agents with handoffs/shared state are introduced. |
| TUNE-01 | N/A | No model weight training/fine-tuning in this release. Evaluation labels and prompt/judge calibration are still controlled. | Project owner: Training or fine-tuning, including a learned router, is proposed. |
| TUNE-02 | N/A | No training run to reproduce; prompts/models/settings and reference splits remain versioned. | Project owner: Training or fine-tuning, including a learned router, is proposed. |
| TUNE-03 | N/A | No trained artifact lifecycle or training expense; serving and offline evaluation expense remain measured. | Project owner: Training or fine-tuning, including a learned router, is proposed. |

## Using the register during delivery

For each working slice, add a failing public-behavior test or a reviewed expected case, implement the smallest complete behavior, and run the affected unit/integration and component/end-to-end checks. Unit tests check exposed rules; real PostgreSQL/pgvector and application contracts are integration boundaries. External service substitutes support routine repeatability, while separately budgeted live checks assess actual provider behavior.

Each evidence update records check IDs, case and dataset versions/splits, source snapshot, relevant code/prompt/model/tool/scorer configuration, results and actual trace/report links. Capture missing measurements and known limitations rather than treating missing values as success. Keep software-test artifacts separate from MLflow model-quality reports and associate both with the same evaluated revision.

Keep correctness, grounding, citation support, completeness, answerability and style separate. Critical biological, guilt, factual and evidence failures remain visible. Calibrate semantic judges against reviewed labels before trusting their scores. Set numerical acceptance thresholds after baseline measurement but before held-out candidate results; keep related story events and duplicates grouped across splits.

Re-evaluate affected evidence when sources, claims, code, dependencies, prompts, models, tools, scores or requirements change. Review meaningful user failures into regression cases. Feedback and automatic online evaluation are current obligations, with the same source-evidence and held-out protections as offline work. The final local release closes the current obligations with actual results; it does not automatically activate future capability modules or mark deployment complete.

## Fusion and cache amendment

The user requested these additions on 23 September 2026. The [research note](../research/rag-fusion-and-answer-caching.md),
[plan 23](../plans/ask-phil-tickets-v2/23-fuse-text-retrieval-and-expand-context.md) and
[plan 24](../plans/ask-phil-tickets-v2/24-cache-repeated-text-answers.md) extend existing
checklist obligations without changing checklist IDs or the six public seams.

- Fusion/expansion: RAG-02/03, AD-02.1, AD-05.1, AD-06.1/2, AD-08.3 and AD-09.1/3
  need reviewed variants/windows, fusion/deduplication/budget results, four uncached
  text ablations, resolvable citations and complete serving measurements.
- Caching: AD-05.3, AD-06.1/2, AD-09.1/3, RAG-03 and ONLINE-01–04 need exact-match
  eligibility, snapshot/configuration invalidation, isolated new delivery identities,
  cold/warm reports and actual feedback/online evaluation of cache hits.
- Final acceptance in plan 20 integrates both. All added runtime evidence is Pending.
  Existing Pass records remain limited to the delivered issue #2/#3 behavior;
  13 Pass and 38 Pending checks do not imply either new feature works.
