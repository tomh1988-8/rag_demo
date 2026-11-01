# Automatic online evaluation and review

The local Compose API starts a separate Prefect worker thread. Feedback receipts
and answers do not wait for judging. The worker discovers committed interactions
and feedback revisions from PostgreSQL, evaluates the preserved response and
original MLflow trace, and exports stable CODE/LLM_JUDGE assessments. It never
asks the answering agent to reproduce an answer. PostgreSQL owns the durable
queue; this implementation does not depend on hosted MLflow automatic judges.

For a separately managed API, set `ASK_PHIL_ONLINE_AUTO_PROCESS=true`, or run
`ask-phil online-worker` against the same `DATABASE_URL` and
`MLFLOW_TRACKING_URI`. A PostgreSQL advisory lock admits one processor across
processes. A stopped application resumes from durable records after restart.

## Selection and input contracts

Default background sampling is a reproducible 10% draw over delivered response
IDs, including unrated outcomes. Every accepted feedback revision is retained
for descriptive counts and separately named `feedback-report-triage-v1` triage.
Feedback-directed sampling defaults to 100%, prioritizing reported facts,
missing/outdated evidence, evidence problems and harm, followed by negative
ratings. Selection is bounded per processing batch. Sampling reasons, rates,
configuration fingerprint and response/generation identities remain visible.
Reported factual/evidence/harm problems also take priority in the runnable queue.
Each normal batch reserves discovery and execution capacity for unrated background
work; a one-item batch alternates that reservation across durable polling rounds.

Code checks verify retained citation identity. They do not infer support from a
matching identifier. Without reviewed expectations, correctness, recall and
completeness remain unavailable. Persona remains unavailable without an
applicable calibrated persona evaluator. Failed, clarification and abstention
outcomes remain in the report but do not acquire a manufactured support score.

Paid support judging is disabled by default. To enable a scoped pilot, configure
`ASK_PHIL_ONLINE_CALIBRATION` with a complete matching calibration artifact and
enable `online_enabled` in the existing `ASK_PHIL_EXECUTION_POLICY`. The worker
recomputes the saved calibration against the human-reviewed support controls,
and checks the exact rubric/model/settings identity. It uses the existing private
key and non-resetting provider ledger. Generic judges see only the preserved
answer and context, without the vote, comment or proposed correction.

Admission is additionally limited to the exact input and source fingerprints in
the [reviewed arrival pilot](../data/references/online-support-scope-v1.json).
Those two positive/negative controls have independent agent source review, not
new human calibration. Unknown inputs remain `requires_scope_review` without a
model reservation. `ASK_PHIL_ONLINE_SCOPE` can name a separately reviewed scope
artifact. The old identity/no-assertion cases and foreman disagreement have
explicit unresolved/excluded admission dispositions; their semantic labels are
unchanged. Two fresh pilot calls cannot establish repeat/sensitivity reliability
or broaden eligible scope.

The existing calibration establishes narrow synthetic context-support controls.
Earlier identity/null-policy disagreements and the disputed foreman-role label
remain unresolved; they do not become canon adjudication or broad judge
acceptance. Review contextual ambiguity and unscored results explicitly.

## Bounds and recovery

`ASK_PHIL_ONLINE_POLICY` can point to an `OnlinePolicy` JSON document. Defaults
are a 20-item batch, 10-second polling/retry intervals, three MLflow attempts,
45 seconds of processing, at most 20 judge attempts and a persistent $0.25 online
allocation. Model calls additionally obey the existing online execution policy
and shared provider cap. The input-contract ceiling remains 12,000 bytes and
20 passages. Model HTTP has no automatic paid retries.

Set `ASK_PHIL_ONLINE_ENABLED=false` to disable processing. Saved interactions and
feedback remain available under their retention policy. Known judge output is
committed before MLflow export. A lost export acknowledgement uses the same
backend-enforced assessment ID. Missing traces and outages retry within the
configured bounds; failed/exhausted work remains inspectable. An interrupted
model attempt is uncertain and is never automatically charged again. Missing
usage stays null and retains its conservative allocation. Configuration changes
and expired interactions do not reset cumulative online expense.
Selection, reporting and retry-policy revisions create new configuration records
without buying an unchanged judge result again. Semantic reuse keys identify
the generation, preserved input/source, calibrated rubric/model and explicit
`evaluator_revision`. Reused results retain their origin with zero new calls/cost.
Paid failed and uncertain outcomes are also retained; unattempted budget skips
can become eligible when limits change. Deliberately changing the evaluator
revision requests a fresh assessment within the same persistent allocation.

Configure HTTP MLflow with `MLFLOW_HTTP_REQUEST_TIMEOUT` at most 5 and
`MLFLOW_HTTP_REQUEST_MAX_RETRIES=0`, as Compose does. Requests already in progress
can require that bounded cleanup interval after the processing deadline.
Restore the original tracking backend before processing its interactions.

## Reports and review

Maintainer commands require local database access; aggregate reports are not
anonymous API endpoints:

```sh
ask-phil online-process
ask-phil online-report --served-from 2026-11-01T00:00:00Z \
  --served-until 2026-11-02T00:00:00Z --as-of 2026-11-01T12:00:00Z
ask-phil online-inspect JOB_UUID
ask-phil online-review-response REPORT_UUID RESPONSE_UUID
ask-phil online-review review-request.json
ask-phil online-review-history REPORT_UUID
ask-phil online-promote promotion-request.json --output data/references/online-regression-v1.json
```

The default report covers the last 24 hours. Explicit timestamps freeze the
served interval `[from, until)` and the latest accepted feedback revision at or
before the cutoff. Processing/selection states describe the current worker at
report creation. Each report is immutable and records its configuration,
denominators, route/outcome/version slices, sample coverage, missing/failure
states, backlog age, assessment lag, separate serving/online expense and missing
offline measurements. Background and feedback cohorts can overlap. Repeated
deliveries are not independent story examples; future cache integration must
preserve `generation_id` and charge serving inference only to its original call.
Late feedback has separate pending-revision counts, backlog age and processing
lag, even when its generic answer assessment completed earlier. Configurations
and their fingerprints are durable and included in reports/inspection. Descriptive
feedback counts cover every retained interaction; online eligibility excludes
interactions belonging to another tracking backend and shows that count explicitly.

Reports designate every category/comment/correction item, every visible
user/judge disagreement, and a reproducible 10% sample of remaining ratings
(at least one when that remainder is nonempty). A `ReportReview` request names
the report, reviewer and note, and supplies each required response/revision,
its original response fingerprint, a disposition and an evidence-based note.
Dispositions include unresolved, confirmed, rejected, duplicate and needs-source-review.
Changed judgements use a new immutable review record. Monitor reports during
each demo session and after evaluator/source/configuration changes; the local
maintainer owns disposition and quality acceptance.

`RegressionPromotion` requires a confirmed inspected failure, a regression-split
`ComparisonCase`, independently established expected facts, and a documented
source check for every fact. Evidence must resolve to the original snapshot and
source revision. Promotion checks registered held-out groups, questions,
evidence and derivatives without returning their labels, and prevents duplicate
generation promotion. It writes versioned offline comparison references plus a
`.lineage.json` artifact containing the original response, review, source checks
and registry fingerprints. Re-evaluate fixes through the established frozen
offline `EvaluationRun`/review process; promotion does not change application
facts, prompts, routing or weights.

Online jobs and reports containing feedback expire with the original feedback;
the running worker purges them. Minimal expense records survive expiry so a
restart cannot reset the spending allocation. Original answer traces and checked
regression artifacts retain their separately documented policies. Protect local
database access and exported maintainer reports. Self-selected helpfulness is not
unbiased accuracy, and observed trends do not establish causal improvement.

Dependency contracts were tested on MLflow 3.16.1 and Prefect 3.8.6. MLflow's
[assessment sources](https://mlflow.org/docs/latest/genai/assessments/feedback/)
distinguish human ratings, code checks and semantic judges; actual local integration
readback, rather than hosted automatic-evaluation assumptions, establishes the
supported lifecycle here.

Reference discovery uses the installed/project location, rather than the caller's
working directory. Packaged deployments set the absolute
`ASK_PHIL_REFERENCE_DIRECTORY` (the image uses `/app/data/references`). Missing or
empty registries fail closed. Promotion checks decoded Unicode/quoted evidence
and existing `prior_group_splits` reservations. Use absolute paths for externally
configured policy/calibration files when invoking the CLI outside the project.
