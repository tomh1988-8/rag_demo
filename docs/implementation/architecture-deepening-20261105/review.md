# Independent review

Fixed point: `dcf2b5e2d53f9e82033dee1eceefd3098e3acbaa`.
Both reviewers inspected the staged implementation before the requested commit,
using `git diff --cached` against that fixed point. The spec is the selected
architecture report and [accepted scope](README.md). Unrelated user work was
excluded. Neither reviewer ran paid inference or the full suite.

## Standards

Final report: **0 remaining findings**. No documented-standard violations found.

The reviewer initially identified two low-priority Duplicated Code judgement
calls: counting model executions separately for admission and final expense, and
selecting complete versus retained capture readers separately for plain and
archived files. `recorded_calls` and one reader selection resolve them.

The final review found no actionable baseline smells in the failed-only retained
factory, shared row validation or continuation guard.

## Spec

Final report: **0 remaining findings**. No scope creep or Character reference
correctness concern remains.

The reviewer independently reproduced three defects with temporary files:

1. A budget stop between requests marked an already verified response failed.
   Strict retained-row validation now preserves that observation without changing
   the failed source journal or making it eligible for ordinary whole-run review.
2. Empty prior directories disappeared from continuation lineage. Their directory
   identities and empty capture sets are now retained; later additions are rejected.
3. A running source could overlap a continuation before changed-file checks ran.
   Retained reads now require failed phases, and explicit phase progress blocks
   admission before a request, between requests and between arms. Blocked
   descendants preserve their active ancestor's lineage.

Each defect first failed a regression and then passed. Independent final
temporary-file checks confirmed the repairs, including continuation through a
blocked descendant. The graph-to-text fallback check now uses a conversation
turn and verifies its retained Character reference.

The initial full-suite attempt subsequently found standalone requests receiving
conversation clarification. Four narrow turn guards restore original questions
and draft validation for standalone requests while preserving shared references
for conversation turns. Both reviewers independently rechecked that repair and
reported zero remaining findings; the original failure artifacts are retained.

The subsequent complete run passed 732 cases and exposed a five-second fixture
shutdown wait that was shorter than the application's two sequential 15-second
worker-drain allowances. The test-only wait is now 35 seconds, with the stopped
thread assertion intact. Both reviewers confirmed that this aligns the harness
with the existing contract and reported zero findings. Four affected conversation
checks passed before the final full run.

The next full run passed 732 cases; its remaining network-timeout check exhausted
the test's 1.2-second allowance before reaching provider I/O. The injected test
deadline is now three seconds, still below the controlled provider's ten-second
hold. Both reviewers confirmed zero findings: all timeout, actual peer-close,
MLflow terminal-trace and empty-result assertions remain, and production limits
are unchanged. Both timeout/disconnect cases pass in the focused repair check.

Standards: 0 remaining. Spec: 0 remaining.
