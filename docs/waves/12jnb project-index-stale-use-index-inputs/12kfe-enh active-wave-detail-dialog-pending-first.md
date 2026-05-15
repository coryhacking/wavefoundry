# Active Wave Detail Dialog Pending-First

Change ID: `12kfe-enh active-wave-detail-dialog-pending-first`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The detail dialogs for changes, ACs, and tasks should put pending items before closed items so the first screenful emphasizes active work.

## Requirements

1. The Changes dialog should list pending changes before closed changes.
2. The ACs dialog should list pending ACs before closed ACs.
3. The Tasks dialog should list pending tasks before closed tasks.
4. Existing counts and filters should remain unchanged.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- wave documentation updates needed to track the dialog ordering behavior

**Out of scope:**

- Metric tile values
- Progress bars
- Wave lifecycle semantics

## Acceptance Criteria

- Detail dialogs show pending entries first and closed entries after.
- Dialog counts remain unchanged.
- Regression coverage proves the sort order is stable.

## Tasks

- Update dialog sorting for changes, ACs, and tasks
- Add regression coverage for the ordering behavior

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Pending items must be visually prioritized. |
| AC-2 | required | Counts must not change as a side effect. |
| AC-3 | required | The ordering must apply consistently across dialogs. |
