# Graph Details Cleanup

Change ID: `12xzl-change graph-details-dialog-cleanup`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-27
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The graph detail dialog already shows the important health state. The schema version and raw graph path pills add noise without helping the operator inspect the graph. Remove those pills so the details panel stays focused on node/edge counts and build status.

## Requirements

1. The graph detail dialog must continue to show graph presence, node count, edge count, and build status.
2. The graph detail dialog must no longer show the raw `schema 1` or `.wavefoundry/index/project-graph.json` style pills.

## Scope

**Problem statement:** The graph details panel includes low-value implementation details that distract from the graph health summary.

**In scope:**

- remove graph schema/version pill from the details dialog
- remove graph path pill from the details dialog
- keep the existing health/status presentation

**Out of scope:**

- changing graph payload schema
- changing health computation
- changing the index cards outside the graph dialog

## Acceptance Criteria

- [x] AC-1: Graph detail dialogs no longer render schema/version pills.
- [x] AC-2: Graph detail dialogs no longer render raw graph path pills.
- [x] AC-3: Existing node/edge/file counts and build status remain visible.

## Tasks

- [x] Remove the schema/version pill from the graph index section renderer.
- [x] Remove the raw graph path pill from the graph index section renderer.
- [x] Update dashboard tests to reflect the slimmer graph detail dialog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| dialog cleanup | engineering | — | Small presentation-only update |
| dashboard tests | engineering | dialog cleanup | Verify the pills are gone and counts remain |

## Serialization Points

- `.wavefoundry/framework/dashboard/dashboard.js`
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A. This is a presentation-only cleanup in the dashboard dialog.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the schema noise the operator called out. |
| AC-2 | required | Removes the raw path noise the operator called out. |
| AC-3 | required | Preserves the actual graph health summary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-27 | Identified the schema/path pills as low-value detail in the graph dialog. | Dashboard screenshot |
| 2026-05-27 | Removed schema/path pills from the graph detail dialog while preserving the count and build-status summary. | `dashboard.js`, `test_dashboard_server.py`, `docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-27 | Remove the graph schema and graph path pills from the details dialog. | Keeps the dialog focused on health and counts. | Leave the pills in place |

## Risks

| Risk | Mitigation |
| --- | --- |
| Removing the schema/path pills may make debugging slightly less direct. | The raw graph file still exists on disk, and the detail dialog still exposes the important health metadata. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
