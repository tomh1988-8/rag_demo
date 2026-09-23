# 07: Ground follow-ups and reset conversation

Status: published as [GitHub #8](https://github.com/tomh1988-8/rag_demo/issues/8); feedback/online-evaluation amendment authorised by the user on 23 September 2026. Remote body and ready-for-agent label verified. Implementation has not started.

Spec stories: S06, S07, S08, S09, S10, S19, S66, S71, S72, S73, S83, S86, S102, S113.

## Parent

#1 — Ask Phil: evidence-backed EastEnders RAG demonstration — specification

Spec stories: S06, S07, S08, S09, S10, S19, S66, S71, S72, S73, S83, S86, S102, S113.

## What to build

Extend the shared conversation API and CLI to use session context for references while retrieving factual evidence again on every turn. A user can ask follow-ups, receive useful clarification when identity remains ambiguous and reset the conversation. Persistent personal memory is outside this release.

## Acceptance criteria

- [ ] Resolve reviewed multi-turn references through stable character identities and known aliases. Ask a clarifying question when context leaves more than one plausible intended character.
- [ ] Retrieve supporting evidence for every factual response. A previous assistant assertion, including an intentionally misleading one in a test, never becomes source evidence.
- [ ] Define finite context limits and session-state lifetime. Keep sessions isolated and make truncation or missing conversational context produce clarification rather than fabricated references.
- [ ] Reset through both the API and CLI removes prior reference context; a subsequent ambiguous question behaves as a new conversation. Do not introduce account or long-term-memory features.
- [ ] Before adding each behavior, create reviewed multi-turn success, ambiguity, misleading-history, reset and session-isolation cases. Unit-test public reference/state rules and integration-test real application/database interactions with controlled provider responses.
- [ ] Evaluate final persona answers, evidence, clarification and reset through the public conversation path, with actual traces and separate factual/support outcomes; include a budgeted live-model sample.
- [ ] Keep turn/session and response identity sufficient to associate authorised later feedback with the exact earlier answer. Reset clears conversational context without relabelling historical traces or making evaluation records available as answer memory. Define the opaque local feedback context/lifetime without adding user accounts; the feedback ticket exercises its submission behavior.
- [ ] Record applicable checklist results and revision-linked evidence in the project register, including failures, limitations and follow-up regressions. A documented plan alone does not pass an implementation check.

## Checklist evidence

The ticket implementer owns these results; the project owner accepts scope and release thresholds. Reuse still-valid evidence, extend affected component and end-to-end cases, and keep software tests and model-quality evaluations distinguishable.

| Checks | Evidence required for completion |
| --- | --- |
| AD-05.3 | Context/state/reset contract with multi-turn, truncation and session-isolation results. |
| AD-06.3, AD-06.4, RAG-03 | Reviewed conversation regressions showing fresh evidence retrieval despite misleading generated history. |

Recheck when: Conversation state, context truncation, identity resolution, reset semantics or prompt/model changes.

## Blocked by

- #4 — Handle incomplete evidence and false premises: The conversation already needs correct clarification, partial and abstention outcomes.
- #5 — Import real sources with character identity and canon scope: Stable character identities and aliases are needed to resolve conversational references.

