# Issue #23: online evaluation cases and operating decisions

Base: `0523496`. Spec: GitHub #23 and #1. Tests use the already confirmed
conversation API/CLI and evaluation/scorer boundaries. PostgreSQL, MLflow and
Prefect stay real; routine model substitutes sit at the external HTTP boundary.

Independent expected cases, fixed before implementation:

1. An unrated delivered answer selected at background rate 1 is assessed from
   its original trace, answer and context. One eligible, zero rated, one selected,
   one completed code assessment; reference correctness and completeness are null.
2. A factual report accepted after assessment creates revision-specific triage,
   without a second generic assessment or model charge. Exact duplicate delivery
   changes neither count. A helpful revision replaces the negative current count,
   retaining both revisions and both triage records.
3. Background rate 0 leaves an unrated answer unselected. A reported fact,
   evidence or harm problem is prioritized for bounded feedback selection. All
   current ratings still appear in descriptive metrics regardless of selection.
4. No interactions gives zero counts and null ratios. Missing context produces
   an unavailable support score, never a pass. Nonfactual outcomes and failed
   serving remain visible. Votes never establish reference truth.
5. Missing trace or MLflow outage leaves bounded retryable pending work. A
   successful assessment write with a lost acknowledgement is recovered with
   its stable ID. Restart preserves attempts, decisions and completed results.
6. Disabled evaluation makes no judge calls. Failed/limited judges, exhausted
   online spend, uncertain interrupted calls, and missing usage remain explicit.
   Completed model results are committed before MLflow export and reused.
7. Comments/corrections are untrusted and redacted. Generic checks/judges never
   receive a vote or comment. Feedback-aware triage is separately named and does
   not execute the comment or adopt a suggested correction.
8. A review is bound to an immutable report and original evidence. Every item
   with a category/comment/correction and a deterministic sample of remaining
   ratings requires an explicit disposition. User/judge disagreements remain
   visible. A confirmed source-checked failure can become a versioned regression
   case, preserving original response and generation identities. Held-out story,
   question, evidence and derivative overlaps prevent promotion.

Default policy: automatic code checks enabled, 10% reproducible background
selection, 100% feedback-directed selection, finite batches, one worker across
processes, bounded MLflow retries, and no paid judge unless explicitly configured
with matching successful calibration and the existing online execution policy.
Online judge allocation is persistent across configuration revisions, separate
from serving/offline expense, and bounded by the existing non-resetting provider
ledger. Demo traffic and scripted feedback are labelled; no organic-use,
independent canon, held-out acceptance or causal improvement is inferred.
