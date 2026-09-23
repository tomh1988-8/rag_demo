# GitHub native dependency access review

Reviewed 23 September 2026 after the user authorised investigating an alternative integration and said the existing references could remain if no usable route was available.

## Current connection and plugin catalog

The installed GitHub plugin has already created and read back specification #1 and implementation issues #2–#21 in `tomh1988-8/rag_demo`. Its current tool surface can create/update issues and labels but has no native dependency-write operation.

The Plugin Management catalog was searched for “GitHub” and “issue dependencies”. The only matching GitHub integration was the already-installed GitHub plugin. Other returned integrations target different services and are not a suitable replacement for this repository's tracker. No additional plugin was suggested or installed.

## Supported alternatives

**GitHub's official MCP server** documents `issue_dependency_write` under its experimental Insiders features. An authenticated connection with that capability can add the existing relationships using `method: add` and `type: blocked_by`. Insiders can be enabled through the server's documented URL/header options. This is a separately configured MCP connection, not another installable plugin found in this session's catalog. Its availability here has not been tested or configured.

Source: [GitHub MCP server's Insiders documentation](https://github.com/github/github-mcp-server/blob/main/docs/insiders-features.md#issue_dependencies).

**GitHub's REST API** supports creating a blocking dependency at `POST /repos/{owner}/{repo}/issues/{issue_number}/dependencies/blocked_by`, with the blocking issue's stable `issue_id`. The documentation specifies Issues write permission for fine-grained authentication. The publication manifest already stores the required issue IDs. A separately authenticated API client could therefore add these links; the current connector's generic fetch operation is GET-only.

Source: [GitHub issue dependency REST API](https://docs.github.com/en/rest/issues/issue-dependencies#add-a-dependency-an-issue-is-blocked-by).

**GitHub CLI** also documents adding dependencies to existing issues. It is not currently installed or authenticated in this workspace. This is another possible future route, not a capability exercised by this review.

Source: [GitHub's dependency creation guide](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies).

## Decision for the current handoff

Leave all 31 existing blocker references and the saved dependency mapping unchanged. Native creation is technically supported by GitHub, but unavailable through the currently connected tools; there is no additional suitable plugin in the searched catalog. A new MCP or CLI setup would require separate authentication. The recommendation is to avoid introducing that setup solely for these tracker links.

Native links remain uncreated, not silently considered complete. This does not prevent selecting the first unblocked implementation ticket, #2, from the saved graph. Do not repeat this investigation on every implementation turn. Revisit it if the user requests the separate connection or an authenticated dependency-write capability becomes available.

No configuration, credentials, remote issues, labels or dependency relationships were changed during this review. The user still intends to trigger the next skill before implementation starts.

