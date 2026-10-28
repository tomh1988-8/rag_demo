# Persona validation protocol

Issue #19 starts at `a5c55489005f56cbed709829f7dd67ee38783eec` on `main`.
The approved conversation API/CLI and evaluation/scorer boundaries apply.
ADRs 0003, 0004 and 0006 govern voice, qualifications and captured evidence.

Freeze references and counterexamples before changing the answer prompt. Review
the final served answer, its citations, qualifications, CLI output and actual
MLflow records. Separate correctness, grounding, completeness, citation support,
answerability, relevance, voice, harm treatment, qualification preservation and
neutral appendix. A style gain cannot compensate for another failing dimension;
missing labels remain unavailable, and harm is applicable only on labelled cases.

The controlled comparison changes only the text persona prompt, uses the pinned
Sol profile and local embedding model, immutable selected source snapshots, k=3,
the existing 1200-byte context limit, no cache and no conversation history.
Repeat every case twice. Retain all initial failures before any prompt revision.
Source selections deliberately isolate wording from broader retrieval coverage;
they are exposed development cases, not held-out or independently adjudicated canon.
Source-based agent labels must not be represented as human adjudication.

Reuse the human-approved, calibrated issue #9 context-support rubric where useful;
it cannot judge persona or harm. Compare any support decisions with separate
source review, retaining unavailable inputs and disagreements. New harm/style
ratings are explicit rubric reviews, not an uncalibrated automatic judge.

The existing shared non-resetting $5 ledger begins at $0.495612. Keep the key and
ledger private; never reset either. Bound each capture to $1, at most 24 answer
calls and no retries; the existing provider reservation and verified key cap
remain authoritative. Evaluation scoring and software tests make no paid calls.

Use focused red/green tests and regular strict mypy checks. At completion run the
full suite once, perform the two independent code-review axes against the starting
revision, retain regressions and update the checklist and handoff. Commit only
this ticket's changes on the current branch, publish and verify its remote tree
before tracker closure. Preserve all pre-existing user files.
