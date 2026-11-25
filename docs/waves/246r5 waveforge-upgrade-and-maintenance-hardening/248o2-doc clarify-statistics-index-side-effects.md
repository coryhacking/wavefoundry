# Clarify statistics index side effects

Change ID: `248o2-doc clarify-statistics-index-side-effects`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-11-24
Wave: 246r5 waveforge-upgrade-and-maintenance-hardening

## Rationale

A reader tracing the read-only SQLite query can miss the build-status branch that refreshes metadata and clears finished build state.

## Product Intent

A host administrator reading the served tool description can tell what an index statistics request may change before allowing it (AC-1 and AC-2).

## Requirements

1. Describe conditional SQLite sidecar activity and finished-build metadata refresh or state cleanup in the stats index section. Distinguish reading statistics from starting an index build. Trace index_health independently and clarify its wording only where its actual behavior warrants it.

## Scope

Documentation and verification only. Preserve tool names, annotations, response shapes and runtime behavior.

## Acceptance Criteria

- [x] AC-1: Trace an ordinary read and a finished-build fixture through the stats entry point. Compare the observed filesystem effects with the description and verify that neither starts a build.
- [x] AC-2: Inspect the served tool description and maintained tool reference for consistency. Record the independent index_health trace, including any differences that affect the wording.

## Tasks

- [x] Describe conditional SQLite sidecar activity and finished-build metadata refresh or state cleanup in the stats index section. Distinguish reading statistics from starting an index build. Trace index_health independently and clarify its wording only where its actual behavior warrants it.
- [x] Exercise AC-1 and AC-2 and record evidence in the Progress Log.

## Agent Execution Graph

The implementer delivers the change and its checks. The reviewers verify the evidence independently.

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`
- `.wavefoundry/framework/scripts/dashboard_lib.py`
- `.wavefoundry/framework/scripts/project_stats.py`
- `docs/specs/mcp-tool-surface.md`

## Affected Architecture Docs

No architecture boundary changes. Keep the existing contract documentation consistent with this change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Verifies the primary outcome. |
| AC-2 | required | Verifies the compatibility boundary. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-24 | Planned from Waveforge’s v1.51.0 feedback. | Item A3. |
| 2026-11-24 | Readback: trace the stats and health handlers separately, including a completed build. Update their served docstrings and reference with the actual bookkeeping effects and preserve runtime behavior. | AC-1 and AC-2. |
| 2026-11-24 | Verified ordinary and finished reads through wf_stats_response on a temporary canonical vector/graph fixture with subprocess starts prohibited. Ordinary read changed only index.sqlite-shm and index.sqlite-wal. Finished read wrote index-build-stats.json (123 files from the fixture log) and removed index-build.json. Booted MCP descriptions name the affected files. | test_stats_index_surfaces and WaveIndexHealthRefreshTests.test_previous_build_stats_refresh_from_finished_log: 5 passed. The independent health handler refreshes statistics from finished logs. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-24 | Use the existing framework path. | Planner default within the operator-selected scope. | Promising zero writes from a read-only SQLite query would overlook build bookkeeping. |

## Risks

Documentation and verification only. Preserve tool names, annotations, response shapes and runtime behavior.

## Session Handoff

Prepare the admitted spec before implementation.
