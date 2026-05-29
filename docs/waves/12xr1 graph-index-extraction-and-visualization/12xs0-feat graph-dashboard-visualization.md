# Graph Dashboard Visualization

Change ID: `12xs0-feat graph-dashboard-visualization`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

Once the graph data exists, the first wave needs a visual validation surface to catch structural mistakes before any query tooling is built on top of it. The dashboard view is not a query product; it is a correctness check for the extracted graph.

Graphify is a useful implementation reference here because it separates graph export from graph presentation. Its `callflow_html.py` module generates an interactive architecture/call-flow view from the already-built graph, and `serve.py` exposes graph interaction through a dedicated server layer. Wavefoundry should follow the same presentation-over-persistent-data split: consume the graph files produced by wave 1 and render them without changing the extraction pipeline.

## Requirements

1. Add a read-only `/api/graph` endpoint to the dashboard server that returns the persisted graph files.
2. Render the graph in the dashboard with a force-directed layout that supports node, edge, and file-level filtering.
3. Keep the visualization additive. No existing MCP tool output should change as part of this change.
4. Treat the dashboard graph as validation tooling, not as a final UX product.
5. Add tests for API loading and dashboard graph rendering behavior.

## Scope

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/dashboard/` visualization assets
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

**Out of scope:**

- graph extraction
- graph query tools
- any change to default MCP tool output
- semantic or LLM-derived graph augmentation

## API Contract

`/api/graph` accepts an optional `layer` query parameter with values `project` or `framework`. The default is `project`. The response must include the selected `layer`, the graph `schema_version`, and the persisted graph payload for that layer. The dashboard uses the same endpoint for both layers rather than inventing a second transport.

## Graphify Reference Implementation

Graphify keeps presentation separated from extraction and graph assembly. The relevant pieces for this wave:

| Graphify module | What it does | Wavefoundry takeaway |
| --- | --- | --- |
| [`graphify/callflow_html.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/callflow_html.py) | Generates interactive call-flow and architecture HTML from the graph | Use the same idea: render from persisted graph data, not from live file parsing |
| [`graphify/serve.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/serve.py) | Exposes structured graph interaction | Keep the dashboard API read-only and narrow |
| [`graphify/watch.py`](https://github.com/safishamsi/graphify/blob/v4/graphify/watch.py) | Auto-refreshes graph outputs when source files change | Useful later, but not required for the first validation surface |

## Acceptance Criteria

- [x] AC-1: `/api/graph` returns the persisted graph data for the current repository layer.
- [x] AC-2: `/api/graph` is layer-selectable (`project` or `framework`) and includes a `schema_version` field so the dashboard can reject incompatible graph files.
- [x] AC-3: The dashboard renders a force-directed graph view from the persisted data.
- [x] AC-4: Node coloring, edge labeling, and filters are present for kind, relation, and file.
- [x] AC-5: Graph visualization does not change the output of existing MCP search or lifecycle tools.
- [x] AC-6: Dashboard tests cover the graph endpoint and the rendered graph surface.

## Tasks

- [x] Add `/api/graph` to the dashboard server with explicit layer selection and schema-version reporting.
- [x] Add graph rendering assets to the dashboard.
- [x] Add tests for graph API loading and the rendered graph surface.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| dashboard API | implementer | wave 1 graph files | Read-only access to persisted graph data |
| visualization | implementer | dashboard API | Force-directed rendering and filters |
| tests | qa-reviewer | dashboard API, visualization | Verify loading and rendering |

## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_server.py`
- `.wavefoundry/framework/dashboard/`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` should mention the graph API as a dashboard consumer of the persisted graph files.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Dashboard must read the graph files produced by wave 1 |
| AC-2 | required | The dashboard view is the validation surface for graph correctness |
| AC-3 | important | Filtering is needed to make the view useful for review |
| AC-4 | required | The graph view must remain additive and non-breaking |
| AC-5 | required | Prevents regressions in the dashboard server path |
| AC-6 | required | The API contract needs schema/version and layer selection so the UI can load the right graph safely |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-27 | Drafted as the presentation companion to the graph extraction wave. | `graphify/callflow_html.py`, `graphify/serve.py`, `graphify/watch.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-27 | Keep visualization separate from extraction. | The dashboard should validate the graph after the data pipeline is stable, not influence extraction semantics. | Bundle the view into the extraction change — rejected to keep review scope clean |
| 2026-05-27 | Use persisted graph files as the dashboard input. | Mirrors Graphify's export-first design and avoids live re-parsing in the dashboard. | Parse files directly in the dashboard — rejected |
| 2026-05-27 | Make the graph API layer-selectable and schema-versioned. | The dashboard already tracks project and framework layers separately, so the graph endpoint should make layer selection explicit and reject incompatible graph payloads cleanly. | Return an unqualified blob with no layer/version metadata — rejected because the dashboard needs a stable contract for both layers |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Dashboard polish becomes the focus before graph correctness | Keep the surface explicitly validation-oriented and minimal |
| Graph rendering slows the dashboard | Load persisted graph data only and keep the API read-only |
| Layer ambiguity causes the dashboard to read the wrong graph file | Require an explicit `layer` parameter contract and surface `schema_version` in the API response |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
