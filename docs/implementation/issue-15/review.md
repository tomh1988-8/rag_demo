# Issue #15 independent reviews

Fixed point: `640084cc2fc55f43abb8f44b7c68c7a3a40d6c72` on `main`.
The task's staged and working changes were reviewed with
`git diff 640084cc2fc55f43abb8f44b7c68c7a3a40d6c72 -- src tests scripts docs/implementation/issue-15`.
There were no task commits at review time. The pre-existing root README and
untracked user work were excluded. The code-review skill's two independent agents
reviewed documented standards and GitHub issue #15/specification #1 separately.

## Standards

Final report:

> Hard violations: zero. The final repair preserves connected correction history
> and competing accounts, consistent with ADRs 0004–0005. Group expansion terminates
> when no additional groups remain and keeps claim-family distinctions through the
> existing group identifiers.
>
> The new regression exercises public review, graph and retrieval interfaces against
> real storage. Its controlled embedding substitute stays at the permitted
> external-model boundary, and its assertions check that all competing claims and
> evidence remain visible after a corrected identity.
>
> Judgment calls: zero outstanding. Renaming the helper to `complete_review_groups`
> resolves the previous naming finding. No additional actionable baseline smells found.
>
> Pending runtime evidence and full-suite completion remain outside this code review.

## Spec

Final report:

> Zero remaining Spec findings. Both reported defects are fixed.
>
> The persisted corrected-child regression passes: retrieving only the predecessor
> includes both current competing accounts and their evidence. Text and graph routes
> share the repaired closure. Correction chains retain history, while cycle, support,
> and prior-version safeguards remain intact.
>
> No confirmed missing requirements, incorrect implementations, or unrequested scope
> remain in the reviewed delta. Final runtime, full-suite, and evidence completion
> are still pending completion gates.

Standards: 0 hard violations and 0 outstanding judgment calls. Spec: 0 remaining
findings. Final execution evidence is recorded separately in `validation.json`.

## Findings repaired and re-reviewed

1. Spec P2: A retired by B prevented a subsequent B-to-C correction or a dispute,
   uncertainty or unsupported outcome for B. The repair binds inherited retirement
   to the immutable parent audit and follows acyclic replacement chains. Four pure
   admission and four persisted review regressions cover those later outcomes;
   fresh unsupported corrections still fail.
2. Spec P2: when A incorrectly named a different child, retrieving A's distinct
   passage could omit the current replacement's competing father account. The
   independent reviewer reproduced this against real PostgreSQL and added a public
   regression. It failed with only `mistaken-child` returned instead of all three
   Claims, then passed after terminal replacement groups became part of connected
   explanation closure. The same shared logic covers corrected episode/event groups.
3. Standards low-severity judgment call: `complete_disputes` described less than its
   expanded responsibility. Both callers now use `complete_review_groups`.

The first runtime also found a context-size failure before independent review:
repeated rationale forced the synthetic dispute's text answer to abstain. Shared rationale now
renders once while every source account and review record remains intact. The
initial results are retained; no context limit was increased for the pilot.

## Final runtime evidence review

The independent Spec reviewer then inspected all twelve `reviewed-*` responses
in `runtime-accepted` against frozen expectations, source passages and final audits:

- Locator correction, 4/4: supported Peggy parentage, explicit 104-to-105-character
  locator repair, unknown timing retained, original Claim retained and replacement admitted.
- Parentage correction, 4/4: biological Den/Sharon assertion explicitly superseded;
  adoption at age three supported and no biological edge remains.
- Synthetic dispute, 4/4: both Phil and Grant accounts and citations remain visible,
  explicitly synthetic and unresolved, with no established father edge or winner.

No factual or evidence-integrity errors were found in these twelve current answers.
All nineteen runtime records share application SHA
`badf2d507c8abcf7cacb8654585026c411f4b64bba531e9513ac0f759318ab07`.
Source offsets/hashes, publication identities and graph versions match the audits;
actual trace/saved-response/citation flags, restart readback, session resets and
frozen-input hashes pass. The failed projection retains the baseline, its candidate
returns HTTP 503, and exact retry succeeds.

The two parentage baseline/rollback responses are factual failures by design and
are excluded from factual passes. They demonstrate restoration of an authored
erroneous prior review. No issue-criterion failure was found in the runtime artifacts.
These are exposed deterministic development cases, with no held-out, human
adjudication or answer-model-quality claim. Full-suite results remain a separate
execution check in `validation.json`.
