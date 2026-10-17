# Reviewed conversation cases — development v1

Fixed before implementing each behavior. References come from the captured core
catalogue and source passages, never from a candidate answer. These are agent
reviewed development cases, not human adjudication, independent canon checks or
held-out labels. All Phil/Grant arrival variants share one story group; Kat alias
variants share one group. The software fixture is synthetic and labelled as such.

| Case | Input / setup | Independently expected behavior |
| --- | --- | --- |
| reference-success | Ask about Phil Mitchell, then “When did he first arrive in Walford?” | Resolve to `phil-mitchell`; retrieve current snapshot evidence again. Captured Phil source states February 1990. |
| alias | Ask about Kat Moon, then “Who is her father?” | Resolve the reviewed alias to `kat-slater`. Captured Kat source identifies Charlie Slater. |
| ambiguity | Mention Phil Mitchell and Grant Mitchell, then “When did he arrive?” | Clarify both plausible identities; no factual claims or model generation. An explicit selection can recover the pending question. |
| misleading-history | Controlled provider falsely says Phil arrived in 2001. Follow up about his arrival. | Retrieve original source again; never put the false assistant statement in the new prompt. Final answer is independently assessed against February 1990. |
| no-context | First question “When did he arrive?” | Clarification, never infer a subject from retrieval prominence. |
| reset | Ask about Phil, reset, then “When did he arrive?” | New-context clarification. Old response/trace/turn identities remain unchanged. |
| isolation | Session A names Phil; session B asks “When did he arrive?” | B clarifies; wrong credentials cannot access or reset A. |
| truncation | Retain at most eight turns; a reference absent from retained state | Clarify rather than recovering old identities from saved responses/traces. |
| lifetime | Thirty minutes idle, two hours absolute | Idle state clears; expired session credentials fail. No sliding absolute lifetime. |
| feedback-lineage | Save answer, reset, inspect answer and anonymous feedback context | Immutable response links session/turn/generation to its trace. Separate feedback capability lasts thirty days and never feeds answer state. Submission is #22. |
| restart / concurrency | Recreate API, concurrent turns/reset on same session | Reference state survives within lifetime; per-session operations serialize without crossing sessions. |
| reviewed repairs | Former wife; object “her”; explicit new alias; lowercase Cindy Williams/Max Bowden; surname choice | Preserve relationship wording and pronoun roles; never infer an unknown character from a partial/performer name; resume the pending question after selection. These regressions reproduce independent review findings. |

Seams: approved conversation API/CLI, public reference/state rules within that
boundary, real PostgreSQL/pgvector, and controlled external model HTTP responses.
Software results do not establish live model quality. Final acceptance separately
reviews persona wording, facts, actual supplied evidence, citations, outcomes and
reset using a small live Sol sample (maximum 12 model calls and $0.25 additional
reported inference spend, inside the existing non-resetting $5 shared ledger).
