# Active Wave Pending-First Metric Tiles

Change ID: `12kfe-enh active-wave-pending-first-metric-tiles`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The metric tiles for changes, ACs, and tasks should emphasize what still needs attention in the active wave(s). The tiles already scope to the current wave; this change simply makes `pending` the primary number and keeps `total` as the secondary context.

## Requirements

1. The Changes tile should show pending as the primary value.
2. The ACs tile should show pending as the primary value.
3. The Tasks tile should show pending as the primary value.
4. The secondary text should continue to show the scoped total.
5. The Wave tile behavior should remain unchanged.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- wave documentation updates needed to track the new metric copy

**Out of scope:**

- Metric scoping logic
- Progress bar calculations
- Wave lifecycle semantics

## Acceptance Criteria

- Changes, ACs, and tasks tiles show pending as the headline number.
- Each tile still shows the scoped total alongside the pending count.
- The Wave tile remains unchanged.
- Regression coverage is not required unless the rendering logic needs it.

## Tasks

- Update dashboard metric tile copy to show pending first
- Sync the wave record with the new metric wording

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The tiles should emphasize open work. |
| AC-2 | required | The scoped totals still need to remain visible. |
| AC-3 | required | The Wave tile must not change. |
| AC-4 | required | The docs must stay in sync with the rendering behavior. |
