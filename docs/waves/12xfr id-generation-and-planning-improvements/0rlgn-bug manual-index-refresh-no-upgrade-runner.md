# Manual Index Refresh Without Upgrade Runner

Change ID: `0rlgn-bug manual-index-refresh-no-upgrade-runner`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: `12xfr id-generation-and-planning-improvements`

## Rationale

The dedicated `update-indexes` launcher is meant for normal post-edit index refreshes. It should not route through the upgrade orchestration script, because that pulls in upgrade-only hooks and makes the manual refresh path look like an upgrade handoff. The dashboard should also stop preserving a stale `failed` badge once its current snapshot is healthy again.

## Requirements

1. `update-indexes` should invoke the normal index setup path directly, not `upgrade_wavefoundry.py`.
2. The setup completion message should point at the canonical `mcp-server` launcher, not the raw Python module path.
3. The dashboard snapshot merge should stop preserving a stale `failed` build state when the live builder is idle.

## Scope

**Problem statement:** Manual index refreshes are currently routed through upgrade machinery, and the dashboard can hold onto an old failed badge longer than the current index state warrants.

**In scope:**

- `.wavefoundry/bin/update-indexes`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

**Out of scope:**

- Any change to the actual indexer or embedding logic
- Any change to upgrade-only hooks during a real upgrade

## Acceptance Criteria

- [x] AC-1: Running `update-indexes` no longer invokes `upgrade_wavefoundry.py`.
- [x] AC-2: The completion output points to the `mcp-server` wrapper as the canonical handoff.
- [x] AC-3: A healthy snapshot is not forced to keep a stale `failed` dashboard badge once the builder is idle.

## Tasks

- [x] Point `update-indexes` at `setup_index.py --background-code`
- [x] Update the setup completion handoff text
- [x] Relax the dashboard snapshot overlay so idle builders do not preserve stale failures
- [x] Add regressions for the launcher path and dashboard reset behavior

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Manual refreshes should not be upgrade-routed |
| AC-2 | important | Makes the operator handoff canonical and consistent |
| AC-3 | required  | The dashboard should reflect the current healthy state |

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| launcher path | implementer | — | Replace the upgrade runner with the normal setup path |
| handoff text | implementer | launcher path | Point at the bin wrapper |
| dashboard snapshot reset | implementer | — | Stop preserving stale failed state when idle |
| regression coverage | implementer | launcher path, dashboard snapshot reset | Prove both paths stay correct |

## Serialization Points

- `.wavefoundry/bin/update-indexes`
- `.wavefoundry/framework/scripts/setup_index.py`
- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_setup_index.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-26 | Change doc created for manual index refresh cleanup | |
| 2026-05-26 | Manual refresh path moved off upgrade runner; dashboard idle-state regression added and verified | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_setup_index.py' -v`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py' -v`; `.wavefoundry/bin/docs-lint` |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
