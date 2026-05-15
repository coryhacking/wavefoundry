# wave_reopen: Support Paused Waves

Change ID: `12mh2-enh wave-reopen-supports-paused-waves`
Change Status: `complete`
Previous Change Status: `planned`
Owner: Engineering
Status: active
Last verified: 2026-05-14
Wave: `12mc3 agent-detail-panel-blank-section-mismatch`

## Rationale

`wave_reopen` previously rejected paused waves with a `wave_not_closed` error, requiring a manual status edit to resume a paused wave. Paused waves are temporarily suspended — not finished — so reopening them to active is a natural operation that the tool should support directly.

## Requirements

1. `wave_reopen_response` must accept waves with status `paused` in addition to `closed`, setting their status to `active`.
2. The error path must still reject `active`, `planned`, and any other status that is not `closed` or `paused`.
3. The error message must reflect the expanded set of accepted statuses.

## Scope

**Problem statement:** `wave_reopen` only accepted `closed` waves, forcing a manual file edit to resume a paused wave.

**In scope:**

- Status guard in `wave_reopen_response` in `server.py`
- Error message update
- Test coverage for the paused-wave success path

**Out of scope:**

- Changes to `wave_pause` behavior
- Any other wave lifecycle tools

## Acceptance Criteria

- AC-1: `wave_reopen` on a paused wave returns `status: ok` and sets the wave to `active`.
- AC-2: `wave_reopen` on an active or planned wave still returns `status: error` with `wave_not_closed`.

## Tasks

- [x] Change guard from `current_status != "closed"` to `current_status not in ("closed", "paused")` in `server.py`
- [x] Update error message to "only closed or paused waves can be reopened"
- [x] Add `test_reopen_paused_wave_sets_status_active` to `test_server_tools.py`

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| server-logic | implementer | — | server.py + test_server_tools.py; framework_edit_allowed gate |

## Serialization Points

- `framework_edit_allowed` gate required for `server.py` and `test_server_tools.py`.

## Affected Architecture Docs

N/A — confined to a single tool handler; no boundary or flow changes.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core fix — paused waves must be reopenable |
| AC-2 | required | Must not regress existing rejection behavior |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-14 | Implemented; 1173 tests pass | test_reopen_paused_wave_sets_status_active added |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-14 | Extend guard rather than add separate tool | Paused and closed are the only two "not active" terminal states worth resuming; one tool is simpler | Separate wave_resume tool — unnecessary complexity |

## Risks

| Risk | Mitigation |
|------|------------|
| None significant | Change is a two-token guard extension with direct test coverage |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
