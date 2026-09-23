# 09: Bound requests and enforce read-only execution

Status: published as [GitHub #10](https://github.com/tomh1988-8/rag_demo/issues/10); feedback/online-evaluation amendment authorised by the user on 23 September 2026. Remote body and ready-for-agent label verified. Implementation has not started.

Spec stories: S15, S35, S36, S37, S44, S45, S46, S47, S70, S72, S73, S74, S82, S86, S94, S109, S113, S116.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S15, S35, S36, S37, S44, S45, S46, S47, S70, S72, S73, S74, S82, S86, S94, S109, S113, S116.

## What to build

Make the existing text-answer request enforce finite execution and authority boundaries programmatically, including relevant failure and adversarial cases. Keep answering confined to captured data. Expose the same budget and cancellation contract for later graph/investigative tools without building speculative multi-agent infrastructure.

## Acceptance criteria

- [ ] Restrict the answering path to declared read-only retrieval capabilities and approved model endpoints. Ingestion/refresh stays a separate maintainer operation; retrieved text cannot authorise live browsing, arbitrary SQL, shell execution or source mutation.
- [ ] Validate request/tool inputs and outputs at their public boundaries. Exercise retrieved instruction attempts, malformed tool data and evidence that asks the system to ignore its task; the execution boundary must remain enforced outside the prompt.
- [ ] Enforce configured finite model/tool-call, time, context and spending bounds, bounded retries and cancellation. Reserve/estimate cost conservatively where exact usage arrives after a call; unknown usage must not silently grant unlimited work. Document the scope and limitations of provider and application controls.
- [ ] On timeout, cancellation, provider failure or budget exhaustion, stop further work and return supported findings where possible with the actual stop reason. Do not present a limit as evidence that an event never occurred.
- [ ] Keep credentials out of source fixtures, prompts, emitted traces and logs. Demonstrate redaction on representative error and tool paths without logging real secrets.
- [ ] Start with failure cases and unit-test exposed limit arithmetic/validation. Integration-test the public API with controlled slow, failing and malformed external services, observing actual calls, cancellation and stored trace outcomes. These are behavior checks, not assertions of one private call sequence.
- [ ] Define separately bounded online-evaluation call/time/spend/concurrency/retry controls alongside serving and offline limits, with shared provider spending protection and observable disabled/pending/failed/skipped outcomes. Later background evaluation must not block answering or acquire new answering-agent tools.
- [ ] Apply validation, length/rate limits, access checks and redaction to later explicit user-feedback submissions and judge inputs. Feedback storage/assessment writes are deterministic application operations; raw comments cannot authorise actions or alter canon. The feedback tickets implement and exercise these controls on their new public paths.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-07.1, AD-07.2 | Enforced capability/argument boundaries and retrieved-instruction/malformed-output regression results. |
| AD-07.3, AD-07.4 | Redaction, finite-budget, cancellation, retry and partial-failure evidence through the public request path. |

Recheck when: New tool/resource, model/provider, credential handling, context/budget accounting, retry policy or cancellation behavior.

## Blocked by

- #4 — Handle incomplete evidence and false premises: Actual request, evidence and failure outcomes are needed to verify enforcement through the public application.

