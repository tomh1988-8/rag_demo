# Issue #23: automatic online evaluation and review

[Ticket](https://github.com/tomh1988-8/rag_demo/issues/23): evaluate live answers
with feedback and close the review loop. The local API now starts a durable
Prefect processor that assesses saved interactions, reconciles feedback revisions,
exports CODE/LLM_JUDGE assessments to MLflow, and exposes immutable reports,
evidence-based dispositions and checked regression promotion. Answers and feedback
receipts return without waiting for judging. See the
[operating guide](../../online-evaluation.md) for commands, controls and ownership.

The implementation starts at `0523496`. Application/test repairs finish at
`1eb8528`; the capture helper's actual CLI/trace verification finishes at
`c4cb625`. The application fingerprint is
`13aca48a9b7c7e8a49ca7f924c75b8f37eefe097c75ad1552dd8e8d3c1bfb1dd`.
The [initial 270 frozen software inputs](software-inputs.json) precede the full
software run and remain preserved. The helper-only change does not alter
application or test bytes. The separate
[272-input publication manifest](published-software-inputs.json) records that
change and the two subsequently registered regression/lineage files; it does not
represent those additional artifacts as frozen inputs to the earlier suite.

## Actual demo and review loop

The [paid pilot manifest](runtime-v1/manifest.json) labels scripted feedback and
controlled serving models as demo/test traffic. FastAPI, PostgreSQL, Prefect,
MLflow, the Ask Phil CLI and the online support provider are real. Two fresh
OpenRouter calls routed to OpenAI's `openai/gpt-6-sol` assess the exact saved
answer/context controls reviewed independently before the calls:

| Saved answer | Reviewed support | Actual judge | Provider expense |
| --- | --- | --- | --- |
| Phil Mitchell first arrived in February 1990. | Supported | Supported | $0.000984 |
| Phil Mitchell first arrived in February 1991. | Contradicted | Unsupported | $0.001004 |

The [assessment readback](runtime-v1/assessments.json) retains model, provider,
request, usage, rubric, configuration and input identities on the original traces.
The two calls cost **$0.001988**. The existing non-resetting $5 ledger moves from
**$0.911656 to $0.913644**, with zero unsettled reservations. Serving and offline
evaluation make zero paid calls. The user's [two-call approval](approval.json)
supersedes the initial automatic rejection; no attempt ran before that approval.

The first supported answer receives a scripted negative factual report.
[Disagreement review](runtime-v1/disagreement-review.json) rejects that report
against the retained Wikipedia clause. A later helpful revision replaces its
active rating without buying another generic assessment. Exact duplicate
submissions do not create new revisions or active votes. A second, unsupported
1991 answer receives a source-based confirmed disposition in the
[final review](runtime-v1/review.json), which also inspects the required sample
of remaining ratings.

Reports are snapshots of different processing times:

- [The reviewed report](runtime-v1/report.json) has two eligible/rated/selected
  interactions, one positive and one negative current rating, two code scores,
  two support scores and **two pending triage revisions** at capture time.
- [The later CLI report](runtime-v1/cli-report.json) has three eligible/selected
  interactions, two rated and one unrated, three code scores and two support
  scores. All three feedback revisions are triaged, with **zero pending**.
  The third answer is explicitly `budget_skipped` for semantic evaluation because
  the two-call allowance is exhausted; its code check and export complete.

Helpfulness, reported problems, citation checks, support, review dispositions and
reference correctness are separate. These online responses have no reviewed
reference expectations, so reference correctness/recall/completeness stay null.
Every current accepted rating contributes to descriptive metrics, regardless of
bounded selection. The cohort records include unrated background work.

The [promotion](runtime-v1/promotion.json),
[versioned regression](runtime-v1/regression-v1.json) and
[original lineage](runtime-v1/regression-v1.lineage.json) retain the wrong answer,
review identity, independently sourced February 1990 expectation, source revision,
evidence hashes and both arrival-story aliases. Split checks expose no held-out
labels. The [offline capture](runtime-v1/offline.json) reuses the wrong answer
and a subsequently served correct control, with matching actual CLI and original
root-trace outputs. Its [source review](runtime-v1/offline-reviewed.json) scores
the wrong year 0 and the correct year 1 on the assessed factual dimensions.
The controlled external-model output correction exercises re-evaluation; it does
not claim that an application or model-quality defect has been fixed.
The exact checked dataset and lineage are also registered as
[versioned reference data](../../../data/references/online-phil-arrival-regression-v1.json).
[Registration validation](registered-regression-validation.json) checks byte and
source identity and recomputes the same verified offline scores without new calls.

An earlier [local-only run](runtime-local/started.json) disabled all external
judges and exercised three real local interactions, feedback, review and promotion
at zero provider cost. Its [original failure](runtime-local/failure.json) and
[original capture](runtime-local/offline.json) remain unchanged: the helper omitted
the actual CLI/trace copies required by strict offline verification.
The [separate repair](runtime-local/verification-repair.json) uses the same saved
responses, actual maintainer CLI and original traces. Its
[verified capture](runtime-local/offline-verified.json) and
[validated review](runtime-local/offline-reviewed.json) pass the established
`CapturedAnswers`/`ReviewedAnswers` contracts. No answers or judges are rerun.
This repeats the same exposed factual example and is not independent quality data.

## Software evidence

Tests stay at the six already approved public boundaries. PostgreSQL, local
MLflow and Prefect are real; ordinary model substitutes use the external HTTP
boundary. The [cases](cases.md) record expected behavior, the
[failure record](failures.json) preserves observed defects and repairs, and the
[independent review](review.md) separates Standards from Spec.

The combined final focused set passes **40 cases**, subsequent narrow checks
pass **12**, and the rebuilt non-root image passes **23 packaged contracts**.
Strict mypy checks 162 source/test/script files; Ruff, formatting and Compose
configuration pass. The [full suite](software-tests.xml) passes **654 cases**
with zero failures, errors or skips; it runs once after application/test repairs.
[Validation](validation.json) binds the result to the unchanged application/test
inputs and records the later helper/data additions separately. The preserved logs
include a Prefect closed-output logging error during interpreter shutdown after
passing checks; the test processes exit zero.

Fault coverage includes late/revised/duplicate feedback; lost triage after a
committed watermark; missing traces; real HTTP MLflow outage and lost export
acknowledgement; restart; disabled and failed judges; uncertain interrupted paid
attempts; missing usage; persistent caps across policy changes and expiry;
configuration-independent result reuse; background progress under bounded batches;
backend isolation; hostile/redacted comments; null reference metrics; and
held-out group/question/decoded-evidence/derivative protections.

## Limits and continuing obligations

The [exact admission scope](../../../data/references/online-support-scope-v1.json)
contains only the two independently source-reviewed controls above. It adds no
human calibration. Unknown inputs remain `requires_scope_review` without a paid
reservation. Twenty earlier unlabelled cases and the disputed foreman-role case
remain explicitly unresolved/excluded. The original human calibration and earlier
quality failures are unchanged. Two fresh calls do not validate repeat/sensitivity
reliability, broader online quality, independent canon or held-out acceptance.

All ratings are scripted and all new factual reviews are by agents. The project
owner/maintainer retains quality acceptance. No organic usage, unbiased accuracy,
causal improvement, persona measurement or current-story completeness is inferred.
Final release/dependency acceptance remains pending in the checklist. Future cache
work must retain delivery and generation identities and avoid duplicate inference
expense or independent-example counts.

Private receipts, provider credentials, tracking databases and budget ledgers stay
outside published evidence. Original data and pre-existing workspace inputs are
preserved. The end-of-issue workflow publishes only the reviewed implementation,
evidence and handoff after checks, then verifies the remote tree and tracker state.
