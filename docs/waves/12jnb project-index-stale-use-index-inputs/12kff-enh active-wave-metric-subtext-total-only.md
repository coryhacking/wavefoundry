# Active Wave Metric Subtext Total Only

Change ID: `12kff-enh active-wave-metric-subtext-total-only`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The active-wave metric tiles already emphasize pending work in the headline number. The subtext should keep the `pending` cue but stop repeating the pending count, so the copy reads `pending, N total` for cleaner context.

## Requirements

1. Changes tile subtext must show `pending, N total`.
2. ACs tile subtext must show `pending, N total`.
3. Tasks tile subtext must show `pending, N total`.
4. The headline number remains the pending count.
5. The Wave tile behavior remains unchanged.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- wave documentation updates needed to track the copy change

**Out of scope:**

- Metric scoping logic
- Progress bar calculations
- Wave lifecycle semantics

## Acceptance Criteria

- The active-wave tiles show `pending, N total` in the subtext.
- The subtext keeps the pending cue without repeating the pending count.
- The headline number remains the pending count.
- The Wave tile remains unchanged.

## Tasks

- Update the metric tile subtext copy to `pending, N total`
- Sync the wave record with the copy change

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Subtext should not repeat the headline number. |
| AC-2 | required | The scoped total still needs to be visible. |
| AC-3 | required | The Wave tile must not change. |
| AC-4 | required | The docs must stay in sync with the renderer. |
