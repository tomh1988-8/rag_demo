# Issue #18 implementation

Starting revision and review fixed point: `664541a` on the current `main` branch.
The existing README edit, agent skills, setup notes and private inputs are preserved.
The saved issue and parent specification define this slice.

Use the already confirmed boundaries in `docs/design/testing-and-evaluation.md`:
routing and bounded investigation, text retrieval and typed graph tools,
conversation API/CLI, and evaluation scorers. Start each behavior with a failing
public rule or API test, implement that slice, run the focused file and strict
typechecking regularly, then run the complete suite once at the end. Review both
standards and spec independently against the starting revision before publication.

Ordinary requests default to automatic selection. Conservative complete-question
templates propose one of the four typed graph families; admitted, source-bound
coverage and capability checks gate execution. Broader requests use the selected
versioned text policy. The text answer model assesses obtained evidence; explicit
rules permit at most one bounded investigation for an unresolved evidence gap.
This assessment is an observation, not an independent factual quality label.
Explicit route overrides remain visible and share all execution authority checks.

Retain one captured publication and request budget through every stage. Preserve
initial text evidence, its pipeline measurements, fallback outcomes and all model
accounting. A failed or exhausted escalation must not erase an earlier supported
partial answer. Record actual checks, executed stages, timings and stop reasons in
the public receipt and its actual MLflow root output.

Before paid work freeze source-reviewed development tasks and settings. Compare
always-text baseline, selected conventional policy, fusion/expansion candidates,
automatic routing and eligible route counterfactuals on the same captured corpus
and answer model. Disable answer caching. Count every serving model operation,
including failed decisions, optional fusion and investigation; separate indexing
and offline review expense and retain unavailable measurements. Use the original
non-resetting $5 ledger (initial $0.975588; no unsettled reservations), with a
finite additional run cap. Reserved acceptance story groups are not executed or
used to tune the policy. Preserve failures and avoid repeating unchanged paid work.
