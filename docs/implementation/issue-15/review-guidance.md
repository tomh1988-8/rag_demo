# Claim review and extraction annotation

The maintainer inspects retained Claims, exact source spans, Character identities,
admission reasons and earlier reviews through `claim-reviews --snapshot ID`.
`review-claims REQUEST.json` is a maintainer database operation. The answering
agent has no review, import, publication or recovery tool.

Every changed review names the exact Claim fingerprint, reviewer, outcome and
rationale. Supported means the captured passage supports that assertion; it does
not mean independent corroboration. Unsupported or uncertain assertions remain
held. Mark every competing source account disputed while disagreement is
unresolved. A more recent fetch, a repeated account, an identifier match, or the
act of reviewing supplies no independent narrative evidence.

A supported correction identifies distinct replacement Claims with
`superseded_by`. Add a new assertion under a new identifier if a value or locator
needs repair. Supply its content-bound support review and identify the source
wording that changes the interpretation. Earlier Claims, source text, locators,
reviews and answers remain unchanged. Correction targets must pass domain
admission; supported negative assertions and non-biological ties remain valid
source accounts while staying outside biological adjacency. A confession,
accusation, belief or explicitly false account cannot establish commission.

Later corrections follow the retained replacement chain to its current terminal
accounts. An earlier retirement stays retired if its replacement is subsequently
disputed, uncertain or unsupported; it must not revive the superseded assertion.
The immutable parent review proves that retirement was already accepted. Fresh
corrections still require supported terminal accounts, and replacement cycles are
rejected. Inspect connected groups after an identity, episode or event correction:
retrieving the predecessor must also expose the current competing accounts.

Inspect the complete competing group, including duplicate source assertions.
Correcting one duplicate does not silently retire the others. Related Claims in
another projection family must be reviewed explicitly in the same request.
The system copies every existing family into the new snapshot, including
unchanged families, and seals presence or absence in the publication manifest.
It does not infer agreement across biological, relationship and event schemas.

Review requests include the inspected source and all graph fingerprints. New
Claims cannot replace existing IDs. Candidate Claims and reviews remain bounded
by the existing batch limits. A stale request or unsupported correction fails
before publication. The source, complete index, admission audits, all graph
versions and review identity publish together. Interrupted or failed work leaves
the last usable version active; inspect `refresh-runs`, retry the exact request,
or use `rollback-snapshot` to restore the checked preceding version. A rollback
withdraws the replaced version for new answers while preserving old receipts and
evidence. Unchanged recapture preserves the review; genuinely changed sources
require fresh extraction/admission rather than automatically inheriting reviews.

## Annotation and matching

The existing parentage, relationship and event reference sets retain their
published scorer versions. This issue changes admission and interpretation,
not their raw extraction labels or scores.

| Dimension | Rule |
| --- | --- |
| Identity | Use reviewed Character IDs; preserve direction, roles and Character/performer distinctions. Never match by an ambiguous display name alone. |
| Claim values | Match the existing scorer's typed assertion, including polarity, certainty, relation/event type, participant roles and supported timing. Extractor-generated Claim IDs are provenance, not proof of semantic equality. |
| Source accounts | Distinguish what a source reports from established narrative fact, and a false confession from commission. Label incompatible accounts separately; do not merge them into one true assertion. |
| Timing tolerance | Exact, approximate, relative and unknown are distinct. Unknown dates are not wildcards. Preserve anchors and qualifiers; use only each versioned scorer's declared normalization. A wording mismatch remains a mismatch where the frozen scorer uses literal wording. |
| Grounding | Resolve Unicode offsets within the identified retained passage and compare the exact quote. Locator resolution is separate from semantic support and conservative full-reference-span coverage. Report all three distinctions. |
| Duplicates | Keep each source assertion and raw candidate in the audit. Use the scorer's semantic/set matching and one-to-one reference credit; duplicate candidates cannot manufacture recall or independent corroboration. |
| Completeness | Precision/recall/F1 apply only to the explicitly fully annotated selected passages, catalogue and claim families. Do not treat missing annotations elsewhere as negatives or claim corpus-wide recall. |
| Corrections | Freeze the original raw batch and reference. Record a new reference version and reason when a label is wrong, then rescore unchanged predictions. Curated replacement Claims measure reviewed capability, never improved original extraction accuracy. |
| Splits | These pilot and failure cases are exposed development/regressions. Group shared events, overlapping biographies and derived synthetic examples before future train/calibration/holdout splits. |

## Initial audit and later review

The pilot audits every Claim and source span. The actual issue #11 Peggy locator
has a 105-character quote with an end offset of 104. Its new replacement uses
the complete 105-character span without changing the parentage value or unknown
story timing. The original failed extraction remains a failed extraction.
The competing Phil/Grant father accounts are explicitly authored synthetic
counterexamples, not an EastEnders source disagreement or human-adjudicated canon.
Their expected outcome is visible disagreement and zero established father edges.
The third case deliberately authors an erroneous biological Den/Sharon assertion
against the unchanged source that explicitly describes adoption at age three.
It is an injected prior review error, not historical extractor output. The new
supported adoption Claim removes the biological edge and explains the correction.
Baseline and rollback answers intentionally reproduce that old error so recovery
is checked separately from factual acceptance of the recovered interpretation.

For later coverage, review all conflicting, uncertain, negated, corrected and
malformed assertions; changes in biological parentage, crime commission, legal
roles, account truth, event identity and chronology; and every assertion affected
by a source or schema change. Review each competing/duplicate group together.
Sample the remaining automated passes by source, extractor version and claim
family, including at least one whole source group per populated stratum. Record
the selection rule, selected IDs, denominator, reviewer and disposition before
reporting a rate. If a critical error appears, expand to the entire affected
source/type group. Automation and sampling do not establish independent verification.
The project owner retains authority over representative release thresholds.
