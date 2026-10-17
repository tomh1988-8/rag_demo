# Independent review

Fixed point: `07a4be2f405051da8ce5edf46957a2590f657d40`.
Both reviewers used the staged implementation diff against that point, including
new files. The spec reviewer read current GitHub #9 and parent #1, the source
references and actual pending execution state. Standards sources were AGENTS.md,
CONTEXT.md, the testing strategy, applicable ADRs and the code-review skill's
Fowler smell baseline. Tool-enforced checks were excluded from smell findings.

## Standards

Initial review: no hard standards violations; one low-priority Duplicated Code
finding in the two maximum-call calculations. The shared `maximum_call_cost`
helper now uses the same request/framing constants as the OpenRouter adapter.

Re-review: “The Duplicated Code finding is fixed: both capture paths use
maximum_call_cost, whose bounds share the adapter's constants. No new material
Standards findings.” The reviewer ran 18 focused comparison/judge tests, all
passing. **Standards: zero remaining findings.**

## Spec

The initial review found three software defects:

1. Unknown serving/judge costs left the prior known total in failed journals.
   Both paths now retain `cost_usd: null`, known accumulated cost and the current
   usage/reservation. Public API and external-provider regressions cover them.
2. Controlled comparisons ignored source identity. Runs now retain and compare
   the commit and application fingerprint. Both altered-source cases are tested.
3. Judge enablement could pass without an independent validation partition.
   Positive and negative reviewed labels are now required in both partitions,
   together with every planned repeat/order/verbosity observation.

Re-review: “All three findings are fixed in the staged changes.” The reviewer
ran the 18 comparison/judge tests and inspected the API regression. **Spec:
zero remaining software findings.**

The source review found that the frozen required facts match retained passages
and all eight proposed synthetic labels match the narrow rubric. They remain
agent-authored until actual human review.

The reviewer separately records live captures, human label review, actual judge
calibration and final MLflow comparison/readback as acceptance blockers.
**Ticket #9 remains open.** Neither a clean software review nor the software test
suite establishes calibrated model quality.
