# Dashboard: Surface Canonical Index Build Status for Background Rebuilds

Change ID: `12khc-enh dashboard-index-build-guidance-background-rebuilds`
Change Status: `complete`
Owner: Engineering
Wave: `12jnb project-index-stale-use-index-inputs`
Status: complete
Last verified: 2026-05-13

## Rationale

The dashboard can already show index build progress when it starts the rebuild, but background rebuilds launched by other entrypoints do not always surface enough guidance in the Semantic Index tile. The dashboard should observe the same canonical build state and log files that the CLI and MCP status query use, so operators can see which layer is rebuilding, whether it is running or finished, and the latest progress line even when the dashboard did not start the worker.

This change keeps the build machinery detached from the dashboard process while making the dashboard a better observer of the shared build protocol.

## Requirements

1. The dashboard snapshot should include index build status for both project and framework layers even when the build was started outside the dashboard.
2. The dashboard should surface the active layer(s) and the latest progress line in the Semantic Index tile.
3. The dashboard should monitor the canonical index build state/log files so background rebuild progress appears without a manual restart.
4. The shared build-status query should remain the source of truth for build state and previous build stats.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_server_tools.py`
- shared index build status helpers if extraction is needed

**Out of scope:**

- Changing the detached build worker model
- Merging project and framework build logs
- Changing the index rebuild command-line interface

## Acceptance Criteria

- The dashboard Semantic Index tile shows an active build state and layer-specific guidance when a project or framework build is running outside the dashboard.
- Background rebuild progress lines are surfaced in the dashboard without requiring a restart.
- The canonical build status response remains the source of truth for build state and persisted stats.
- Regression tests cover both dashboard snapshot refresh and the shared build-status protocol.

Implementation verification: `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`, `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_server_tools.py'`, `python3 .wavefoundry/framework/scripts/run_tests.py` (1156 tests), and `./.wavefoundry/bin/docs-lint` all passed.

## Tasks

- Add dashboard snapshot plumbing for canonical index build status
- Surface layer-specific running guidance in the Semantic Index tile
- Add regressions for external/background build state visibility

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The dashboard should not hide background rebuilds |
| AC-2 | required | Operators need visible guidance while a build is active |
| AC-3 | required | The shared build-status protocol must remain authoritative |
| AC-4 | required | Tests should keep the cross-process behavior from regressing |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The dashboard could drift from the canonical build state protocol | Reuse the existing state/log files and shared status query semantics |
| Too much implementation coupling could make the dashboard own the build lifecycle | Keep the dashboard as an observer and only surface status/progress |
