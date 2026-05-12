# Dashboard: Semantic Index Tile Should Show Combined Totals

Change ID: `12j2v-enh index-tile-combined-totals`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The Semantic Index tile currently reports only the project-layer file count as its headline value and folds file count, chunk count, and status into one dense line. The dashboard now exposes both project and framework index layers, so the tile should summarize the combined indexed footprint across both layers. The freshness/build status should be visually separated onto its own line rather than packed into the same combined summary.

## Requirements

1. The Semantic Index tile must summarize combined project + framework indexed totals.
2. The combined totals must include both files and chunks.
3. Freshness/build status text such as `Up to date`, `Stale`, `Indexing…`, or `Index build failed` must render on a separate line from the combined totals.
4. Existing index tile click-through behavior must remain unchanged.

## Scope

**Problem statement:** the index tile underreports its scope by showing only project files and mixes totals with status in one line.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
  - Aggregate project/framework counts for the tile
  - Separate totals from status rendering
- `.wavefoundry/framework/dashboard/dashboard.css`
  - Add minimal styling for a distinct status line if needed

**Out of scope:**

- Changes to the full Semantic Index dialog
- Index build logic or health calculation changes

## Acceptance Criteria

- AC-1: The Semantic Index tile shows combined project + framework file totals.
- AC-2: The Semantic Index tile shows combined project + framework chunk totals.
- AC-3: Status text renders on a separate line from the totals summary.
- AC-4: Dashboard JS syntax and docs lint verification pass.

## Tasks

- Aggregate project/framework file and chunk totals for the tile
- Split the tile summary into totals line plus separate status line
- Preserve the existing tile click behavior
- Run dashboard verification

## Affected Architecture Docs

N/A — tile presentation only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core request: combined file totals |
| AC-2 | required | Core request: combined chunk totals |
| AC-3 | required | Core request: status on its own line |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Change doc created to aggregate project/framework totals in the index tile and separate the freshness/build status onto its own line. | Operator request; `dashboard.js`; `dashboard.css` |
| 2026-05-11 | Updated the Semantic Index tile to aggregate project + framework files/chunks, show the combined totals in the tile headline/summary, and render freshness/build state on its own line below the totals. | `dashboard.js`; `dashboard.css`; `node --check .wavefoundry/framework/dashboard/dashboard.js`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Combine project and framework counts in the tile rather than leaving the tile project-only | The dashboard already surfaces both layers elsewhere; the tile should reflect the full indexed footprint | Keep project-only tile value (rejected: misleadingly narrow) |

## Risks

| Risk | Mitigation |
|------|------------|
| Combined totals could crowd the tile | Keep status separate and use a compact secondary line for totals |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
