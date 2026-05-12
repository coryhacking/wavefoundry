# Dashboard: Remove Dead `activity.files_changed` Payload

Change ID: `12j2q-maint remove-dead-files-changed-activity`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

After the Files tile moved from “files updated today” semantics to git working-tree semantics, the dashboard no longer reads `snapshot.activity.files_changed`. The frontend now uses `snapshot.git.files_changed`, `snapshot.git.lines_added`, `snapshot.git.lines_removed`, and `snapshot.activity.files_changed_all`. The older `activity.files_changed` list is still being built and tested, which makes it dead payload surface area and dead verification noise.

## Requirements

1. Remove the unused `activity.files_changed` field from the dashboard snapshot.
2. Remove tests that exist only to preserve the dead `activity.files_changed` field.
3. Preserve the live working-tree signals:
   - `snapshot.git.files_changed`
   - `snapshot.git.lines_added`
   - `snapshot.git.lines_removed`
   - `snapshot.activity.files_changed_all`
4. Do not change the Files tile or changed-files dialog behavior introduced by `12j2j`.

## Scope

**Problem statement:** the dashboard still computes and tests a “files changed today” activity payload that is no longer consumed anywhere in the UI.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_lib.py`
  - Remove `activity.files_changed`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Remove or update obsolete assertions that only validate `activity.files_changed`

**Out of scope:**

- Any change to current git summary stats
- Any change to the all-files dialog payload
- Reintroducing a time-window-specific files metric

## Acceptance Criteria

- AC-1: The dashboard snapshot no longer includes `activity.files_changed`.
- AC-2: No dashboard UI path depends on `activity.files_changed`.
- AC-3: Obsolete tests for the removed field are deleted or updated.
- AC-4: Dashboard verification passes after the cleanup.

## Tasks

- Remove `activity.files_changed` from `collect_activity()`
- Remove obsolete tests that assert the field exists
- Re-run dashboard verification

## Affected Architecture Docs

N/A — dead payload cleanup only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core cleanup target |
| AC-2 | required | Prevents removing something still in use |
| AC-3 | required | Keeps tests aligned with the real contract |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Cleanup change created after confirming `activity.files_changed` is no longer consumed by the dashboard UI and only remains in snapshot construction plus obsolete tests. | `dashboard.js`; `dashboard_lib.py`; `test_dashboard_server.py` |
| 2026-05-11 | Removed `activity.files_changed` from the snapshot, deleted obsolete tests for the removed field, and kept the live working-tree git stats plus `files_changed_all` dialog path unchanged. Dashboard tests pass and docs lint is clean. | `dashboard_lib.py`; `test_dashboard_server.py`; `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Remove the dead field rather than keeping it as undocumented compatibility baggage | The dashboard is the only consumer here and no remaining UI path reads it | Keep the dead field “just in case” (rejected: unnecessary payload and test noise) |

## Risks

| Risk | Mitigation |
|------|------------|
| Hidden UI dependency was missed | Search references before deletion; rerun dashboard verification after cleanup |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
