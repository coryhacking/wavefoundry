# Dashboard Graph Rendering Fidelity Updates for Wave 131bt Graph Changes

Change ID: `131es-enh dashboard-graph-rendering-fidelity-updates`
Change Status: `partially-implemented`
Owner: Engineering
Status: in-progress
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Wave 131bt shipped eight graph-builder, MCP, and confidence-tag changes. The dashboard renders graph data via fallback paths that handle the new shapes correctly (no crashes, no incorrect data), but does not surface several signals that wave 131bt added to the graph payload:

1. **New node kinds** — `1319m` produces `kind: "package"` and `kind: "namespace"` nodes when `collapse_package_to_directory=True` is requested. The dashboard's color palette does not include these kinds; they fall back to the "external" grey, indistinguishable from genuine `external::*` nodes.
2. **New confidence tags** — `1319s` introduced `CONSTRUCTION_RESOLVED`; `1319q` populated `RECEIVER_RESOLVED` densely across TS/Python/PHP/JS. The dashboard color-codes edges only by relation type, not by confidence — operators can't distinguish structurally-verified edges from heuristic ones.
3. **Collision-diagnostic fields** — `13129`'s per-entry collision fields (`same_name_node_count`, `cross_file_collision`, `external_name_collision_count`) flow into the dashboard payload but are never extracted for display. Operators inspecting a node in the dashboard see no warning when its simple name collides project-wide.
4. **Class/module merge markers** — `1319o` extended `collapsed_pair: true` to Python/JS/TS merged nodes. The dashboard renders the merged node but has no visual indicator distinguishing it from a regular module.
5. **Stale-graph signal** — `131e2` adds the `graph_auto_rebuilt` diagnostic on MCP responses, but the dashboard reads the graph payload directly (no MCP round-trip) and has no equivalent surface for staleness or for the version-mismatch trigger.

None of these are blocking — fallback behavior is safe. But each leaves operator-facing information on the table that the framework already computes.

## Approach

Five focused additions to the dashboard rendering layer, grouped by file. Each is a small, isolated change with no cross-coupling — they can be picked up in any order.

### 1. Node-kind colors for `package` and `namespace`

**File:** `.wavefoundry/framework/dashboard/dashboard.js` around line 1024 (`GRAPH_KIND_COLORS` dict).

Add two entries:

```javascript
const GRAPH_KIND_COLORS = {
  module: "#1976d2",
  class: "#6f42c1",
  function: "#53ac04",
  doc: "#495057",
  seed: "#c25800",
  community: "#0f766e",
  package: "#e91e63",      // wave 1319m — directory-aggregation package
  namespace: "#00bcd4",    // wave 1319m — C#/PHP namespace
  external: "#7a7f87",
};
```

Verify `_graphKindBucket` (around line 1090) treats `package` and `namespace` as their own buckets rather than collapsing to `module`. Operators reading the legend get a distinct color for each.

### 2. Edge confidence color-coding

**File:** `.wavefoundry/framework/dashboard/dashboard.js` (extend the edge-rendering path) + `.wavefoundry/framework/dashboard/dashboard.css` (add color tokens).

Add `GRAPH_CONFIDENCE_STYLES` controlling either stroke opacity, dasharray, or a secondary color overlay:

```javascript
const GRAPH_CONFIDENCE_STYLES = {
  RECEIVER_RESOLVED: { opacity: 1.0, dash: "" },      // solid, full opacity
  CONSTRUCTION_RESOLVED: { opacity: 1.0, dash: "" },  // peer-level to RECEIVER_RESOLVED
  EXTRACTED: { opacity: 0.45, dash: "4 2" },          // dashed, half opacity
  AMBIGUOUS: { opacity: 0.30, dash: "2 4" },          // dotted, low opacity
};
```

Edges keep their relation color (calls, imports, defines) for at-a-glance identification; confidence modulates the stroke style so operators can visually scan for high-confidence subgraphs without losing relation typing.

Add a legend entry to the existing edge-relation legend explaining the encoding (solid = type-resolved, dashed = heuristic).

### 3. Collision diagnostics in node detail panel

**File:** `.wavefoundry/framework/dashboard/dashboard.js` (node detail rendering — likely the right-side panel or click-to-expand handler).

Extract three fields from the node payload when present:

- `same_name_node_count: int`
- `cross_file_collision: bool`
- `external_name_collision_count: int`

Display as a compact diagnostic line in the node detail:

> ⚠ Name collision: 3 same-name nodes (cross-file: yes); 1 external stdlib match

Or when none apply: omit the line. Visual treatment: small warning icon when the seed-211 verification trigger fires (`(same_name_node_count > 1 AND cross_file_collision: true)` OR `(external_name_collision_count > 0)`).

### 4. `collapsed_pair` badge

**File:** `.wavefoundry/framework/dashboard/dashboard.js` node rendering + minor CSS.

When `node.collapsed_pair === true`, append a small "[merged]" badge or distinct border to the node's visual representation. The hover/click handler shows which language and which file basename the merge applied to (extracted from the node's `kind` + `label` + `source_file`).

### 5. Graph staleness / version-mismatch indicator

**File:** `.wavefoundry/framework/scripts/dashboard_lib.py` (server-side staleness check) + `.wavefoundry/framework/dashboard/dashboard.js` (banner).

On the server side, when assembling the dashboard snapshot, compare the graph state's `builder_version` to the runtime `graph_indexer.GRAPH_BUILDER_VERSION`. If they differ, attach a structured flag to the payload:

```python
{"graph_stale_reason": "builder_version_mismatch",
 "from_version": "14", "to_version": "15"}
```

On the client side, when the flag is present, show a top-of-panel banner:

> Graph builder version advanced (14 → 15). Next graph query will trigger a synchronous rebuild (~10–30 s once). Run `wave_index_build(content="graph")` to rebuild proactively.

The banner dismisses itself after the next dashboard rebuild detects the version match.

## Requirements

1. New `package` and `namespace` entries in `GRAPH_KIND_COLORS` with visually distinct colors.
2. `_graphKindBucket` recognizes the new kinds as first-class (not collapsed to `module` / `external`).
3. New `GRAPH_CONFIDENCE_STYLES` dict applied to edges in addition to the existing relation-color path.
4. Edge legend updated to describe the confidence encoding (solid vs dashed).
5. Node detail panel surfaces `same_name_node_count`, `cross_file_collision`, `external_name_collision_count` when present.
6. Warning icon fires on the seed-211 verification trigger formula.
7. `collapsed_pair: true` nodes carry a visual badge or border.
8. `dashboard_lib.py` attaches a structured `graph_stale_reason` flag when state `builder_version` ≠ runtime `GRAPH_BUILDER_VERSION`.
9. Client renders a dismissable banner when `graph_stale_reason` is present.
10. No regression on existing dashboard tests (`test_dashboard_server.py`).
11. Snapshot test for each new rendering path against a synthetic graph fixture (or visual regression test if one exists).

## Scope

**Problem statement:** Wave 131bt adds new node kinds, confidence tags, collision diagnostics, merge markers, and a stale-graph signal. The dashboard renders the data correctly via fallback paths but does not surface any of these signals to operators. The framework computes the information; the dashboard discards it.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js` — color palette, edge style modulation, node detail rendering, banner.
- `.wavefoundry/framework/dashboard/dashboard.css` — color tokens, dashed/dotted strokes, badge styling, banner styling.
- `.wavefoundry/framework/scripts/dashboard_lib.py` — staleness flag in server snapshot.
- `.wavefoundry/framework/scripts/dashboard_server.py` — minimal wiring if needed (likely no change).
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` — fixture coverage for the new flag.

**Out of scope:**

- CHANGELOG link in dashboard header (separate concern; can land in a follow-on if operator demand surfaces).
- `wave_mcp_reload` guidance / status indicator in the dashboard.
- Edge-density indicator for `1319q`'s denser `RECEIVER_RESOLVED` coverage. Lower-value diagnostic.
- Live update of the staleness banner via SSE during a dashboard session — server-side snapshot rebuild on the next refresh interval is sufficient.
- Auto-triggering the graph rebuild from the dashboard. Operator runs `wave_index_build(content="graph")` per the existing seed-160 workflow OR pays the auto-rebuild cost on the next MCP query (`131e2`). The dashboard signals the condition; it does not trigger the action.

## Acceptance Criteria

**Node kinds (1319m):**

- [x] AC-1: `GRAPH_KIND_COLORS` includes distinct entries for `package` and `namespace`.
- [x] AC-2: A node with `kind: "package"` rendered in the dashboard has the new color (not the "external" fallback).
- [x] AC-3: A node with `kind: "namespace"` rendered in the dashboard has the new color.
- [ ] AC-4: Legend rendering shows the new kinds when at least one such node exists in the visible graph.
- [x] AC-1b: Palette fully redesigned for pairwise-distinct hues across all 10 node kinds. Field feedback flagged `variable` falling back to "external" grey and being indistinguishable from `doc` charcoal. Added `variable: "#d32f2f"` (vivid red) and shifted `community` (teal→emerald), `package` (cyan-teal→bright cyan), `namespace` (deep purple→magenta) out of their prior near-collision zones. Distinctness enforced by `test_graph_kind_colors_are_all_distinct_including_variable` in `test_dashboard_server.py`.

**Edge confidence (1319s + 1319q):**

- [ ] AC-5: `GRAPH_CONFIDENCE_STYLES` exists and applies to edge rendering alongside the existing relation-color path.
- [ ] AC-6: An `EXTRACTED` edge is visually distinct from a `RECEIVER_RESOLVED` edge of the same relation (e.g., dashed vs solid).
- [ ] AC-7: `CONSTRUCTION_RESOLVED` edges render with the same style as `RECEIVER_RESOLVED` (peer-level confidence per `1319s`).
- [ ] AC-8: Edge legend describes the confidence encoding.

**Collision diagnostics (13129):**

- [ ] AC-9: Node detail panel shows `same_name_node_count`, `cross_file_collision`, `external_name_collision_count` when any of them indicate a non-trivial value.
- [ ] AC-10: Warning icon appears when the seed-211 verification trigger fires: `(same_name_node_count > 1 AND cross_file_collision: true)` OR `(external_name_collision_count > 0)`.

**Collapsed-pair marker (1319o):**

- [ ] AC-11: Nodes with `collapsed_pair: true` display a visual indicator distinguishing them from regular module nodes.

**Staleness signal (131e2):**

- [ ] AC-12: `dashboard_lib.py` snapshot includes `graph_stale_reason: "builder_version_mismatch"` with from/to versions when state `builder_version` ≠ runtime `GRAPH_BUILDER_VERSION`.
- [ ] AC-13: Dashboard client renders a banner with the from/to versions, the operator-action hint, and a dismiss control.
- [ ] AC-14: Banner disappears on the next snapshot when the versions match (e.g., after the operator runs `wave_index_build(content="graph")` or the auto-rebuild fires via an MCP query).

**Flicker on graph reload (field-feedback round 4):**

- [x] AC-17: Graph re-renders on auto-refresh AND on operator-triggered reload do not produce a full-page flash. Implemented by gating the loading banner on initial-load only, comparing incoming-payload signature against prior, and preserving the operator's selection across refreshes when the selected node still exists. React's keyed reconciliation handles the incremental DOM updates downstream.
- [x] AC-18: When the delta is empty (snapshot identical to prior), the dashboard performs no DOM update at all — operator sees a stable view. Signature comparison (`_graphSigRef.current === newSig`) short-circuits `setGraph` so React skips reconciliation entirely.
- [ ] AC-19: Regression test: synthetic snapshot transition (5-node graph → 6-node graph) — assertion that only the new node and its edges are added to the DOM, existing nodes are not removed-and-re-added. **Deferred** — DOM-level assertion requires a browser harness (jsdom/Playwright) not currently shipped in the framework test suite. Substrate test (signature-skip + initial-load guard markers) covered by `test_dashboard_js_includes_flicker_fix_signature_skip` in `test_dashboard_server.py`.

**Information-architecture: secondary route for the graph view (field-feedback round 4):**

- [ ] AC-20: Graph view moved off the main dashboard landing page; primary page focuses on wave / index / activity orientation (the high-frequency operator surface).
- [ ] AC-21: Secondary route (e.g. `/graph` or a "Graph" tab in the dashboard nav) hosts the graph view in full fidelity — all existing functionality preserved, nothing removed.
- [ ] AC-22: Discoverability: a clear navigation link or tab in the dashboard header surfaces the graph route. Operators occasionally visiting the dashboard can find it without prior knowledge of the URL.
- [ ] AC-23: Backward-compat: bookmarked deep links to the existing graph-view URL fragment continue to resolve (HTTP 301 redirect to the new route if necessary).

**Regression / hygiene:**

- [ ] AC-15: All existing `test_dashboard_server.py` tests pass without modification.
- [ ] AC-16: New tests cover the staleness flag fixture: stale → flag present; fresh → flag absent.

## Tasks

- [ ] Phase 0 — audit `_graphKindBucket` behavior on `package` / `namespace` kinds against the current fallback (verify what color they currently render as)
- [ ] Open `framework_edit_allowed` gate
- [ ] Add `package` / `namespace` to `GRAPH_KIND_COLORS`; verify `_graphKindBucket`
- [ ] Add `GRAPH_CONFIDENCE_STYLES` + apply to edge rendering
- [ ] Update edge legend with confidence encoding
- [ ] Extract + render collision-diagnostic fields in node detail panel
- [ ] Add warning icon firing on the seed-211 trigger formula
- [ ] Add `collapsed_pair` badge to node rendering
- [ ] Add staleness flag to `dashboard_lib.py` snapshot
- [ ] Add staleness banner to `dashboard.js`
- [ ] Add CSS tokens for dashed/dotted strokes, badge, banner
- [ ] Add fixture coverage for the new staleness flag
- [ ] Wave 4 field-feedback expansion — implement graph-render delta + no-op-on-empty (AC-17, AC-18) and add regression coverage (AC-19)
- [ ] Wave 4 field-feedback expansion — move graph view to secondary route + nav link (AC-20, AC-21, AC-22) with bookmarked-URL redirect (AC-23)
- [ ] Run framework tests
- [ ] Close gate; mark change `implemented`

## Affected Architecture Docs

- N/A — this change extends an existing UI surface. No architectural boundary change. If the dashboard gains substantial new rendering primitives, consider folding into `docs/references/dashboard-install-upgrade.md` or similar.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | New node kinds without distinct colors fall back to "external", a wrong-signal default |
| AC-1b | required | Variable nodes fell back to "external" grey and read as `doc` charcoal; pairwise-distinct palette is required for operator legibility |
| AC-2 | required | Visible operator outcome |
| AC-3 | required | Visible operator outcome |
| AC-4 | important | Legend completeness |
| AC-5 | required | Edge confidence is the headline new signal from `1319s`/`1319q` |
| AC-6 | required | Without visual distinction operators can't filter by confidence |
| AC-7 | required | Peer-level encoding per `1319s` design |
| AC-8 | important | Legend completeness |
| AC-9 | required | Collision data shipped in 13129 was operator-facing; not surfacing it leaves the signal stranded |
| AC-10 | required | Verification trigger is the operator-actionable case |
| AC-11 | important | Merge markers are a subtle but high-value signal for refactor planning |
| AC-12 | required | Staleness flag is the foundation for the banner |
| AC-13 | required | Operator-facing signal |
| AC-14 | required | No-stale-after-rebuild UX correctness |
| AC-15 | required | No baseline regression |
| AC-16 | required | Fixture coverage |
| AC-17 | required | Field-feedback round 4: flicker on reload is a visible operator-UX defect |
| AC-18 | required | Empty-delta no-op — eliminates flicker on auto-refresh when nothing changed |
| AC-19 | required | Regression coverage for the incremental-update path |
| AC-20 | required | Field-feedback round 4: graph is low-frequency surface; main page should be high-frequency orientation |
| AC-21 | required | Secondary route preserves full graph functionality |
| AC-22 | required | Discoverability — operators occasionally visiting find it without prior URL knowledge |
| AC-23 | required | Backward-compat for bookmarked URLs |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-01 | Use stroke style (dashed/solid) to encode confidence rather than a secondary color overlay | Preserves the existing relation-color encoding for at-a-glance type identification; layering two color dimensions on one edge is visually noisy | Color overlay (rejected — overwhelms the relation color signal); separate edge layers per confidence (rejected — clutters the graph) |
| 2026-06-01 | Peer-level visual treatment for `RECEIVER_RESOLVED` and `CONSTRUCTION_RESOLVED` | Matches the `1319s` design decision that both tags represent the same evidence quality on different call shapes | Distinct styles for each tag (rejected — implies a precision hierarchy that doesn't exist) |
| 2026-06-01 | Dashboard signals staleness, does not auto-trigger rebuild | Auto-trigger from the dashboard would compete with the `131e2` MCP-query auto-rebuild and the explicit `wave_index_build` path. Surfacing the signal lets the operator pick the right trigger | Dashboard initiates the rebuild itself (rejected — creates a third trigger path; complexity without clarity) |
| 2026-06-01 | Staleness flag in the snapshot payload, not pushed live via SSE | Server snapshot already rebuilds on its own cadence; live push for a once-per-upgrade signal is over-engineered | SSE live push (rejected — disproportionate complexity) |
| 2026-06-01 | Defer CHANGELOG link, `wave_mcp_reload` guidance, edge-density indicator | Lower-value relative to the rendering fidelity items; scope creep | Bundle all eight audit items (rejected — distinct concerns, longer ship cycle) |

## Risks

| Risk | Mitigation |
|---|---|
| Color palette additions clash with existing terminal/theme conventions | Pick from established Material palettes; verify against any dashboard theme tests if they exist |
| Dashed-edge rendering performance on dense graphs (post-1319q TS/Python/PHP/JS receiver-type coverage produces ~6× more `RECEIVER_RESOLVED` edges) | Solid edges are the default for high-confidence; dashed only for `EXTRACTED` / `AMBIGUOUS`. Rendering cost should be balanced or lower (fewer solid edges on average) |
| Operators dismiss the staleness banner before running the rebuild and then forget — first MCP query still pays the 10–30 s cost | Acceptable — banner is informational, not a gate. The MCP-query auto-rebuild is the safety net (`131e2`) regardless of dashboard interaction |
| Snapshot tests need a synthetic graph fixture covering every new render path — non-trivial setup | Reuse existing dashboard fixture infrastructure; if absent, scaffold one. Cost is one-time |
| `_graphKindBucket` collapsing logic surprises when `package` / `namespace` interact with community membership | Phase 0 audit verifies current behavior before changes |
| Staleness flag fires false-positives when state file is missing or unreadable | Treat missing/unreadable state as "current" (no flag); only fire on explicit mismatch |

## Related Work

- Direct follow-on to wave 131bt:
  - `1319m` — directory aggregation; new `package` / `namespace` kinds (AC-1 through AC-4)
  - `1319s` — `CONSTRUCTION_RESOLVED` confidence tag (AC-5 through AC-8)
  - `1319q` — `RECEIVER_RESOLVED` for TS/Python/PHP/JS (AC-5 through AC-8, same encoding path)
  - `1319o` — `collapsed_pair: true` for Python/JS/TS (AC-11)
  - `131e2` — synchronous auto-rebuild + `graph_auto_rebuilt` diagnostic (AC-12 through AC-14, MCP-side signal mirrored by dashboard-side banner)
  - `13129` (prior wave) — collision diagnostic fields (AC-9, AC-10)
- Companion follow-ons (NOT in this change, scoped separately):
  - Dashboard CHANGELOG link
  - `wave_mcp_reload` status indicator
  - Edge-density indicator for `1319q` coverage

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
