# Issue tracker: GitHub

Issues and specs for this repo live in GitHub Issues for
`tomh1988-8/rag_demo`. Use the `gh` CLI. Version 2.102.0 is installed at
`/home/tom/.local/bin/gh`, authenticated as `tomh1988-8`, and configured for native
Git HTTPS credentials. The user has also authorised the installed GitHub plugin;
its connector tools remain a fallback if native access becomes unavailable.

Pass `--repo tomh1988-8/rag_demo` to all `gh issue` and `gh pr`
commands so they work even without a configured Git remote.

## Current Ask Phil handoff

Issue #8 is complete and closed after [verified publication](https://github.com/tomh1988-8/rag_demo/commit/1991e3bf1e5a404137b1b8cb178a15bf85ebc6cf).
[Evidence](../implementation/issue-8/README.md)
records 182 passing tests, zero remaining independent review findings, nine live
CLI/API responses plus reset, actual MLflow trace readback and API restart checks.
All 15 factual claims, seven required facts and nine outcomes pass source-based
review. Six paid calls cost $0.0237656; the preserved shared $5 ledger is $0.232666
with zero unsettled reservations. The user explicitly approved both live execution
and publication; prior automatic approval denials are historical, not current
permission blockers. The published tree exactly matched local acceptance commit
`319de84` before closure; all eight checked criteria and the completed state were
read back. [The receipt](../implementation/issue-8/publication.json) records the
authenticated connector publication and native Git credential limitation.
#9 is now in progress. [Implementation and execution status](../implementation/issue-9/README.md)
records the quality-comparison workflow, failed live pilot and corrected API
regression. All 248 software tests, strict mypy and Ruff pass; both independent
reviews have zero remaining software findings. [Published implementation 928c0fb](https://github.com/tomh1988-8/rag_demo/commit/928c0fb6d12d5178aad25716dfe4146bb94cda32)
was pushed with native Git and its exact tree read back. Human review of eight
support labels and authorization for the corrected OpenRouter payloads are
pending in this session. The ticket remains
open; finish its actual comparison/calibration evidence before selecting another
ticket. Preserve the $0.241848 shared ledger and zero unsettled reservations.

The approved specification is [issue #1](https://github.com/tomh1988-8/rag_demo/issues/1). The 24 implementation tickets are issues #2–#25, with ready-for-agent labels and explicit blocker references. Do not recreate them. The user's feedback/online-evaluation amendment is included in specification #1 and tickets #22–#23; final acceptance #21 requires the full loop. Fusion/context expansion is #24 and repeated-question caching is #25; #21 requires both, with #23 inherited through #25. See the [saved handoff](../plans/ask-phil-tickets-v2/HANDOFF.md) and publication manifest for the exact mapping and remaining native-link work. Issues #2 and #3 are completed and closed. Issue #4 is completed and closed after scoped Sol acceptance and [verified publication](https://github.com/tomh1988-8/rag_demo/commit/a5062593449a941d28248614e1f3977d14fc9a57). #5 is completed and closed after 115 passing Docker tests, zero remaining review findings and [verified publication](https://github.com/tomh1988-8/rag_demo/commit/b6b45cb5eea3402ffe2be466e1693ef91af4ecf5). See its [acceptance evidence](../implementation/issue-5/README.md). #6 is completed and closed after 131 passing Docker tests, zero remaining review findings and [verified publication](https://github.com/tomh1988-8/rag_demo/commit/408012156c55d040bc69a22bff034f87dd9a5dbd). See its [refresh/recovery evidence](../implementation/issue-6/README.md). #7 is complete and closed after 149 passing tests, independently reviewed sourced API/CLI success for all 20 profiles and [verified publication](https://github.com/tomh1988-8/rag_demo/commit/55616db5ad07f686dce5d4ec96193ab73b1f0eaf); #8 is complete and closed as recorded above. #9 is in progress; #10, #11 and #24 are also unblocked. The laptop model remains development-only. See the handoff before selecting subsequent work.

The connector exposes issue creation/read/update and label operations but no native dependency/sub-issue mutation. Until that capability is available, consult each issue's Blocked by references and the saved graph before selecting work. Do not claim that native links have been installed. The [alternative-access review](../research/github-issue-dependency-access.md) records the official MCP/API/CLI options and the recommendation to retain the working references for now; do not repeat the investigation on each implementation turn.

## Conventions

- Create: `gh issue create --repo tomh1988-8/rag_demo --title "..." --body-file /path/to/body.md`
- Read: `gh issue view <number> --repo tomh1988-8/rag_demo --comments`
- List: `gh issue list --repo tomh1988-8/rag_demo --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --repo tomh1988-8/rag_demo --body-file /path/to/comment.md`
- Apply labels: `gh issue edit <number> --repo tomh1988-8/rag_demo --add-label "..."`
- Remove labels: `gh issue edit <number> --repo tomh1988-8/rag_demo --remove-label "..."`
- Close: `gh issue close <number> --repo tomh1988-8/rag_demo --comment "..."`

Issue #4 now has 85 passing software tests, an independently reviewed 13-case
cloud policy matrix and five actual CLI/API/restart checks. Use
`config/openrouter-sol.json` for this accepted slice. Qwen's smoke was rejected;
GLM is untested. The shared non-resetting $5 trial remains in force; recorded spend
for that historical slice was $0.10890587; see the latest #8 total above. Preserve the private key and shared ledger. See the
[private setup](../implementation/openrouter-setup.md) and
[cloud evidence](../implementation/issue-4/cloud/README.md). Run the staged-secret
scan before every publication. Broader calibrated quality remains #9; scoped
acceptance does not establish broad canon accuracy. Wait for the user's next
implementation instruction before starting another issue.

For multiline bodies, write the exact text to a temporary file and
pass its path with `--body-file`.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## When a skill says "publish to the issue tracker"

Create a GitHub issue in `tomh1988-8/rag_demo`.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --repo tomh1988-8/rag_demo --comments`.

## Repository publication

The user requested that implemented code and planning updates be visible on GitHub,
not only in issue bodies. The repository remote is `origin` at
`https://github.com/tomh1988-8/rag_demo.git`. Native Git HTTPS credentials are
configured through `gh auth setup-git`; use native Git for authorised publication
and verify the remote tree against the intended local tree. The authenticated
GitHub connector can also publish repository trees/commits and advance `main`
without forcing if native access is unavailable. Preserve existing work and both
histories when reconciling connector and local commits.

### Required at the end of every issue

The user explicitly requires committing and pushing at the end of each issue.
After the required checks and reviews, commit the issue's code, evidence and
handoff changes, then push to GitHub. If native push remains unauthenticated,
use the authorised connector fallback and state that publication method clearly.
Read back the remote revision and verify that its tree matches the intended
local commit before closing the issue or reporting completion. Include the
published commit link in the completion report. Local commits alone do not
satisfy this requirement; if publication fails, report the blocker explicitly.

Issue #7 is complete and closed after [exact-tree publication](https://github.com/tomh1988-8/rag_demo/commit/55616db5ad07f686dce5d4ec96193ab73b1f0eaf)
and readback of all seven checked criteria. [Evidence](../implementation/issue-7/README.md) records
149 passing tests, sourced API/CLI success for all 20 core profiles, and retained
Janine/context and garage/co-ownership gaps (21/23 full required-fact coverage).
The 26 live serving calls cost $0.0999804. Total reported trial spend at #7 was
$0.20888627; the preserved shared ledger was $0.208899 after upward rounding,
with zero unsettled reservations. #8 subsequently completed and closed above;
#9 is now in progress as recorded in the current handoff above.
