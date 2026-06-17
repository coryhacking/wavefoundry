# Remove the dashboard's staleness watch (MCP now owns it)

Change ID: `1p5xw-enh remove-dashboard-staleness-watch`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Last verified: 2026-06-16
Wave: `1p5xt mcp-index-freshness-monitor`

## Rationale

Once the MCP server owns continuous index-staleness monitoring (`1p5xu`), the dashboard's own staleness watcher is redundant — and keeping two continuous monitors is exactly the duplicate-builder hazard this wave is trying to avoid. Remove the dashboard's staleness detection + build-triggering so monitoring lives in one place (the MCP, the query consumer), and the dashboard becomes a **read-only health/status UI** rather than a correctness dependency.

This change is **sequenced strictly after `1p5xu`**: the dashboard's monitor must not be removed until the MCP monitor has replaced it and is verified, or there would be a coverage gap.

## Requirements

1. **Sequenced after `1p5xu`.** Do not land this until the MCP in-session monitor (`1p5xu`) is implemented and verified. (Depends On: `1p5xu`.)
2. **Remove the dashboard's continuous staleness monitor + build triggers.** Retire the periodic hash-staleness recheck (`_index_is_stale` / `_project_index_inputs_stale` / `_STALENESS_CHECK_INTERVAL`) and the mtime-watch → `signal_change` rebuild trigger in `dashboard_server.py::_watch_loop` that exist solely to detect staleness and kick a build.
3. **Dashboard becomes read-only for index state.** It may still *display* index health (reading the same offline detection on demand for the UI), but it no longer *triggers* index builds.
4. **Preserve upgrade coordination — verify, don't assume.** The dashboard's upgrade-lock pause/resume behavior (e.g. `signal_startup` on lock removal) must not silently break the post-upgrade reindex. Confirm the upgrade flow itself (or a retained minimal handler) still drives the post-upgrade reindex; if the dashboard's lock-removal reindex was the only path, keep that narrow piece or move it, but do not regress upgrade auto-reindex.
5. **No coverage gap, no double-build.** After this change: with the MCP running, the MCP monitor provides continuous freshness; git hooks cover commit boundaries; the dashboard no longer triggers builds (so no duplicate concurrent builds with the MCP monitor). The accepted tradeoff — "dashboard open but no MCP session connected" — is documented (see Decision Log).
6. **No contract change.** Dashboard HTTP/health endpoints keep their response shapes (they may now reflect on-demand rather than watcher-pushed freshness).

## Scope

**In scope:**

- Remove the staleness-detection + build-trigger path from `dashboard_server.py` (`_watch_loop` staleness recheck, `_index_is_stale`/`_project_index_inputs_stale` usage for triggering, `signal_change` on file change).
- Keep read-only health display; verify + preserve the post-upgrade reindex path.
- Update dashboard tests to drop the watcher-trigger expectations and assert the dashboard no longer kicks builds; full suite green.

**Out of scope:**

- The MCP monitor itself (`1p5xu`) and the session-end hook (`1p5xv`).
- Removing the dashboard's UI/health display or its upgrade-lock awareness (kept).
- Changing the index builder or retrieval contracts.

## Acceptance Criteria

- [x] AC-1: `1p5xu` is landed + verified before this change is implemented (dependency honored; no window where neither monitor runs).
- [x] AC-2: The dashboard no longer runs a continuous staleness monitor and no longer triggers index builds on file change / periodic recheck; verified by updated dashboard tests (watcher-trigger expectations removed, dashboard asserts it does not kick builds).
- [x] AC-3: Post-upgrade reindex is verified to still occur (via the upgrade flow or a retained minimal handler) — no regression to upgrade auto-reindex.
- [x] AC-4: With the MCP monitor running and the dashboard open, there are no duplicate concurrent builds (single-flight respected, only one monitor now); read-only dashboard health still displays; full suite + docs-lint clean.

## Tasks

- [x] Confirm `1p5xu` is landed + verified (gate this change on it).
- [x] Remove the staleness recheck + build-trigger path from `dashboard_server.py`; keep read-only health display.
- [x] Verify/preserve the post-upgrade reindex path (upgrade flow or retained handler).
- [x] Update dashboard tests; run full suite + docs-lint.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| remove     | Engineering | `1p5xu`    | strip staleness watch + build trigger from dashboard |
| preserve   | Engineering | remove     | keep read-only health + verify upgrade reindex path |


## Serialization Points

- Hard dependency on `1p5xu`: the MCP monitor must be the live continuous monitor before the dashboard's is removed. Do not implement `1p5xw` until `1p5xu` is verified.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — update the index-refresh trigger map: the dashboard is no longer a continuous monitor / build trigger; continuous monitoring is the MCP in-session monitor; the dashboard is a read-only health UI.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Removing the dashboard monitor before the MCP one exists would leave a coverage gap. |
| AC-2 | required | Removing the redundant monitor (one owner) is the deliverable. |
| AC-3 | required | Upgrade auto-reindex must not regress. |
| AC-4 | required | No duplicate builds + read-only health preserved. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Operator folded the dashboard-check removal into this wave (was initially out of scope). Sequenced strictly after `1p5xu`. Dashboard monitor map: `_watch_loop` (645–713), `_index_is_stale`/`_project_index_inputs_stale`, `_STALENESS_CHECK_INTERVAL`, `signal_change`/`signal_startup`. | `dashboard_server.py` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Remove the dashboard's continuous monitor + build triggers once the MCP owns monitoring | One continuous monitor (the MCP, the query consumer); the dashboard becomes a read-only UI, not a correctness dependency; eliminates the two-monitor duplicate-build hazard | Keep both monitors (rejected — duplicate builds + the dependency this wave removes); remove the dashboard watcher entirely incl. UI health (rejected — the read-only display is still useful) |
| 2026-06-16 | Accept the "dashboard up, no MCP connected" tradeoff | When no agent is connected, nothing is querying the index, so continuous freshness is unnecessary; git hooks still cover commits, and the dashboard can read health on demand. Continuous monitoring rightly follows the consumer (MCP), not the viewer (dashboard) | Retain a dashboard-only fallback monitor (rejected — reintroduces the second monitor) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Coverage gap if removed before `1p5xu` lands | Hard dependency + AC-1; implement only after `1p5xu` is verified |
| Post-upgrade reindex silently breaks | AC-3 explicitly verifies the upgrade-reindex path; preserve a minimal handler if the dashboard was the only driver |
| Duplicate builds during the transition | Single-flight lock already coordinates; after removal only the MCP monitor triggers |
| Dashboard health display goes stale-looking | Dashboard reads health on demand for the UI; freshness for *retrieval* is owned by the MCP monitor |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
