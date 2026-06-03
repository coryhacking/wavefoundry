# Dashboard Rendering Fidelity Phase 2 — Edge Confidence, Collision Diagnostics, Staleness Banner, Secondary Route

Change ID: `1p30y-enh dashboard-rendering-fidelity-phase-2`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-06-03
Wave: TBD (UX-polish wave, follow-on to 1p2q3 field-feedback-round-4)

## Rationale

Continuation of `1p2q3/131es-enh dashboard-graph-rendering-fidelity-updates`. The parent change shipped the high-frequency-render items (new node-kind colors, pairwise-distinct palette, graph-render delta + empty-delta no-op flicker fix). This change picks up the remaining work the parent doc explicitly carved off:

- Edge confidence color-coding (1319s / 1319q signals are computed but not surfaced).
- Node-detail collision diagnostics (13129 fields flow into the dashboard payload but are never extracted for display).
- `collapsed_pair: true` visual badge (1319o merged nodes look identical to regular modules).
- Graph-staleness banner driven by a server-side `graph_stale_reason` flag.
- Information-architecture: move the graph view off the main landing page to a secondary route.
- Regression coverage for the delta-render path (deferred from parent because it requires a browser harness).

None of these are blocking — fallback behavior is safe. Each leaves operator-facing information on the table that the framework already computes. The parent change shipped what was most user-visible on first impression; this change finishes the surface.

## Requirements

1. `GRAPH_CONFIDENCE_STYLES` dict applied to edge rendering alongside the existing relation-color path.
2. Edge legend updated to describe the confidence encoding (solid = type-resolved, dashed = heuristic).
3. Node detail panel surfaces `same_name_node_count`, `cross_file_collision`, `external_name_collision_count` when present.
4. Warning icon fires on the seed-211 verification trigger formula: `(same_name_node_count > 1 AND cross_file_collision: true)` OR `(external_name_collision_count > 0)`.
5. Nodes with `collapsed_pair: true` carry a visual badge or distinct border.
6. `dashboard_lib.py` attaches `graph_stale_reason: "builder_version_mismatch"` with from/to versions when state `builder_version` ≠ runtime `GRAPH_BUILDER_VERSION`.
7. Dashboard renders a dismissable banner when `graph_stale_reason` is present; banner clears on next snapshot when versions match.
8. Graph view moved off the dashboard landing page to a secondary route (e.g. `/graph` or a "Graph" tab in the nav).
9. Primary landing page focuses on wave / index / activity orientation (the high-frequency operator surface).
10. Discoverability: clear navigation link or tab surfaces the graph route without prior URL knowledge.
11. Backward-compat: bookmarked deep links to the existing graph-view URL fragment resolve (HTTP 301 redirect to the new route).
12. Regression test for the delta-render path: synthetic snapshot transition (5-node graph → 6-node graph) — assert that only the new node + its edges are added to the DOM, existing nodes are not removed-and-re-added.
13. No regression on existing `test_dashboard_server.py` tests.

## Scope

**Problem statement:** The parent change `1p2q3/131es` shipped Phase 1 (colors + flicker fix) but explicitly deferred edge-confidence visual encoding, collision-diagnostic surfacing, `collapsed_pair` badge, staleness banner, secondary-route information architecture, and the delta-render regression test. This change finishes the surface.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.js` — edge style modulation by confidence, node detail diagnostics, `collapsed_pair` badge, staleness banner, secondary-route routing + nav link.
- `.wavefoundry/framework/dashboard/dashboard.css` — dashed/dotted edge strokes, badge styling, banner styling, secondary-route layout.
- `.wavefoundry/framework/scripts/dashboard_lib.py` — staleness flag in server snapshot.
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py` — fixture coverage for the staleness flag + delta-render regression test (requires a browser harness; can substitute substrate test if harness not feasible — see parent's AC-19 deferral rationale).

**Out of scope:**

- New node-kind colors and the pairwise-distinct palette (shipped in parent).
- Graph-render delta + empty-delta no-op flicker fix (shipped in parent).
- CHANGELOG link in dashboard header.
- `wave_mcp_reload` guidance / status indicator.
- Edge-density indicator for `1319q`'s denser `RECEIVER_RESOLVED` coverage.

## Acceptance Criteria

Inherited from parent `1p2q3/131es` (numbered per the parent doc for traceability):

**Edge confidence (1319s + 1319q):**

- [ ] AC-5 (parent): `GRAPH_CONFIDENCE_STYLES` exists and applies to edge rendering alongside the existing relation-color path.
- [ ] AC-6 (parent): An `EXTRACTED` edge is visually distinct from a `RECEIVER_RESOLVED` edge of the same relation (dashed vs solid).
- [ ] AC-7 (parent): `CONSTRUCTION_RESOLVED` edges render with the same style as `RECEIVER_RESOLVED` (peer-level confidence per `1319s`).
- [ ] AC-8 (parent): Edge legend describes the confidence encoding.

**Collision diagnostics (13129):**

- [ ] AC-9 (parent): Node detail panel shows `same_name_node_count`, `cross_file_collision`, `external_name_collision_count` when any of them indicate a non-trivial value.
- [ ] AC-10 (parent): Warning icon appears when the seed-211 verification trigger fires: `(same_name_node_count > 1 AND cross_file_collision: true)` OR `(external_name_collision_count > 0)`.

**Collapsed-pair marker (1319o):**

- [ ] AC-11 (parent): Nodes with `collapsed_pair: true` display a visual indicator distinguishing them from regular module nodes.

**Staleness signal (131e2):**

- [ ] AC-12 (parent): `dashboard_lib.py` snapshot includes `graph_stale_reason: "builder_version_mismatch"` with from/to versions when state `builder_version` ≠ runtime `GRAPH_BUILDER_VERSION`.
- [ ] AC-13 (parent): Dashboard client renders a banner with the from/to versions, the operator-action hint, and a dismiss control.
- [ ] AC-14 (parent): Banner disappears on the next snapshot when the versions match.

**Information architecture (field-feedback round 4):**

- [ ] AC-20 (parent): Graph view moved off the main dashboard landing page; primary page focuses on wave / index / activity orientation.
- [ ] AC-21 (parent): Secondary route (e.g. `/graph` or a "Graph" tab in the dashboard nav) hosts the graph view in full fidelity — all existing functionality preserved.
- [ ] AC-22 (parent): Discoverability — a clear navigation link or tab in the dashboard header surfaces the graph route.
- [ ] AC-23 (parent): Backward-compat — bookmarked deep links to the existing graph-view URL fragment resolve (HTTP 301 redirect to the new route).

**Regression / coverage:**

- [ ] AC-4 (parent): Legend rendering shows the `package` / `namespace` kinds when at least one such node exists in the visible graph. (Carried forward from parent — legend infrastructure rather than palette.)
- [ ] AC-15 (parent): All existing `test_dashboard_server.py` tests pass without modification.
- [ ] AC-16 (parent): New tests cover the staleness flag fixture: stale → flag present; fresh → flag absent.
- [ ] AC-19 (parent): Regression test for the delta-render path: synthetic snapshot transition (5-node graph → 6-node graph) asserts only the new node + its edges are added to the DOM, existing nodes are not removed-and-re-added. (Requires a browser harness — substrate test substitutes via assertion on the signature-skip + initial-load guard markers if a browser harness isn't introduced for this change.)

## Tasks

- [ ] Open `framework_edit_allowed` gate
- [ ] Add `GRAPH_CONFIDENCE_STYLES` dict + apply to edge rendering
- [ ] Update edge legend with confidence encoding
- [ ] Extract + render collision-diagnostic fields in node detail panel
- [ ] Add warning icon firing on the seed-211 trigger formula
- [ ] Add `collapsed_pair` badge to node rendering
- [ ] Add staleness flag to `dashboard_lib.py` snapshot
- [ ] Add staleness banner to `dashboard.js`
- [ ] CSS tokens for dashed/dotted strokes, badge, banner, secondary-route layout
- [ ] Add fixture coverage for the new staleness flag
- [ ] Move graph view to secondary route + nav link + bookmarked-URL redirect
- [ ] Audit and decide on the delta-render regression test approach (browser harness vs substrate-only)
- [ ] Run framework tests
- [ ] Close gate; mark change `implemented`

## Affected Architecture Docs

`N/A` — extends an existing UI surface. No architectural boundary change. The secondary-route move may warrant a brief note in `docs/references/dashboard-install-upgrade.md` documenting the route structure.

## Related Work

- Parent: `1p2q3/131es-enh dashboard-graph-rendering-fidelity-updates` (the Phase 1 portion of this surface).
- Related sibling: `1p310-enh mcp-protocol-surface-phase-1b-2` (Phase 1b + Phase 2 of `1p2q3/131hh` MCP-protocol surface adoption, splitting from the same field-feedback round).

## Session Handoff

Unattached future-wave plan. Admit when a Wave Council readiness review accepts the follow-on UX-polish wave. No urgency — fallback behavior is correct for every item below; the dashboard renders today without these signals.
