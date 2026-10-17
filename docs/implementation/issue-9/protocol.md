# Quality comparison protocol v1

The implementation starts at `07a4be2`. The existing six public testing boundaries
apply. This ticket uses evaluation scorers and the conversation API, real
PostgreSQL/MLflow and controlled external-provider substitutes in software tests.
Real model results are separate from software-test results.

## Cases and splits

`data/references/quality-comparison-v1.json` freezes seven previously exposed
development cases, with expected facts, alternative wording, forbidden assertions,
source revisions, passage hashes, evidence sets and review notes. Repeated runs,
paraphrases, follow-ups and source derivatives retain their story group. Historic
group assignments remain development; Janine's caregiver and garage co-ownership
gaps remain regressions within that exposed partition. They cannot become a new
holdout by changing a case ID.

`data/references/support-judge-v1.json` supplies eight explicitly synthetic controls
in two disjoint story groups. Four calibrate the narrow support rubric and four
validate it without tuning. The separate human label review is recorded in
`label-review.md`. These controls are not canon accuracy examples. Missing input
and missing reference labels remain different conditions. No factual answer key
is derived from a candidate answer, helpfulness vote or raw correction text.

The partition manifest names development, judge calibration, judge validation,
held-out comparison and regression uses. There is no final held-out answer run in
this ticket. The project owner must provide fresh grouped held-out cases for final
acceptance; previously exposed development material remains excluded. Retrieval
of supporting source material is permitted when questions/labels are held out.

## Dimensions and inputs

`reviewed-binary-dimensions-v2` retains correctness, grounding, completeness,
relevance, citation support and answerability separately. Each dimension exposes
passed, assessed, unassessed and value. No assessed labels means `null`.

| Check | Inputs and meaning | Later online eligibility |
| --- | --- | --- |
| Correctness | Source-reviewed claim/reference labels; agreement with the reference | Requires reviewed expectations |
| Completeness | Complete ordered required-fact list and reviewed coverage | Requires reviewed expectations |
| Answerability | Reviewed expected outcome and appropriateness of the actual response | Requires reviewed expectations |
| Grounding | Reviewed assertions against the original supplied context | Can review recorded context without a reference answer |
| Citation support | Reviewed claim-to-citation mappings and actual passages | Can review recorded citations/context without a reference answer |
| Relevance | Reviewed question/answer relationship | Can review a recorded interaction without a reference answer |
| Narrow semantic support | Every assertion supported by the supplied context, independently of omissions or style | Only the exact calibrated rubric/model/settings combination; input context required |
| Retrieval/context | Selected relevant spans, sufficient evidence sets, actual retrieved/context IDs | Recall/sufficiency require reviewed expectations |

All six deterministic dimensions aggregate external annotations. They do not
infer semantics by string matching. The semantic judge estimates support only;
it does not automatically supply correctness or completeness annotations.
Missing-reference examples are eligible for support, while missing-context
examples are unavailable without a judge call. Unverified human reports remain
reports and never enter the support prompt.

## Controlled run

Run each selected development case twice through the public session API. Use a
fresh session for every case/repeat except the explicit Phil follow-up sequence.
Keep corpus, answer prompt, model version, retrieval k=3 and the 1,200-byte context
budget fixed. Compare medium versus low reasoning using the same pinned answer
model; reasoning settings are the one declared change. Neither run enables an
answer cache. Each run has a unique development namespace and private receipt
directory. Retain the original uncached single-query identity. Future #24 fusion
and expansion versions use the same configuration/paired-observation contract;
this ticket does not claim the four ablations have run.

Report paired case means, per-case/category failures, actual sample sizes and
repeat ranges. Repeats are dependent observations and do not increase independent
story-group count. Ranges from two repeats do not establish confidence intervals
or a reliable provider latency distribution. Record retrieval and final-context
sufficiency separately from final-answer quality. Preserve missing stage timings
as `null`; do not substitute total answer latency for generation latency.

Separate serving expenditure from offline judge expenditure. Existing shared
OpenRouter controls retain the non-resetting $5 total trial cap, with a maximum
$1 additional slice budget for each command and no automatic paid retries.
Failed or interrupted attempts and unknown spending stay explicit.

## Judge procedure

Freeze support rubric v1 and the reviewed labels before calls. Use a pinned
provider profile; retain model/settings, input identity, exact rubric, decision,
reason and usage. Judge only the answer/context, with no label or user report in
the prompt. Measure calibration and validation separately. Repeat each control;
reverse evidence order and add wordier equivalent answers for a positive and
negative control in each partition. Inspect false passes, disagreement and
unavailable results. A model/rubric/label change invalidates this calibration.

The prototype enable gate requires complete reviewed coverage, human-reviewed
labels, zero unresolved disagreements/false passes and no observed sensitivity
changes. Passing eight controls would establish only this narrow synthetic scope.
Do not treat it as a release-quality numeric threshold or broadly validated judge.

The completed run in `judge-calibration.json` passes those controls. Subsequent
application to preserved development answers uses independently frozen AGENT
labels, not additional human calibration. It reveals four null-policy mismatches
on no-assertion abstentions and four Boolean decisions on unresolved identity
references. Keep those eight decisions unscored and requiring review; they do not
broaden eligibility. No negative development support labels exist, so the live
application has no false-pass-rate denominator. Before automatic reuse in #23,
adjudicate these cases and add fresh validation controls for the changed scope.

## Cadence, critical gates and threshold selection

Run focused deterministic tests during each slice. Run affected public API and
scorer regressions after changes to prompts, models, retrieval, data or schemas.
Run the full software suite once before completion, independently of model
scoring, and associate its XML and hash with the same comparison in MLflow.
Run budgeted development comparisons when answer/scorer controls change and
before a demo checkpoint. Recalibrate the judge when its exact inputs change.
Use fresh held-out comparisons periodically and at the final release checkpoint.

Critical gates are zero unresolved false factual assertions, unsupported negative
claims, false citations, biological/guilt-role errors, fabricated measurements,
split leakage or stale evidence identity. Safe abstention can pass grounding and
still fail completeness or expected answerability. Keep such failures visible.

After measuring the development baseline, the implementer proposes numeric
quality, cost and latency thresholds with denominators, required category
coverage, repeat counts and sample-size limits. Tom accepts them in a versioned
policy linked to that baseline's hash. Freeze that policy **before** opening
held-out candidate outputs. If a policy changes, retire the comparison, document
why and obtain a new untouched holdout. This development comparison supplies
measurements and diagnostics; it cannot silently establish held-out acceptance.
