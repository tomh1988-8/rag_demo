# 05: Ground follow-ups and reset conversations

Draft for breakdown review; not approved or published.

Spec story references: 7, 8, 9, 10, 83.

## What to build

A viewer can hold a session conversation, ask a question such as 'and who was their father?', clarify an ambiguous name, and reset the discussion. Each factual follow-up obtains supporting evidence again instead of treating generated conversation history as a source.

## Acceptance criteria

- [ ] Resolve reviewed follow-up references using session context and character identities, while retrieving evidence for every factual response from its selected captured snapshot.
- [ ] Demonstrate an ambiguous reference followed by a clarification and a supported answer; do not silently resolve genuinely ambiguous identities.
- [ ] Earlier generated text is not accepted as factual evidence, including when a previous answer contained an unsupported statement.
- [ ] Reset clears the session's conversational reference state and is observable through both API and CLI behavior; sessions do not require accounts or persistent personal memory.
- [ ] Partial and abstain outcomes work across turns, and citations, route, source version, and uncertainty remain consistent with the new retrieval.
- [ ] Add reviewed multi-turn cases covering successful reference resolution, ambiguity, misleading history, and reset; measure final-answer and evidence quality through the public conversation path.
- [ ] Before implementation, add independently reviewed reference cases and applicable failing tests at the confirmed public boundaries. Test observable behavior, not private methods, internal call order, or expectations recomputed by the implementation under test.
- [ ] Run relevant unit/integration checks and component/end-to-end evaluations for this slice, extending the existing baseline with versioned cases and actual evidence. Use real PostgreSQL where persistence matters, substitutes only at external source/model boundaries for routine runs, and separately budgeted live-provider checks where needed; report limitations and missing measurements honestly.

## Blocked by

- 02: Handle incomplete evidence and false premises
- 03: Resolve characters and keep sources in scope

