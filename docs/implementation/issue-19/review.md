# Two-axis code review

Fixed point: `a5c55489005f56cbed709829f7dd67ee38783eec`, the recorded ticket start.
Initial reviewed commit: `d2e61a3`. Diff command:
`git diff a5c55489005f56cbed709829f7dd67ee38783eec...HEAD`.
Two separate sub-agents reviewed Standards and Spec under the code-review skill.
Neither changed files or made paid calls.

## Standards

**0 remaining findings.**

One documented-standard violation was found and repaired. `compare()` validated
`persona_scores` but aggregated factual values from an unchecked duplicate
`scores` field, violating the reviewed-scoring contract in
`docs/design/testing-and-evaluation.md`. Editing one duplicate score changed the
reported mean from 1.0 to 0.95 without rejection.

The fix validates both representations and aggregates verified persona results.
Independent verification rejects tampering before output and replays unchanged
artifacts with identical dimensions. No additional documented violations or
applicable baseline smells were found.

## Spec

**0 remaining findings.**

The same comparison-integrity defect independently violated “Compare before/after
persona behavior on controlled source/model cases” with distinct factual
measures. Editing a baseline duplicate correctness value changed the reported
baseline mean from 0.99 to 1.0.

The reviewer independently verified that the original probe now raises
`ValueError` before output, and unchanged baseline/final inputs reproduce identical
dimensions and critical-failure records. No other missing behavior or scope creep
was found. Sampled final responses preserve unknown presence, outcome/date/conflict
qualifications and neutral records. Human calibration reuse, new agent labels,
the foreman dispute and over-specified Jane reference have explicit limits.

Standards: one repaired, zero remaining. Spec: one repaired, zero remaining.
Both axes identified the same original comparison-integrity defect.
