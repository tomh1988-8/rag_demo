# Captured-answer retention and bounded stop replies

The user selected the first two recommendations from the 28 October 2026
architecture report and requested implementation with `/implement`.
The starting revision and review fixed point is
`76a7b147a2babea62ac6567b28d9a938cb77757f` on `main`.

## Scope and test seams

1. Retain each captured answer before verification or comparison pairing. A later
   capture or verification failure must preserve the responses already received,
   their fingerprints and separate verification outcomes. Keep frozen references,
   immutable run outputs and failed-run review rejection. Share this lifecycle
   with graph acceptance; preserve existing successful comparison artifacts.
2. Concentrate stopped-answer construction for text and investigation. Keep reply
   wording within the draft limit while retaining complete citation passages,
   stop reasons and unresolved question parts. Each route still decides which
   evidence it can safely cite and whether provider failure means a failed answer.

The already-confirmed evaluation capture and bounded-investigation/answer seams
in [the testing strategy](../../design/testing-and-evaluation.md) apply. Tests
observe temporary journals and actual returned/saved answers, citations and traces;
use disposable PostgreSQL, local MLflow and controlled external model transports.
No renewed test-seam approval is required. The originating specification is the
user's selection and the report at
`/tmp/architecture-review-20261028-141741.html`; the scope above preserves its
requirements in the repository for review.

Graph interpretation, issue #19 implementation and paid inference are outside
this change. ADRs 0003–0007 continue to apply.

## Implementation

`EvaluationRun.capture` saves received results before optional verification.
`capture_pair` records both named attempts separately and selects the primary
response only after both finish. Verification cannot replace captured data or
its fingerprints. Failures retain their type and verification state without
including private exception messages. Existing frozen-run completion and review
eligibility rules still apply.

Investigation comparison delegates pairing and retention to this module;
fingerprint checks, scoring and trace/citation readback happen after capture.
Graph acceptance uses the same lifecycle and derives its established `responses`
presentation from detached journal records, including failed verification.

`answers.stopped_answer` owns short stop wording, the reply limit, citation
identifiers and the default unresolved outcome. Text answering supplies its
retained context except on failed generation; investigation supplies only the
passages its coverage assessment has resolved. Both retain the complete source
passages in citations. The shared implementation retains investigation's
conservative excerpt allowance so required route labels still fit.

## Regression evidence

- A new capture-before-verification test failed before the new lifecycle existed,
  then passed. Paired tests cover failure in the first readback, second capture
  and second readback, as well as successful primary selection and immutable
  returned records. All 49 evaluation-capture tests pass.
- The new long-passage text case reproduced the original `Draft` validation
  exception through the actual answer interface. It now returns a bounded partial
  answer with complete citations and exact saved-response/trace readback.
- A near-limit investigation case caught an initial shared-construction attempt
  that left insufficient room for its required synthetic-source label. The
  retained excerpt allowance addresses that regression.
- One initial relationship acceptance check rejected changed application identity
  because source files were edited during that check. Its failed artifact showed
  the differing application fingerprint. Integration checks were then rerun with
  stable software inputs.
