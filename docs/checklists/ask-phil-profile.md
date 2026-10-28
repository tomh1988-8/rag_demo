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

Of the 51 current checks, **35 Pass** and **16 remain Pending**. [Issue #9](../implementation/issue-9/README.md) adds the scoped comparison/evaluation checks AD-04.3/4, AD-06.4, AD-08.1/2 and AD-09.2. Actual public API runs, independently reviewed outcomes and human-approved synthetic judge calibration validate the measurement workflow. Both answer configurations fail critical quality gates, and the live support application exposes unresolved identity/null-policy limits. These measured failures remain current release obligations. Broader graph, fusion, cache, final held-out acceptance and automatic online-feedback capabilities remain pending. Historical issue #2–#8 results remain preserved. [Issue #10](../implementation/issue-10/README.md) adds scoped execution controls AD-07.1–4: public stop receipts, adversarial/malformed inputs, credential redaction, deadlines/cancellation and separate evaluation admission. Its independent reviews have zero remaining findings; the full software validation is recorded with the implementation.

[Issue #11](../implementation/issue-11/README.md) adds scoped AD-05.2 and EXT-02/03 evidence: reviewed parentage extraction, separate normalized-value and grounding measurements, content-bound admission and typed bounded SQL graph answers. Its final runtime and independent reviews match the accepted implementation. Values pass 4/4, while strict grounding is 2/4 and raw-pilot graph recall is 2/3. These remain explicit model-quality/completeness failures; measurement and conservative admission do not pass wider family coverage. RAG-04 and EXT-04 remain Pending for their broader graph-family and correction/review obligations.

[Issue #12](../implementation/issue-12/README.md) extends scoped RAG-04,
EXT-02/03, AD-06.3 and AD-08.1 evidence to family/romantic histories. The
original pre-frozen twelve-claim reference and a separately versioned thirteenth
source correction separate directed biological/adoptive/step/ward
meanings, repeated marriage episodes, separation/divorce, reconciliation,
reported status and uncertain timing. The one actual extraction has valid schema,
5 matched values (precision 5/12, corrected recall 5/13) and 2/12
resolvable/strict-grounded locators; all twelve raw
candidates are held after content-bound review. The retained raw-only graph
therefore has zero recall. Actual API/CLI and MLflow evidence separately exercises
the twelve pre-pilot curated claims plus documented extra supporting marriage
assertion while retaining the raw holds; this is
manually curated capability, not a model-quality pass. The
[regression record](../implementation/issue-12/regressions.json) preserves those
failures, and the issue evidence binds final validation/reviews to the tested
revision. No checklist count changes: RAG-04 remains Pending for the wider graph
families and checked coverage; corrections, held-out and release acceptance
remain outstanding.

[Issue #13](../implementation/issue-13/README.md) extends scoped EXT-02/03,
RAG-04, AD-06.3 and AD-08.4 evidence to shared crime/justice incidents. Seventeen
source labels precede the one Sol pilot; a versioned post-pilot source correction
restores five relative timing qualifiers without changing the original labels or
raw output. Four schema-valid predictions have
three exact matches (precision 3/4, recall 3/17); three locators resolve and one
meets the conservative full-span grounding proxy. Content-bound review admits two
raw candidates and holds the malformed false confession and incomplete commission.
Separate real API/CLI and MLflow evidence exercises all reviewed roles, false
accounts, shared participants, empty histories and execution bounds while retaining
the raw failures. All 24 final API/CLI/session outcomes have exact MLflow
readback; no forbidden guilt conflation appears. The reviewed source `cc34208`
passes all 388 software cases, strict mypy across 90 files, Ruff/formatting and
both independent review axes after resolving the source-label timing omission
and a shared conversation row-lock wait defect. [Validation](../implementation/issue-13/validation.json)
binds these separate software and model-quality records. This is scoped curated capability with explicit extraction/coverage
failures, not a broad automatic-extraction, held-out or canon pass. The linked
regressions and revision-bound validation remain part of the evidence; checklist
counts are unchanged and wider RAG-04, EXT-04 and AD-08.4 obligations remain Pending.

[Issue #14](../implementation/issue-14/README.md) extends scoped EXT-02, EXT-04,
RAG-04, AD-06.3 and RAG-03 evidence to pregnancy/death roles and separate thematic
or unclassified text. Its frozen seven-passage pilot records 4/5 exact event
values, 3/5 resolvable event locators and 0/5 conservative full-span grounding;
content-bound review admits three shorter supported event quotes and holds two
malformed locators. Theme/unclassified values match 1/2, with 2/2 resolvable
locators and 1/2 strict grounding. The curated projection retains every raw
record. Thirty final API/CLI/session outcomes have exact actual trace readback.
Three live text cases retain the tape fact and the theme distinction; two pass
source-based quality review, while the unsupported-manosphere response fails its
expected status and explicit coverage caveat. Its incidental facts and citations
are supported. Both independent reviews found zero implementation issues, and
the final trace audit passed. This is a scoped extension with explicit extraction
and text-quality failures. [Validation](../implementation/issue-14/validation.json)
records 414 passing tests, strict mypy across 99 files, Ruff/formatting and the
unchanged application fingerprint at `ef77ce8`. Checklist counts are unchanged;
wider RAG-04 and EXT-04 remain Pending.

The [answer execution deepening](../implementation/answer-execution-deepening/README.md)
rechecks scoped AD-05.4, AD-06.1–3, AD-07.4 and AD-09.1–3 through shared text/Family
tree admission, separate serving/offline limits, retained stop receipts and actual
MLflow output readback. Its validation binds the software checks to the tested
source and unchanged public contracts. Existing model-quality failures and wider
release obligations retain their current status.

[Issue #15](../implementation/issue-15/README.md) completes the scoped EXT-04
review/annotation workflow and extends AD-03.3, AD-06.2, RAG-03 and the recovery
portion of AD-10.2. Content-bound maintainer outcomes preserve raw Claims and review
history; supported corrections and complete disputed groups appear in current text
and graph answers. Immutable manifests bind source, retrieval, every graph family
and review identity. [Runtime quality](../implementation/issue-15/answer-quality.json)
records twelve passing current reviewed answers among nineteen actual API/CLI/session
responses, including real projection failure, retry, restart and rollback. Two old
biological Den/Sharon answers deliberately reproduce an authored prior-review error
and are excluded from factual passes. The initial text-budget failure and both
independently found correction-history defects remain in the
[regression record](../implementation/issue-15/regressions.json).
[Annotation guidance](../implementation/issue-15/review-guidance.md) defines matching,
duplicates, uncertainty, reference completeness and later targeted review/sampling.
The synthetic dispute and authored correction are exposed development evidence;
original extraction and ordinary text-quality failures remain unchanged. Full-product
code/prompt recovery, wider graph coverage and representative release gates remain
Pending. [Validation](../implementation/issue-15/validation.json) binds the final
software/runtime checks and separate independent reviews to frozen implementation inputs.

[Issue #16](../implementation/issue-16/README.md) extends scoped RAG-04, AD-05.2,
AD-06.3 and AD-08.1 evidence to composed character connections. Its reviewed
development cases preserve biological/social direction, historical status,
incident roles, alternate paths, traversal bounds and qualified empty results.
The four graph families are exercised through their public contracts; result
correctness, step meaning, provenance and final prose support remain separate
measurements. [Independent review](../implementation/issue-16/review.md) found and
repaired a biological-history fallback that bypassed family admission; the public
cycle regression and earlier event-only/legacy-manifest failures remain recorded.
Source-backed Claims, original extraction failures and text-quality gaps are
unchanged. Broad checked graph coverage and release acceptance remain Pending;
the checklist counts stay 35 Pass and 16 Pending. The issue's
[validation](../implementation/issue-16/validation.json) binds final software and
runtime evidence to the reviewed revision and frozen inputs.

[Issue #17](../implementation/issue-17/README.md) adds explicit bounded investigation
over captured text and all four typed graph families in one sealed publication.
The [paired comparison](../implementation/issue-17/comparison-summary.json) contains
three exposed questions/story groups and six actual API responses with exact
root/tool/citation/recreation readback. Independent source review passes all nine
factual claims; investigation covers 3/3 required facts and text 2/3, with honest
unsupported outcomes. Argument/eligibility, recovery/stop, context sufficiency,
task completion and final support remain separate. Total reported serving inference
is $0.0306264; offline source review uses no model credits. The original query drift,
baseline context miss, disputed-claim bypass and two independently found stop-path
failures remain [recorded](../implementation/issue-17/regressions.json). Both review
axes have zero remaining findings after passing public stop regressions. Live
responses belong to `b599783`; final software `13d38e0` changes stop handlers only,
with unchanged prompt/model/tool contracts. Frozen inputs and full-suite evidence
remain revision-linked. This extends scoped evidence without changing the checklist
counts: routing, wider quality/release and online obligations remain Pending.

[Issue #19](../implementation/issue-19/README.md) extends AD-06.3, AD-08.2,
RAG-03 and the persona portion of AD-10.4 with 72 actual API responses and exact
CLI/trace/citation readback. The controlled final comparison improves neutral
appendices from 21/24 to 24/24 and removes the mandatory opener, while separate
voice, harm and outcome/qualification results remain 24/24, 8/8 and 24/24.
The first candidate's unsupported-absence regression is retained and repaired.
The unchanged human-calibrated support judge agrees with 9/10 new agent labels;
one foreman-role interpretation requires human adjudication. The over-specified
Jane reference keeps one conservative final coverage failure visible. These
are exposed source-based results, not human canon or held-out acceptance.
Full software/review validation is recorded with the issue before closure.
Checklist counts remain 35 Pass and 16 Pending; AD-10.4's feedback/release
obligations and broader judge acceptance are unchanged.

Design Pass records below concern the approved design, including the user's feedback/online-evaluation and fusion/cache amendments, captured by specification SHA-256 `a82e93bd170be20c253415606fcb9a6ab082f7a9a7c991d56ca5e757ca728c53`. Runtime Pass records link to the exact scoped slice artifacts below; other runtime evidence remains prospective. On implementation, add artifact/run links and source/code/configuration identities before changing a check to Pass. Update affected checks to Pending, In progress or Fail when their evidence is invalidated. A current-release failure cannot be turned into a deployment deferral merely to complete a ticket.

Primary ownership is an index into a continuing evidence obligation, not a licence to postpone all work to that ticket. For example, caps and basic traces start in 02, stronger failure enforcement is proved in 09, and every tool extension rechecks the affected constraints. Source claims are reviewed before their extraction pilot. Per-slice tests and evaluations start in 01/02; final acceptance in 20 reuses their results.

## Current evidence register

[Issue #9 evidence](../implementation/issue-9/README.md) records two controlled 14-response public API runs across seven exposed cases/three story groups, six independent dimensions, separate retrieval/context outcomes and source-bound MLflow artifacts. [The comparison](../implementation/issue-9/comparison.json) preserves Janine false-premise/context failures and unnecessary garage clarification; both critical gates fail. [Calibration](../implementation/issue-9/judge-calibration.json) completes 24 synthetic observations against Tom's eight approved labels, with zero false passes or sensitivity changes. [Application to saved answers](../implementation/issue-9/support-application.json) retains eight unscored decisions requiring review, so no broad automatic judge reliability is claimed. [Regressions](../implementation/issue-9/regressions.json) identify resolver, context, identity and judge follow-ups. Final software checks, source identity and actual artifact readback are in [live validation](../implementation/issue-9/live-validation.json). These scoped measurement passes do not pass answer-quality release gates. ONLINE-02/04 retain Pending status for #23's automatic execution and human review loop.

All rows apply to the current local release. Runtime evidence owners are ticket implementers, with the project owner accountable for design scope and acceptance thresholds.

| Check | Status | Primary ticket | Existing or required evidence | Recheck trigger |
| --- | --- | --- | --- | --- |
| AD-01.1 | Pass | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) / project owner | [Spec: problem and scope](../specs/ask-phil.md#problem-statement) and this profile's owner assignment; design evidence only. Agreed spec names viewers, demonstrators and maintainers; this profile names the project owner as acceptance owner. | Users, release scope or accountable owner changes. |
| AD-01.2 | Pass | [03](../plans/ask-phil-tickets-v2/03-handle-incomplete-evidence.md) / project owner | [Spec: conversation and evidence contracts](../specs/ask-phil.md#conversation-and-evidence-contracts); design evidence only. Agreed response contract describes supported, clarification, partial and abstention outcomes. [Issue #4](../implementation/issue-4/cloud/README.md) implements and tests that contract; the 13-case Sol policy matrix and five actual CLI/API cases now pass scoped semantic review. | Response outcome policy or user interaction changes. |
| AD-01.3 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) / project owner | Setup caps, measured baseline and quality/latency/cost thresholds recorded before held-out candidate inspection. | Limits, release criteria, baseline or acceptance dataset changes. |
| AD-01.4 | Pass | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) / project owner | [Spec: testing decisions](../specs/ask-phil.md#testing-decisions) and [exclusions](../specs/ask-phil.md#out-of-scope); design evidence only. Agreed spec records factual/guilt/biological/citation failures, CLI interaction and explicit exclusions. | Important failure consequences, assumptions or exclusions change. |
| AD-02.1 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Deterministic baseline](../implementation/issue-2/baseline.json) and [single-query uncached text baseline](../implementation/issue-3/text-baseline-v4.json), pinned to snapshot, package, model, prompt and application identities. Pass covers the exposed seed only; future fusion/route comparisons must retain this baseline. | Source snapshot, answer model or comparison task changes. |
| AD-02.2 | Pending | [17](../plans/ask-phil-tickets-v2/17-route-and-escalate.md) | [Issue #17](../implementation/issue-17/README.md) implements declared read-only investigator discretion, typed validation, fixed publication and finite request limits. Automatic routing/eligibility workflow in #18 remains Pending. | Tool capabilities, routing policy or model responsibilities change. |
| AD-02.3 | Pending | [17](../plans/ask-phil-tickets-v2/17-route-and-escalate.md) | [Three paired development cases](../implementation/issue-17/comparison-summary.json) compare the actual investigator and text route on identical source/index/answer-model identities, context ceilings and full serving expense. Curated/exposed scope and simple-task overhead remain explicit; automatic eligible-route comparisons and release thresholds remain Pending for #18/#21. | Any added route, model, retrieval or orchestration complexity. |
| AD-02.4 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [Issue #2 acceptance evidence](../implementation/issue-2/README.md): complete captured-passage inspection through real CLI/HTTP, FastAPI and PostgreSQL; stable evidence survives reimport/application recreation and an actual database restart. Fresh Docker startup and database/API restart also passed; AD-10.1 remains Pending for the complete product. | First-slice scope or public contract changes. |
| AD-03.1 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | Initial reviewed seed plus [issue #7 references](../../data/references/core-profiles-v2.json): 25 source-reviewed development questions across all 20 core profiles, two cross-profile and two absent-identifier cases, with 21 shared story groups and explicit source/currentness limits. Independent Spec review checked every source mapping and additional actual assertion. | New task category, source type or roster expansion. |
| AD-03.2 | Pass | [04](../plans/ask-phil-tickets-v2/04-import-real-sources.md) | [Original source inventory](../../data/sources/README.md) and [20-profile inventory/review](../implementation/issue-7/coverage-review.json) retain roles, attribution/license, source hashes, check dates and reviewed scope. Freshness is not storyline completeness; source-supported claims are not independently corroborated canon. | Source, access/usage rules or captured-data scope changes. |
| AD-03.3 | Pass | [05](../plans/ask-phil-tickets-v2/05-refresh-and-recover-snapshot.md) | [Issue #6 lifecycle](../implementation/issue-6/lifecycle.json) establishes immutable source/text publication. [Issue #15](../implementation/issue-15/README.md) seals all claim/graph and review identities with source and vector artifacts, preserves correction history, rejects incomplete candidates and holds one version throughout an answer. [Public recovery regressions](../../tests/test_review_refresh.py) cover unchanged recapture, old pins and withdrawal; final API/CLI rollback and failure evidence is retained. Scope is compatible captured artifacts, not full code/prompt release recovery. | Capture/publication/projection or evidence identity changes. |
| AD-03.4 | Pass | [06](../plans/ask-phil-tickets-v2/06-cover-core-text-profiles.md) | [Issue #7 inventory](../implementation/issue-7/coverage-inventory.json) and [review](../implementation/issue-7/coverage-review.json) cover every core profile: retained/unreviewed/excluded content, dates, duplicates, inspected chronological discrepancies and concrete gaps. The [Cindy alias correction](../implementation/issue-7/corpus-correction.json) retains immutable before/after evidence and a public regression. No exhaustive conflict detector or current-history claim. | Source refresh, roster, parsing or normalization changes. |
| AD-04.1 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [Reviewed seed](../../data/references/phil-arrival-v1.json) established from source inspection before model work, independently checked by the Spec review agent. New behavior/graph labels must be reviewed before their pilots; no human or independent-canon verification claimed. | New behavior, corpus category or reviewed failure. |
| AD-04.2 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [Frozen development cases](../../data/references/phil-arrival-v1.json) record stable IDs, source/span expectations, acceptable alternatives, forbidden assertions, answerability, grouping, synthetic provenance and actual review notes. | Reference correction, evidence revision or new outcome. |
| AD-04.3 | Pass | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | [Grouped splits](../implementation/issue-9/splits.json), frozen source-bound cases and enforced story/evidence ownership. Seven exposed development cases remain separate from two synthetic judge groups; final held-out comparison is reserved for fresh cases. Future cases must retain these controls. | New cases, source overlap, synthetic derivatives or split changes. |
| AD-04.4 | Pass | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | [Protocol](../implementation/issue-9/protocol.md) and actual [comparison](../implementation/issue-9/comparison.json): six separate answer dimensions, retrieval/context metrics, critical gates, cadence and reference requirements. Numeric release policy must be frozen after baseline measurement and before fresh held-out outputs. | Capability, metric, failure category or acceptance policy changes. |
| AD-05.1 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Issue #3 configuration and bounds](../implementation/issue-3/README.md#bounds-and-truthful-measurements): pinned model digests/settings, versioned prompt/schema, whole-span context and per-call bounds. Zero local API charge excludes hardware/hosting; paid-provider controls and a new baseline precede migration. | Prompt, model, context construction or output contract changes. |
| AD-05.2 | Pass | [10](../plans/ask-phil-tickets-v2/10-answer-biological-family.md) | [Issue #11 biological contract](../implementation/issue-11/README.md#public-contract) and [issue #17 investigator tools](../implementation/issue-17/README.md#invocation-and-authority): versioned text/family/relationship/event/connection arguments and results, snapshot/provenance checks, bounded read-only SQL and real public positive/negative/recovery outcomes. | Any new or changed tool or graph capability. |
| AD-05.3 | Pass | [07](../plans/ask-phil-tickets-v2/07-ground-followups-and-reset.md) | [Issue #8 software and contract](../implementation/issue-8/README.md) implement eight retained references, thirty-minute idle/two-hour absolute lifetime, reset, session isolation, monotonic turn identities and separate thirty-day feedback capability. Public API/CLI and reference/state regressions protect fresh retrieval despite misleading history. Independent Standards/Spec reviews have zero remaining findings. [Actual live results](../implementation/issue-8/summary.json) record six fresh factual retrieval/generation paths, three zero-model clarifications and public reset/isolation/API restart; all nine outcomes pass reviewed source-based assessment. The approved sample used $0.0237656 with no unsettled reservations. | Conversation persistence, truncation or reference resolution changes. |
| AD-05.4 | Pending | [17](../plans/ask-phil-tickets-v2/17-route-and-escalate.md) | [Issue #17 actual execution records](../implementation/issue-17/comparison-summary.json) expose declared-tool findings, multi-fact sufficiency, overrides and stops. Eligible automatic routing, fallback and escalation still require #18; this check remains Pending. | Routing/evidence policy, limits or tool availability changes. |
| AD-06.1 | Pass | [01](../plans/ask-phil-tickets-v2/01-inspect-captured-evidence.md) | [TDD record and actual results](../implementation/issue-2/README.md): failing public provenance, API, CLI and citation-resolution cases followed by minimal working changes. Reopen/extend this evidence for each later behavior change. | Every behavior change. |
| AD-06.2 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Issue #3](../implementation/issue-3/validation.json) and [issue #6](../implementation/issue-6/validation.json) establish real PostgreSQL/pgvector, API/CLI, Prefect and MLflow testing. [Issue #15 validation](../implementation/issue-15/validation.json) extends the agreed seams with actual review outcomes, retained evidence, all-family publication, failed projection, interrupted indexing, exact retry, unchanged refresh, pinned queries and compatible recovery. Nineteen actual API/CLI/session responses have exact trace and saved-answer readback. External-model substitutes stay at the permitted boundary. | Affected rule, integration, dependency or provider contract changes. |
| AD-06.3 | Pass | [03](../plans/ask-phil-tickets-v2/03-handle-incomplete-evidence.md) | [Issue #4 software and observed regressions](../implementation/issue-4/cloud/summary.json): public outcome/citation/date rules, real API/CLI counterexamples and frozen model failures. 85 software tests and scoped Sol semantic review pass; regression v2 preserves old and new failures with profile-specific dispositions. [Issue #8 repaired reference/state regressions](../implementation/issue-8/regressions.json) add misleading-history, alias/performer, role/relative-owner, selection, reset/expiry and isolation cases with 182 passing tests. | New failure mode or changed public behavior. |
| AD-06.4 | Pass | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | [Software and actual API evidence](../implementation/issue-9/README.md) exercise scorer/public conversation boundaries, known successes, failures and missing-data outcomes. Independent source/response reviews bind all 28 live outcomes; new routes must extend these scoped text/conversation results. | Scorer, public capability or failure behavior changes. |
| AD-07.1 | Pass | [09](../plans/ask-phil-tickets-v2/09-enforce-execution-boundaries.md) | [Issue #10 execution boundary](../implementation/issue-10/README.md) extended by [issue #17](../implementation/issue-17/README.md#invocation-and-authority): schema-validated declared read-tool dispatch in one sealed publication, typed parameterized SQL, exact provider resources, no arbitrary SQL/shell/ingestion/source mutation/live web, redirects/proxies/retries disabled. Actual forbidden-tool attempts preserve authority. | New tool/resource, privileges or agent-triggered action. |
| AD-07.2 | Pass | [09](../plans/ask-phil-tickets-v2/09-enforce-execution-boundaries.md) | [Public execution regressions](../../tests/test_execution_api.py) and [investigator cases](../../tests/test_investigation_api.py) exercise hostile authority requests, extra snapshot/action fields, malformed arguments, repeat calls, disputed source interpretations and validated citations. Safe retained outcomes and actual traces are recorded; no semantic prompt-injection immunity is inferred. | New source/tool format, validation or model context policy. |
| AD-07.3 | Pass | [09](../plans/ask-phil-tickets-v2/09-enforce-execution-boundaries.md) | [Issue #10 redaction](../implementation/issue-10/README.md#credentials-and-later-feedback): recognizable credentials and the configured key are removed before prompts/output traces; unsafe captures/settings are rejected; static error locations also omit credential-shaped extra JSON keys. Synthetic credential/provider-error regressions and the staged-secret scan pass. Arbitrary personal information is not automatically classified. | Credential, logging, tracing or sensitive context handling changes. |
| AD-07.4 | Pass | [09](../plans/ask-phil-tickets-v2/09-enforce-execution-boundaries.md) | [Issue #10 controls](../implementation/issue-10/README.md#limits-and-cancellation) and [issue #17 full investigation](../implementation/issue-17/README.md): shared decision/query-embedding/tool/HTTP/context/time/spend caps, conservative unknown-cost reservations, zero transport retries, real HTTP cancellation/deadlines and SQL-timeout stop receipts. Separate serving/offline investigator quotas and bounded stop wording preserve the shared $5 ledger. Original stop failures and passing repairs remain recorded. | Budget accounting, provider, retry or cancellation policy changes. |
| AD-08.1 | Pass | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | [Issue #9 measurement workflow](../implementation/issue-9/comparison.json) and [issue #17 separate diagnostics](../implementation/issue-17/comparison-summary.json): eligibility/argument validity, recovery/stop, multi-fact context sufficiency, task completion and independent final support. Multiple successful strategies are accepted; exact internal order and self-reported coverage are not quality labels. | Component, task success definition or persistent-state behavior changes. |
| AD-08.2 | Pass | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | [Known-outcome tests and calibration](../implementation/issue-9/README.md): human-approved positive/negative/missing synthetic labels, two disjoint judge groups, repeats/order/verbosity and false-pass analysis. Actual support application keeps eight null-reference decisions unscored and requiring review; broad automatic support remains unaccepted. | Judge/model/rubric, scorers or reference label changes. |
| AD-08.3 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Frozen baseline/candidate settings, paired route comparisons and ablations with quality/latency/cost separated. | Candidate configuration, dataset, snapshot or comparison protocol changes. |
| AD-08.4 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Category failures, sample/variation reporting and explicit resolution of critical failures. | New release candidate or critical failure. |
| AD-09.1 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Issue #3 baseline traces](../implementation/issue-3/text-baseline-v4.json) extended by [issue #17 actual root/tool/context/citation readback](../implementation/issue-17/README.md#development-comparison), immutable original responses, complete per-decision accounting and application recreation. SQL deadline and large-context stops retain their actual outcomes after the reviewed repairs. Read tokens are excluded. | Trace/evidence construction, tool or error handling changes. |
| AD-09.2 | Pass | [08](../plans/ask-phil-tickets-v2/08-inspect-calibrated-comparisons.md) | [Frozen evaluation runs and readback](../implementation/issue-9/live-validation.json) bind code/application, source revision, datasets/splits, prompt, model/settings, retrieval/context/cache controls, scorer/rubric and separate software XML. Self-hosted MLflow downloads match hashes; future execution capabilities must extend this scoped lineage. | Any recorded execution or evaluation dependency changes. |
| AD-09.3 | Pending | [17](../plans/ask-phil-tickets-v2/17-route-and-escalate.md) | [Issue #17 paired serving measurements](../implementation/issue-17/comparison-summary.json) include all investigator decisions/embeddings, known/null accounting, conservative reservations and complete API latency. Offline source review costs zero model credits. Automatic routing/retry comparison and online expense remain Pending; ONLINE-03 owns live evaluation accounting. | Routing, retry, provider/pricing or measurement changes. |
| AD-09.4 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Repeatable local evaluation/demo procedure and documented provider variability limits. | Runtime, dependency, provider or evaluation procedure changes. |
| AD-10.1 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Fresh Docker Compose startup, configuration/limits and complete local workflow demonstration. First-slice Docker startup and restart passed; acceptance evidence is in [issue #2](../implementation/issue-2/README.md); later-slice/full-release requirements remain open. | Setup/runtime/dependency or intended environment changes. |
| AD-10.2 | Pending | [20](../plans/ask-phil-tickets-v2/20-accept-complete-local-demo.md) | Release gates plus compatible code/prompt/data recovery remain required. [Issue #6](../implementation/issue-6/README.md) verifies source/text rollback. [Issue #15](../implementation/issue-15/README.md) extends recovery to sealed graph/claim/review artifacts, preserving last usable versions through projection/indexing failure and allowing existing request pins while withdrawn snapshots reject new requests. Full-product code/prompt recovery and release gates remain Pending. | Release candidate, snapshot/schema, prompt or recovery changes. |
| AD-10.4 | Pending | [22](../plans/ask-phil-tickets-v2/22-evaluate-live-feedback.md) | Actual feedback/disagreement dispositions and checked regression promotion, with known limitations and dependency re-evaluation verified again in final acceptance. | User feedback, observed failure, dependency or corpus change. |
| RAG-01 | Pass | [06](../plans/ask-phil-tickets-v2/06-cover-core-text-profiles.md) | [Actual issue #7 results](../implementation/issue-7/summary.json): one generic 20-profile import, earlier history and supporting mentions, 461 admitted paragraphs/794 exact-span passages, source/identity/retention/currentness inventory and independently reviewed sourced API/CLI success for all 20 profiles. Two context/completeness failures remain visible. Checked graph coverage remains 19. | New sources, snapshot, roster, canon or access constraints. |
| RAG-02 | Pass | [02](../plans/ask-phil-tickets-v2/02-generate-grounded-answer.md) | [Issue #7 retrieval/context evidence](../implementation/issue-7/retrieval-final.json) retains its two known failures. [Issue #17 paired multi-fact evaluation](../implementation/issue-17/comparison-summary.json) finds context/answer coverage of 3/3 required facts for investigation and 2/3 for text across two answerable cases, plus one unsupported case. Alternative sufficient sets and null factual denominators are explicit. These three exposed story groups do not establish held-out quality. | Retrieval/context policy, embeddings, corpus or task distribution changes. |
| RAG-03 | Pass | [03](../plans/ask-phil-tickets-v2/03-handle-incomplete-evidence.md) | [Issue #7](../implementation/issue-7/answer-quality.json) and [issue #8](../implementation/issue-8/answer-quality.json) retain separate support, coverage and abstention outcomes. [Issue #15](../implementation/issue-15/answer-quality.json) adds twelve current corrected/disputed text/graph/CLI/session answers with source support, complete competing accounts, partial status and coverage/corroboration caveats. The connected group is indivisible under the context limit; low-budget cases abstain rather than pick a winner. The two injected wrong baseline/rollback answers are excluded from factual passes. Exposed development evidence only; historical quality failures remain retained. | Answer prompt/model, evidence, corpus conflicts or output policy changes. |
| RAG-04 | Pending | [15](../plans/ask-phil-tickets-v2/15-trace-character-connections.md) | [Issue #16](../implementation/issue-16/README.md) validates all four public graph families on reviewed exposed cases, with separate result, step-meaning, provenance and [final-answer support](../implementation/issue-16/answer-quality.json) results. Biological connections cannot bypass family admission through history. Alternative, false-role, cycle, no-path, source exclusion and bounded-work cases are retained. Original [raw-pilot missing Peggy path](../implementation/issue-11/regressions.json) and extraction scores remain unchanged; broader checked graph coverage and release gates remain Pending. | Graph relations/roles, path logic, claims or provenance changes. |
| EXT-01 | Pass | [04](../plans/ask-phil-tickets-v2/04-import-real-sources.md) | [Issue #5 report](../implementation/issue-5/retention-report.json): 79/79 independently reviewed main-series paragraphs retained in order, 138 exact-span passages, five exclusions, 198 unreviewed paragraphs, four structured metadata records and one reported missing summary. Public malformed/missing/duplicate regressions and real PostgreSQL/API/CLI checks complement the [separate live check](../implementation/issue-5/live-compatibility.json). PDF/OCR and semantic extraction measures do not apply to this slice. | Source format/filter/parser or proposed PDF/OCR inputs change. |
| EXT-02 | Pass | [10](../plans/ask-phil-tickets-v2/10-answer-biological-family.md) | [Frozen four-claim pilot](../implementation/issue-11/extraction-pilot.json) and [span-aware final rescore](../implementation/issue-11/extraction-score-final.json): normalized identities, direction, relation, parent role, polarity, certainty and story timing separately from schema validity. Values 4/4; duplicate/missing/reversed/performer and non-biological software counterexamples remain separate from model observations. Exposed development slice only. | Schema, extraction/model, taxonomy, normalization or source changes. |
| EXT-03 | Pass | [10](../plans/ask-phil-tickets-v2/10-answer-biological-family.md) | [Independent four-claim audit](../implementation/issue-11/claim-reviews.json), [admission](../implementation/issue-11/admission.json) and [final runtime](../implementation/issue-11/runtime-final.json): exact span resolution required for admission; raw locators 3/4 and frozen full-span grounding 2/4, separately from 4/4 normalized values and semantic support. Malformed Peggy locator is held; all returned edge citations resolve. These measurements preserve quality failures rather than establish broad grounding reliability. | Evidence mapping, extracted claims, source revisions or scorer changes. |
| EXT-04 | Pass | [14](../plans/ask-phil-tickets-v2/14-review-corrections-and-disputes.md) | [Issue #15 guidance](../implementation/issue-15/review-guidance.md) defines content-bound outcomes, correction chains, duplicate handling, matching/timing tolerances, source support versus corroboration, complete-reference denominators and targeted later review/sampling. [Immutable before/after audits and runtime](../implementation/issue-15/runtime-accepted/summary.json) cover the actual malformed Peggy locator, an authored biological/adoptive interpretation error and an explicitly synthetic unresolved dispute. Original reference labels, raw predictions and extraction scores remain unchanged. [Review](../implementation/issue-15/review.md) records both repaired history/closure findings and zero remaining findings. | Annotation policy, review criteria, category or reference completeness changes. |
| ONLINE-01 | Pending | [21](../plans/ask-phil-tickets-v2/21-capture-response-feedback.md) | Optional CLI/API feedback, durable receipt/revisions, original response/trace identity and real storage/MLflow access/retention results. | Feedback/session/response contract, storage/export, privacy or retention changes. |
| ONLINE-02 | Pending | [22](../plans/ask-phil-tickets-v2/22-evaluate-live-feedback.md) | [Versioned scorer contracts](../../data/references/quality-scorer-contracts-v1.json) distinguish reviewed-reference and context-only inputs. #23 must implement automatic normal-use evaluation, preserved outputs, directed/background samples and late/revised-feedback reconciliation; synthetic calibration does not accept broad online use. | Sampling/eligibility, evaluator input, orchestration or trace/feedback lifecycle changes. |
| ONLINE-03 | Pending | [22](../plans/ask-phil-tickets-v2/22-evaluate-live-feedback.md) | Versioned live report with explicit counts/denominators, missing/failure/lag states and bounded online expense. | Metric/cohort definitions, evaluator versions, retry/budget policy or measurement changes. |
| ONLINE-04 | Pending | [22](../plans/ask-phil-tickets-v2/22-evaluate-live-feedback.md) | [Synthetic support fixtures](../../data/references/support-judge-v1.json) include missing references and a human-report contradiction; [retained live decisions](../implementation/issue-9/regressions.json) expose unresolved identities and four no-assertion/null-policy mismatches. #23 must expose evidence-based human dispositions and promote checked regressions with story-group/split controls. | Review/source policy, reference correction, regression or held-out group changes. |

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
  Existing Pass records remain limited to the delivered issue #2–#10 scopes;
  31 Pass and 20 Pending checks do not imply either new feature works.
