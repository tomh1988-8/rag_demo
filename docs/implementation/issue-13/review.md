# Independent two-axis review

Baseline: `8c19539bfe768e5fdb2a8278122add3606ac8934`, confirmed by the user.
Initial reviewed HEAD: `9a23a72`; initial diff command:
`git diff 8c19539bfe768e5fdb2a8278122add3606ac8934...HEAD`.

## Standards

No documented-standard violations found.

Judgment call — Repeated Switches: `family_answering.py` repeatedly selects
between the same three graph kinds for limitation, span name, query execution,
empty-result subject, unanswered coverage and prompt fingerprint. Select the
route's metadata and operations together in one dispatch block, then let the
common answer lifecycle use that selection.

Initial count: zero hard violations, one smell finding. Fixed by selecting each
route's metadata and bound query operation together before common execution.

## Spec

P2 — Preserve supported relative timing in five reference assertions. The ticket
requires: “Distinguish exact/approximate/relative/unknown dates.” Five v1 labels
incorrectly use unknown/unknown: Max's arrest and charge (“when Lucy's blood is
found on his shoe”), accusation of Bobby (“As he is being arrested”), later
imprisonment, and Phil's later release following confession/custody.

Preserve v1 and raw pilot, create a versioned reference correction, expand the
arrest/charge evidence quotes, update reviewed claims/reviews, rescore the
unchanged pilot and protect corrected final wording with a regression.

No scope creep or additional identity, role, guilt or provenance findings. The
reviewer independently checked all seventeen scoped assertions, all six excerpts
against captured origins, raw admission and final false-confession/framing answers.

Initial count: one finding. Fixed through the documented v2 source correction,
unchanged-output rescore, expanded evidence spans and final API regressions.

## Follow-up

Follow-up independent reviews of the corrected implementation are pending.
