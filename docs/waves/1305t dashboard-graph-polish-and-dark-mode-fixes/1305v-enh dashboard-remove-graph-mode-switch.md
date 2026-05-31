# Dashboard: Remove the Graph Mode-Switch Filter Pills

Change ID: `1305v-enh dashboard-remove-graph-mode-switch`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 1305t dashboard-graph-polish-and-dark-mode-fixes

## Rationale

The Graph card currently renders a four-button mode-switch row — Communities / Focus / Files / Clear — that lets operators explicitly toggle the graph view mode. In practice the view mode is also driven implicitly by selection: `selectedMode = selectedNodeId ? "focus" : selectedClusterId ? "overview" : viewMode` (`dashboard.js:3494`). When the operator clicks a node, the graph switches to focus mode automatically; when they click a community in the overview, it stays in overview. The explicit pills are redundant with that implicit behavior and add visual noise to the card header.

Operator requested removing the pills entirely so mode is fully determined by selection.

Source: operator request 2026-05-30.

## Requirements

1. The `<div className="graph-mode-switch">` block in `dashboard.js` (around line 3641-3661) must be removed, including the three view-mode pills (Communities / Focus / Files) and the trailing Clear button.
2. The implicit mode logic in `selectedMode` (line 3494) must remain unchanged — `focus` when a node is selected, `overview` when a cluster is selected, else the `viewMode` state default ("overview").
3. The breadcrumb-driven view-mode setters in the same file (`setViewMode("focus")` on node click at line 3613, `setViewMode("overview")` on cluster click at line 3624, breadcrumb-driven `setViewMode(crumb.viewMode)` at line 3496) must remain unchanged — those are the implicit drivers that take over.
4. No CSS changes; the `.graph-mode-switch` and `.graph-layer-pill*` classes are also used by other dashboard elements and remain in CSS.

## Scope

**Problem statement:** Explicit mode-switch pills are redundant with the implicit selection-driven mode logic and add visual noise.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js` — delete the `<div className="graph-mode-switch">` block (one `h(...)` call covering ~12 lines).

**Out of scope:**

- Changes to `selectedMode` logic
- Removing the `viewMode` React state — still needed as the implicit-default
- CSS edits — `.graph-mode-switch` class is shared
- Renaming or relocating any other Graph card elements

## Acceptance Criteria

- [x] AC-1: The `<div className="graph-mode-switch">` block was removed from the Graph card render in `dashboard.js`. Existing test (`test_dashboard_js_includes_readable_graph_overview_controls`) was updated to assert the block is **absent** (`assertNotIn`) and to document the new contract.
- [x] AC-2: The implicit mode logic (`selectedMode = selectedNodeId ? "focus" : ...`) is unchanged.
- [x] AC-3: Clicking a node still switches to focus mode — the existing `setViewMode("focus")` handler at line 3613 is untouched.
- [x] AC-4: Clicking a community in the overview still switches to overview mode — the existing `setViewMode("overview")` handler at line 3624 is untouched.
- [x] AC-5: `tests/test_dashboard_server.py` continues to pass — 138/138 after the in-session test update.
- [x] AC-6: Manual smoke verification — operator confirmed "looks good now" after dashboard restart; the four pills are gone and the graph still navigates via node-click and cluster-click.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Delete the `<div className="graph-mode-switch">` block in `dashboard.js`
- [x] Update `test_dashboard_js_includes_readable_graph_overview_controls` to assert the new contract
- [x] Close gate
- [x] Run framework tests — 1878/1878 pass
- [ ] Manual smoke verification — pending
- [x] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Pill removal is the entire purpose |
| AC-2 | required | Implicit mode logic must keep working |
| AC-3 | required | Node-click drives focus mode; this is the new sole way to enter focus |
| AC-4 | required | Cluster-click drives overview mode; this is the new sole way to switch back |
| AC-5 | required | Tests must not regress |
| AC-6 | important | Manual smoke catches any interaction regression |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Keep `viewMode` React state | The implicit-default still needs storage; state is the right home | Remove state too (rejected — implicit-default fallback requires it) |
| 2026-05-30 | Don't touch shared CSS classes | `.graph-mode-switch` and `.graph-layer-pill*` are used elsewhere | Delete classes too (rejected — would break other elements) |

## Risks

| Risk | Mitigation |
|---|---|
| Operators rely on the Clear button to reset filters when stuck | The implicit logic auto-clears when selection clears; if a state is reachable that's not auto-clearable, file as follow-on |

## Related Work

- Companion to `1305u` (graph dark mode) and `1305w` (section separator contrast).

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
