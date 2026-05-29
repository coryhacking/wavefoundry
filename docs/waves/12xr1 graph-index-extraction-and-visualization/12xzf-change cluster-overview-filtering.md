# Cluster Overview Filtering

Change ID: `12xzf-change cluster-overview-filtering`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The aggregated community overview is useful, but the ungrouped bucket is currently dominating the first view. That makes the overview feel cluttered again and hides the value of the actual communities. We need a simple filter rule so the default overview emphasizes real communities and keeps the unassigned bucket out of the way.

## Requirements

1. The default community overview must exclude the ungrouped bucket when at least one real community is present.
2. The overview should continue to use the aggregated community graph and preserve the raw-node drilldown path.
3. If ungrouped nodes are visible at all, they must be presented as a secondary / explicit bucket rather than the primary overview.

## Scope

**Problem statement:** The community overview is still crowded because unassigned nodes are rendered as a giant "Ungrouped" node.

**In scope:**

- hide ungrouped from the default aggregated overview when communities exist
- preserve the current community drilldown and raw focus behavior
- add tests for default exclusion and fallback handling

**Out of scope:**

- changing the clustering backend
- changing graph payload schemas
- altering the raw focus view

## Acceptance Criteria

- [x] AC-1: Overview mode excludes the ungrouped bucket when real communities exist.
- [x] AC-2: The overview remains usable when the graph contains only ungrouped nodes.
- [x] AC-3: Dashboard tests cover the ungrouped exclusion and the fallback path.

## Tasks

- [x] Update the community aggregation helper to suppress the ungrouped bucket from the default overview when at least one real community exists.
- [x] Keep the raw-node focus view unchanged.
- [x] Add regression tests for default exclusion and ungrouped-only fallback behavior.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| overview filtering | engineering | cluster overview aggregation | Remove the ungrouped bucket from the default overview |
| dashboard tests | engineering | overview filtering | Verify exclusion and fallback behavior |

## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A. This is a dashboard presentation refinement that reuses the existing cluster payload and graph aggregation helper.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | This is the core simplification. |
| AC-2 | required | We still need a usable fallback if the graph has no cluster coverage. |
| AC-3 | required | Regression coverage keeps the default view honest. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-27 | Identified that the ungrouped bucket dominates the aggregated overview. | Graph screenshots |
| 2026-05-27 | Filtered the default overview to real communities and kept raw-node fallback when community coverage is absent. | `dashboard.js`, `test_dashboard_server.py`, `docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-27 | Suppress the ungrouped bucket from the default overview when real communities exist. | Keeps the overview focused on actual communities while preserving fallback behavior. | Keep ungrouped as a visible overview bucket |

## Risks

| Risk | Mitigation |
| --- | --- |
| Hiding ungrouped may hide genuinely important orphan nodes. | Preserve raw focus and allow the ungrouped-only fallback when cluster coverage is absent. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
