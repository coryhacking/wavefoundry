# Index Tile And Graph Status

Change ID: `12xtu-enh index-tile-and-graph-status`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The dashboard now has two index surfaces: the semantic index and the graph index. The current tile still says "Semantic Index", which undercounts what the dashboard is actually validating and makes the graph feel like a separate, secondary artifact. This change makes the dashboard read as one local index surface with multiple stored views: semantic retrieval plus graph structure.

The graph view itself is also too dense to scan at a glance. The same change should make that surface approachable by default: start from a focused overview, reduce label clutter, and let the user drill into a selected node or a small neighborhood instead of exposing the full hairball immediately.

Graphify is the useful shape reference here, not a code dependency. Its presentation layer reads from persisted graph outputs and keeps graph serving separate from graph extraction. Wavefoundry should do the same: the dashboard should consume stored graph artifacts and surface their status without re-parsing or rebuilding them at render time.

Relevant Graphify references:

- [`graphify/callflow_html.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/callflow_html.py) for rendering a graph-backed inspection view from persisted data
- [`graphify/serve.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/serve.py) for a read-only graph access pattern
- [`graphify/watch.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/watch.py) for the later watch/refresh pattern, not required for this change

## Requirements

1. Rename the dashboard metric tile from "Semantic Index" to "Index".
2. Treat graph index health as part of the same dashboard surface, not as a separate product tile.
3. Surface graph index state for both `project` and `framework` layers in the metric summary and in the detail dialog.
4. Show graph-specific status in the detail dialog, including whether each graph is present, stale, building, failed, or missing.
5. Preserve the current semantic index statistics in the same dialog so the dashboard shows both the semantic and graph views together.
6. Make the graph panel approachable by default: prefer a hub or ego-centric overview, hide most node labels until hover or selection, and bias the first screen toward interpretation rather than the full graph.
7. Add file/group-oriented navigation so the user can pivot from the broad overview to clusters or file neighborhoods without reloading the page.
8. When a node is selected, highlight its direct connections and dim unrelated nodes/edges so the local structure is obvious.
9. Keep the change additive: no graph extraction semantics, graph file layout, or MCP output should change as part of this work.
10. Add tests for the renamed tile label, the combined summary state, the graph status rendering in the detail dialog, and the new graph exploration defaults.

## Scope

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
- dashboard styling only if needed to fit the expanded detail dialog
- graph exploration defaults and summary affordances within the existing graph panel

**Out of scope:**

- graph extraction or graph build logic
- `/api/graph` shape changes unrelated to status presentation
- graph query tooling
- MCP output changes
- other wave docs or feature work

## Dashboard Contract

The metric tile should become a single "Index" tile that aggregates the dashboard's index surfaces. The tile may still show the semantic index counts the user already expects, but it must also reflect graph index health so the title and state match what the dashboard is actually tracking.

The detail dialog should present both families of index data:

- semantic index sections for `Project` and `Framework`
- graph index sections for `Project Graph` and `Framework Graph`

Graph sections should report the persisted graph file path, presence, schema/version metadata if available, node/edge counts, and build state. The dialog should make it clear when a graph is missing, stale, building, or failed so the operator can tell whether the graph is current without leaving the dashboard.

The graph panel should not default to a dense full-graph visualization. It should:

- start from a small, readable subset or summary view
- prefer highly connected nodes or the selected node's neighborhood
- hide most labels until hover or selection
- allow relation filtering to be opt-in rather than visually dominant
- provide a path from the overview into cluster- or file-oriented inspection

## Graphify Reference Implementation

Graphify keeps graph presentation separate from graph extraction, and that separation is the key precedent for this change. The relevant modules for this wave are:

| Graphify module | What it does | Wavefoundry takeaway |
| --- | --- | --- |
| [`graphify/callflow_html.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/callflow_html.py) | Renders a graph-backed inspection view from persisted graph output | The dashboard should render from stored graph artifacts, not live parse results |
| [`graphify/serve.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/serve.py) | Exposes structured graph access | Keep the dashboard graph status read-only and narrowly scoped |
| [`graphify/watch.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/watch.py) | Watches source changes and refreshes graph outputs | Useful later for automation, but not needed for this presentation change |
| [`graphify/analyze.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/analyze.py) | Computes graph-oriented summaries such as hubs and community structure | Use the same idea for a readable overview instead of dropping users into the whole graph |
| [`graphify/cluster.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/cluster.py) | Groups nodes into communities | A later/optional path for cluster-aware browsing and file neighborhood views |

## Acceptance Criteria

- [x] AC-1: The dashboard metric tile label reads "Index" instead of "Semantic Index".
- [x] AC-2: The metric tile state reflects both semantic and graph index health across `project` and `framework` layers.
- [x] AC-3: The detail dialog shows semantic index sections plus graph index sections for both layers.
- [x] AC-4: Graph sections display meaningful build/status information for each layer, including missing/stale/building/failed states when applicable.
- [x] AC-5: The graph panel defaults to a readable overview and hides most labels until hover or selection.
- [x] AC-6: The graph panel supports filtering or grouping that lets the user move from overview to a smaller neighborhood or file-oriented view.
- [x] AC-7: Selecting a node highlights its direct connections and de-emphasizes unrelated graph elements.
- [x] AC-8: The change does not alter graph extraction behavior, graph file layout, or existing MCP output.
- [x] AC-9: Tests cover the renamed tile label, combined summary state, graph status rendering in the detail dialog, and the new graph exploration defaults.

## Tasks

- [x] Update `dashboard.js` metric label and state aggregation.
- [x] Extend the dashboard health/snapshot data path if needed so graph index status is available in the detail dialog.
- [x] Add graph status sections to the index detail dialog.
- [x] Rework the graph panel to start from a compact overview and progressively reveal detail.
- [x] Add file/group-oriented graph navigation affordances.
- [x] Add selected-node highlighting so direct connections are emphasized and unrelated nodes/edges are dimmed.
- [x] Add or update tests for the tile label, the summary state, the dialog rendering, and the graph exploration defaults.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| dashboard summary | implementer | wave 1 graph files | Rename the tile and aggregate semantic + graph state |
| detail dialog | implementer | dashboard summary | Render semantic and graph sections side by side |
| graph exploration | implementer | graph panel | Make the graph readable by default and support drilled-in navigation |
| selection emphasis | implementer | graph exploration | Highlight direct connections around the selected node |
| tests | qa-reviewer | dashboard summary, detail dialog, graph exploration | Verify label, graph status, and approachable graph defaults |

## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` should note that the dashboard now surfaces graph index state alongside semantic index health in the local index surface.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The dashboard label should match the actual index surface |
| AC-2 | required | The summary tile should reflect graph index health, not just semantic index health |
| AC-3 | required | Operators need both views in the detail dialog to inspect status quickly |
| AC-4 | required | Graph status is the new information this change adds |
| AC-5 | required | The graph must be readable by default or it will not be usable as a validation surface |
| AC-6 | important | Cluster/file navigation improves drill-down without changing the graph model |
| AC-7 | required | Selected-node highlighting is the main local-structure affordance |
| AC-8 | required | This change must stay presentation-only |
| AC-9 | required | The UI contract needs test coverage before implementation lands |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Drafted as the dashboard presentation follow-on to the graph index wave. | `dashboard.js`, `dashboard_lib.py`, `dashboard_server.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-27 | Rename the tile to "Index" instead of adding a second metric tile. | The dashboard is surfacing one local index surface with multiple views; the label should reflect that. | Keep "Semantic Index" and add a separate graph tile — rejected because it splits a single operational concept into two unrelated badges |
| 2026-05-27 | Show graph status in the existing detail dialog rather than a separate graph-only modal. | The semantic and graph states should be inspected together so operators can compare them in one place. | Add a second dialog for graph status — rejected because it makes the status check slower |
| 2026-05-27 | Default the graph view to an overview/focus mode rather than a full unfiltered canvas. | The current full graph is visually too dense to read; a readable default is required before the graph can serve as a review surface. | Render the entire graph with all labels visible — rejected because it is hard to interpret at a glance |
| 2026-05-27 | Add cluster/file-oriented drill-down rather than exposing every node equally. | The graph needs an obvious path from summary to neighborhood to file-level inspection. | Rely only on a search box and global filters — rejected because it still leaves the first view overloaded |
| 2026-05-27 | Highlight direct connections around the selected node. | Selection needs to make local structure obvious, not just mark a node in isolation. | Leave all edges and nodes at the same visual weight — rejected because selected-node context is hard to read |
| 2026-05-27 | Keep the change presentation-only. | The graph pipeline already exists; this change should expose status, not alter the graph build contract. | Fold UI changes into graph extraction work — rejected to keep scope clean |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The combined tile becomes too dense to read | Keep the note compact and move detailed status into the dialog |
| Graph and semantic state drift in the UI | Drive both from the dashboard snapshot so the tile and dialog use the same source of truth |
| The dialog gets too wide after adding graph sections | Use the existing dialog layout with minimal expansion; only add styling if necessary |
| The graph remains a hairball even after adding filters | Default to a hub/ego view, hide labels, and support drill-down to smaller neighborhoods |
| Selected nodes are hard to distinguish from nearby structure | Dim unrelated nodes/edges and keep direct connections visually prominent |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
