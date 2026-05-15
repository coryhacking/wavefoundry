# Active Wave Index Note Comma Separator

Change ID: `12kfh-enh active-wave-index-note-comma-separator`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-13
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

The Semantic Index tile should match the comma-separated style used by the other active-wave metric tiles.

## Requirements

1. The Index tile subtext must use a comma separator instead of a slash.
2. The rest of the tile copy should remain unchanged.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- wave documentation updates needed to track the separator change

**Out of scope:**

- Index totals
- Wave tile behavior
- Metric scoping logic

## Acceptance Criteria

- The Index tile subtext uses `files, N chunks`.
- The other metric tiles remain unchanged.
- The Wave tile remains unchanged.

## Tasks

- Update the index tile subtext separator
- Sync the wave record with the copy change

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The separator should match the rest of the metric tiles. |
| AC-2 | required | No other tile copy should change. |
| AC-3 | required | The Wave tile must not change. |
