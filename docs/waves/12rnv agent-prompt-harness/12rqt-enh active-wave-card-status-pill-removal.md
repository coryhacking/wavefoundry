# Active Wave Card Status Pill Removal

Change ID: `12rqt-enh active-wave-card-status-pill-removal`
Change Status: `implemented`
Owner: Engineering

Status: implemented
Last verified: 2026-05-20
Wave: `12rnv agent-prompt-harness`

## Rationale

The active-wave card already has enough signals: the wave identifier, the title, the handoff marker when present, the change count, and the nested change list. The extra `active` status pill does not add much value and competes with the other metadata in the same row. Removing it simplifies the card without changing the underlying wave state.

## Requirements

1. Remove the visible status pill from the active-wave card only.
2. Keep pending-wave rows showing their status pill unchanged.
3. Keep the wave card layout, change count, and click behavior unchanged.
4. Add tests that guard the active-wave card render path.

## Scope

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Acceptance Criteria

- AC-1: The active-wave card no longer renders a visible status pill.
- AC-2: Pending-wave rows still render their status pill.
- AC-3: The active-wave card still shows the handoff marker, change count, and nested changes.
- AC-4: The dashboard test suite covers the active-wave card render path.
- AC-5: `docs-lint` passes after the change.

## Tasks

- [x] Remove the status pill from the active-wave card header
- [x] Update tests to assert the active-wave card render no longer includes the status pill
- [x] Run docs validation and the dashboard test suite

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|-----------|-------|------------|-------|
| active-wave-status-pill-removal | implementer | Prepare wave | dashboard UI edit |

## Serialization Points

- None beyond the standard dashboard edit/test flow.

## Affected Architecture Docs

N/A — dashboard presentation only.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core visible change |
| AC-2 | required | Must not regress pending-wave status cues |
| AC-3 | required | Preserves the useful active-wave metadata |
| AC-4 | required | Prevents the status pill from returning silently |
| AC-5 | required | Standard docs gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-20 | Change doc created in response to active-wave card cleanup request. | operator request |
| 2026-05-20 | Implemented: active-wave cards no longer render the status pill; pending-wave rows still show their status pill. | implementer |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
