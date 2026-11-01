# Response feedback

Ask Phil accepts optional feedback on a selected delivered response. Read the
collection policy with `ask-phil feedback-policy`. Feedback helps describe
helpfulness and prioritize review; a reported factual error or suggested
correction is untrusted input until independently checked against the sources.
Comments do not enter conversation memory or the retrieval corpus.

## Give feedback

In `ask-phil chat`, use `/feedback helpful`, `/feedback not_helpful [comment]`
or `/feedback skip` to rate the last response. Continue asking questions or use
`/reset` without submitting a rating. Reset preserves the original response's
identity for later feedback; it clears the answer's conversational context.

For a selected saved answer, keep its receipt private:

```sh
umask 077
ask-phil ask "When did Phil arrive?" --snapshot phil-arrival-v1 > answer.json
ask-phil feedback answer.json --rating not_helpful --category evidence \
  --comment "Please check the supporting passage."
ask-phil feedback-history answer.json
```

For an answer requested with `ask --session session.json`, supply that same
private session receipt to `feedback` and `feedback-history` using
`--session session.json`. Session answers require the session's separate
feedback capability. Another session's capability and the answer's read token
cannot authorize feedback on that session answer.

Categories are `facts`, `missing_outdated`, `evidence`, `harm`, `clarity`, `persona_tone`
and `other`. `--proposed-correction` accepts an optional suggestion. Comment and
correction are each limited to 500 characters and share a 1,000 UTF-8 byte
budget. Recognizable credentials and the submitted capability are redacted.
Arbitrary personal information is not automatically recognized: omit it.

The CLI prints the submission ID before sending. Reuse it with
`--submission-id ID` after an uncertain result to retry the same redacted
payload. A different payload with that ID conflicts; use a new ID for a revision.
Up to ten new submissions per minute are accepted per anonymous context. Exact
retries do not consume another slot.

HTTP clients first read `GET /v1/feedback-policy` and submit its policy version,
a UUID `submission_id`, rating and optional fields. Session paths are
`/v1/sessions/SESSION/responses/RESPONSE/feedback`; standalone paths are
`/v1/responses/RESPONSE/feedback`. POST accepts feedback; GET inspects authorized
history and the original served response. Bearer capabilities belong in the
Authorization header. Clients cannot select a trace or MLflow write target.

## Receipts and delivery

HTTP 202 means PostgreSQL durably accepted the revision. Its receipt identifies
the response, feedback, submission and revision, with acceptance/expiry times and
delivery state. It does not claim that a semantic judge has evaluated the answer.
The API's local background worker exports human-origin rating/category assessments
to the original MLflow trace. Comments and corrections stay in local PostgreSQL.
Each newer assessment supersedes the previous revision; both histories remain
inspectable. Backend-enforced stable assessment IDs cover lost acknowledgements.

Missing traces and export errors leave pending work. Restart the API to resume,
or run the maintainer command `ask-phil feedback-deliver` with `DATABASE_URL` and
the original `MLFLOW_TRACKING_URI`. A batch processes at most 20 items by default;
unsuccessful revisions wait before retrying. The reply's `pending` field counts
the remaining queue, including items currently waiting for retry.

For HTTP MLflow, configure `MLFLOW_HTTP_REQUEST_TIMEOUT` to at most 5 seconds and
`MLFLOW_HTTP_REQUEST_MAX_RETRIES=0`; application retries are durable. The local
Compose API sets these bounds. Unbounded client settings leave delivery pending.
The backend URI fingerprint is fixed at serving time. Restore the original URI
after a configuration change; a different backend cannot stand in for its trace
or falsely complete assessment deletion.
Work belonging to another backend stays pending while the current backend's
eligible work continues; it does not consume that backend's batch slots.

## Retention and access

Collection is enabled by default. Set `ASK_PHIL_FEEDBACK_ENABLED=false` to stop
new capture/export. Configure `ASK_PHIL_FEEDBACK_RETENTION_DAYS` from 1 to 30
before capture; the default is 30. The policy endpoint exposes the effective
settings. Session feedback is additionally bounded by its capability's lifetime.

Expired feedback becomes inaccessible. The running worker or maintainer delivery
command removes expired feedback text/revisions and schedules assessment deletion.
An unavailable MLflow service leaves minimal cleanup identifiers and a visible
`cleanup_pending` count until deletion succeeds. Run the API or the maintainer
command to perform cleanup; a stopped application cannot execute deletion.
Existing source captures, immutable original answer receipts and original MLflow
traces retain their separate pre-existing policies.

Anonymous users can inspect only their own response-bound feedback. Aggregate
reports and the review list are maintainer CLI operations requiring local
PostgreSQL access. Protect database, MLflow and private receipt files accordingly.

## Inspect live signals

With `DATABASE_URL` configured, run:

```sh
ask-phil feedback-report
ask-phil feedback-report --served-from 2026-11-01T00:00:00Z \
  --served-until 2026-11-02T00:00:00Z --as-of 2026-11-01T12:00:00Z
```

Use explicit timestamps for a repeatable report. Served cohorts use `[from, until)`;
the feedback cutoff selects the latest accepted revision at or before that time.
The cohort contains retained, committed API outcomes offered for delivery. It does
not establish socket receipt or a count of unique people. Expired history is
unavailable; the report is a retained-data view. Delivery state describes current
processing, even for an earlier rating cutoff.

`rated = positive + negative`; coverage is `rated / eligible`; positive share is
`positive / rated`. Empty denominators give null. Skip and missing feedback never
become positive ratings. Reported factual/evidence errors are separate counts;
independently reviewed correctness remains unavailable in this collection slice.
Counts include every current item, even when inspection is paginated. Reuse the
same cohort/cutoff with `--offset` and `--limit` to inspect all priorities.
Reports also separate actual route, outcome, source snapshot, application,
prompt and model versions. Self-selected ratings do not establish unbiased
accuracy or causal improvement.

Automatic sampled checks, feedback-directed evaluation, dispositions and checked
regression promotion use the [online workflow](online-evaluation.md). Raw feedback never
changes source claims, prompts, routing or a gold expectation.
