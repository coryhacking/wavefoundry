# Graph Back Navigation Control

Change ID: `12xzz-enh graph-back-navigation-control`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The graph now has bounded community overview and drilldown limits, but the user still needs a clear way to exit the current selection state after clicking a node, a community, or a file neighborhood. Without an explicit back action, the graph feels sticky even when the underlying view is still navigable. This change adds a single back control that clears the active selection and returns the graph to the default overview state.

## Requirements

1. Add an explicit back control that clears the active node, community, and file selection state.
2. The back control should return the graph to the default overview mode.
3. The control should be visible whenever the graph is in a selected state, not just when a raw node is selected.
4. The control should not change the canonical graph payload or any backend API contract.

## Scope

**Problem statement:** The graph has clear drilldown behavior, but no equally clear way to leave the drilldown once the user has clicked into it.

**In scope:**

- expose a back action in the graph summary/selection area
- clear node, community, and file selection when back is used
- keep the default overview as the landing state after back
- add a regression test for the back control visibility

**Out of scope:**

- changing graph payloads
- changing clustering or extraction behavior
- adding new graph modes

## Acceptance Criteria

- [x] AC-1: The graph shows a back control whenever node, community, or file selection is active.
- [x] AC-2: Activating the back control clears the selected node, selected community, and selected file state.
- [x] AC-3: Activating the back control returns the graph to overview mode.
- [x] AC-4: Dashboard tests cover the back control visibility and clearing behavior.

## Tasks

- [x] Add a unified back action to the graph summary/selection area.
- [x] Ensure the back action clears node, community, and file selection state.
- [x] Return the graph to overview mode when back is used.
- [x] Add regression coverage for the back action.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| back control | engineering | graph overview navigation limits | Add an explicit way to exit the current selection state |
| regression tests | engineering | back control | Verify the control shows up and clears state |

## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A. This is a dashboard interaction refinement on top of the existing graph navigation model.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The control must be visible from every selected state. |
| AC-2 | required | The control needs to reliably clear the active selection. |
| AC-3 | required | Back should always land on the overview. |
| AC-4 | required | Regression coverage keeps the interaction stable. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-27 | Identified that the graph needs a clear exit path after community or node drilldown. | Graph screenshots / operator feedback |
| 2026-05-28 | Implemented a unified back control for node, community, and file selections, with regression coverage. | Dashboard graph UI and tests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-27 | Use a unified back control that clears all current graph selections and returns to overview. | One clear escape path is better than separate per-mode affordances. | Separate back buttons for each mode |

## Risks

| Risk | Mitigation |
| --- | --- |
| Clearing selection state too aggressively could surprise the user. | Keep the action labeled clearly as a back/overview return control. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
