# Cluster Overview Aggregation

Change ID: `12xz3-change cluster-overview-aggregation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The current graph overview still renders raw node neighborhoods, which is too dense to scan once the graph grows. We already have persistent cluster metadata, but the dashboard only uses it as a filter. The first screen needs to collapse that structure into a real community overview so the graph reads as a map of subsystems instead of a hairball.

## Requirements

1. Overview mode must render one synthetic node per community when cluster metadata is available.
2. Overview edges must represent cross-community connections, weighted by the number of raw edges they collapse.
3. Clicking a community node must drill into that community's raw node graph without changing the canonical graph payload.
4. Focus mode must stay one-hop around the selected raw node and must not use the aggregated community graph.
5. Relation filters must still apply to the community overview by filtering the raw edges before aggregation.

## Scope

**Problem statement:** The dashboard exposes community metadata, but the default graph view still shows too many raw nodes and edges. Community clustering is not yet visible as a first-class overview.

**In scope:**

- aggregated community overview in the dashboard graph panel
- community node labels and counts
- weighted cross-community edges in overview mode
- preserved raw-node drilldown for selected communities
- dashboard tests for aggregated overview and drilldown behavior

**Out of scope:**

- new graph schema fields
- backend clustering changes
- replacing the raw focus or files views
- changing the canonical directed graph payload

## Acceptance Criteria

- [x] AC-1: Overview mode renders community nodes instead of raw nodes when cluster metadata is present.
- [x] AC-2: Overview edges are aggregated across communities and retain relation-based filtering.
- [x] AC-3: Selecting a community drills into that community's raw node graph without changing the focus view contract.
- [x] AC-4: Dashboard tests cover aggregated overview rendering, community drilldown, and the fallback path when no communities are present.

## Tasks

- [x] Add a graph aggregation helper in `dashboard.js` that converts raw nodes/edges plus cluster metadata into community nodes and weighted cross-community edges.
- [x] Wire overview mode to the aggregated community graph and keep focus/files modes on the raw graph.
- [x] Update the summary panel so overview mode reports community counts rather than raw-node counts.
- [x] Add dashboard tests for aggregation, drilldown, and fallback behavior.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| dashboard aggregation | engineering | — | Build the community overview helper and wire it into overview mode |
| dashboard tests | engineering | dashboard aggregation | Verify overview, drilldown, and no-community fallback |

## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A. This is a dashboard presentation change that reuses existing graph and cluster payloads without changing the architecture docs or backend contracts.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | This is the primary user-visible simplification. |
| AC-2 | required | The overview must stay semantically useful under filters. |
| AC-3 | required | Drilldown is the path from overview to detail. |
| AC-4 | required | The change needs regression coverage. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-27 | Planned aggregated community overview to replace the raw-node overview mesh. | Wave discussion and graph screenshots |
| 2026-05-27 | Implemented the aggregated community overview in the dashboard client and verified the new overview/drilldown contract. | `dashboard.js`, `test_dashboard_server.py`, `docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-27 | Use the persisted cluster metadata to build an aggregated community overview in the dashboard client. | No backend contract change is needed, and the existing cluster payload is already sufficient. | Backend aggregation or a separate community graph payload |

## Risks

| Risk | Mitigation |
| --- | --- |
| Aggregation can hide detail that some users need immediately. | Keep focus mode as the raw one-hop view and preserve community drilldown. |
| Cluster counts can become confusing under filters. | Use filtered raw nodes for the overview counts and keep the full cluster metadata in the detail view. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
