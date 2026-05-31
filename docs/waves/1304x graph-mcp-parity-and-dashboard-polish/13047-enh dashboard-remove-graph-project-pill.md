# Dashboard: Remove the Standalone "project" Layer Pill from the Graph Card

Change ID: `13047-enh dashboard-remove-graph-project-pill`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-30
Wave: 1304x graph-mcp-parity-and-dashboard-polish

## Rationale

The dashboard Graph card header currently renders a single-button "layer switch" tablist with one pill labeled "project". There's no other layer option — the only graph layer the dashboard reads is the project layer (framework / union layers are not exposed). The pill has no onClick handler; it does nothing when clicked and just declares itself the active tab. It's visual noise that implies a layer selector exists when it does not.

Remove the pill (and its wrapping `<div class="graph-layer-switch">` container). Keep the graph card title and the subtitle (node/edge counts) intact.

Source: operator request during wave `1304x` implementation (2026-05-30).

## Requirements

1. The `<div class="graph-layer-switch">` element containing the lone "project" `<button>` must be removed from the Graph card render in `dashboard.js`.
2. The Graph card title (`<h2 class="panel-heading">Graph</h2>`) and subtitle (the `graph-subtitle` count line) must remain unchanged.
3. The mode switch (`graph-mode-switch`: Communities / Focus / Files / Clear) directly below the pill must remain unchanged.
4. No CSS rule changes required; the `graph-layer-switch` and `graph-layer-pill--active` classes are also used elsewhere (the mode-switch row), so neither class definition is removed.

## Scope

**Problem statement:** A single-button layer selector with no onClick handler implies functionality that doesn't exist (you cannot switch to framework or union layer from the dashboard). Removing it cleans up the card header.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js` — delete the `<div class="graph-layer-switch">` block (lines 3640-3647 in the current file).

**Out of scope:**

- Adding a real multi-layer selector — separate concern; dashboard would need framework/union layer support first
- Restyling the graph card header
- Changes to the `graph-mode-switch` (Communities/Focus/Files/Clear)
- CSS edits; the shared `graph-layer-pill*` classes remain in use elsewhere

## Acceptance Criteria

- [x] AC-1: The Graph card header renders the title and count subtitle with no "project" pill below or beside them. Verified — the `<div className="graph-layer-switch">` block was deleted from `dashboard.js` (8 lines removed).
- [x] AC-2: The mode switch row (Communities / Focus / Files / Clear) remains visually unchanged. Verified — `<div className="graph-mode-switch">` block at lines 3641-3653 untouched.
- [x] AC-3: `tests/test_dashboard_server.py` continues to pass — 138/138 tests pass.
- [x] AC-4: Manual smoke verification — operator confirmed "dashboard looks good" after live restart; the lone "project" pill is gone and the Graph card header now shows only the title + count subtitle.

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Delete the `<div class="graph-layer-switch">` block in `dashboard.js` (around the current line 3640)
- [ ] Close gate
- [ ] Run framework tests; confirm `test_dashboard_server.py` passes
- [ ] Manual smoke: `wave_dashboard_start` → visually verify
- [ ] Mark change `implemented`

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | The removal is the entire purpose of the change |
| AC-2 | required | Scope guard — adjacent row must not be touched |
| AC-3 | required | Tests must not regress |
| AC-4 | important | Manual verification confirms the rendered result |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-30 | Delete the entire `graph-layer-switch` wrapping div, not just the button | The wrapper exists only to host this one pill; leaving it would be dead markup | Hide via CSS (rejected — leaves the DOM noise and the class is shared) |
| 2026-05-30 | Don't delete the `.graph-layer-pill` CSS class | The class is reused by the mode-switch row | Delete the class too (rejected — would break the mode switch) |

## Risks

| Risk | Mitigation |
|---|---|
| The pill was being used as a future hook for multi-layer support | Acceptable — multi-layer is out of scope; if added later, restore the structure |
| The wrapping div had a flexbox spacer role for the header | Verified by manual smoke that the header still looks correct without it |

## Related Work

- Companion to wave `1304x` change `1304w` (`dashboard-agents-above-graph`); both are small dashboard polish items.

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
