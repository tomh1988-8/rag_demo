# Ask Phil: checklist-based ticket breakdown, version 2

Status: approved and published on 23 September 2026, with the user's feedback/online-evaluation amendment integrated. These 24 implementation tickets are GitHub issues #2–#25 under specification #1. Bodies and ready-for-agent labels are verified. Native dependency links remain pending a supported write capability; all 41 blocker references are saved. See the [next-skill handoff](HANDOFF.md), [publication manifest](publication.json) and [scope amendment record](feedback-amendment.json). Issue #2 is complete and closed; [native and Docker acceptance evidence](../../implementation/issue-2/README.md) is saved. Issue #3 is also complete and closed; [text-RAG evidence](../../implementation/issue-3/README.md) is saved. Issue #4 is complete with scoped Sol policy acceptance. Issue #5 has passed its implementation review; its [acceptance evidence](../../implementation/issue-5/README.md) and publication/closure status are tracked in the handoff. Issue #6 is recommended next after #5 publication.

Sources: the [agreed specification](../../specs/ask-phil.md), [checklist v1.1](../../checklists/agent-development.md), [project profile and evidence register](../../checklists/ask-phil-profile.md), [testing strategy](../../design/testing-and-evaluation.md), root domain glossary and active ADRs. The [story coverage matrix](spec-coverage.md) maps all 130 stories. The [previous proposal](../ask-phil-tickets/README.md) is retained as superseded history.

## How this breakdown applies the checklist

Tickets deliver complete observable behaviors. Checklist areas provide obligations and evidence ownership across those behaviors, rather than separate horizontal “all data”, “all tests” or “all evaluation” implementation phases. Each issue body records the checks it advances, required evidence, recheck triggers and genuine blockers.

The project profile reviews all 64 checklist items: 51 apply to the local release, one is deferred to deployment and 12 are not applicable to the chosen capabilities. Three applicable items have design evidence, five have inspection-slice evidence, five have initial text-RAG evidence, two have #4 policy-slice evidence and two have #5 source-ingestion evidence; 34 remain Pending. The first slice has 17 passing tests in each of the native and Docker environments, reviewed development references, and a successful fresh Compose startup and database/API restart. Issue #3 adds 32 passing tests and a local-model smoke baseline; representative generative quality and complete-product acceptance remain unverified.

The sequence starts with a deterministic evidence-inspection baseline and reviewed seed, then a complete measured text answer. Source coverage for all 20 characters can land early while graph semantics develop. Crime/justice and other events have separate slices. Execution limits precede model-directed investigation. Broader checked graph coverage reuses the proven ingestion/review path. All feature tickets carry tests and evaluations; final acceptance in ticket 20 integrates the suite, including feedback/online evaluation in 21–22 and fusion/caching in 23–24.

The breakdown was approved before application code existed; issue #2 now supplies the initial CLI/API/database path. The six confirmed test boundaries remain unchanged. Initial models/providers, numerical caps, dataset sizes and thresholds are setup choices: choose conservative bounds before paid work, and set measured acceptance thresholds before examining held-out candidates.

## Approved tickets

1. **[Inspect captured source evidence locally](01-inspect-captured-evidence.md)**  
   **Blocked by:** None; can start immediately.  
   **What it delivers:** Inspect a reviewed captured passage through the CLI and API, with a deterministic evidence baseline and reproducible local storage.

2. **[Generate a grounded Ask Phil answer](02-generate-grounded-answer.md)**  
   **Blocked by:** 01.  
   **What it delivers:** Ask one natural-language question and receive a Phil-style text-RAG answer with citations, an honest engineering appendix and a measured baseline.

3. **[Handle incomplete evidence and false premises](03-handle-incomplete-evidence.md)**  
   **Blocked by:** 02.  
   **What it delivers:** Give supported partial answers, clarify or abstain when needed, and challenge false premises only when evidence supports doing so.

4. **[Import real sources with character identity and canon scope](04-import-real-sources.md)**  
   **Blocked by:** 01.  
   **What it delivers:** Import a small real source set and inspect retained main-series evidence under stable character identities.

5. **[Refresh and recover a captured snapshot](05-refresh-and-recover-snapshot.md)**  
   **Blocked by:** 04.  
   **What it delivers:** Run a manual Prefect refresh, inspect its outcome and recover the previous usable text snapshot after failure.

6. **[Answer from all 20 core character profiles](06-cover-core-text-profiles.md)**  
   **Blocked by:** 02, 05.  
   **What it delivers:** Answer sourced text questions across the complete core roster and show per-character coverage and gaps.

7. **[Ground follow-ups and reset conversation](07-ground-followups-and-reset.md)**  
   **Blocked by:** 03, 04.  
   **What it delivers:** Continue a grounded conversation, clarify ambiguous references and reset the session without carrying earlier context forward.

8. **[Inspect calibrated quality comparisons](08-inspect-calibrated-comparisons.md)**  
   **Blocked by:** 03.  
   **What it delivers:** Run reviewed chat cases through the API and inspect reproducible, separately scored quality results in MLflow.

9. **[Bound requests and enforce read-only execution](09-enforce-execution-boundaries.md)**  
   **Blocked by:** 03.  
   **What it delivers:** A request stops predictably at its configured limits, rejects unauthorised capabilities and reports supported findings or failure honestly.

10. **[Answer biological family questions from admitted claims](10-answer-biological-family.md)**  
   **Blocked by:** 03, 04.  
   **What it delivers:** Extract and review a small parentage set, then answer biological ancestry and descendant questions with supported graph evidence.

11. **[Explain family and romantic histories](11-explain-relationship-histories.md)**  
   **Blocked by:** 10.  
   **What it delivers:** Explain social family ties and romantic histories without confusing them with biological ancestry or current relationships.

12. **[Explain crimes and criminal justice roles](12-explain-crime-and-justice.md)**  
   **Blocked by:** 10.  
   **What it delivers:** Explain a crime and its justice history while keeping perpetrators, accused people, victims and legal outcomes distinct.

13. **[Explain life events, themes and unclassified facts](13-explain-life-events-and-themes.md)**  
   **Blocked by:** 12.  
   **What it delivers:** Answer supported pregnancy, death and other event questions while retaining themes and facts outside the classification.

14. **[Review corrected and disputed knowledge](14-review-corrections-and-disputes.md)**  
   **Blocked by:** 05, 10.  
   **What it delivers:** Review held claims, apply supported corrections and keep current answers, earlier evidence and snapshot recovery consistent.

15. **[Trace evidenced connections between characters](15-trace-character-connections.md)**  
   **Blocked by:** 11, 13.  
   **What it delivers:** Explain a bounded connection between two characters with the meaning and evidence preserved at every step.

16. **[Investigate with bounded text and graph tools](16-investigate-with-bounded-tools.md)**  
   **Blocked by:** 09, 15.  
   **What it delivers:** Run an investigative route that combines captured evidence, stops within limits and exposes the actual tools and findings.

17. **[Route and escalate according to evidence](17-route-and-escalate.md)**  
   **Blocked by:** 16, 23.\
   **What it delivers:** Select an eligible route, escalate when evidence warrants it and show whether routing improves quality and total expense.

18. **[Validate Phil's voice without changing facts](18-validate-phil-voice.md)**  
   **Blocked by:** 08.  
   **What it delivers:** Demonstrate convincing Phil-style responses while preserving supported facts, uncertainty and respectful treatment of serious harm.

19. **[Establish checked graph coverage across the core roster](19-establish-core-graph-coverage.md)**  
   **Blocked by:** 06, 11, 13, 14.  
   **What it delivers:** Use the established pipeline across the 20 profiles, audit its coverage and answer reviewed graph questions with visible gaps.

20. **[Reproduce and accept the complete local demo](20-accept-complete-local-demo.md)**  
   **Blocked by:** 17, 18, 19, 24.\
   **What it delivers:** Run the complete local product and inspect reproducible software-test, component/e2e quality, latency and cost evidence against the text baseline, including the complete feedback-to-online-evaluation-to-review loop.

21. **[Capture response feedback and inspect live quality signals](21-capture-response-feedback.md)**  
   **Blocked by:** 07, 09.  
   **What it delivers:** Submit optional response feedback through the CLI/API, receive a durable receipt, and inspect trace-linked human assessments and live feedback metrics.

22. **[Evaluate live answers with feedback and close the review loop](22-evaluate-live-feedback.md)**  
   **Blocked by:** 08, 21.  
   **What it delivers:** Automatically evaluate original served interactions using feedback-directed and background samples, then review reports and promote checked failures into regression data within explicit limits.

23. **[Answer with fused retrieval and wider source context](23-fuse-text-retrieval-and-expand-context.md)**
   **Blocked by:** 03, 04.
   **What it delivers:** A conventional text answer using multi-query RRF and bounded sentence-window expansion, with citations and four measured retrieval ablations.

24. **[Reuse eligible text answers with a versioned cache](24-cache-repeated-text-answers.md)**
   **Blocked by:** 23, 05, 22.
   **What it delivers:** Repeated standalone questions reuse compatible supported answers, with invalidation, new serving identities, honest measurements and working feedback/online evaluation.

## Dependency review

- Plan numbers are stable identifiers, not execution order: new tickets 21–24 must finish before final acceptance in 20. One valid dependency order is 01–09, 21–22, 23–24, 10–19, 20. Start any ticket whose blockers are complete.
- After 01, the text-answer and real-source paths can proceed independently. After 03, conversation work (once identities exist), calibrated comparisons and execution limits can proceed alongside the first graph capability.
- Ticket 06 brings the complete text roster into use before the checked graph expansion in 19. The same generic pipeline supports future notable characters; family names do not define separate code features.
- Relationship histories and crime/justice build independently on 10. Other life events extend the actual shared-event path in 12. Connection queries compose those established capabilities in 15.
- The investigator depends on enforced execution boundaries and graph capabilities. Routing depends on real available routes. Persona refinement depends on calibrated evaluation, not on completion of graph work.
- Source recovery and claim admission join in 14. The core graph expansion in 19 needs working relationship/event semantics and review, but does not need automatic routing.
- Feedback capture in 21 uses conversation identity and execution boundaries; online evaluation in 22 also needs calibrated scorers. These can proceed before the graph routes are complete, with every later route preserving the same feedback/trace contract.
- Ticket 20 joins routing, persona, core graph coverage and the feedback/online-evaluation loop. All 23 other implementation tickets are ancestors of 20; cache plan 24 inherits feedback/online evaluation through 22 → 21 → 07.

Static planning validation: 24 uniquely numbered tickets; 41 blocking edges; no cycles or redundant transitive blocking edges; all 130 stories mapped; all 51 currently applicable checklist items have a primary evidence owner. These are document consistency checks, not product tests.

## Shared completion pattern

1. Read the agreed domain/spec decisions and identify affected checklist items. Reuse existing valid decisions without reopening the confirmed design.
2. Establish an independently reviewed expected behavior or a meaningful failing test before the smallest complete change. Expand the reference set before a new extraction/model pilot.
3. Implement through the relevant public path. Use exposed domain-rule tests, real database/application integrations and controlled substitutes only at external boundaries.
4. Run the relevant component and end-to-end checks, including counterexamples and failure outcomes. Budget and distinguish live-provider quality checks from deterministic fixtures; validate scoring code against independent expectations.
5. Record actual dataset/source/configuration/code/scorer identity, results, trace/evidence links, critical failures and measurement gaps. Keep costs of serving, online evaluation and offline evaluation separate where models run.
6. Update the evidence register. Pass requires evidence for the relevant revision; current-release failures stay blocking. Turn meaningful failures into reviewed regression cases.

This completion pattern applies throughout. It does not require irrelevant model judges for a deterministic slice, nor claim that every checklist item needs to be rerun after every edit.

## Publication record

GitHub is the configured tracker for `tomh1988-8/rag_demo`. The installed GitHub plugin published the [agreed specification as #1](https://github.com/tomh1988-8/rag_demo/issues/1) and the initial 20 approved tickets as #2–#21. The user's later scope amendment updated #1, #3, #8, #9, #10 and #21 and added #22–#23. Every issue has the ready-for-agent label. Independent remote readback confirmed the intended titles, bodies and labels. Initial issue publication performed no Git commit, branch or push.

Each ticket contains a Parent reference to specification #1, spec-story references, the approved acceptance criteria and checklist evidence, and real issue numbers in its Blocked by section. The [handoff](HANDOFF.md) maps every local plan number to its GitHub issue. Do not confuse plan number 01 with specification issue #1: the first implementation ticket is [issue #2](https://github.com/tomh1988-8/rag_demo/issues/2).

Native GitHub blocking relationships required by the skill remain outstanding. The connector has no dependency/sub-issue mutation tool, and gh/CLI credentials are unavailable. Readback confirms no native links were created. All 41 directed edges, including stable issue IDs, are saved for reconciliation when the capability becomes available; textual blocker references are not represented as native relationships.

## Approval recorded

The user approved this breakdown on 23 September 2026: “ok thats good lets proceed with those, store what you have to and when we are ready to move on I will trigger the next skill”. The [to-tickets skill](../../../.agents/skills/to-tickets/SKILL.md) review requirement is satisfied. That publication handoff was completed. The user subsequently invoked implement, starting issue #2; its current acceptance state is recorded in the handoff.

## Feedback and online-evaluation amendment

The user subsequently required the final product to enable user feedback and use it in online evaluations. [Primary-source research](../../research/feedback-and-online-evaluation.md) informed the updated specification, checklist v1.1 and two new complete behavior slices. This explicit request authorises the parent-spec amendment; original story IDs 1–98 and ticket IDs are preserved, with stories 99–116 appended. Feedback and automatic online evaluation are required during local use, before hosting. All new runtime evidence remains Pending.

## Fusion and cache amendment

The user explicitly requested this scope update and publication of local code.
The [research](../../research/rag-fusion-and-answer-caching.md) distinguishes RAG-Fusion
from surrounding-context expansion; both belong to conventional text retrieval.
Plans 23–24 add complete observable slices without enlarging the next basic-answer
ticket. Final acceptance requires both; the single-query baseline stays available
and semantic-cache matching remains a separately gated future extension.
The [amendment record](fusion-cache-amendment.json) records current scope validation.
