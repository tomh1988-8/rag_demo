# Independent review

Fixed base: `0523496`. Initial candidate: `2232987`.
Separate Standards and Spec agents reviewed the committed diff. They did not
change files, run paid inference or run the full software suite.

## Standards — initial findings

Three documented-standard findings: the old synthetic calibration admitted
broader online inputs; a committed feedback watermark could hide missing triage;
and held-out registry discovery depended on the caller's working directory.
No additional actionable baseline smells were reported.

The reviewer independently checked the retained clause in Wikipedia revision
1375499431: February 1990 is supported and the explicit 1991 variant contradicted.
This is agent source review, not human canon adjudication. The workflow cases
and literal public-result expectations were considered reasonable independent
controls; the combined implementation commit alone cannot prove their original
freeze timing.

## Spec — initial findings

Five source defects: calibration scope; interrupted triage; incomplete split
guards (working directory, escaped text and prior reservations); repeated model
charges after reporting/sampling-policy changes; and hidden late-feedback
backlog/lag. No scope creep was found.

The reviewer independently reproduced triage loss with a real PostgreSQL INSERT
fault: one active negative rating and revision watermark 1 remained, but restart
discovered zero work and triage stayed empty. The new recovery regression passes.
It also reproduced promotion of protected Unicode evidence and two controlled
judge charges after changing only `review_rate`. Those simulations made no paid
calls and used disposable databases with real MLflow/Prefect.

## Repairs under re-review

- Exact input/source admission uses independently reviewed positive/negative
  pilot controls. All 20 earlier unlabelled cases and the foreman disagreement
  remain unresolved/excluded; human calibration is unchanged.
- Discovery reconciles missing triage independently of the revision watermark.
  Reports separately measure pending revisions, backlog age and triage lag.
- Reference discovery is anchored and fails closed. Split checks use decoded
  strings, prior reserved groups and inherited held-out partitions.
- Durable semantic-result identity is separate from selection/report settings.
  Completed, paid failed and uncertain outcomes are reused before allocation;
  new configurations retain provenance and zero repeated judge expense.
- Reported problems remain prioritized during execution; background discovery
  and processing retain a reserved slot. Export backlogs remain inspectable and
  retryable without repeating scoring. Configurations are durably inspectable.

Final independent re-review and runtime validation are recorded when completed.
