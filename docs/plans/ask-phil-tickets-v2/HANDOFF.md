# Ask Phil: publication and next-skill handoff

Updated 25 September 2026. The user approved the initial checklist/ticket breakdown, authorised publication, and subsequently required user feedback and online evaluation. Checklist v1.1 and the amended 24-ticket breakdown are published. Issues #2 and #3 are complete and closed. Issue #4 now passes its scoped cloud policy acceptance, with publication and closure handled as the final steps below.

## Issue #4: scoped cloud acceptance passed

[Issue #4](https://github.com/tomh1988-8/rag_demo/issues/4) passes the independently
reviewed 13-case policy matrix and five actual CLI/API/restart checks with
`config/openrouter-sol.json`. Full software validation passes 85 tests, Ruff and
strict mypy. [Cloud evidence](../../implementation/issue-4/cloud/README.md) retains
all failed attempts, reviewed regressions and the date-policy prompt repair.
Reference labels remain unchanged; no critical failures remain in the final matrix.

The [OpenRouter setup](../../implementation/openrouter-setup.md) uses the locally
entered key, verified non-resetting $5 provider cap and shared persistent ledger.
The 32 paid attempts cost $0.10890587, leaving $4.89109413. Preserve both private
key and ledger. Qwen failed its smoke; GLM remains untested. This scoped evidence
does not establish held-out reliability, human calibration or broad canon accuracy.
Publish the reviewed tree, verify it against GitHub, then close #4. Check the live
issue for closure readback; the final receipt is ignored local evidence.
The temporary cloud API was stopped; existing Docker API/MLflow containers still
use #3. A persistent cloud deployment has not been configured.

## Published and verified

- [Specification #1](https://github.com/tomh1988-8/rag_demo/issues/1) contains the agreed specification with the feedback/online-evaluation and fusion/cache amendments (130 stories).
- Implementation tickets **#2–#25** are published and labelled `ready-for-agent`. **#2 and #3 are closed as completed**; #4 has passed scoped acceptance and closes after verified publication. #5–#25 remain open.
- All 25 remote bodies, states and ready-for-agent labels were read back and checked against the intended content after the fusion/cache amendment.
- The 41 blocking relationships are recorded as real issue references in ticket bodies and as a machine-readable mapping in [publication.json](publication.json).
- Issue #2 has a reviewed captured seed, CLI/API/PostgreSQL behavior, 17 passing tests in both native and Docker environments, and recorded deterministic baseline outputs. [Fresh Compose startup and database/API restart passed](../../implementation/issue-2/README.md); no generative model quality is claimed. GitHub closure and all seven checked criteria were read back and verified.

The [to-spec skill](../../../.agents/skills/to-spec/SKILL.md) authorised specification publication and the [to-tickets skill](../../../.agents/skills/to-tickets/SKILL.md) authorised the approved ticket publication. The installed GitHub plugin performed the remote operations. The user's explicit amendment request authorised updating parent specification #1. Their later Docker setup request authorised closing #2 once its remaining acceptance checks passed.

## First available work

**[#5 — Import real sources with character identity and canon scope](https://github.com/tomh1988-8/rag_demo/issues/5)** is recommended next, using `<pro>` for source ingestion and provenance. Once #4 is closed, #9 (calibrated comparisons) and #10 (execution boundaries) also become unblocked. Wait for the next implementation instruction before starting another ticket. Specification #1 remains parent context.

For subsequent work, read the current issue and comments, the relevant domain/ADR decisions and the checklist profile. Work the dependency frontier; the shared `ready-for-agent` label does not mean a blocked ticket can begin. Existing approved decisions and the six public test boundaries do not need another design interview.

## Plan-to-issue mapping

The “Blocked by” column contains **GitHub issue numbers**, which differ from local plan numbers because specification #1 was published first. Plan IDs remain stable; they are not execution order. New plans 21–24 must finish before final acceptance in plan 20.

| Plan ticket | GitHub issue | Title | Blocked by GitHub issues |
| --- | --- | --- | --- |
| 01 | [#2](https://github.com/tomh1988-8/rag_demo/issues/2) | Inspect captured source evidence locally | None |
| 02 | [#3](https://github.com/tomh1988-8/rag_demo/issues/3) | Generate a grounded Ask Phil answer | [#2](https://github.com/tomh1988-8/rag_demo/issues/2) |
| 03 | [#4](https://github.com/tomh1988-8/rag_demo/issues/4) | Handle incomplete evidence and false premises | [#3](https://github.com/tomh1988-8/rag_demo/issues/3) |
| 04 | [#5](https://github.com/tomh1988-8/rag_demo/issues/5) | Import real sources with character identity and canon scope | [#2](https://github.com/tomh1988-8/rag_demo/issues/2) |
| 05 | [#6](https://github.com/tomh1988-8/rag_demo/issues/6) | Refresh and recover a captured snapshot | [#5](https://github.com/tomh1988-8/rag_demo/issues/5) |
| 06 | [#7](https://github.com/tomh1988-8/rag_demo/issues/7) | Answer from all 20 core character profiles | [#3](https://github.com/tomh1988-8/rag_demo/issues/3), [#6](https://github.com/tomh1988-8/rag_demo/issues/6) |
| 07 | [#8](https://github.com/tomh1988-8/rag_demo/issues/8) | Ground follow-ups and reset conversation | [#4](https://github.com/tomh1988-8/rag_demo/issues/4), [#5](https://github.com/tomh1988-8/rag_demo/issues/5) |
| 08 | [#9](https://github.com/tomh1988-8/rag_demo/issues/9) | Inspect calibrated quality comparisons | [#4](https://github.com/tomh1988-8/rag_demo/issues/4) |
| 09 | [#10](https://github.com/tomh1988-8/rag_demo/issues/10) | Bound requests and enforce read-only execution | [#4](https://github.com/tomh1988-8/rag_demo/issues/4) |
| 10 | [#11](https://github.com/tomh1988-8/rag_demo/issues/11) | Answer biological family questions from admitted claims | [#4](https://github.com/tomh1988-8/rag_demo/issues/4), [#5](https://github.com/tomh1988-8/rag_demo/issues/5) |
| 11 | [#12](https://github.com/tomh1988-8/rag_demo/issues/12) | Explain family and romantic histories | [#11](https://github.com/tomh1988-8/rag_demo/issues/11) |
| 12 | [#13](https://github.com/tomh1988-8/rag_demo/issues/13) | Explain crimes and criminal justice roles | [#11](https://github.com/tomh1988-8/rag_demo/issues/11) |
| 13 | [#14](https://github.com/tomh1988-8/rag_demo/issues/14) | Explain life events, themes and unclassified facts | [#13](https://github.com/tomh1988-8/rag_demo/issues/13) |
| 14 | [#15](https://github.com/tomh1988-8/rag_demo/issues/15) | Review corrected and disputed knowledge | [#6](https://github.com/tomh1988-8/rag_demo/issues/6), [#11](https://github.com/tomh1988-8/rag_demo/issues/11) |
| 15 | [#16](https://github.com/tomh1988-8/rag_demo/issues/16) | Trace evidenced connections between characters | [#12](https://github.com/tomh1988-8/rag_demo/issues/12), [#14](https://github.com/tomh1988-8/rag_demo/issues/14) |
| 16 | [#17](https://github.com/tomh1988-8/rag_demo/issues/17) | Investigate with bounded text and graph tools | [#10](https://github.com/tomh1988-8/rag_demo/issues/10), [#16](https://github.com/tomh1988-8/rag_demo/issues/16) |
| 17 | [#18](https://github.com/tomh1988-8/rag_demo/issues/18) | Route and escalate according to evidence | [#17](https://github.com/tomh1988-8/rag_demo/issues/17), [#24](https://github.com/tomh1988-8/rag_demo/issues/24) |
| 18 | [#19](https://github.com/tomh1988-8/rag_demo/issues/19) | Validate Phil's voice without changing facts | [#9](https://github.com/tomh1988-8/rag_demo/issues/9) |
| 19 | [#20](https://github.com/tomh1988-8/rag_demo/issues/20) | Establish checked graph coverage across the core roster | [#7](https://github.com/tomh1988-8/rag_demo/issues/7), [#12](https://github.com/tomh1988-8/rag_demo/issues/12), [#14](https://github.com/tomh1988-8/rag_demo/issues/14), [#15](https://github.com/tomh1988-8/rag_demo/issues/15) |
| 20 | [#21](https://github.com/tomh1988-8/rag_demo/issues/21) | Reproduce and accept the complete local demo | [#18](https://github.com/tomh1988-8/rag_demo/issues/18), [#19](https://github.com/tomh1988-8/rag_demo/issues/19), [#20](https://github.com/tomh1988-8/rag_demo/issues/20), [#25](https://github.com/tomh1988-8/rag_demo/issues/25) |
| 21 | [#22](https://github.com/tomh1988-8/rag_demo/issues/22) | Capture response feedback and inspect live quality signals | [#8](https://github.com/tomh1988-8/rag_demo/issues/8), [#10](https://github.com/tomh1988-8/rag_demo/issues/10) |
| 22 | [#23](https://github.com/tomh1988-8/rag_demo/issues/23) | Evaluate live answers with feedback and close the review loop | [#9](https://github.com/tomh1988-8/rag_demo/issues/9), [#22](https://github.com/tomh1988-8/rag_demo/issues/22) |
| 23 | [#24](https://github.com/tomh1988-8/rag_demo/issues/24) | Answer with fused retrieval and wider source context | [#4](https://github.com/tomh1988-8/rag_demo/issues/4), [#5](https://github.com/tomh1988-8/rag_demo/issues/5) |
| 24 | [#25](https://github.com/tomh1988-8/rag_demo/issues/25) | Reuse eligible text answers with a versioned cache | [#24](https://github.com/tomh1988-8/rag_demo/issues/24), [#6](https://github.com/tomh1988-8/rag_demo/issues/6), [#23](https://github.com/tomh1988-8/rag_demo/issues/23) |

## Saved context

- [Approved ticket breakdown](README.md), including rationale and the common evidence-completion pattern.
- [Reusable checklist v1.1](../../checklists/agent-development.md).
- [Ask Phil applicability profile and evidence register](../../checklists/ask-phil-profile.md): 51 current items, one deployment deferral and 12 N/A items. Three items pass on design evidence, five on inspection, five on initial text RAG and two on #4 software counterexamples/quality measurement; 36 current obligations remain Pending. #4's scoped Sol policy acceptance now passes; this does not discharge full-product comparison, calibration, graph, fusion, cache or online-feedback obligations.
- [All 130 specification stories mapped to tickets](spec-coverage.md).
- [Local specification](../../specs/ask-phil.md), [test/evaluation strategy](../../design/testing-and-evaluation.md), [domain glossary](../../../CONTEXT.md) and [architecture decisions](../../adr/).
- [Publication manifest](publication.json), including issue IDs/URLs, approval, source fingerprints, readback verification and the outstanding native relationship operations.

The [feedback/online-evaluation research](../../research/feedback-and-online-evaluation.md) and [amendment record](feedback-amendment.json) capture the new requirement. Optional user feedback is linked to original served responses; all accepted current feedback informs metrics/triage, and automatic bounded evaluation samples both reported and unrated interactions. Late/revised feedback, truthful denominators, review dispositions and source-checked regression promotion are mandatory locally. Hosted operations remain deferred; raw feedback is not factual ground truth or training data.

Model/provider versions, numerical spending/call limits, dataset sizes and acceptance thresholds remain setup/pilot choices. Choose conservative limits before paid calls; establish reviewed cases before model work; set measured thresholds before viewing held-out candidate acceptance results.

## Remaining tracker limitation

**Native dependency links have not been created.** GitHub readback reports zero native blocking links. The connector can create/update issues and labels but exposes no dependency/sub-issue mutation tool. The `gh` executable and normal CLI authentication sources are unavailable.

The to-tickets skill says: “Use the platform's native blocking / sub-issue relationship where it has one”. Its native-link requirement therefore remains outstanding; textual references are not a claim that it has been satisfied. The first unblocked ticket can still be identified from the saved mapping.

Following the user's request to investigate alternatives, the [access review](../../research/github-issue-dependency-access.md) found no additional suitable plugin in the available catalog. GitHub's official MCP server offers experimental dependency-write tools, and its REST API/CLI also support native links, but each alternative requires a separate authenticated setup. The recommendation for this handoff is to keep the working blocker references and revisit native links only when that connection is requested or becomes available. Do not repeat this investigation on every implementation turn.

When an authenticated native relationship-write capability is available, use the existing issue IDs in the manifest, inspect existing links, add only the missing 41 directed blocking edges and verify the resulting relationships. Do not recreate the published issues, convert the parent spec into implementation work, or change the agreed dependency graph. No new permission for these already approved relationships is implied by this handoff.

Issue #2 is complete. Docker Engine 29.8.1 and Compose 5.5.1 remain installed and enabled; the acceptance project was stopped with its data volume retained. Runtime evidence and the installer are saved locally. No commits were pushed during acceptance.

## Current fusion/cache and code-publication handoff

The user requested fusion/context expansion and repeated-question caching before
the next implementation. [Research](../../research/rag-fusion-and-answer-caching.md)
and [scope validation](fusion-cache-amendment.json) describe the changes. GitHub #24
and #25 own the new behavior; #18 and #21 include their actual prerequisites.
After completion of #4, #5 is recommended next. Neither new feature is implemented.

Historical issue #2 publication: the validated code was published on GitHub `main` at `1a186fd1c6cbf306742a7ef6868f5b2cded58df2`,
whose tree exactly matches local `e5ac34c`. Publication used the authenticated GitHub
connector because command-line Git has no push credentials. `origin` is configured;
do not confuse connector publication commits with the original local commit IDs.
The planning amendment is published as a subsequent repository update. Preserve
both histories when reconciling native Git; never force-push over published work.

## Completed grounded-answer slice and model migration

Issue #3 is closed after [recorded acceptance](../../implementation/issue-3/README.md):
real LlamaIndex/pgvector retrieval, sourced basic Phil-style answers, private original
response lookup, MLflow traces and separated usage/cost evidence. The complete
Docker suite passes 32 tests. Persona and token-accounting failures are retained;
the final traces correct the aggregate and explicitly label incomplete usage.
The [review](../../implementation/issue-3/review.md) has zero remaining findings
on either axis. This is a one-passage exposed development baseline, not broad quality.

The user explicitly limits local Gemma 4 E2B QAT to convenient development/smoke
work. Recommend and configure a more capable model before broad-roster answer
acceptance (#7), representative evaluation (#9), or substantive extraction (#11
onward), or sooner if local-model weaknesses prevent useful progress. **That gate was reached and satisfied for the policy slice in #4.**
The Sol baseline and conservative key/account/request controls are recorded above;
re-evaluate for broader corpus or extraction work. No paid API calls were used for #3.

The running Compose project is `ask-phil-issue3`; use `docker compose -p ask-phil-issue3`
to reuse its installed model/data volumes. API: localhost:8000; MLflow: localhost:5000.
The old host Ollama/Qwen installation is unchanged. See the evidence README for
startup, lookup and stop commands.

The implementation and this handoff are committed together. Publication uses the
authenticated GitHub connector because native Git lacks push credentials, and
must verify an exact local/remote tree match before reporting completion. The
publication receipt is saved locally in ignored `artifacts/issue-3-github-publication.json`;
GitHub commit history records the published revision. Preserve both histories on
reconciliation; do not force-push. Fusion, caching and feedback remain later tickets.
