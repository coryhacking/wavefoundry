# Dashboard Stop and Restart MCP Commands

Change ID: `12kh7-enh dashboard-stop-restart-mcp-commands`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The dashboard already has a start command, but the operator path is incomplete when multiple repositories are open at once. Stop and restart commands should target only the current repository's dashboard process so an operator can cleanly control one checkout without affecting other running dashboards.

## Requirements

1. The MCP tool surface should expose stop and restart dashboard commands alongside the existing start command.
2. Stop should target the current repository's dashboard process only, using the repo-local dashboard metadata.
3. Restart should stop the current repository's dashboard and then start a new one for the same repository.
4. The public prompt surface should advertise the new Stop dashboard and Restart dashboard commands.
5. Regression coverage should verify per-repository process targeting and restart behavior.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/server.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md`
- `.wavefoundry/framework/seeds/152-start-dashboard.prompt.md`
- `.wavefoundry/framework/seeds/153-stop-dashboard.prompt.md`
- `.wavefoundry/framework/seeds/154-restart-dashboard.prompt.md`
- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/index.md`
- `docs/prompts/start-dashboard.prompt.md`
- `docs/prompts/stop-dashboard.prompt.md`
- `docs/prompts/restart-dashboard.prompt.md`
- `docs/prompts/prompt-surface-manifest.json`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing dashboard server binding logic
- Changing the dashboard bin launcher behavior
- Changing unrelated MCP tools

## Acceptance Criteria

- The MCP server exposes stop and restart dashboard tools.
- Stop only terminates the dashboard process recorded for the current repository.
- Restart returns a fresh dashboard URL for the current repository after stopping the existing process.
- The public prompt surface includes `Stop dashboard` and `Restart dashboard`.
- Regression coverage locks the process targeting and restart behavior in place.

## Tasks

- Add dashboard stop and restart helpers to the MCP server
- Register new MCP tools for stop and restart
- Update the prompt surface docs and canonical seeds for the new commands
- Add tests for repo-local stop and restart behavior

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Operators need the tools in the MCP surface |
| AC-2 | required | Cross-repo safety depends on repo-local targeting |
| AC-3 | required | Restart must reuse the same repo context |
| AC-4 | required | The commands should be discoverable from the public prompt surface |
| AC-5 | required | Tests should prevent regressions |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Stopping the wrong process could disrupt another repo | Use the repo-local dashboard metadata as the process source of truth |
| Restart could leave stale metadata behind | Refresh or clear the repo-local metadata as part of stop/restart handling |
| Prompt docs and seeds could drift | Update canonical seeds and rendered prompt docs together |
