# Issue #10 independent review

Fixed point: `f1ecc315eeb5e9a14843d6f56c401882b3250cde`.
Initial review commit: `6753c7c`.
The code-review skill ran Standards and Spec in separate parallel agents.

## Standards

Initial report: no findings. The diff follows the documented vocabulary and
relevant ADRs, including snapshot-bound investigation, preserved captured
evidence, neutral execution reporting, and PostgreSQL retrieval storage. Tests
exercise public budget arithmetic, HTTP outcomes, real PostgreSQL/pgvector,
MLflow records, and controlled external model services as required by the testing
strategy. Documented-standard breaches: 0. Baseline judgement-call findings: 0.

## Spec

The initial independent review found three issues and no scope creep:

1. **P1: incomplete database execution bounds.** Manifest queries lacked
   statement/lock timeouts; vector connections lacked connection timeouts.
   Manifest validation ran before the traced stop handler. The new locked-table
   API regression exceeded its two-second observation window with a half-second
   budget. The repair applies bounded read and connection settings and moves
   manifest validation into the traced execution boundary. The regression now
   returns a saved timeout with zero model attempts.
2. **P2: online spending exhaustion reported the wrong outcome.** The generic
   ValueError handler swallowed SpendingLimit and returned failed/provider_failure.
   New provider-cap and shared-ledger regressions both failed, then passed after
   a specific handler preserved skipped/spend_limit without paid inference.
3. **P2: validation errors echoed credentials in field names.** Although values
   and messages were sanitized, the error location copied an unknown JSON field
   verbatim. A synthetic-key field regression failed, then passed when locations
   were restricted to the static request source rather than user-selected keys.

The first Spec re-review confirmed those repairs but found one remaining P2:
only manifest timeouts were translated to saved outcomes. A direct retrieval
index timeout still returned 503, and a vector timeout escaped as a SQLAlchemy
error. Both new public API regressions failed. A shared translator now covers
direct and adapter-wrapped timeouts inside retrieval spans; both regressions pass
with saved timeout receipts and no generation call.

A final deadline audit also found that the local shared spending ledger still
used its older thirty-second lock wait. Its public budget regression failed
after thirty seconds. The ledger now bounds lock waits and query progress to the
remaining request time (at most five seconds), and the regression passes.

Final independent re-review of `cdc0438245e3cf8bc41ee9c98c7d08171b43257e`:

- **Standards:** 0 documented-standard breaches; 0 consequential baseline smells.
  The shared translator avoids duplicated handling; ledger deadlines and
  cancellation stay within the existing execution contract. Added regressions
  use approved public boundaries.
- **Spec:** zero remaining findings; no scope creep. All previous findings are
  resolved, including saved outcomes for direct and adapter-wrapped retrieval
  timeouts and bounded shared-ledger operations. The reviewer independently
  reran six accounting, cancellation and spending-exhaustion checks; all passed.

The final full suite passes 282 tests with no failures, errors or skips, recorded
in `software-tests.xml` and `validation.json`. All 101 tested inputs remain
unchanged; strict mypy, Ruff and formatting pass. No paid calls were made.
Model-quality release acceptance remains outside this slice.
