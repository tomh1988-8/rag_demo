# Independent review

Fixed point: `0ee405782b37d226ceec2cfad1dbde16d68e02a7`, the source revision
underlying the two architecture candidates selected by the user. Both axes
reviewed the scoped staged changes before the requested commit, excluding the
user's pre-existing README and untracked work. The accepted scope is in
[README.md](README.md).

## Standards

Initial finding: **P2 — Bind scorer inputs to the recorded frozen bytes.**
The relationship and event commands parsed source/reference files before
constructing the tracking client; the run subsequently froze those paths again.
A change during setup could make scores describe older bytes than the artifact.
This conflicts with the frozen-artifact requirements in
`docs/design/testing-and-evaluation.md`.

Resolution: `GraphPhase.reference` is frozen alongside the snapshot, Claim batch
and reviews. Assessments receive those frozen reference bytes and the run's
parsed snapshot. Commands retain only case scope identifiers. The copied-reference
regression first reproduced stale nonzero expected-label counts after tracking
setup replaced the labels with an empty reference, then passed using the actual
frozen labels. The failed-trace retention tracer also passed after this fix.

Final independent readback:

> Standards: 0 remaining findings. The P2 finding is resolved. Both commands
> retain only scenario scope in their callbacks. No additional actionable
> documented-standard breaches or smell-baseline findings.

## Spec

The initial and final independent reviews reported **zero findings**. They
confirmed ownership of capture, retention, actual trace proof and restart
readback; preservation of domain cases/scoring, raw/reviewed distinctions and
historical command behavior; refresh capture/outcome and publication atomicity;
and no source/reference, credential, ledger or unrelated user-file changes.

Final independent readback:

> No new Spec findings. The reference-binding fix matches the accepted
> requirement that assessments use the run's frozen snapshot and reference
> bytes. Capture retention, historical command behavior, domain scoring,
> raw/reviewed distinctions and refresh atomicity remain intact.

The Docker test stage includes the commands and existing reviewed fixtures
needed by their integrations. Missing Git metadata is explicit while actual
application identity remains recorded. HTTP elapsed measurements remain on
HTTP cases; the general capture measurement includes CLI execution.

Remaining findings: **Standards 0; Spec 0**. The original worst Standards finding
was P2 and is resolved; the Spec axis had no findings.
