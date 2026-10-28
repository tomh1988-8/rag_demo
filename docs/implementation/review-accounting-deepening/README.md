# Reviewed-answer consistency and model accounting

The user selected both recommendations from the 28 October 2026 architecture
report and requested implementation with `/implement`. The starting revision and
review fixed point is `1de70ac36e56a8a618230c36ee0ff57ab306e00a` on `main`.
The originating report is `/tmp/architecture-review-20261028-164801-589816.html`;
the scope below retains its requirements for future review.

## Accepted scope and test seams

1. Concentrate shared frozen capture, review and score consistency in the
   evaluation module. Keep factual and persona criteria distinct. Derive the
   compatible factual/review fields from one checked result; reject divergent
   copies when reading existing artifacts. Preserve historical artifact formats,
   dimensions, critical gates, immutable outputs and frozen source/reference
   identities. Commands should not coordinate the proof obligations themselves.
2. Concentrate per-operation model measurements and request aggregation in the
   model execution module. Text answers and investigation must not erase stale
   embedding counts, infer embedding attempts from budget counters or reconstruct
   totals. Preserve individual decision receipts, embedding measurements, failed
   and skipped calls, unknown measurements, conservative spending reservations,
   request limits, provider costs and neutral recorded execution. The answer
   modules retain evidence selection and answer validation.

Use the already-confirmed evaluation scorer, bounded investigation and returned
answer/receipt seams in [the testing strategy](../../design/testing-and-evaluation.md).
Tests use temporary artifacts, real disposable PostgreSQL and local MLflow;
controlled HTTP responses substitute external model operations. Test observable
scores, failures, saved answers, receipts and trace agreement. Existing seams
require no renewed approval. Retain useful regressions and historical replay.

ADRs 0003–0007 remain in force. Preserve original evidence, source/reference
inputs, prompts, schemas, private files, the shared spending ledger and the user's
pre-existing workspace changes. No paid calls or unrelated issue implementation
are part of this work.

## Implementation

`CapturedAnswers` owns capture completion, case identity, frozen references,
usable responses, fingerprints and optional exact CLI/trace verification.
`ReviewedAnswers` binds a completed score artifact to that capture, checks each
reviewed case and recomputes factual scores. Generic review, quality comparison
and persona evaluation use the same checks. Evaluation publication also checks
the fingerprints of the bytes actually parsed before writing a new run.

Persona review and comparison now live in the persona evaluation module. One
checked persona observation supplies both the persona result and its compatible
factual/review fields. The command retains argument parsing and optional tracking
configuration. Factual, voice, harm, qualification and neutral-appendix criteria
remain separate, with unchanged rubric and historical output fields.

`Models.accounting` scopes the measurements for one answer. Model generation
retains each decision's receipt; query embedding records its own measurement at
execution, before later retrieval validation can fail. The model module owns
request totals and conservative propagation of unknown measurements. Text and
investigation consume those results without clearing counters or inferring
embedding attempts. Investigation tools no longer require a Models dependency.

## Regression evidence

Failure logs retain the original diagnostics with trailing whitespace normalized.

- Persona comparison initially accepted a captured answer with failed
  verification. A second case showed that a failed reviewed case could also
  appear inside a completed comparison. Both now fail before output publication.
- The new investigation case initially reported unknown embedding usage after a
  provider supplied seven tokens for one search and eleven for a malformed
  embedding. It now retains eighteen tokens and both measurements, while a later
  request reports only its own seven tokens. Actual receipts and root traces
  agree with both returned answers.
- Historical persona comparison dimensions, failures, variation, costs and case
  records replay exactly. Existing stale-review, copied-score and hidden-control
  regressions remain. A relabelled quality reference is rejected earlier by the
  shared loader, so its test accepts the reference error independently of wording.
- The independent Spec review caught a compatibility regression: quality replay
  accepted missing declared case identifiers or completion states. Both mutations
  first reproduced the failure. The shared loader now requires recorded-capture
  declarations; only generic review of pre-recorder artifacts enables legacy
  defaults.
- The Spec review also caught persona review accepting missing explicit case
  identifiers or embedded references. Both omissions were reproduced before
  tightening recorded-capture identity checks. All 87 affected offline checks
  pass after both repairs.


## Final verification

The full suite ran once against the final source and passed **575 tests**,
with zero failures, errors or skips, in **1417.71 seconds**.
Strict mypy passed all **131 files**, and Ruff lint/formatting and diff checks passed.
The final focused checks passed **87 offline evaluation checks** and **55 integration
checks**. Both independent review axes have **zero open findings**, after repairing
the two Spec findings and retaining their failing regressions.

All **186 frozen software/configuration/data inputs** still match the tested
source. All **809 protected existing files** remain unchanged, including the
user's pre-existing work, original source/reference inputs and private key. The
shared ledger remains **$0.673627**, with zero unsettled reservations and unchanged
bytes since the focused checks. No paid model calls were made. Four public schemas,
four prompt/rubric hashes and the investigation tool contract match the starting
revision. Historical persona and quality comparisons remain replayable.

- [Validation record](validation.json)
- [Independent review](review.md)
- [Full test report](software-tests.xml) and [log](software-tests.log)
- [Frozen inputs](software-inputs.json) and [compatibility](compatibility.json)

Reproduce with a disposable PostgreSQL/pgvector admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/postgres
MLFLOW_DISABLE_AGENT_HINT=1 PREFECT_HOME=/tmp/ask-phil-verification PREFECT_SERVER_ANALYTICS_ENABLED=false .venv/bin/pytest -v -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
