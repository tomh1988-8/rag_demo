# Issue #17: bounded investigation

Work starts at `6294744`, after the reviewed shared graph executor. The live
[ticket](issue.json) and [parent specification](parent-spec.json) are retained.
#10 and #16 were read back as closed before implementation.

The confirmed routing/bounded investigation, text/typed graph, conversation
API/CLI and evaluation seams in [the testing strategy](../../design/testing-and-evaluation.md)
apply. No new seam is introduced. Use one red/green slice at a time, controlled
external model services with real PostgreSQL and MLflow, then a bounded live
same-corpus/same-answer-model comparison. Held-out data remains untouched.

The investigator is explicitly selected. It can request captured text or the four
typed graph query families. Source ingestion, mutation, arbitrary SQL/shell and
live-web access are absent from the dispatch contract. A single request budget
covers decisions, query embeddings, tools, repairs, HTTP, elapsed time, cumulative
evidence/context and conservative spending reservations. Every requested part
needs an explicit evidence sufficiency assessment before a final answer.

Pre-existing changes, original data and the private inputs are frozen in the
ignored `artifacts/issue-17/preservation-start.json`. The shared, non-resetting
$5 trial ledger starts at $0.464981, with zero unsettled reservations. Preserve
that ledger and record complete serving expense separately from offline review.

Validation and measured quality evidence will be recorded here after execution.
