# Exclude Wavefoundry Logs From Project Stale Detection

Change ID: `12khb-bug exclude-wavefoundry-logs-from-project-stale-detection`
Change Status: `complete`
Owner: Engineering
Wave: `12jnb project-index-stale-use-index-inputs`
Status: complete
Last verified: 2026-05-13

## Rationale

The dashboard writes `.wavefoundry/logs/dashboard.log` continuously while it is running. That runtime log file is not a semantic project input, but it can still show up as a changed `.wavefoundry/` path and keep the project index marked stale even when the repository itself is otherwise idle.

This change excludes dashboard log files from the project-layer index and stale detection so the dashboard stops rebuilding because of its own runtime logging.

## Requirements

1. `.wavefoundry/logs/` should be excluded from the project index walk and stale detection.
2. Dashboard runtime log writes should not keep the project index stale.
3. Existing project/runtime exclusions should remain intact for `.wavefoundry/dashboard-server.json` and `.wavefoundry/guard-overrides.json`.
4. Regression coverage should lock the log exclusion in place.

## Scope

**In scope:**

- `.gitignore`
- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing the dashboard log format
- Changing the general index freshness model
- Changing framework-layer stale detection

## Acceptance Criteria

- `.wavefoundry/logs/` is excluded from project index traversal and project stale detection.
- Dashboard runtime log updates no longer trigger project stale rebuild loops.
- Existing runtime state exclusions remain in place.
- Regression tests cover both the indexer traversal and dashboard stale checks.

## Tasks

- Add `.wavefoundry/logs/` to the project exclusion surface
- Update stale detection to ignore dashboard log files
- Add regression tests for project walk and stale checks

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The runtime logs are the direct source of false stale triggers |
| AC-2 | required | Rebuild loops are the user-visible failure mode |
| AC-3 | required | Existing runtime exclusions must stay intact |
| AC-4 | required | Tests should prevent the regression from coming back |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Excluding too broadly could hide real project inputs | Limit the exclusion to `.wavefoundry/logs/` only |
| Different runtime files could later be added under `.wavefoundry/` | Keep the runtime log exclusion explicit and add targeted tests for new host-local files as needed |
