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
and all eight proposed synthetic labels match the narrow rubric. At that stage,
they remained agent-authored until actual human review.

Before live approval, the reviewer recorded live captures, human label review,
actual judge calibration and final MLflow comparison/readback as acceptance
blockers. The ticket remained open at that historical stage. The execution review
below supersedes that pending state. Neither a clean software review nor the
software test suite establishes model quality by itself.

## Execution evidence review

Both agents independently reviewed the continuation from published `e21e43d`.
No product implementation changed. The Spec agent separately reviewed all 28
original questions, answers, qualifications, final contexts and citations against
the retained source batch, preserving null identity labels and original-question
failures. The resulting annotation files explicitly record AGENT provenance;
Tom's human approval covers the eight synthetic labels, not live-answer review.

Standards verified both 14-response captures, all response/reference fingerprints,
actual MLflow stage spans, serving costs, unchanged human-approved examples and
absence of session/credential leakage. Both deterministic review reports
recompute exactly. The 24-observation calibration plan and report reproduce, and
the model/settings/rubric and $0.020680 cost match the records.

Both reviewers verified every support-application input against the independently
frozen plan and the $0.028290/16-call usage total. Eight boolean references agree;
all 20 null references remain unscored. Four identity-adjudication gaps and four
no-assertion/null-policy mismatches are separately retained for review. There are
no negative application labels, so its false-pass rate is unavailable. The
retained harness uses the public journal/judge interfaces, bounds spending and
retains unknown usage before failing. Standards reports zero material violations
or new smell findings.

Final Standards and Spec checks independently reproduce the entire comparison,
including the failed answer-quality gates, and verify all 76 source/input hashes.
Both directly read back seven FINISHED MLflow results, 41 declared frozen inputs,
16 related comparison artifacts and all 28 real serving-stage dictionaries. The
final XML has 248 tests and zero failures/errors/skips; its exact hash is bound to
the comparison and manifest. Both confirm the preserved $0.343084 shared ledger,
zero unsettled reservations and 118 entries.

The final Spec review finds all nine criteria covered within the declared
development/narrow-judge workflow scope, with no remaining material finding or
runtime acceptance blocker. Broad automatic support and release answer quality
remain unaccepted. **Standards: zero remaining findings. Spec: zero remaining
findings.** `live-validation.json` records the completed runtime checks;
`publication.json` separately records verified publication and tracker closure.
