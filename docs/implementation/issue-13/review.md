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

Both reviewers rechecked `8163135` independently against the same baseline.

Standards: **zero remaining findings**. The repeated dispatch is resolved; shared
assertion semantics, duplicate-support handling and versioned labels introduce no
new documented-standard violations or significant baseline smells.

Spec: **zero remaining findings**. The reviewer independently verified all five
relative qualifiers, expanded evidence, correction hashes, unchanged raw candidates,
content-bound reviews, admission and same-pilot rescore. The initial finding is
resolved; dispatch and duplicate-support changes introduce no additional concerns.

Final counts: **Standards 0, Spec 0**.


## Final runtime evidence review

The Spec reviewer independently read all 22 final MLflow traces at `8163135`.
Every root output matches the recorded API/CLI response and every tool output
matches its captured graph result. Reviewed results rescore against v2 references;
all five corrected qualifiers appear in final wording. False accounts have
narrative support, Max's conviction never becomes commission, citations retain
source evidence and duplicate support appears once in prose. Empty, unknown,
bounded and context-stop results remain qualified. No concrete issue was found.

The reviewed phase has eight partial and three insufficient-evidence outcomes.
The raw phase has two partial and nine insufficient-evidence outcomes; only two
raw assertions are admitted. Recall 3/17 and strict full-span grounding 1/4 remain
quality failures. Zero inference calls were made while serving. This review
confirms scoped capability, without automatic-extraction, held-out or canon approval.


## Full-suite conversation repair review

The first full suite at `8163135` completed with 386 passes and one existing
concurrent-session failure. `f3cb895` fixes the fixed SQL lock-wait mismatch;
the initial failure and deterministic red/green evidence are retained separately.
Standards found zero new findings. Spec found one post-wait deadline/cancellation
race, resolved by a guard before any new acquisition attempt. Both reviewers
independently rechecked that guard and report zero remaining findings.
Authorization, rollback, lock ownership through commit and individual SQL limits
are preserved. The final full suite and runtime recapture bind this source revision.
