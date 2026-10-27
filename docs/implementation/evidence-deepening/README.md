# Comparison evidence and Claim extraction deepening

The user selected both candidates from the 27 October 2026 architecture report
and instructed implementation. The starting revision is `9283368`.

## Accepted scope

The captured-answer comparison module owns consistency between declared controls,
frozen dataset cases, saved answers, independent reviews and retrieval scores.
Capture and review use the same interpretation of recorded answer controls.
Reject a changed prompt, source fingerprint, model configuration, context budget,
retrieval policy or application identity that disagrees with the saved answer.
Reject relabelled references even when their hashes have been updated, and
recompute retrieval scores from the saved passages and frozen reference.

Keep the existing comparison interface, dimensions and critical quality gates.
Original issue #9 captures and reviews remain readable and reproduce their
original measurements. Historical v2 receipts predate execution records and used
the fixed 1200-byte context budget; newer receipts carry the actual budget in
their execution record. No retained evidence is rewritten to fit new validation.

The Claim extraction-run module owns frozen input loading, single-call execution,
raw candidates, scoring, provider usage, conservative shared-ledger readback,
trace completion and durable outcomes. Parentage and Character relationship
extraction and scoring retain their distinct meanings. The command keeps its
existing options, defaults and success/failure exit status.

Claim a fresh output path and retain a running record before model execution.
Retain the completed model outcome before trace readback, so unavailable tracing
cannot leave an empty extraction artifact after model work. Retain malformed
output, known charges and unsettled reservations honestly. Preserve attempted
work before propagating interruption. Never reuse a prior run's call accounting.
Fingerprint the input bytes actually parsed, rather than rereading them after
the call. Existing artifact fields remain; state and failure/source identities
are additive. Successful local outcomes match their actual trace outputs.

Preserve prompts, extraction schemas, source/reference data, admission rules,
private credentials, the existing non-resetting shared ledger, and the separation
of offline evaluation and serving. Add no paid calls or automatic retries.
ADRs 0004–0007 continue to apply; no new domain term or ADR is needed.

## Interfaces and test seams

`reviewed_comparison_run` validates the entire evidence chain before returning a
comparison run. Its public arguments and result are unchanged. It shares recorded
control and retrieval-reference interpretation with `capture_quality`.

`ClaimExtractionRun.run` accepts source/reference/output paths and the existing
relationship selection. The module takes the existing profile, credential, HTTP
adapter, shared Budget and MLflow client as dependencies. It owns the OpenRouter
call adapter for each attempt, so failed setup cannot inherit an earlier charge.
`Budget.summary` owns read-only ledger interpretation. The command no longer
coordinates raw candidates, scoring, ledger SQL, trace completion or file writes.

The optional `validate_extraction_inputs` preflight lets the command report a
reference mismatch before profile, credential, ledger or tracking setup, including
when the profile or key is absent. `run` independently validates and freezes its
actual input bytes, so callers need no validation ordering. Rejected provider
completions retain redacted received content without changing their failed status
or exposing raw content in the public provider-accounting schema.

Tests use the already-confirmed evaluation-scorer and Claim extraction/admission
seams in [the testing strategy](../../design/testing-and-evaluation.md). Use real
temporary files, SQLite ledgers and local MLflow; substitute external provider
HTTP and unavailable MLflow operations. The full regression suite uses real
disposable PostgreSQL/pgvector databases and Prefect. Keep existing domain-rule
tests; the new tests exercise previously untested retained-run behavior.

## Verification

The final full suite passed **366 tests**, with zero failures, errors or skips,
in 728.402 seconds using real disposable PostgreSQL/pgvector databases and local
MLflow/Prefect. The earlier full run was deliberately interrupted to apply the
independent review fixes; the completed suite used the final source. All 85
pinned source/dependency files match their tested hashes.

All **56 focused comparison, extraction and provider checks** passed. Strict mypy
passed all 82 files; Ruff, formatting and the staged secret scan passed. The
suite reports the existing Starlette/httpx deprecation and JUnit record-property
warning categories. Independent [Standards and Spec reviews](review.md) have zero
remaining findings.

Readback of real local MLflow storage confirmed **two successful extraction
traces across two spans**, with exact agreement between retained outcomes and
actual root outputs. The [trace readbacks](runtime-traces.json) retain their
identities and matching fingerprints. These are controlled software checks;
they do not establish live extraction quality or canon accuracy.

The original issue #9 comparison reproduces every recorded quality dimension and
both failed critical gates. No paid calls were required. All 34 protected input,
lockfile, credential and ledger files match their starting fingerprints. The
shared ledger remains **$0.386799**, with zero unsettled reservations. Pre-existing
user work is excluded from this change.

The [validation record](validation.json) binds the results to the tested source,
frozen inputs, prompts and artifacts. See the [full test report](software-tests.xml).
To reproduce with a disposable PostgreSQL admin connection:

```sh
export ASK_PHIL_TEST_DATABASE_URL='postgresql://USER:PASSWORD@HOST:PORT/postgres'
.venv/bin/pytest -q -p no:cacheprovider
.venv/bin/mypy src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff check src tests scripts docs/implementation/issue-9/apply_support.py
.venv/bin/ruff format --check src tests scripts docs/implementation/issue-9/apply_support.py
```
