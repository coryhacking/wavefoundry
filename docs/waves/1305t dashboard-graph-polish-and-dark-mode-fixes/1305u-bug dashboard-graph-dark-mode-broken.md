# Dashboard: Graph Card Doesn't Switch to Dark Mode Properly

Change ID: `1305u-bug dashboard-graph-dark-mode-broken`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 1305t dashboard-graph-polish-and-dark-mode-fixes

## Rationale

The dashboard Graph card displays a duplicate `html[data-theme="dark"] .graph-svg` rule pair in `dashboard.css` (lines 1883-1898). The first rule (1883-1892) sets a light-mode white gradient background under the dark-mode selector — copy/paste error from light mode. The second rule (1894-1898) overrides it with `background: transparent`, but only for the `background` property. The first rule still wins for `width`, `min-height`, `height`, `border-radius`, and `border` declarations, polluting the dark-mode style cascade with light-mode values.

Result: when the operator toggles to dark mode, the graph canvas area renders with a stale light-mode geometry/background mix instead of clean dark-mode styling.

Source: operator report 2026-05-30.

## Requirements

1. The duplicate `html[data-theme="dark"] .graph-svg` block at lines 1883-1892 must be deleted. The second block at 1894-1898 (`background: transparent; border: none; box-shadow: none;`) is the intended dark-mode declaration and must remain.
2. After the deletion, the graph canvas in dark mode must use the unscoped (light mode default) `width: 100%; min-height: 420px; height: auto;` from `.graph-svg-wrap .graph-svg` (line 1730-1735) — the geometry is theme-agnostic and lives in the wrong block currently.
3. No other CSS rules touched. No JS changes.

## Scope

**Problem statement:** A duplicate, miscoped dark-mode rule applies light-mode background styling to the graph SVG when dark mode is active.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.css` — delete the 10-line block at lines 1883-1892.

**Out of scope:**

- Rebalancing graph node/edge colors for dark mode (separate concern; track if reported)
- Restructuring `.graph-svg-wrap` geometry
- Theme-toggle JS

## Acceptance Criteria

- [x] AC-1: The duplicate `html[data-theme="dark"] .graph-svg { ... }` block ending with the broken white-gradient background was removed from `dashboard.css`. Only one dark-mode `.graph-svg` rule remains (`background: transparent; border: none; box-shadow: none;`).
- [x] AC-2: `tests/test_dashboard_server.py` continues to pass — 138/138.
- [x] AC-3: Manual smoke verification — operator confirmed "looks good now" after dashboard restart with the combined `1305u` + `130ec` fix.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Delete the duplicate dark-mode `.graph-svg` block (lines 1883-1892)
- [x] Close gate
- [x] Run framework tests
- [ ] Manual smoke: restart dashboard, toggle dark mode, verify Graph card
- [ ] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The bug is the duplicate rule; removal is the fix |
| AC-2 | required | Tests must not regress |
| AC-3 | important | Manual verification confirms the visual outcome |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Delete the broken block entirely rather than fix its values | The block is duplicate; the second block already provides the intended dark-mode style | Edit the broken block to be the right value (rejected — would still leave duplicate rules) |

## Risks

| Risk | Mitigation |
|---|---|
| The broken block had a side effect that was hiding another issue | Tests + manual smoke catch any cascade regression |

## Related Work

- Companion to `1305v` (filter pill removal) and `1305w` (section separator contrast) in the same dashboard polish wave.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
