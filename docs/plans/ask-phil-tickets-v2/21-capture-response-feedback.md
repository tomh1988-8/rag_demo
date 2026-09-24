# 21: Capture response feedback and inspect live quality signals

Status: published as [GitHub #22](https://github.com/tomh1988-8/rag_demo/issues/22); fusion/cache scope amendment requested on 23 September 2026. Publication readback is recorded in the manifest. Implementation has not started.

Spec stories: S99, S100, S101, S102, S103, S105, S108, S110, S113, S115, S125, S126.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S99, S100, S101, S102, S103, S105, S108, S110, S113, S115, S125, S126.

## What to build

A user can optionally rate a selected Ask Phil response and explain a problem through the CLI/FastAPI path. The submission receives an honest receipt, is durably associated with the actual served interaction and appears as distinguishable human feedback in MLflow and an inspectable live feedback summary. This is working feedback collection and use, not a standalone storage layer or a requirement for users to open MLflow.

## Acceptance criteria

- [ ] Offer helpful/not-helpful/skip and optional categories for facts, missing/outdated information, evidence, clarity, persona/tone or other, with bounded comment/proposed-correction text. Conversation and reset remain usable without feedback; no account or graphical client is introduced.
- [ ] Resolve authorised feedback to an opaque response identifier, original final answer, context/evidence, turn/session, source/graph snapshot, actual route and application/prompt/model trace versions. Reject invalid or other-session references; clients cannot supply arbitrary MLflow write targets.
- [ ] Persist feedback identity, revision, timestamp and reliable delivery state in PostgreSQL and publish human-origin assessments to the original MLflow trace. Acknowledge saved feedback only after durable acceptance; delayed trace export or MLflow outage leaves recoverable pending delivery. Retry idempotently, and count a changed rating once as the current rating while retaining revision history.
- [ ] Use every accepted current feedback item in a live summary and review-priority list, separating helpfulness from reported factual errors and independently reviewed correctness. Define served-time cohorts, feedback-as-of cutoff, eligible/rated/positive/negative counts and denominators. No feedback is not a positive rating; revisions and repeated delivery do not manufacture additional people or interactions.
- [ ] Explain evaluation use and configure minimal identifiers, access, redaction and bounded retention before capture. Treat comments as untrusted data, keep them out of retrieval/conversation memory and minimise external disclosure. Verify reset cannot mix sessions or reassign historical feedback.
- [ ] Before implementation, define reviewed success/counterexample cases and exposed-rule tests. Integrate real PostgreSQL, local MLflow and the API/CLI for positive/negative/skip, optional comments, duplicate/revised input, invalid/cross-session response IDs, reset, delayed trace export, restart and failed delivery. Verify resulting records and assessments, not just a success message.
- [ ] Test summary arithmetic against independent expected counts, including no ratings, zero denominators and late/revised feedback. Demonstrate normal CLI use reaching a human assessment and changed live feedback summary. Raw feedback never edits source claims or becomes a gold expectation.
- [ ] Update the checklist evidence register with revision-linked results, failures and limitations. Required runtime evidence remains Pending until demonstrated.

- [ ] Preserve the contract that feedback addresses a delivered response, not a reusable answer value. The later cache slice must issue new response/trace identities and inherit evidence lineage without exposing another session or reusing its feedback.

## Checklist evidence

The ticket implementer owns runtime evidence; the project owner/maintainer owns quality review and acceptance. Preserve the six confirmed public test boundaries.

| Checks | Evidence required for completion |
| --- | --- |
| ONLINE-01 | Public feedback/receipt contract; original response/trace linkage; real storage/MLflow and access/idempotence/revision results. |
| AD-06.2, AD-07.2, AD-07.3, AD-09.1, AD-09.2 | Reviewed API/CLI cases, source/version attribution, redaction/retention checks and recoverable delivery evidence. |
| ONLINE-03, AD-10.4 | Live feedback summary with explicit denominators, revision handling and an inspectable review-priority record. |

Recheck when: Feedback contract, response/session identity, MLflow integration, revision/counting rules, data-use/retention or input/access controls.

## Blocked by

- #8 — Grounded conversation supplies stable turn/session identity and reset/isolation behavior.
- #10 — The public input, redaction, authority and finite-resource controls must exist before accepting feedback and scheduling assessment work.
