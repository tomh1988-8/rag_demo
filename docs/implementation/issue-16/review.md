# Issue #16 independent code review

The implement skill required the code-review skill. Its two axes ran in separate
agents against the verified starting point
`2412c23172b7c343a37ce23463fd0ecece98920e`. The initial implementation is
`8061786`; the reviewed biological-admission repair is
`e2eb7f5e8c3f87ee2b1900445927d1debd697ad5`.

Diff command: `git diff 2412c23172b7c343a37ce23463fd0ecece98920e...HEAD`.
The user’s pre-existing README and untracked workspace changes are excluded.
Reviewers did not edit files or run paid models or the full suite.

## Standards

No remaining documented-standard violations or actionable smell findings.

The follow-up repair reinforces ADR 0005: biological connections now require the
family projection’s admission checks. Relationship history remains inspectable
without restoring held parentage through another path. Removing the fallback also
simplifies traversal and biological derivation.

The regression exercises public installation, admission and connection-query
contracts using explicitly labelled counterexamples. Contract and failure records
describe the final behavior consistently.

Reviewed `8061786..e2eb7f5`, retaining original fixed point
`2412c23172b7c343a37ce23463fd0ecece98920e`.

Standards findings: **0 hard violations, 0 actionable judgment calls**.

The Standards reviewer also checked the one-line test-fixture packaging change at
`4b883ede085d83750344220ccc60c46c6ae2a233`. It follows the existing test-stage
COPY pattern and supplies the new test’s declared dependency. Application behavior
and runtime-stage content are unchanged; no new finding was identified.

## Spec

No remaining findings after reviewing `e2eb7f5`.

Resolved P2: biological relationship-history fallback bypassed family admission.
The ticket requires composing established capabilities and excluding
“unchecked/held claims”; ADR 0005 requires the agreed admission checks. Equivalent
parentage assertions held for cycles could previously re-enter connection paths
through relationship history.

The repair uses admitted FamilyEdges exclusively for biological traversal and
derivations, excludes biological assertions from relationship adjacency, rejects
biological RelationshipStep values and preserves biological history for inspection.

The public SQL regression reproduces the original failure and now passes.
The [final focused report](final-focused-tests.xml) records 33 tests with zero
failures, errors or skips. [Regressions](regressions.json) preserve the finding and
the earlier event-only and legacy-manifest failures.

Spec findings: **1 resolved P2; 0 remaining findings**.

## Independent answer review

All 17 final runtime cases pass within their exposed scope. Eleven factual cases
pass source support, derivation/role preservation and citation support. Six empty
or unknown-character cases make no factual assertions; their outcomes and coverage
qualifications pass. Persisted MLflow root/tool outputs match all 17 responses;
every populated citation matches retained source text and hash.

The cases cover adoption, biological ancestry, historical alternatives, conviction
versus commission, composed paths, cycle/depth limits, performer exclusion,
CLI/session behavior and the other graph contracts. No explicitly false event
account appears in this runtime; prior evidence covers that behavior. These
results establish curated composition capability. Held-out accuracy and independent
canon corroboration remain unmeasured.

[Answer quality](answer-quality.json) records the individual dispositions and
applicability denominators. The [content comparison](runtime-review-comparison.json)
matches every final answer, path, evidence and other compared content field to the
independently source-reviewed initial response. The Spec reviewer subsequently
checked all 17 actual final MLflow root/tool outputs and populated citation text
and hashes independently, confirmed the current application fingerprint and
verified the register’s unchanged 35 Pass/16 Pending counts. No inconsistency or
remaining Spec finding was found. Final validation binds review applicability to
the accepted source and actual captured response content.

Standards: 0 hard violations and 0 actionable judgments; Spec: 1 resolved P2 and
0 remaining findings, with no unresolved worst issue on either axis.
