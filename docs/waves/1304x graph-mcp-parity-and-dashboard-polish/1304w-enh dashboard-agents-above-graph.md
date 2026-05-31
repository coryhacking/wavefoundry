# Dashboard: Move Agents Panel Above Graph Panel

Change ID: `1304w-enh dashboard-agents-above-graph`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 1304x graph-mcp-parity-and-dashboard-polish

## Rationale

The dashboard's main column currently renders panels in this order: `ProgressCard` → `FrameworkFlow` → `GraphPanel` → `Agents`. The Agents panel is the operator's primary tool for understanding *who* is doing what in the active wave — coordinators, builders, reviewers — and is consulted more often than the graph visualization. Moving Agents above Graph puts the higher-frequency, lower-vertical-space panel closer to the wave-status hero, and pushes the larger Graph visualization further down where it doesn't compete for the first scroll position.

The change is a single component reorder in `dashboard.js` — no new components, no CSS work, no data-shape change.

Source: operator request during wave `12xr3` close-review.

## Requirements

1. In `dashboard.js`, the main column render tree must render the `Agents` component immediately after `FrameworkFlow` and before `GraphPanel`. The existing `agents.length ?` conditional must be preserved (the panel is hidden when no agents are roster-assigned).
2. No other panel ordering changes.
3. No CSS class changes, no markup changes inside either component, no prop changes.
4. The dashboard server tests must continue to pass with the same fixtures.

## Scope

**Problem statement:** Agents is the highest-frequency-read panel in the main column; it's currently below the Graph panel, requiring an extra scroll past a large visualization to see the wave's lane assignments.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js` — swap the order of `h(Agents, ...)` and `h(GraphPanel, ...)` in the parent render tree at the existing call site
- Verification via the dashboard server tests (`tests/test_dashboard_server.py`) — the dashboard renders are HTTP-fetched and snapshotted indirectly; confirm tests still pass

**Out of scope:**

- CSS / styling changes
- Responsive behavior changes
- Adding new panels, removing panels, or restructuring panel hierarchy beyond the single swap
- Changing the `agents.length ?` conditional render guard
- Reordering panels in any other section (sidebar, content grid, wave detail, etc.)
- Updating screenshots in docs that show the old order — those will refresh organically when next regenerated

## Acceptance Criteria

- [x] AC-1: In the dashboard's main column, the rendered order is `ProgressCard` → `FrameworkFlow` → `Agents` → `GraphPanel` (when `agents.length > 0`); when `agents.length === 0` the order is `ProgressCard` → `FrameworkFlow` → `GraphPanel`. Verified by `dashboard.js` swap at the parent's main-column render.
- [x] AC-2: No other rendered order changes anywhere in the dashboard. Verified — only the two adjacent `h(...)` calls were swapped.
- [x] AC-3: `tests/test_dashboard_server.py` continues to pass — 138/138 tests pass.
- [x] AC-4: Manual smoke verification — operator confirmed "dashboard looks good" after live restart with new render order (Agents above Graph).

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Swap the two adjacent `h(...)` calls in `dashboard.js` at the parent's main-column render (around line 4445–4446)
- [ ] Close gate
- [ ] Run framework tests; confirm `test_dashboard_server.py` passes
- [ ] Manual smoke test: `wave_dashboard_start` → load the dashboard → visually verify the new order
- [ ] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The ordering change is the entire purpose of the change |
| AC-2 | required | Scope guard — no other panels should move |
| AC-3 | required | Tests must not regress |
| AC-4 | important | Manual verification confirms the rendered result matches intent |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Single line swap, no component changes | The Agents and Graph components are self-contained; ordering is purely a parent-render concern | Wrap both in a configurable section component (rejected — over-engineering for a one-line change) |
| 2026-05-30 | Preserve the `agents.length ?` conditional | If no agents are assigned, the panel renders nothing; this is correct behavior and doesn't change with the reorder | Always render the panel (rejected — would leave an empty heading when no agents exist) |

## Risks

| Risk | Mitigation |
|---|---|
| The two panels have visual styles that assume a specific neighbor (margins, borders) | Both are independent components with their own styling; swapping them at the parent doesn't change their inner CSS |
| Dashboard server tests assert specific HTML order | None observed in `test_dashboard_server.py`; the tests focus on API endpoints and data shape, not rendered DOM order |

## Related Work

- This change is independent of wave `12xr3` graph work.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
