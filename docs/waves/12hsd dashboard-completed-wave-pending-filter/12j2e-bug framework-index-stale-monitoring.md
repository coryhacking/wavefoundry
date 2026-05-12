# Dashboard: Framework Index Stale Monitoring Parity

Change ID: `12j2e-bug framework-index-stale-monitoring`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-05-11
Wave: `12hsd dashboard-completed-wave-pending-filter`

## Rationale

The dashboard's Semantic Index dialog computes and displays live stale state for the project index, but the framework section only shows passive build metadata from `.wavefoundry/framework/index/`. As a result, the project layer can show `Up to date` or `Stale` while the framework layer shows only build age and elapsed update time, even though framework-source edits can make the framework docs index stale. This creates an accuracy gap in the dashboard's operational status surface.

## Requirements

1. The dashboard server must compute staleness independently for both index layers:
   - project index at `.wavefoundry/index/`
   - framework index at `.wavefoundry/framework/index/`
2. Framework-layer staleness must consider changes under `.wavefoundry/framework/` while excluding `.wavefoundry/framework/index/` itself.
3. The dashboard snapshot health payload must expose `stale` and `build_status` for the framework layer in the same shape used by the project layer.
4. When dashboard `auto_index` is enabled and the framework layer becomes stale, the background index builder must be signalled to rebuild, just as it is for the project layer.
5. The Semantic Index dialog must render the framework section with the same `Up to date` / `Stale` status badge behavior already used for the project section.
6. The change must not regress existing project-layer stale detection or auto-index behavior.

## Scope

**Problem statement:** framework index freshness is visible only as old build metadata, not as a live stale/clean state, so the dashboard cannot accurately report whether framework edits need a refresh.

**In scope:**

- `.wavefoundry/framework/scripts/dashboard_server.py`
  - Generalize index staleness checks to support project and framework layers
  - Track framework stale state in `SnapshotStore`
  - Include framework index stats file in watched paths where needed
  - Signal auto-index rebuilds when the framework layer becomes stale
- `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`
  - Add regression tests for framework stale detection, snapshot payload status, and stale-triggered rebuild behavior
- `.wavefoundry/framework/dashboard/dashboard.js`
  - Reuse existing badge logic by supplying framework-layer stale/build state in the same payload shape

**Out of scope:**

- Changing the semantic index data model itself
- Adding framework code chunks to the framework docs layer
- Broad redesign of the index dialog UI

## Acceptance Criteria

- AC-1: The dashboard server can report `stale: true|false` for the framework index layer.
- AC-2: Framework-source edits under `.wavefoundry/framework/` can mark the framework layer stale without marking the project layer stale solely for that reason.
- AC-3: Framework index metadata changes are reflected in the dashboard snapshot health payload.
- AC-4: With dashboard `auto_index` enabled, a framework stale transition signals a rebuild.
- AC-5: The Semantic Index dialog can render `Up to date` or `Stale` for the framework section using the same state rules as the project section.
- AC-6: Existing project-layer stale detection tests continue to pass.
- AC-7: The dashboard test suite passes.

## Tasks

- Generalize dashboard index stale detection to accept `project` and `framework` layers
- Track framework stale state alongside project stale state in `SnapshotStore`
- Ensure watched paths include framework index build metadata for snapshot refreshes
- Add tests for framework stale detection and auto-index signal behavior
- Run the dashboard test suite

## Affected Architecture Docs

N/A — operational parity fix inside the existing dashboard/index topology.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Core correctness for framework-layer status |
| AC-2 | required | Prevents false coupling between project and framework stale states |
| AC-3 | important | Makes framework rebuild metadata visible in the dashboard |
| AC-4 | required | Monitoring without rebuild signaling would be incomplete |
| AC-5 | important | User-visible confirmation of parity |
| AC-6 | required | Regression guard for the existing project layer |
| AC-7 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-11 | Confirmed that the dashboard watcher computes stale state only for `.wavefoundry/index/`, while framework index status is passive metadata only. Framework refresh triggers exist in hook/background paths, but the dashboard does not surface framework stale/clean parity. | `dashboard_server.py`, `dashboard_lib.py`, `dashboard.js`, `render_platform_surfaces.py`, `server.py` |
| 2026-05-11 | Generalized dashboard stale detection to project/framework layers, taught the dashboard auto-index builder to rebuild the framework docs layer when requested, added framework stale/watch regressions, and verified the live `SnapshotStore` payload now includes `build_status` + `stale` for both layers. The dashboard suite passes and docs lint is clean. | `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_dashboard_server.py'`; `./.wavefoundry/bin/docs-lint`; live `SnapshotStore(root).get()` output |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-11 | Reuse the existing index-section badge UI and supply framework stale state via the same payload shape | Minimal UI change; keeps project/framework semantics aligned | Add framework-only badge rules (rejected: unnecessary divergence) |
| 2026-05-11 | Keep stale computation layer-specific rather than collapsing project/framework into one overall flag | The two layers index different path sets and can drift independently | Single combined stale bit (rejected: loses operational precision) |

## Risks

| Risk | Mitigation |
|------|------------|
| Framework stale checks accidentally treat framework index output as source changes | Explicitly exclude `.wavefoundry/framework/index/` from framework-layer source-path checks |
| Shared watcher changes regress project auto-index behavior | Preserve project tests and add framework-parity tests in the same suite |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
