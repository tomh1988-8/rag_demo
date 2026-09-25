# Issue #4 cloud acceptance — 25 September 2026

**The Sol profile passes the scoped response-policy acceptance.** All 13 exposed
development cases and five actual CLI/API responses passed independent semantic
review. The full software suite passed 85 tests. This completes the model-quality
work for #4. [Publication](https://github.com/tomh1988-8/rag_demo/commit/a5062593449a941d28248614e1f3977d14fc9a57) was verified against the exact
reviewed tree, and GitHub closure was read back as completed.

The accepted profile is `config/openrouter-sol.json`: provider OpenAI,
`openai/gpt-6-sol`, canonical version `openai/gpt-6-sol-20260922`, medium reasoning,
8192 completion tokens including reasoning. Local embedding, snapshots, retrieval
and context budgets are unchanged. Selecting the profile is explicit; the running
issue-3 Docker API has not been switched to cloud inference.

## Retained attempts and the repair

| Capture | Paid attempts | Reported cost | Result |
| --- | ---: | ---: | --- |
| [Qwen smoke](qwen-smoke-v1.json) | 1 | $0.00044787 | Rejected invented citation IDs; served safe technical failure. |
| [Sol smoke](sol-smoke-v1.json) | 1 | $0.003688 | Correct supported arrival answer. |
| [Sol matrix v1](sol-policy-v1.json) | 12 | $0.043868 | 12/13 appropriate outcomes; one critical false-citation defect. |
| [Targeted repair](sol-unknown-date-v2.json) | 1 | $0.0041385 | Unknown-date case passes after prompt clarification. |
| [Sol matrix v2](sol-policy-v2.json) | 12 | $0.0497655 | All 13 cases pass independent review; zero critical failures. |
| [Actual CLI/API](sol-cli-v1.json) | 5 | $0.006998 | All five cases pass; citations resolve and original receipts survive restart. |

The empty-context case in each matrix bypasses generation. There were **32 paid
attempts**, no automatic retries and no provider fallback. Qwen's invented citation
and incorrect synthetic label belong to the rejected draft; they were not served
as facts. One rejected smoke does not establish a general model ranking. GLM remains
untested.

Sol v1 correctly said a hearing date was unknown but marked the question fully
answered and called the publication/broadcast dates different from the unknown
story date. The latter is unsupported calendar inequality, a served critical
false-citation defect. The prompt now explicitly requires a partial answer, the
missing date in both answer and unanswered fields, and wording that those other
dates **do not establish** the story date. Missing timing is not an explicit
negative claim about an event. Both defects remain in
[regressions v2](../../../../data/references/answer-policy-regressions-v2.json),
alongside the historical local-model failures.

The reference labels were unchanged. [The run plan](run-plan-v1.json) was recorded
after the Qwen smoke and before the first full Sol matrix. The targeted repair
was followed by a complete rerun, with all outputs preserved. This is development
evaluation, including a prompt tuned against an observed failure, not a held-out
test or a calibrated estimate of future reliability.

## Separate quality dimensions

| Dimension | Sol v1: passed / assessed (unassessed) | Sol v2: passed / assessed (unassessed) | CLI: passed / assessed (unassessed) |
| --- | ---: | ---: | ---: |
| Correctness against retained references | 17/17 (1) | 19/19 (0) | 4/4 (0) |
| Groundedness in supplied context | 17/18 (0) | 19/19 (0) | 4/4 (0) |
| Required-fact completeness | 19/20 (0) | 20/20 (0) | 7/7 (0) |
| Claim-to-citation support | 17/18 (0) | 19/19 (0) | 4/4 (0) |
| Appropriate outcome | 12/13 (0) | 13/13 (0) | 5/5 (0) |
| Critical failures | 1 | 0 | 0 |

V1's unsupported date inequality is unassessable for correctness against the
retained reference and fails grounding and citation support. It is not hidden by
the other correct claims. Claim counts vary with response content. Zero claim
denominators, such as a clarification, remain unavailable in the per-case scores.

[V1 reviews](reviews-sol-policy-v1.json), [v2 reviews](reviews-sol-policy-v2.json)
and [CLI reviews](reviews-sol-cli-v1.json) are separate annotations by an independent
Codex Spec review agent. Response and reference fingerprints bind each review;
every required fact is assessed in reference order. The reviewer checked persona,
neutral appendix, qualifications and synthetic provenance, not only status fields.
The missing-day answer preserves the known February 1990 month while describing
the requested exact day's precision as unknown.

[V1 scores](scores-sol-policy-v1.json), [v2 scores](scores-sol-policy-v2.json),
[targeted scores](scores-sol-unknown-date-v2.json) and [CLI scores](scores-sol-cli-v1.json)
use the existing `reviewed-binary-dimensions-v1` scorer. Captures, reviews and scores
are retained in local MLflow (`sqlite:///artifacts/issue-4-mlflow.db`); the summary
links run and trace IDs. CLI results retain serving expenditure categorisation.

The matrix uses one real retained source passage plus authored synthetic policy
fixtures. These annotations are not human-calibrated and do not establish
cross-source canon accuracy, broad roster coverage or release acceptance. #9 owns
calibrated comparisons; #21 owns acceptance of the complete demonstration.

## Software, transport and spending

The full suite passed **85 tests**, zero failures/errors/skips, against disposable
real PostgreSQL/pgvector and MLflow: [JUnit](tests.xml). Ruff and strict mypy
(27 files) passed. Software tests substitute the model HTTP boundary; the model
quality results above come from actual calls. The one upstream Starlette
test-client deprecation warning is nonfatal.

Five actual `ask-phil --api-url http://127.0.0.1:8184 ask ...` requests exercised
clarification, abstention, partial arrival/mother, unknown story date and supported
arrival. Every returned citation resolved through the HTTP evidence endpoint.
After restarting the temporary Uvicorn API, `ask-phil ... response <receipt-file>`
returned all five original responses exactly. Private receipt capabilities remain
in ignored local artifacts and are absent from published captures. The temporary
API was stopped; this does not claim a persistent cloud deployment.

Reported spend is **$0.10890587**: $0.10190787 offline evaluation and $0.006998
serving. [Final readback](cap-after-runs.json) verifies **$4.89109413** remaining
under the non-resetting $5 key cap, with all 32 ledger reservations settled. The
ledger conservatively rounds each charge upward to whole microdollars, totalling
$0.108911. Preserve the ledger; do not reset the trial by rotating keys or copying
it into separate runners. No credential is stored in the captures or Git.

Latency and token totals in [summary.json](summary.json) are observations, not a
controlled performance comparison. Prompt-cache effects may affect reported
charges; fees, taxes, hardware, electricity and hosting are excluded.

To rerun, use the [setup guide](../../openrouter-setup.md), select the Sol profile,
set `DATABASE_URL` to the retained development database and run
`scripts/evaluate_answer_policy.py capture` with a fresh output path. It indexes
the declared fixtures and uses the same shared cap. Independently review the new
frozen responses before invoking `score`; never reuse response-bound review labels
for a newly generated answer. A rerun consumes the remaining authorised trial budget.

The [two-axis review](review.md), application/prompt/reference/lock fingerprints,
artifact hashes and preserved regressions make this revision reviewable. Wait for
the next implementation instruction before starting #5 or another ticket.
