# Graph Visualization and Navigation Overhaul

Change ID: `12yro-enh graph-visualization-navigation-overhaul`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-05-28
Wave: TBD (future graph wave; pairs with `12xr2 graph-query-surface`)

## Rationale

The dashboard graph view uses a hand-rolled SVG force-directed layout (`_layoutGraph` in `dashboard.js`): deterministic hash-ring seeding, O(n²) all-pairs repulsion, edge springs, center gravity, fixed 120 iterations with constant damping, rendered as SVG `<circle>`/`<text>` DOM nodes. Two real problems result:

1. **It does not scale.** SVG renders every node, edge, and label as a DOM element; it degrades well before the node counts a real project graph produces. No layout tuning fixes a rendering ceiling.
2. **One layout for every view is wrong.** A single force layout turns a high-degree node into an unreadable starburst (the ego/drill-down case) and lets disconnected nodes drift to the canvas boundary (the community-overview case). All labels render at once with no level-of-detail, producing label soup.

A council advisory review (red-team `technology-evaluation` primer + frontend, architecture, performance, reality-checker, and senior-engineering-challenger seats) reframed the problem around **what people actually do to navigate source code**:

- IDEs (VS Code, JetBrains) navigate via go-to-definition, find-references, and **call/type hierarchies** — expand-on-demand **trees**, not rendered global graphs.
- Sourcegraph / GitHub / code-search navigate by **search + precise jump + local context**, having moved away from large graph visualizations.
- When a *picture* is wanted, the ecosystem standardizes on **hierarchical/layered** layout (Graphviz `dot`, dependency-cruiser, Madge, Structurizr, Backstage's dagre catalog graph) because direction is the meaning.
- **Force-directed / ForceAtlas2** (Gephi, Neo4j Bloom) is for **exploratory analysis of large graphs**, not day-to-day navigation.

The council's load-bearing conclusion: the win is an **interaction model (search-to-focus + expand-on-demand) plus per-view layouts on a WebGL renderer**, not picking a single "better" global layout. A prettier global force graph becomes hairball art that does not get used. This change implements that reframing.

## Council Reframing Summary

| Seat | Key finding |
| ---- | ----------- |
| red-team (primer) | "Best layout algorithm" is partly the wrong question; real navigation is local/search, not a global picture. Strongest alternative: IDE-style local navigation with the global graph demoted to an optional overview mode. |
| frontend-developer | A WebGL canvas is not screen-reader navigable; the accessible fallback is a tree/list (call-hierarchy) view — which is also the primary nav pattern for most users. |
| architecture-reviewer | Keep layout/render separate from data; drive grouping from server-side Leiden communities (`graph_cluster.py`) and neighbor expansion from the `12xr2` query surface. |
| performance-reviewer | SVG is the ceiling; WebGL + worker layout + level-of-detail labels are table stakes — but set explicit node-count budgets rather than assuming. |
| reality-checker | Highest-risk unverified assumptions: (1) users want a global graph at all, (2) a better force layout fixes legibility (false for directed graphs), (3) node counts actually require WebGL (unmeasured). |
| senior-engineering-challenger | The smallest correct change is the interaction model, not the layout engine; render the neighborhood, not the whole graph. |

`seat_agreement_aggregate`: `majority`, `max_severity: medium`. Unanimous: replace SVG with WebGL; adopt per-view layouts; interaction-first over layout-first. Split (resolved as "measure first"): adopt the full `graphology + sigma + ForceAtlas2 + ELK` stack now vs. start with the lighter vanilla `force-graph` and add the heavier stack only when measured counts justify it.

## Requirements

1. **Measure before committing (opening gate).** Capture the real distribution of rendered graph sizes (typical and ~95th-percentile node/edge counts per view) before any rendering or layout dependency is selected. This directly tests the council's highest-risk unverified assumptions and decides the renderer tier.
2. **Interaction model first.** Implement search-to-focus plus **expand-on-demand** neighborhood navigation: start from a focus node (or search result), show its immediate neighborhood, and expand outward on demand rather than rendering the whole graph. Back expansion with server-side neighbor queries (the `12xr2` query surface) rather than client-side full-graph traversal.
3. **Per-view layouts.** Use the layout that matches each view's intent:
   - **Directed dependency / impact / DI detail** (`calls`/`imports`/`defines`, and future `binds`/`injects`) → **hierarchical/layered** (ELK via `elkjs`, or dagre).
   - **Community overview** → **ForceAtlas2** (graphology) run in a Web Worker, grouped/colored by existing Leiden communities.
   - **Ego / single-focus** → **radial/concentric by hop distance** with the focus pinned, plus expand-on-demand.
4. **WebGL rendering** for the graph surface, with **level-of-detail label culling** (labels by zoom/degree/hover, not all at once), zoom/pan, hover highlight, and node sizing by degree. Vendor the renderer as a UMD global served by the dashboard server (same pattern as `react.production.min.js`); no bundler, no network.
5. **Accessible peer view.** Provide a tree/list (call-hierarchy style) navigation view as a first-class peer to the canvas — both the accessibility fallback for the non-navigable WebGL canvas and the primary navigation surface for many users. Keyboard-operable, screen-reader labeled.
6. **Data-driven, not recomputed.** Drive grouping/color from server-side Leiden community ids and node degree supplied in the graph payload; do not recompute graph metrics or communities in the browser.
7. **State completeness.** Handle loading, empty, error, and "no neighbors / isolated node" states explicitly for the focus/expand interactions.
8. Keep the change reviewable: layout engine(s), renderer, and the React UI shell remain separable so a renderer or layout choice can be swapped without rewriting the surrounding dashboard.

## Scope

**Problem statement:** The graph view does not scale (SVG) and uses a single force layout for every intent, producing hairballs and starbursts that are not usable for navigation; the interaction model renders everything instead of supporting focus + expand the way real code navigation works.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js` — replace `_layoutGraph`/SVG rendering with the WebGL renderer, per-view layouts, and the search-to-focus + expand-on-demand interaction model; add the accessible tree/list view.
- `.wavefoundry/framework/dashboard/dashboard.css` — styling for the new surfaces.
- `.wavefoundry/framework/dashboard/dashboard.html` — vendored `<script>` tags for the chosen renderer/layout UMD bundles.
- Vendored renderer/layout library files under `.wavefoundry/framework/dashboard/`.
- `.wavefoundry/framework/scripts/dashboard_server.py` and/or graph payload shape only if the view needs server-side neighbor queries or additional node attributes (degree, community id) not already provided.
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` — assertions for the new served assets and payload fields.

**Out of scope:**

- The graph **extraction** model and new edge kinds (owned by `12xr1` and `12ynp-enh graph-dependency-injection-wiring`).
- The MCP graph **query tools** themselves (`code_impact`, `code_callgraph`) — owned by `12xr2 graph-query-surface`; this change consumes them for expand-on-demand but does not define them.
- 3D rendering, graph editing, or persistence of user-arranged layouts.
- Replacing the dashboard's React/vendored-JS delivery model.

## Renderer and Layout Selection

The renderer tier is decided by Requirement 1's measurement, between two vendored-UMD options:

- **Best-of-breed at scale:** `graphology` (model) + **Sigma.js** (WebGL renderer, native level-of-detail labels) + `graphology-layout-forceatlas2` (Web Worker) for the overview, + `elkjs` for directed views. Gephi-lineage; scales to tens of thousands of nodes.
- **Lighter / faster to ship:** vanilla **`force-graph`** (WebGL, d3-force built in, trivial React-imperative integration) for overview/ego, + `elkjs`/dagre for directed views.

Both keep local-only intact (UMD globals served by the dashboard). The council left this split deliberately unresolved pending the measurement; do not pre-commit the heavier stack if measured counts do not justify it.

## Acceptance Criteria

- [ ] AC-1: A measurement of real per-view graph-size distribution (typical and ~95th-percentile node/edge counts) is recorded in this change doc before a renderer/layout dependency is selected.
- [ ] AC-2: Navigation supports search-to-focus and expand-on-demand from a focus node; the full graph is not rendered up front for large graphs.
- [ ] AC-3: Directed dependency/impact views use a hierarchical/layered layout (ELK or dagre); edge direction is legible top-down.
- [ ] AC-4: The community overview uses ForceAtlas2 (or the selected force engine) off the main thread, grouped/colored by server-supplied Leiden community ids.
- [ ] AC-5: The ego/single-focus view uses a radial/concentric-by-hop layout with the focus pinned, not a force starburst.
- [ ] AC-6: The graph surface renders via WebGL with level-of-detail labels, zoom/pan, and hover highlight; renderer/layout libraries are vendored as UMD globals served by the dashboard (no network, no bundler).
- [ ] AC-7: A keyboard-operable, screen-reader-labeled tree/list navigation view exists as a first-class peer to the canvas.
- [ ] AC-8: Grouping/color/size are driven by server-supplied community id and degree; no graph-metric recomputation in the browser.
- [ ] AC-9: Loading, empty, error, and isolated-node states are handled for focus/expand interactions.
- [ ] AC-10: A documented performance budget (interactive at the measured ~95th-percentile node count) is met; layout runs off the main thread for the overview.

## Tasks

- [ ] Instrument and record per-view graph-size distribution; write the measurement into this doc and select the renderer tier (AC-1).
- [ ] Vendor the chosen renderer/layout UMD bundles into the dashboard dir and wire `<script>` tags in `dashboard.html`.
- [ ] Implement the search-to-focus + expand-on-demand interaction model, backed by server-side neighbor queries where needed.
- [ ] Implement the three per-view layouts (ELK hierarchical, ForceAtlas2 worker, radial/concentric ego) behind a view selector.
- [ ] Mount the WebGL renderer into a container ref; drive it from React effects; remove `_layoutGraph` and SVG rendering once views are migrated.
- [ ] Implement level-of-detail labels, degree-based sizing, and community coloring from server-supplied attributes.
- [ ] Implement the accessible tree/list peer view with keyboard and screen-reader support.
- [ ] Add `dashboard_server` payload fields (degree, community id, neighbor query) if not already present, plus tests.
- [ ] Verify the performance budget at the measured node count.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| size measurement + tier decision | implementer | existing dashboard graph payload | Opening gate; resolves the renderer split |
| renderer vendoring + mount | frontend-developer | tier decision | UMD globals, React-imperative mount |
| interaction model (focus + expand) | frontend-developer | renderer mount; `12xr2` neighbor queries | Search-to-focus, expand-on-demand |
| per-view layouts | frontend-developer | renderer mount | ELK hierarchical, FA2 worker, radial ego |
| accessible tree/list view | frontend-developer | graph payload | a11y peer; keyboard + screen reader |
| server payload/queries | implementer | size measurement | degree, community id, neighbor query |
| tests | qa-reviewer | implementation | served assets, payload fields, state coverage |

## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.js` (renderer mount, interaction model, and layout selection all converge here)
- `.wavefoundry/framework/dashboard/dashboard.html` (vendored script tags)
- `.wavefoundry/framework/scripts/dashboard_server.py` (payload/asset serving)

## Affected Architecture Docs

`docs/references/dashboard-adapter-model.md` and `docs/architecture/data-and-control-flow.md` should note that the dashboard graph view renders via WebGL with per-view layouts and an expand-on-demand interaction model backed by server-side neighbor queries, and that grouping/color derive from server-supplied Leiden communities rather than client-side recomputation.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Tests the council's highest-risk assumptions before any dependency is committed |
| AC-2 | required | Expand-on-demand is the core "what people actually do" navigation pattern |
| AC-3 | required | Directed code graphs need hierarchical layout to be legible |
| AC-4 | important | Community overview is valuable but secondary to navigation |
| AC-5 | required | The ego view is the visibly broken case today |
| AC-6 | required | WebGL is the actual scaling fix; local-only vendoring is a hard constraint |
| AC-7 | required | Accessibility is non-negotiable and doubles as the primary nav for many users |
| AC-8 | required | Avoids client-side recomputation and keeps render/data separated |
| AC-9 | required | State completeness for the focus/expand flow |
| AC-10 | important | A measured budget prevents shipping an unusable-at-scale view |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-28 | Drafted from a council advisory review reframing the work around real source-navigation practice (interaction model + per-view layouts on WebGL) rather than a single global layout algorithm. | `dashboard.js` `_layoutGraph`, `graph_cluster.py` (Leiden communities), `12xr2 graph-query-surface/wave.md` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-28 | Lead with the interaction model (search-to-focus + expand-on-demand), not a global layout algorithm. | Real code navigation (IDEs, Sourcegraph) is local + search; rendering the whole graph is the pattern that does not get used at scale. | Ship a better global force layout (rejected: hairball art that goes unused) |
| 2026-05-28 | Use per-view layouts: hierarchical (ELK/dagre) for directed views, ForceAtlas2 for community overview, radial/concentric for ego. | Direction is the meaning for code dependency graphs; the ecosystem (Graphviz, Backstage, dependency-cruiser) standardizes on hierarchical for directed graphs, and force/FA2 is for exploratory community structure. | One force layout for all views (rejected: starburst/hairball per the screenshots) |
| 2026-05-28 | Render via WebGL with vendored UMD libraries, not SVG. | SVG is the true scaling ceiling; WebGL + LOD labels are table stakes at the implied node counts; UMD vendoring keeps the local-only/no-build constraint intact. | Keep/extend SVG (rejected: does not scale); add a bundler (rejected: breaks the no-build dashboard model) |
| 2026-05-28 | Defer the renderer-stack choice (sigma+graphology+FA2+ELK vs. vanilla force-graph+ELK) until per-view graph sizes are measured. | The council split was unresolved and hinges on real node counts; committing the heavier stack without evidence risks over-engineering. | Commit sigma stack now (deferred: pending measurement) |
| 2026-05-28 | Treat the accessible tree/list view as a first-class peer, not a fallback bolt-on. | A WebGL canvas is not screen-reader navigable, and the tree view is also the primary navigation mode for many users. | Canvas-only (rejected: inaccessible and misaligned with real usage) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Building a global graph view users do not actually want | Measure first (AC-1); lead with expand-on-demand navigation that matches real behavior |
| Hierarchical layout handles cyclic code graphs poorly | Use a layout engine (ELK) with cycle-breaking; constrain hierarchical layout to the directed detail views, not the overview |
| Over-engineering with the heavier graphology/sigma stack | Defer the stack choice to the measurement; start lighter if counts allow |
| WebGL canvas excludes assistive-technology users | Ship the accessible tree/list peer as a required AC, not optional |
| Expand-on-demand depends on the `12xr2` query surface | Sequence after `12xr2`, or provide a bounded client-side neighbor expansion fallback for small graphs |
| New vendored dependencies increase maintenance/footprint | Keep renderer/layout/UI separable; pin and vendor specific UMD builds; document update path |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
