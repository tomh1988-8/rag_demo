# Source snapshot readiness deepening

Implements candidate 01 from the architecture review, selected by the user on
18 October 2026. The starting revision is
`22870fc3f353d55d719b731b0523665c86ea6d51`. The user authorized implementation,
review, a commit on the current branch and publication to GitHub.

## Accepted scope

Concentrate source snapshot readiness in the text retrieval module so answering,
recovery and corpus evaluation share version selection and compatibility rules.

- Pin the publication and captured source once per operation. Preserve explicit
  legacy snapshots, unpublished candidate rejection and withdrawn-publication
  rejection.
- Verify the configured embedding identity, source identity, index manifest and
  retained index artifacts before using a published snapshot. Preserve full
  artifact verification and the existing ranking and context-selection behavior.
- Keep a pinned source inspectable before index verification so a deadline during
  verification still produces the existing saved stop outcome and MLflow trace.
- Normalize direct and vector-adapter index/retrieval timeouts inside the module.
  Callers do not compare index manifests or interpret database adapter errors.
- Recovery validates the previous publication before changing the active pointer.
  A failed recovery preserves the current publication and retains a failed run.
- Retain source/citation/receipt identities, public HTTP/CLI contracts, execution
  accounting, request limits, bounded read-only access and historical evidence.

The comparison metadata mismatch and refresh journal deepening are separate
architecture candidates. This change retains the existing passage-context,
conversation-turn, evaluation-run and model-execution depth.

## Test seams

Use the existing confirmed text retrieval, source refresh/recovery and public
conversation/HTTP seams in [the testing strategy](../../design/testing-and-evaluation.md).
PostgreSQL/pgvector, Prefect and local MLflow remain real. Substitute only external
source/model adapters. The first tracer exercises a pinned legacy snapshot through
retrieval; subsequent slices cover publication compatibility and public outcomes.
Tests assert returned passages, publication identity, retained evidence and explicit
failure results. ADRs 0004, 0006 and 0007 continue to apply.

## Module and interface

`TextRetriever.pin` selects the publication and loads its source once. Its
`PinnedText` exposes the retained source and publication as read-only properties.
`verify` owns source/index compatibility and complete artifact verification;
`retrieve` enforces that verification before returning passages. Each pin belongs
to one operation and verifies published artifacts afresh; verification is retained
only within that pin, with no shared readiness or answer cache.

The two phases preserve tracing behavior: answer execution can retain the source
identity before bounded index verification, then save the same explicit timeout
outcome as before. Source selection failures retain the existing public errors.
Explicit legacy snapshots retain source-only clarification and their existing
prepared-index requirement when retrieving.

`TextRetriever.previous` validates the prior source/index pair before recovery can
restore its publication. The corpus evaluation script uses the same pin while
retaining its separate frozen-reference checks. Database timeout normalization
belongs to the retrieval implementation; answering no longer imports database
adapter errors or compares index manifests. Existing PostgreSQL, embedding and
external model adapters remain in place.
