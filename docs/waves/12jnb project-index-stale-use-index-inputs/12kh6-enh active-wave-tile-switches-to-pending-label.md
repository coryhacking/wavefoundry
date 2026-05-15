# Active Wave Tile Switches to Pending Label When No Active Wave

Change ID: `12kh6-enh active-wave-tile-switches-to-pending-label`
Change Status: `complete`
Owner: Engineering
Status: ready
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

When there is no active wave, the dashboard already switches the Changes / ACs / Tasks tiles and dialogs to pending wording. The Waves tile should follow the same mode so the overview card does not continue to say `Active Waves` while everything else is presenting pending work.

## Requirements

1. The Waves tile should continue to show active wording while a wave is active.
2. The Waves tile should switch to pending wording when no wave is active.
3. The Waves tile count should reflect the current mode it is displaying.
4. The pending AC and Task metric tiles should use the same pending-scope change set as the dialogs when no wave is active.
5. Regression coverage should verify the no-active-wave pending label and the shared pending scope.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- `docs/waves/12jnb project-index-stale-use-index-inputs/wave.md`

**Out of scope:**

- Changing wave lifecycle state calculations
- Changing pending/active change counts
- Changing any dialog behavior

## Acceptance Criteria

- With an active wave, the Waves tile still says `Active Waves`.
- With no active wave, the Waves tile says `Pending Waves`.
- The count shown in the tile matches the displayed mode.
- The pending AC and Task tiles use the same pending-scope change set as the dialogs when no wave is active.
- Regression coverage exercises the no-active-wave label.

## Tasks

- Add a shared active/pending label helper for the Waves tile
- Update the Waves metric tile to switch labels and counts by mode
- Point the pending AC and Task metric tiles at the same pending-scope change set used by the dialogs
- Add regression coverage for the no-active-wave wording

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The overview should stay consistent with the dashboard mode |
| AC-2 | required | The tile wording must match the visible state |
| AC-3 | required | The tile count should not contradict the label |
| AC-4 | required | Pending AC and Task tiles should match the dialog scope |
| AC-5 | required | Regression coverage should lock the behavior in place |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Pending wording could be confusing if the repo has zero pending waves | Keep the count visible and continue to show the total waves note |
| Switching the metric value could make the tile feel inconsistent | Use the same count logic already used by the note and dialog mode |
