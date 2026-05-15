# Pending Dialog Titles When No Active Wave

Change ID: `12kh5-enh pending-dialog-titles-when-no-active-wave`
Change Status: `complete`
Owner: Engineering
Status: ready
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

When no wave is active, the dashboard already switches the metric tiles to pending scope. The detail dialogs should match that state so operators do not see "Active Changes", "Active ACs", or "Active Tasks" when the dashboard is summarizing pending work instead.

## Requirements

1. The Changes dialog title should switch between active and pending wording based on whether a wave is active.
2. The ACs dialog title should switch between active and pending wording based on whether a wave is active.
3. The Tasks dialog title should switch between active and pending wording based on whether a wave is active.
4. The empty-state copy should stay aligned with the current dialog mode.
5. Regression coverage should verify the no-active-wave dialog titles.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing the active-wave metric tile semantics
- Changing the underlying filters or counts
- Changing repository-local prompt surfaces

## Acceptance Criteria

- With an active wave, the dialogs continue to use the active wording.
- With no active wave, the dialogs use pending wording.
- Empty-state messages remain consistent with the active/pending mode.
- Regression coverage exercises the no-active-wave title path.

## Tasks

- Add a shared title helper for the dialog modes
- Update the Changes, ACs, and Tasks dialogs to use the helper
- Add regression coverage for the no-active-wave dialog titles

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The title should match the dashboard state |
| AC-2 | required | All three dialogs should use the same mode switch |
| AC-3 | required | Empty-state copy should not contradict the title |
| AC-4 | required | Regression coverage should prevent drift |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Pending terminology could be confusing if the snapshot still contains historical active waves | Use the existing active-wave check that already drives the metric tiles |
| The copy change could miss one of the dialogs | Use a shared helper instead of duplicating string literals |
