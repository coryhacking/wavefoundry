# Dashboard Silent Staleness: Watcher Wedge, Shallow Watch, No Client Watchdog

Change ID: `1rtju-bug dashboard-silent-staleness`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-06
Wave: `1rtnn dashboard-lifecycle-reliability`

## Rationale

The dashboard pushes live updates over Server-Sent Events (`/api/events`, `dashboard_server.py:531-557`), driven by a single background watcher thread (`_watch_loop`, `dashboard_server.py:156-208`) that polls the repo and calls `_notify_sse()` on a real change. The browser only re-renders when it receives an `update` event (`dashboard.js:4398-4401`). The page can go stale "after a while" while the HTTP server keeps serving, through several compounding gaps:

1. **The watcher thread can wedge invisibly.** `SnapshotStore.get()` returns the last cached snapshot (`dashboard_server.py:210-213`), so every HTTP request keeps succeeding regardless of watcher health. Each SSE connection heartbeats on its **own** independent 15s timer (`_SSE_HEARTBEAT`, `dashboard_server.py:544-553`), so even a fully wedged watcher keeps the browser's `EventSource` "connected" — `onerror` never fires, no reconnect is triggered — but heartbeats are not `update` events, so nothing refreshes. `_watch_loop` catches thrown exceptions (`393-394`) but not a call that **blocks forever**: the bulk snapshot collection (`collect_waves`/`collect_changes`/`collect_agents`/`collect_activity` via `collect_dashboard_snapshot`, `dashboard_lib.py:1462`) does plain synchronous filesystem reads with no per-call timeout, so a slow/hung stat wedges the one and only watcher thread with nothing to detect or restart it.

2. **The change-watch is shallow and non-recursive.** `_watched_paths()`/`_current_mtimes()` stat *directory* mtimes for `docs/waves`, `docs/plans`, `docs/agents` (`dashboard_server.py:217-245`). A directory's mtime changes only when a direct child is added/removed/renamed — not when a file nested inside an existing subdirectory is edited. So the common editing pattern (`docs/waves/<wave-id>/<change>.md`, `wave.md` checkbox/section edits) does not trip the fast-change branch (`375-381`) and is only caught by the unconditional full recollect every `_GIT_INTERVAL = 60`s (`382-385`). That is "up to 60s lag" on its own, and complete staleness when it compounds with (1).

3. **No end-to-end liveness the client can act on.** The client suspends its poll fallback whenever SSE reports connected (`dashboard.js:4368-4369`) and has no watchdog for "connected but no data in a long time" — its only refresh trigger is a real `update` event. So a silent server-side stall has no client-side recovery.

4. **The failure is undiagnosable in the normal launch path.** When spawned via the MCP tool, the dashboard's stdout/stderr are `subprocess.DEVNULL` (`server_impl.py:7611-7614`), so `_dashboard_log` output — including the watcher's own `watcher error: ...` line (`dashboard_server.py:394`) — is discarded. Only the separate `--daemon` path routes logging to `.wavefoundry/logs/dashboard.log` (`dashboard_server.py:706-733`).

The server is correctly `ThreadingHTTPServer`-derived (`dashboard_server.py:441`), so a blocking SSE connection does **not** starve other requests — that hypothesis is ruled out. The defect is the watcher/observability/watch-granularity chain, not the HTTP transport.

## Requirements

1. **Bound the watcher's work so it cannot wedge silently.** The snapshot collection invoked from `_watch_loop` must not be able to block the watcher thread indefinitely: apply a per-cycle timeout/guard (consistent with the existing `collect_git_stats` `timeout=5` posture, `dashboard_lib.py:1375-1396`) so a slow/hung filesystem or git call is abandoned for that cycle and the loop continues, rather than freezing the single watcher for the process lifetime.
2. **Detect and surface a stalled/dead watcher.** Track a watcher liveness signal (e.g. last-successful-cycle timestamp) and expose it so the stall is observable: the server should emit a distinct SSE signal and/or a health field on `/api/dashboard` when the watcher has not completed a cycle within a bounded multiple of its interval, so "stale but serving" becomes visible instead of silent.
3. **Make change detection catch nested edits.** The watch must trip its fast-change path on edits to files nested inside watched directories (e.g. `docs/waves/<wave-id>/<change>.md`), not only on direct-child add/remove/rename — via a recursive/nested mtime scan of the watched trees (bounded and cheap) or an equivalent that captures nested writes, so routine wave-doc editing surfaces promptly rather than only on the 60s fallback.
4. **Give the client a staleness watchdog.** The client must recover from a silent server stall: if it is "connected" but has received no `update` (only heartbeats) beyond a bounded window, it must fall back to an active poll and/or force a reconnect, rather than sitting on a stale render indefinitely. Preserve the existing SSE-first behavior when updates are flowing.
5. **Always-available diagnostics.** The watcher's error/liveness logging must be capturable without the `--daemon` path — e.g. always write dashboard/watcher logs to `.wavefoundry/logs/dashboard.log` regardless of how the process was spawned (or an equivalent that survives the MCP `DEVNULL` stdout/stderr), so a future stall is diagnosable from the log instead of invisible.
6. **Keep the SSE + `ThreadingHTTPServer` architecture and stay local-only.** No new filesystem-notification dependency (watchdog/inotify/FSEvents) and no transport rewrite; harden the existing model. No network dependency.
7. **No busy-loop regression.** Hardening must not turn the 3s/60s polling cadence into a tight CPU loop or materially increase steady-state git/FS load; the nested scan must be bounded.

## Scope

**Problem statement:** The dashboard silently stops reflecting repository changes while still serving HTTP, because (a) the single watcher thread can block forever with no timeout/watchdog, (b) the directory-mtime watch misses edits to nested files, (c) the client has no recovery when SSE is "connected" but no updates arrive, and (d) the normal MCP launch discards the logs that would reveal it.

**In scope:**

- Per-cycle timeout/guard on the watcher's snapshot collection.
- Watcher-liveness tracking + surfaced health signal (SSE and/or `/api/dashboard`).
- Nested/recursive change detection for watched doc trees.
- Client-side staleness watchdog (poll/reconnect fallback when connected-but-silent).
- Always-on watcher/dashboard logging independent of the `--daemon` path.
- Tests: nested-edit triggers refresh; wedged-collection is bounded and surfaced not silent; client falls back on connected-but-silent; logging captured under MCP-style spawn; no busy-loop.

**Out of scope:**

- The zombie/process-lifecycle defect — owned by `1rswx-bug dashboard-zombie-child-reaping` in the same wave (that is a dead process; this is a live process gone stale).
- Replacing mtime polling with an OS filesystem-event library (rejected in the Decision Log: new dependency, platform variance).
- Rewriting the transport (WebSocket, etc.) or the client framework.
- Changing what data the dashboard shows.
- Reducing the poll intervals purely for freshness (addressed by nested detection + watchdog instead).

## Acceptance Criteria

- [x] AC-1: A watcher cycle whose snapshot collection hangs (fixture: a stubbed collector that blocks) is bounded by the per-cycle timeout — the watcher loop continues, later real changes are still detected, and the thread does not freeze for the process lifetime. Evidence: `_collect_bounded` (single-worker executor + `future.result(timeout=_COLLECT_TIMEOUT_SECONDS)`, retains the hung future so no pile-up); `test_collect_bounded_times_out_and_does_not_pile_up`.
- [x] AC-2: When the watcher has not completed a cycle within a bounded window, a distinct health/staleness signal is exposed (SSE event and/or `/api/dashboard` field); a test asserts the signal fires on a simulated stall and is absent in the healthy case. Evidence: `watcher_health()` merged additively into `/api/dashboard`; `watcher_status` SSE event on stall/recovery transition; `test_watcher_health_*`, `test_stall_and_recovery_emit_sse_once`, `test_api_dashboard_includes_watcher_health`.
- [x] AC-3: Editing a file nested inside a watched directory (e.g. `docs/waves/<id>/<change>.md`) triggers a refresh via the fast-change path in well under the 60s fallback; a test pins that a nested-file edit is detected (previously only direct-child changes were). Evidence: `_watched_trees`/`_nested_signature` (bounded recursive max-mtime+count) folded into `_current_mtimes`; `test_current_mtimes_detects_nested_file_edit` (also asserts the flat dir mtime alone did NOT change).
- [x] AC-4: With SSE "connected" but no `update` delivered beyond the bounded window, the client falls back to an active poll and/or reconnect and re-renders fresh data; when updates flow normally, SSE-first behavior and suspended polling are preserved (no double-fetching). Evidence: `dashboard.js` client watchdog (`lastUpdateAtRef` + `WATCHDOG_STALE_MS` safety poll while connected) + `watcher_status` listener (immediate poll on server stall signal); `_snapshotHash` excludes the live `watcher` field so healthy-path change-detection is unchanged. Test: `test_dashboard_js_has_client_staleness_watchdog` (source-assertion locking the watchdog contract, added after the qa lane flagged this AC as code-present-but-untested).
- [x] AC-5: The watcher's error/liveness log lines are captured to `.wavefoundry/logs/dashboard.log` even when the dashboard is spawned MCP-style with `DEVNULL` stdout/stderr; a test/inspection confirms a simulated watcher error reaches the log. Evidence: `_dashboard_log` always-on file append gated by `_LOG_ROOT` (set in `main()`), skipped only for the `--daemon` child whose stderr is already redirected; the per-request HTTP access-log firehose is kept OFF the file via `persist=False` from `log_message`, and consecutive identical watcher errors are deduped — so the file stays a diagnostics sink, not an unbounded firehose (delivery-review fixes). Tests: `test_dashboard_log_persists_to_file_when_root_set`, `test_dashboard_log_skips_file_for_daemon_child`, `test_dashboard_log_persist_false_stays_off_the_file`.
- [x] AC-6: Steady-state resource use does not regress into a busy loop — the watcher cadence and the bounded nested scan keep CPU/FS/git load comparable to today; asserted by a bounded-work check or timing guard. Evidence: `_NESTED_SCAN_MAX_ENTRIES` cap short-circuits `os.walk` (measured ~922 stats/3s on this repo, ~1 ms, vs the existing 60s git recollect); watch cadence unchanged (3s poll / 60s git); client watchdog is a low-frequency safety poll that stands down when updates flow; `test_nested_signature_is_bounded`. Accepted residual (P1): the nested scan is count-bounded, not wall-clock-bounded (it runs outside the collect-timeout guard) — a hung stat still surfaces via the read-time `watcher_health` time-based stall.
- [x] AC-7: The `ThreadingHTTPServer` transport and SSE contract are unchanged for the healthy path; existing dashboard tests stay green; no new runtime dependency is added. Evidence: additive `watcher_status` event + `watcher` field only; stdlib `concurrent.futures` only; full 164-test dashboard suite green.
- [x] AC-8: Full framework tests run bytecode-free and docs validation passes. Evidence: full suite re-run at wave close; docs-lint clean.

## Tasks

- [x] Add a per-cycle timeout/guard around the watcher's snapshot collection so a hung FS/git call cannot freeze the thread.
- [x] Track last-successful-cycle liveness and surface a stall signal on SSE and/or `/api/dashboard`.
- [x] Make change detection recurse into watched doc trees so nested-file edits trip the fast path (bounded scan).
- [x] Add a client staleness watchdog: on connected-but-silent beyond the window, poll/reconnect; keep SSE-first when healthy.
- [x] Route watcher/dashboard logging to `.wavefoundry/logs/dashboard.log` independent of `--daemon`/DEVNULL spawn.
- [x] Add tests: bounded-wedge, stall signal, nested-edit refresh, client fallback, log capture, no busy-loop.
- [x] Run `python3 .wavefoundry/framework/scripts/run_tests.py` and `wave_validate`.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| watcher-hardening | implementer | — | Per-cycle timeout, liveness tracking, nested detection (`dashboard_server.py`) |
| observability | implementer | watcher-hardening | Stall signal on SSE/API + always-on logging |
| client-watchdog | implementer | observability | `dashboard.js` connected-but-silent fallback |
| tests | qa-reviewer | all implementation streams | Wedge, stall, nested, fallback, logging, no busy-loop |


## Serialization Points

- The stall signal (server) must exist before the client watchdog can consume it if the watchdog keys off a server health field; if the watchdog is purely client-timer-based it can land independently — decide at implementation and record.
- Companion to `1rswx-bug dashboard-zombie-child-reaping` in the same wave: different surfaces (live-process watcher/SSE here vs process lifecycle in `server_impl.py` there); coordinate on any shared dashboard helper.

## Affected Architecture Docs

- N/A — a defect fix within the existing dashboard subsystem (watcher thread, SSE endpoint, client script). No module boundary, cross-cutting contract, or data-flow topology change; the SSE/API contract is preserved and only gains an additive health signal.

## AC Priority

(Proposed; confirmed at Prepare wave.)


| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | A watcher that can block forever is the root of the "stops forever" symptom. |
| AC-2 | important | Surfacing the stall turns a silent failure into a visible one; recovery-adjacent but not the core fix. |
| AC-3 | required | The shallow-watch gap is the everyday cause of staleness for nested wave-doc edits. |
| AC-4 | required | Without a client watchdog a silent server stall has no recovery on the page. |
| AC-5 | important | Diagnosability prevents this class from being invisible again; not user-facing behavior. |
| AC-6 | required | The fix must not trade staleness for a CPU busy-loop. |
| AC-7 | required | Preserve the healthy-path transport and the no-new-dependency constraint. |
| AC-8 | required | Standard framework verification gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-05 | Diagnosed from operator report ("dashboard stops updating after a while") via a guru trace of the live-update path. Root causes: watcher thread can block with no timeout/watchdog; per-connection SSE heartbeats keep the client "connected" so it never reconnects; directory-mtime watch misses nested-file edits (surfaces only on the 60s fallback); no client staleness watchdog; MCP-spawn DEVNULL discards watcher logs. Transport (`ThreadingHTTPServer` + SSE) ruled healthy. | `dashboard_server.py:156-208` (`_watch_loop`), `:210-245` (`get`/watched paths), `:441` (ThreadingHTTPServer), `:531-557` (SSE + heartbeat), `:706-733` (`--daemon` logging), `dashboard_lib.py:1375-1396`/`:1462` (git timeout vs untimed collect), `dashboard.js:4353-4429` (SSE/poll/reconnect); `server_impl.py:7611-7614` (DEVNULL spawn). |
| 2026-07-06 | Delivery review (code-correctness, qa, perf+security-faithfulness). No blocking findings. Applied in-session fixes: (S3) HTTP access-log lines now go to stderr only (`_dashboard_log(persist=False)` from `log_message`) so the always-on `dashboard.log` isn't flooded per request; (#2) consecutive identical watcher-error lines are deduped so a persistent per-cycle failure can't grow the log unbounded; (#3) on a collect-timeout stall the watcher no longer commits `_last_mtimes`, so a pending edit retries every 3s instead of waiting up to the 60s git timer to resurface. Added the missing AC-4 client-watchdog coverage (`test_dashboard_js_has_client_staleness_watchdog`, source-assertion matching the suite's JS-locking pattern) + `test_dashboard_log_persist_false_stays_off_the_file`. Accepted residual (P1): `_current_mtimes`/`_nested_signature` is count-bounded (`_NESTED_SCAN_MAX_ENTRIES`), not wall-clock-bounded — it runs outside the collect-timeout guard, but a hung stat still surfaces via the read-time `watcher_health` time-based stall (age > `_WATCHER_STALL_SECONDS`). | reviews (3 lanes); `dashboard_server.py` `_dashboard_log`/`log_message`/`_watch_loop`; tests `DashboardWatcherHardeningTests` (12); full suite green. |
| 2026-07-06 | Implemented. Serialization-point resolution: shipped BOTH a server-side stall signal (`watcher_status` SSE event + additive `watcher` field on `/api/dashboard`) AND a purely client-timer-based watchdog — the two are independent, so the client recovers even if it missed the SSE transition (e.g. reconnected after the signal) and the observability field surfaces staleness to any consumer. Bounded collection via a single-worker `concurrent.futures` executor (stdlib, no new dependency); a timed-out future is retained to prevent pile-up. Nested detection via a bounded `os.walk` max-mtime+count signature per watched tree. Always-on logging via `_LOG_ROOT` (skipped for the `--daemon` child to avoid double-write). | `dashboard_server.py` (`_collect_bounded`, `watcher_health`, `_notify_watcher_sse`, `_watched_trees`/`_nested_signature`, `_dashboard_log`); `dashboard.js` (watchdog + `watcher_status` listener, `_snapshotHash` excludes `watcher`); tests `DashboardWatcherHardeningTests`. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-05 | Harden the existing mtime-poll + SSE model (timeout, liveness signal, nested detection, client watchdog, always-on logging) rather than adopt an OS filesystem-event watcher. | Fixes all four root causes with no new dependency and no transport rewrite, staying inside the local-only constraint; the architecture (`ThreadingHTTPServer` + SSE) is sound — only the watcher robustness, watch granularity, and observability are weak. | **OS filesystem-event library (watchdog/inotify/FSEvents):** rejected — a new dependency with platform variance for a repo that is deliberately local-only/no-network and stdlib-first. **Drop the fast path; shorten the periodic full recollect to ~5s:** rejected — raises steady-state CPU/git load and still stalls if a collection call hangs (does not fix the wedge). **Client-only fix (aggressive poll):** rejected — masks a wedged server without surfacing it and gives up the SSE efficiency in the healthy case. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Per-cycle timeout abandons a legitimately slow-but-progressing collection and shows partial data | Timeout is a bounded multiple of the normal cycle; on timeout keep the last good snapshot and emit the stall signal rather than publishing partial state. |
| Recursive nested scan becomes expensive on a large docs tree | Bound the scan to the watched trees and cache; the codebase already does a full 60s recollect, so a bounded mtime walk is comparable; guard with the no-busy-loop AC. |
| Client watchdog double-fetches or fights SSE | Watchdog only engages after a bounded connected-but-silent window and stands down as soon as an `update` arrives; healthy-path behavior asserted unchanged. |
| Always-on file logging grows unbounded | Reuse/repoint the existing `dashboard.log` mechanism with its current rotation/size posture; do not introduce a new unbounded sink. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
