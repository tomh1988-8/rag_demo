# Issue #4 two-axis review

Fixed base: `936f265d614345a3209e7f955f1aa82fa9f95a28`.
Initial implementation: `1187289`. Review included subsequent working-tree fixes,
retained captures and independent reference/score inspection.

## Standards

The Standards agent found no initial hard violation and one optional setup-duplication
smell in the integration tests. Explicit load/index setup was retained for readability
at the agreed seams. A follow-up found that the invalid-citation provider fixture
omitted newly required fields, making the test fail for the wrong reason. It now
provides a complete draft with only the invented citation defective; the targeted
regression and full 66-test Docker suite passed.

**Remaining required Standards findings: 0.** One accepted maintenance suggestion.

## Spec

The Spec agent independently confirmed all retained facts and synthetic provenance.
Two initial findings were fixed: the obsolete three-field exemplar/optional generated
fields, and the reference outcome that incorrectly required partial for a fully
corrected false-premise answer. References v2 preserve the correction without rewriting
v1. A further live-discovered conditional-schema gap was fixed with a discriminated
timing variant, verified by an independent JSON Schema regression. The 512-token ceiling
is supported by an observed truncated conflict response at 256 tokens.

The reviewer independently checked all 13 v2 annotations, identity hashes and score
arithmetic, then supplied the six v3 per-claim/per-fact annotations. The v3 results
still fail the requirement to clarify unresolved intent, abstain for missing evidence,
correct false premises and preserve material qualifications. A served unsupported
completed-act assertion is retained as a critical citation-support regression.
Persona and synthetic-provenance presentation also remain deficient.

**Remaining Spec finding: semantic acceptance is incomplete. Keep #4 open.** No
unasked implementation scope was identified. These are independent agent reviews,
not human-calibrated judgments or independent canon verification.

Summary: Standards 0 required findings; Spec 1 unresolved acceptance area with the
specific failures preserved in the evidence and regression records.
