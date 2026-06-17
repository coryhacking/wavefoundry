# MCP in-session index-staleness monitor

Change ID: `1p5xu-enh mcp-in-session-staleness-monitor`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Completed At: 2026-06-16
Last verified: 2026-06-16
Wave: `1p5xt mcp-index-freshness-monitor`

## Rationale

Today the **dashboard watcher** is the only *continuous* index-staleness monitor (`dashboard_server.py::_watch_loop` — mtime poll + a 60s hash-staleness recheck via `_index_is_stale` → `_project_index_inputs_stale`). The other refresh triggers are discrete: git hooks (`.wavefoundry/git-hooks/post-*` → detached `indexer.py`) fire on commit/checkout/merge/rewrite, and MCP mutation tools fire `_trigger_background_index_refresh_for_paths` — but **only for docs/folded-framework paths, not arbitrary code edits**. So when the dashboard is not running, uncommitted **code** edits (an agent editing a `.py` directly, or an external editor) are invisible to the index until the next commit or docs save.

Move continuous monitoring into the MCP server so freshness no longer depends on the dashboard process. The MCP is the natural owner: it serves the queries that need a fresh index, it is host-agnostic, and it runs whenever an agent is working. It already has the machinery — staleness detection, a single-flight background-refresh lock (`_background_refresh_active`), a throttle (`BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS`), and a detached builder (`_start_background_index_refresh`). This change wires a lightweight daemon monitor that reuses all of it.

## Requirements

1. **In-session daemon monitor in the MCP.** `ImplHandler` starts a daemon thread that, on a throttled interval, detects index staleness and triggers a refresh when stale. It runs for the life of the MCP session (stdio/per-session) and stops cleanly on shutdown.
2. **Reuse the single-flight refresh path.** The monitor triggers refresh **only** through the existing `_start_background_index_refresh` guarded by `_background_refresh_active` + `BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS`. No new build path; concurrent sessions, the dashboard, and git hooks all coordinate through the one lock.
3. **Reuse staleness detection.** Use the existing stat-fast-path detection (`indexer._detect_changes` / the dashboard's `_project_index_inputs_stale` logic), not a full SHA256 walk every tick — cheap by default, hashing only on stat mismatch.
4. **Fail-safe + non-blocking.** The thread is a daemon, never blocks MCP startup or any query, swallows all its own exceptions, and never crashes the server. A monitor error degrades to "no auto-refresh," never to a broken server.
5. **Config-gated, framework-owned default.** A `workflow-config` flag (framework-owned default, not pre-emitted per project) enables/disables the monitor and sets its interval. Downstream can turn it off without editing code.
6. **No always-on daemon.** Per-session scope is intentional; this change does not add a separate long-lived process (that would recreate the dashboard-process dependency being removed).
7. **No contract change.** Index/retrieval response shapes are unchanged; this changes *when* a refresh is triggered, not how the index is built or queried.

## Scope

**Problem statement:** Continuous index freshness depends on the dashboard running; without it, uncommitted code edits go un-reindexed between commits/docs-saves.

**In scope:**

- A daemon staleness-monitor thread in `ImplHandler` (`server_impl.py`) reusing the existing detection + single-flight refresh + throttle.
- A config flag (enable + interval) with a framework-owned default.
- Clean start/stop with the MCP session lifecycle.
- Tests: triggers refresh when stale, no-ops when fresh, respects the single-flight lock/throttle (no double build), fail-safe on detection error, disabled by config.

**Out of scope:**

- Removing or changing the dashboard watcher (it stays; it just stops being the only monitor). Dashboard/MCP coexistence is verified, not refactored.
- Any change to how the index is built (`indexer.py`/`setup_index.py`) or to retrieval contracts.
- A standalone always-on daemon / OS service.
- Filesystem-event watching (inotify/watchdog) — polling with the stat-fast-path matches the dashboard's proven, dependency-free approach.

## Acceptance Criteria

- [x] AC-1: `_maybe_refresh_if_stale` triggers a refresh when `indexer.project_index_inputs_stale` reports changed/removed inputs; the daemon monitor calls it on the configured interval — verified by `MaybeRefreshIfStaleTests` + `ProjectIndexInputsStaleTests` (dashboard-independent: pure functions, no dashboard).
- [x] AC-2: `_maybe_refresh_if_stale` triggers only via `_start_background_index_refresh`, guarded by `_background_refresh_active` first → at most one in-flight build (the single existing lock/throttle); `active→no second build` test covers it.
- [x] AC-3: The monitor is a `daemon` thread; loop swallows all exceptions; `__init__` start is try/wrapped; `close()` sets the stop event + best-effort joins → never blocks/crashes the server. `StalenessMonitorLifecycleTests` (starts/stops, disabled→no thread, close-safe-when-never-started).
- [x] AC-4: Config-gated via `indexing.monitor` (`enabled` default True, `interval_seconds` default 20, clamped ≥5) — framework-owned defaults, NOT pre-emitted per project; disabled→no thread (`MonitorConfigTests`). No contract change; **full suite 3175 OK**; docs-lint clean.

## Tasks

- [x] Add the daemon monitor to `ImplHandler` (start in `__init__`, stop in `close`); throttled loop calling existing staleness detection.
- [x] Trigger refresh via the existing `_start_background_index_refresh` single-flight path; confirm lock/throttle coordination.
- [x] Add the `workflow-config` flag (enable + interval) with a framework-owned default.
- [x] Tests: stale→refresh, fresh→noop, single-flight (no double build), fail-safe, config-disabled.
- [x] Extracted the cheap check to `indexer.project_index_inputs_stale` (shared by the dashboard, which now delegates); full suite 3175 OK + docs-lint clean. (Dashboard watch-loop coexistence is finalized by `1p5xw`.)

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| monitor    | Engineering | —          | daemon thread + lifecycle in ImplHandler |
| trigger    | Engineering | monitor    | wire to existing single-flight refresh + throttle |
| config     | Engineering | —          | workflow-config flag + framework default |


## Serialization Points

- Trigger wiring depends on the monitor loop existing; both must use the existing `_background_refresh_active` lock — do not introduce a parallel build path.

## Affected Architecture Docs

`docs/architecture/graph-index-system.md` — add the MCP in-session monitor to the index-refresh trigger map (alongside git hooks, MCP mutation tools, dashboard watcher). Note the dashboard is no longer the sole continuous monitor.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Dashboard-independent continuous freshness is the whole point. |
| AC-2 | required | Single-flight coordination prevents duplicate concurrent builds — the core risk. |
| AC-3 | required | The monitor must never degrade the server. |
| AC-4 | required | Config-gating + no contract change keep it safe to ship on by default. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-16 | Scoped from the 1p5tg delivery discussion. Confirmed current triggers: git hooks (`.wavefoundry/git-hooks/post-*`), MCP `_trigger_background_index_refresh_for_paths` (docs-only), explicit `wave_index_build`, dashboard `_watch_loop` (only continuous monitor). MCP is stdio/per-session; existing single-flight infra (`_background_refresh_active`, `BACKGROUND_INDEX_REFRESH_THROTTLE_SECONDS`, `_start_background_index_refresh`) to be reused. | `server_impl.py`, `dashboard_server.py`, `.wavefoundry/git-hooks/post-commit` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-16 | Host the monitor in the MCP (in-session daemon), not the dashboard or a session-end hook | MCP is host-agnostic, runs during active work, and owns the query path; per-session scope covers exactly when freshness matters | Dashboard-only (rejected — the dependency being removed); session-end hook as primary (rejected — weak proxy, Claude-only, session-end ≠ code-change); always-on daemon (rejected — recreates a long-lived-process dependency) |
| 2026-06-16 | Reuse the existing single-flight refresh + throttle | One lock coordinates monitor + dashboard + git hooks; avoids duplicate concurrent builds | A second independent builder (rejected — race/duplicate builds) |
| 2026-06-16 | Polling with stat-fast-path, not filesystem events | Matches the dashboard's proven, dependency-free approach; cheap | inotify/watchdog (rejected — new dep + cross-platform complexity) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Duplicate concurrent builds (monitor + dashboard + git hook) | Single shared `_background_refresh_active` lock + throttle; AC-2 tests it |
| Monitor thread crashes or blocks the server | Daemon thread, swallows errors, never blocks startup/queries; AC-3 tests fail-safe |
| Constant rebuild churn on a busy repo | Throttle + stat-fast-path; only builds when genuinely stale and not within the throttle window |
| Per-session scope misread as "always monitoring" | Documented: monitors during active sessions (when it matters); git hooks cover commit boundaries |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
