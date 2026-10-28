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
passages in citations. The shared implementation sizes the complete reply,
including required classification qualifications and synthetic-source labels.
It uses citation-only support wording when excerpts would overflow. If the
qualifications alone cannot fit, it returns insufficient evidence and retains
the captured context, without presenting an unqualified cited fact.

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
- All 53 affected execution, investigation/cloud and graph-acceptance checks then
  passed on stable inputs. Strict mypy passed all 126 files; Ruff and formatting
  passed.
- The independent Spec review found that required classification qualifications
  were appended after the initial size guard. New returned-answer tests reproduced
  the overflow in both routes. The fix sizes those qualifications with the reply;
  an additional case checks bounded abstention when the qualification cannot fit.

## Final verification

The full suite ran once at the end and passed **561 tests**, with zero failures,
errors or skips, in **23 minutes 15 seconds**. The single warning is the existing
Starlette/httpx deprecation. Strict mypy passed all **126 files**, and Ruff lint
and formatting passed. Both independent review axes have **zero remaining
findings** after the qualification fix.

All **176 frozen software/configuration/data inputs** still match the tested
revision `34aa0bf`. All **753 protected existing files** remain unchanged,
including the user's original workspace changes, **40 original data files**,
private inputs and the shared spending ledger. No paid model calls were made.
The ten intentional existing-file edits implement the selected scope; the third
architecture candidate and issue #19 remain subsequent work.

- [Validation record](validation.json)
- [Independent Standards and Spec reviews](review.md)
- [Full test report](software-tests.xml) and [test log](software-tests.log)
- [Frozen software inputs](software-inputs.json)

Reproduce with a local disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
MLFLOW_DISABLE_AGENT_HINT=1 PREFECT_HOME=/tmp/ask-phil-verification PREFECT_SERVER_ANALYTICS_ENABLED=false .venv/bin/pytest -v -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
