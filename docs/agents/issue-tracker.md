# Issue tracker: GitHub

Issues and specs for this repo live in GitHub Issues for
`tomh1988-8/rag_demo`. Use the `gh` CLI when available. The user has also authorised the installed GitHub plugin; its connector tools are the current working fallback because `gh` and CLI credentials are unavailable.

Pass `--repo tomh1988-8/rag_demo` to all `gh issue` and `gh pr`
commands so they work even without a configured Git remote.

## Current Ask Phil handoff

The approved specification is [issue #1](https://github.com/tomh1988-8/rag_demo/issues/1). The 24 implementation tickets are issues #2–#25, with ready-for-agent labels and explicit blocker references. Do not recreate them. The user's feedback/online-evaluation amendment is included in specification #1 and tickets #22–#23; final acceptance #21 requires the full loop. Fusion/context expansion is #24 and repeated-question caching is #25; #21 requires both, with #23 inherited through #25. See the [saved handoff](../plans/ask-phil-tickets-v2/HANDOFF.md) and publication manifest for the exact mapping and remaining native-link work. Issues #2 and #3 are completed and closed. The initial text-RAG slice has 32 passing tests and recorded local-model/MLflow/restart evidence; the next available tickets are #4 and #5. The laptop model is development-only; the handoff records the stronger-model migration gate. See the handoff before selecting subsequent work.

The connector exposes issue creation/read/update and label operations but no native dependency/sub-issue mutation. Until that capability is available, consult each issue's Blocked by references and the saved graph before selecting work. Do not claim that native links have been installed. The [alternative-access review](../research/github-issue-dependency-access.md) records the official MCP/API/CLI options and the recommendation to retain the working references for now; do not repeat the investigation on each implementation turn.

## Conventions

- Create: `gh issue create --repo tomh1988-8/rag_demo --title "..." --body-file /path/to/body.md`
- Read: `gh issue view <number> --repo tomh1988-8/rag_demo --comments`
- List: `gh issue list --repo tomh1988-8/rag_demo --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --repo tomh1988-8/rag_demo --body-file /path/to/comment.md`
- Apply labels: `gh issue edit <number> --repo tomh1988-8/rag_demo --add-label "..."`
- Remove labels: `gh issue edit <number> --repo tomh1988-8/rag_demo --remove-label "..."`
- Close: `gh issue close <number> --repo tomh1988-8/rag_demo --comment "..."`

Issue #4 is now implemented at the software-contract level (66 Docker tests), but
remains **open** because local Gemma fails semantic acceptance, including a served
citation-support regression. Resume #4 with a stronger provider, conservative local
credential/spend controls and a new baseline. Provider choice and environment-variable
name are pending user input. #5 remains independently unblocked; #4's dependants
must not be advanced. See [the evidence](../implementation/issue-4/README.md).

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
`https://github.com/tomh1988-8/rag_demo.git`. Native Git has read access but currently
lacks push credentials. The authenticated GitHub connector can publish repository
trees/commits and advance `main` without forcing; use that fallback for authorised
publication and verify the remote tree against the intended local tree. Preserve
existing work and both histories when reconciling connector and local commits.

### Required at the end of every issue

The user explicitly requires committing and pushing at the end of each issue.
After the required checks and reviews, commit the issue's code, evidence and
handoff changes, then push to GitHub. If native push remains unauthenticated,
use the authorised connector fallback and state that publication method clearly.
Read back the remote revision and verify that its tree matches the intended
local commit before closing the issue or reporting completion. Include the
published commit link in the completion report. Local commits alone do not
satisfy this requirement; if publication fails, report the blocker explicitly.
