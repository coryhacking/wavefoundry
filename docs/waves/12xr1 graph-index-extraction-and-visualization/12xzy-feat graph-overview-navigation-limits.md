# Graph Overview Navigation Limits

Change ID: `12xzy-feat graph-overview-navigation-limits`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The graph community view is now structurally correct, but the next drilldown level is still too broad. Clicking a community can expose a large raw node set, which makes the graph hard to navigate again. We need the dashboard to keep only one organizational layer on screen at a time so the graph remains readable as the operator drills down.

## Requirements

1. Hide the ungrouped bucket from the default community overview when at least one real community exists.
2. Rank community quick-picks by a deterministic inspectability score, not raw size alone. The score is `boundary_node_count / node_count * log2(node_count + 1)` with tiebreakers on `boundary_node_count`, then `node_count`, then label.
3. Only show aggregated cross-community edges in community overview mode.
4. Keep drilldown to one community at a time.
5. Keep node focus one-hop only.
6. Keep default relation filters narrow and leave noisier relations behind toggles.
7. Enforce visible budgets for overview, community drilldown, and focus views.
8. Keep file/subsystem browsing as a separate lens when communities are not the right shape.
9. Make ungrouped explicit but not dominant when it must be shown. In that fallback state, ungrouped may appear, but it must not be mixed with real communities in the default overview.

## Scope

**Problem statement:** The graph overview is readable, but the drilldown path still opens too much structure at once.

**In scope:**

- suppress ungrouped from the default overview when real communities exist
- cap community quick-picks at 6 and rank them by inspectability score
- preserve aggregated cross-community edges in overview mode
- keep one-community-at-a-time drilldown behavior
- keep one-hop focus for selected nodes
- maintain a file/subsystem lens as a separate navigation mode
- add tests for ranking, budgets, and drilldown isolation

**Out of scope:**

- changing the canonical graph schema
- changing the clustering backend
- changing the extraction pipeline
- adding new graph data sources

## Acceptance Criteria

- [x] AC-1: Default community overview excludes the ungrouped bucket when real communities exist.
- [x] AC-2: Community quick-picks are capped at 6 and ranked by inspectability score, not raw size alone.
- [x] AC-3: Community overview shows only aggregated cross-community edges.
- [x] AC-4: Clicking a community drills into that community only.
- [x] AC-5: Focus mode remains one-hop only.
- [x] AC-6: The graph maintains a visible budget per view mode: overview <= 24 community nodes, community drilldown <= 50 raw nodes, focus = selected node plus one-hop neighbors only.
- [x] AC-7: File/subsystem browsing remains available as a separate lens, distinct from community mode.
- [x] AC-8: When the graph has only ungrouped nodes, the fallback overview may show a single ungrouped bucket and must not mix in real communities.

## Tasks

- [x] Update community ranking so quick-picks prefer inspectable communities over oversized buckets.
- [x] Sort community quick-picks by the inspectability score and cap the row at 6 entries.
- [x] Suppress ungrouped from the default overview when real communities exist.
- [x] Enforce one-community-at-a-time drilldown behavior.
- [x] Keep focus mode at one hop.
- [x] Add/adjust tests for ranking, budgets, fallback handling, and view isolation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| community ranking | engineering | graph community clustering | Rank by the inspectability score and cap the quick-pick row at 6 |
| overview limits | engineering | community ranking | Cap overview and suppress ungrouped from the default view |
| drilldown limits | engineering | overview limits | Keep only one community open at a time |
| tests | engineering | drilldown limits | Verify view isolation and budgets |

## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A. This change narrows dashboard navigation behavior without changing the graph payload or indexer contracts.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The default view should stop competing with the real communities. |
| AC-2 | required | The quick-pick row needs deterministic ordering and a bounded surface area. |
| AC-3 | required | Overview should explain community boundaries, not internal mesh. |
| AC-4 | required | Drilldown must not mix communities. |
| AC-5 | required | Focus is the symbol inspection path. |
| AC-6 | required | The graph needs hard limits or it becomes unreadable again. |
| AC-7 | required | File browsing is still useful when community grouping is not. |
| AC-8 | required | The ungrouped fallback needs a defined empty-coverage behavior. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-27 | Identified that community drilldown opens too much raw structure. | Graph screenshots |
| 2026-05-27 | Drafted the remaining navigation limits so the dashboard keeps one organizational layer visible at a time. | Change doc |
| 2026-05-27 | Implemented the bounded community quick-picks, explicit budgets, and ungrouped fallback path in the dashboard graph client. | `dashboard.js`, `test_dashboard_server.py`, `docs-lint` |
| 2026-05-28 | Suppressed singleton communities from the default overview and kept labels always visible within the bounded node budget. | Dashboard graph UI and tests |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-27 | Keep the community layer, but cap and rank it by relevance and make drilldown single-community only. | The graph is too dense to expose multiple organizational layers at once. | Keep the current multi-layer presentation |

## Risks

| Risk | Mitigation |
| --- | --- |
| Hiding too much structure could make the graph feel sparse. | Keep file browsing and one-hop focus available as separate lenses. |
| Strict budgets may hide useful nodes in dense repositories. | Use relevance ranking and explicit toggles instead of unconditional expansion. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
