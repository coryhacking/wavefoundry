# Remove Change from Wave

Owner: Engineering
Status: active
Last verified: 2026-04-30

Shortcut: **`Remove change from wave`**

## Purpose

Remove an admitted change from the active wave. Record the removal explicitly with a disposition.

## Steps

1. Update the wave record to mark the change as `deferred`, `moved`, or `superseded` with rationale.
2. Move the active change doc out of `docs/waves/<wave-id>/` and back to `docs/plans/` when the change remains active outside this wave. If duplicate staged and wave copies exist, stop and resolve the conflict explicitly instead of leaving both in place.
3. Record the removal in the wave's `## Wave Summary` at closure or note it in the Progress Log.
4. Do not delete the change doc unless the change is explicitly superseded and no carry-forward intent exists.

## Disposition Options

| Status | When to Use |
|--------|------------|
| `deferred` | Change is valid but will be handled in a future wave |
| `moved` | Change is being moved to a different wave |
| `superseded` | Change is replaced by a different approach; record rationale |
