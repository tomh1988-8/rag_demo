# Issue #17: bounded investigation

Ask Phil now accepts `--route investigation` through the CLI and the standalone
or session answer API. One investigator chooses captured text or typed graph
queries, gathers evidence in one sealed publication, assesses each requested part
and returns a supported answer or an explicit partial/abstention/stop outcome.

Work starts at `6294744`, after the reviewed shared graph executor. The live
[ticket](issue.json) and [parent specification](parent-spec.json) are retained.
#10 and #16 were read back as closed before implementation.

## Invocation and authority

```sh
ask-phil ask "Who are Ben Mitchell's biological parents, and who is Phil's mother?" \
  --route investigation
```

The active publication is the default. `--snapshot` selects an explicit compatible
publication; `--session` uses the existing private session receipt. The JSON request
is `{"question":"...","route":"investigation"}` on `/v1/answers` or session turns.
Investigation requires a published source/index/claim/graph manifest. Unsealed
legacy sources receive an explicit unavailable response.

The investigator is explicitly selected. It can request captured text or the four
typed graph query families. Source ingestion, mutation, arbitrary SQL/shell and
live-web access are absent from the dispatch contract. A single request budget
covers decisions, query embeddings, tools, repairs, HTTP, elapsed time, cumulative
evidence/context and conservative spending reservations. The actual five tool
contracts are `text_search`, `family`, `relationships`, `events` and `connections`.
Their schemas, capability mapping and descriptions have a recorded version/hash.
Graph results retain paths, edge/participant roles, source evidence and bounds.

Every requested part needs an explicit evidence sufficiency assessment before a
final answer. Stable distinct part labels, available evidence IDs and final
citations are validated; unresolved parts cannot become an `answered` outcome.
Semantic decomposition/support still needs evaluation. A relevant passage or the
model's own coverage statement does not establish complete support.

Default investigation limits are eight model calls (including query embeddings),
four tools, 24 HTTP calls, 180 seconds, 4,000 bytes of retained tool/evidence context,
$0.15 reserved spend, one concurrent investigation and zero HTTP retries. Serving
and offline investigation policies are separately configurable in
`ASK_PHIL_EXECUTION_POLICY`. The ordinary text default remains 1,200 context bytes;
the common configurable maximum is 6,000 bytes. Invalid arguments can be repaired
through another charged decision; identical normalized calls stop before another
tool execution. Missing billing retains its conservative reservation.

The neutral `investigation` appendix contains actual attempts/results, accepted
context, per-part assessment, each model execution's accounting and the real stop
reason. Unknown measurements stay null. Full citations survive bounded stop
wording. Complete correction/dispute groups retain their reviewed interpretation;
retrieving an old passage cannot re-establish a held claim.

## Development comparison

The [pre-call plan](run-plan.md) freezes three exposed questions/story groups and
the existing curated connection snapshot. [Smoke](live-smoke.json) and
[remaining pairs](live-comparison.json) contain six actual public API responses.
Each pair shares the exact source, retrieval-index and answer-model identities,
with a common 4,000-byte ceiling and the same $0.20 finite request caps. Every
root/tool output and citation was read back; original responses survive application
recreation. No read tokens are published.

[Independent source assessments](independent-quality-review.json) and the
[scored comparison](comparison-summary.json) separate factual support,
completeness, answerability, context sufficiency and orchestration diagnostics.
All nine factual claims pass correctness, actual-context grounding and citation
support. Both unsupported-question outcomes have no factual claims; their factual
rates are unavailable. All six answerability/relevance assessments pass.

| Measure | Text RAG | Investigation |
| --- | --- | --- |
| Completed reviewed tasks | 2/3 | 3/3 |
| Required facts covered | 2/3 | 3/3 |
| Supported/correct/cited factual claims | 4/4 | 5/5 |
| Reported serving inference cost | $0.0089510 | $0.0216754 |
| Mean complete API latency, three requests | 5.397 s | 9.159 s |
| Paid model calls | 3 | 7 |

The investigator's biological query acquires both parentage facts. Text RAG misses
Peggy's identity and honestly returns partial. Both routes answer the sufficient
pregnancy passage and abstain on the unsupported theme. All four live investigator
tool attempts are eligible and argument-valid; all three stops are expected and
within the recorded limits. Live repair/recovery has no denominator; the controlled
tests supply that evidence. Graph-only text ranking diagnostics are not used to
grade graph quality; required-fact context sufficiency is assessed separately.

Investigation adds cost and latency on these simple/unsupported cases. Two initial
queries add unrelated Ben Mitchell; final scope stays correct, but query relevance
and route necessity remain useful #18 diagnostics. The baseline context failure is
retained for #24. These curated exposed results do not establish automatic extraction,
wide-roster accuracy, independent canon corroboration or held-out release acceptance.

The local MLflow comparison run `0716a584990d4e70a92a4068e860447f` is FINISHED
with 168 read-back metrics, source/review artifacts and separate zero-cost offline
review. Raw serving traces are retained in `artifacts/issue-17-mlflow.db`.

The actual live responses belong to `b599783` and its recorded application hash.
The final software revision `13d38e0` repairs only SQL deadline handling and bounded
stop wording, with two new regressions. Prompt, model and tool contracts are
unchanged. The live comparison is not presented as a new execution of those repairs.

## Software and review

The confirmed investigation, text/typed-graph, conversation and scorer seams in
[the testing strategy](../../design/testing-and-evaluation.md) apply. TDD uses real
PostgreSQL/pgvector, actual HTTP/CLI and MLflow, with controlled external providers.
The [55 focused checks](focused-tests.xml), [two repaired stop regressions](review-regressions-final.xml)
and three independent scorer arithmetic/counterexample checks pass. Strict mypy
checks 125 files; Ruff and formatting pass. The final full suite passes **550 tests**
with no failures/errors/skips in 1,410.039 seconds. The
[complete log](software-tests.log) and [XML](software-tests.xml) are retained.
The [Docker build](docker-build.log) and [six container API/CLI/typed-graph checks](docker-tests.log)
also pass against the same frozen application fingerprint. The completion
[validation](validation.json) records all identities and preservation checks.

[Two-axis review](review.md) has zero remaining findings. Both original P2 findings
and the earlier disputed-claim bypass remain in [the regressions](regressions.json).
The [failed stop regressions](review-regressions-initial.xml) are preserved beside
their passing rerun. [Frozen software inputs](software-inputs.json) bind the full
suite to the final source. No held-out labels were inspected or changed.

Pre-existing changes, original data and the private inputs are frozen in the
ignored `artifacts/issue-17/preservation-start.json`. The shared, non-resetting
$5 trial ledger starts at $0.464981. Ten paid calls report $0.0306264 inference
charges; the upward-rounded shared ledger is **$0.495612**, with zero unsettled
reservations. The $1.20 additional live tranche was not exhausted. Offline source
review/scoring used zero model credits. Provider fees, local embeddings, hardware
and hosting remain outside reported inference charges.

All 39 original data files, 51 pre-existing workspace files and the private key
remain protected by the initial hash inventory. Final preservation/publication
readback is recorded in the completion validation and receipt. Routing (#18),
fusion (#24), broader graph coverage, feedback/online evaluation and release
acceptance retain their existing obligations. Checklist counts remain 35 Pass
and 16 Pending.
