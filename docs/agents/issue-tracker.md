# Issue tracker: GitHub

Issues and specs for this repo live in GitHub Issues for
`tomh1988-8/rag_demo`. Use the `gh` CLI when available. The user has also authorised the installed GitHub plugin; its connector tools are the current working fallback because `gh` and CLI credentials are unavailable.

Pass `--repo tomh1988-8/rag_demo` to all `gh issue` and `gh pr`
commands so they work even without a configured Git remote.

## Current Ask Phil handoff

The approved specification is [issue #1](https://github.com/tomh1988-8/rag_demo/issues/1). The 22 implementation tickets are issues #2–#23, with ready-for-agent labels and explicit blocker references. Do not recreate them. The user's feedback/online-evaluation amendment is included in specification #1 and tickets #22–#23; final acceptance #21 requires the full loop. See the [saved handoff](../plans/ask-phil-tickets-v2/HANDOFF.md) and publication manifest for the exact mapping and remaining native-link work. The user invoked implement for the first unblocked ticket, #2. Its native and Docker acceptance passed and #2 is closed as completed; the next available tickets are #3 and #5. See the handoff before selecting subsequent work.

The connector exposes issue creation/read/update and label operations but no native dependency/sub-issue mutation. Until that capability is available, consult each issue's Blocked by references and the saved graph before selecting work. Do not claim that native links have been installed. The [alternative-access review](../research/github-issue-dependency-access.md) records the official MCP/API/CLI options and the recommendation to retain the working references for now; do not repeat the investigation on each implementation turn.

## Conventions

- Create: `gh issue create --repo tomh1988-8/rag_demo --title "..." --body-file /path/to/body.md`
- Read: `gh issue view <number> --repo tomh1988-8/rag_demo --comments`
- List: `gh issue list --repo tomh1988-8/rag_demo --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --repo tomh1988-8/rag_demo --body-file /path/to/comment.md`
- Apply labels: `gh issue edit <number> --repo tomh1988-8/rag_demo --add-label "..."`
- Remove labels: `gh issue edit <number> --repo tomh1988-8/rag_demo --remove-label "..."`
- Close: `gh issue close <number> --repo tomh1988-8/rag_demo --comment "..."`

For multiline bodies, write the exact text to a temporary file and
pass its path with `--body-file`.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## When a skill says "publish to the issue tracker"

Create a GitHub issue in `tomh1988-8/rag_demo`.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --repo tomh1988-8/rag_demo --comments`.
