# Independent review

Fixed point: `92833682c091a1faf7f8ea4c2d29315ca1893740`.
The review covered the staged implementation and its tests/specification. Existing
unstaged README changes and untracked user files were excluded.

## Standards

Zero remaining actionable findings. Tests observe public retained outcomes,
frozen-evidence rejection, budget accounting, actual MLflow outputs and command
diagnostics. HTTP substitutes and MLflow failure injection use external adapters.
The extraction selection preserves distinct parentage and Character relationship
semantics. No documented-standard breaches, ADR conflicts or actionable baseline
smells remain.

The final preflight review confirmed that shared module-owned input validation
preserves command error precedence while `run` still validates independently;
there is no caller ordering requirement.

## Spec

Zero remaining actionable findings. The initial review identified two issues:

- A rejected truncated completion lost received raw text despite a settled charge.
  The provider adapter now retains redacted completion content before acceptance
  checks, and Claim extraction retains that content when the adapter raises.
  The rejected output remains failed and cannot become an admitted batch.
- A reference mismatch changed the command from usage exit 2 to traceback/exit 1.
  A typed mismatch is translated back into the parser error, with module-owned
  preflight before credential/profile setup. Actual subprocess checks cover
  configured, missing-key and missing-profile cases; all return exit 2 with the
  mismatch diagnostic and no output, ledger or tracking database.

Both findings received failing regressions before fixes and were independently
rechecked. Comparison evidence binding, historical replay, retrieval-score
recomputation, frozen-byte hashing and per-run accounting meet the accepted scope.

Final findings: Standards **0**; Spec **0**. Neither axis has an unresolved issue.
