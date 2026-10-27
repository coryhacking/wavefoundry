# Dashboard reports when it is running stale index code

Change ID: `21s7a-enh dashboard-stale-runtime-banner`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-26
Wave: 21s7b dashboard-stale-runtime-reporting

## Rationale

The dashboard server is long-lived: the incident process had run from 2026-10-25 to 2026-10-26. Index producer modules are captured once at import (`index_compatibility._SOURCE_HASHES`), so after a framework change rewrites the index, every compatibility-guarded read in the old process is refused and stays refused until restart. Nothing in the dashboard says so outside the Index dialog, and inside it the refusal read as "not built" (change `21s79-bug`). The MCP server already detects this condition (`_index_runtime_stale` in `wf_server/server_impl.py`, a stat-signature-cached call to `index_compatibility.ensure_runtime_current`) and tells the agent to restart; the dashboard has no equivalent. In this repository every framework wave that touches an index producer makes a running dashboard stale.

## Product Intent

An operator with a dashboard open learns, on whatever view they are looking at, that the dashboard is running index code older than what is installed and that restarting it fixes that, instead of trusting or misreading data the dashboard can no longer load. After a restart the notice is gone. The dashboard does not restart itself. AC-1 together with AC-2 tests the intent.

## Requirements

1. The dashboard server determines whether its loaded index runtime is stale by calling the existing `index_compatibility.ensure_runtime_current()` when `/api/dashboard` is served (the way `watcher_health` is read at request time), not inside the bounded snapshot collection, so the result reaches the browser even while collection is stalled and the last good snapshot is being served. It does not introduce a second fingerprint scheme, source list, or cache: the existing guarded reads already hash the producer files every cycle, so one more uncached check per request is acceptable. The `index_compatibility` import happens inside the check so a failed import is retried on the next request.
2. The `/api/dashboard` response exposes the result as a small typed field (stale flag, the stale component name, and the recovery action **Restart dashboard** / `wf_restart_dashboard`).
3. The dashboard UI shows a persistent notice on every view while the field reports stale, naming the recovery action, and shows nothing when current.
4. Detection never refuses or blocks a snapshot: a failure to evaluate staleness reads as "not stale" with no notice, matching the MCP server's detector.

## Scope

**Problem statement:** a long-running dashboard cannot tell the operator that its index code is out of date.

**In scope:**

- `dashboard_server.py`: request-time staleness evaluation and response field.
- `dashboard.js` / `dashboard.css`: global notice.
- Tests in `test_dashboard_server.py`.

**Out of scope:**

- Automatic restart, re-exec, or subprocess-per-snapshot collection (see Decision Log).
- Staleness of non-producer dashboard modules (`dashboard_lib.py`, `dashboard_server.py`, `dashboard.js`); they do not trip the compatibility guard.
- The CPU and watcher-stall behavior seen on the stale process (cause unverified).
- MCP server reload (`20jo3-enh complete-framework-runtime-reload`), and any change to `wf_server/server_impl.py`.
- A sources-older-than-index state (`index_version_newer`, for example after a branch switch) is not runtime staleness and gets no notice here; 21s79 shows it inside the Index dialog.

**Platform behavior:** the check is stat plus SHA-256 of nine local framework files, identical on Windows, macOS, Linux and WSL2. On filesystems where `st_ino` or `st_ctime_ns` is unstable or zero (some Windows and network volumes), the signature changes more or less often than ideal, which costs at most an extra hash; correctness comes from the byte hash. The notice is plain HTML.

## Acceptance Criteria

- [x] AC-1: When an index producer source changes after the dashboard loaded it, the next `/api/dashboard` response reports the runtime as stale and names the component and the restart action; with unchanged sources it reports current. Oracle: a server test that preloads the modules and then makes the capture stale, plus the scratch-copy rendered check. Fails before the change, where the snapshot has no such field.
- [x] AC-2: The dashboard shows the stale-runtime notice on every top-level view while the response reports stale and shows none when current. Required evidence is a rendered check of a dashboard whose loaded capture is made stale after startup, including that a restart clears the notice; a dashboard.js source-contract test is supplementary and does not satisfy this AC alone. Fixture mechanics are designed during implementation and must not touch the repository's index or the operator's running dashboard.
- [x] AC-3: While snapshot collection is stalled (collection held past its bound so the last good snapshot is served), a stale runtime is still reported on `/api/dashboard`. Oracle: a server test that blocks collection and makes the capture stale. Fails if the check is placed inside collection.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Evaluate `ensure_runtime_current()` at `/api/dashboard` request time and add the response field.
- [x] Render a global notice in `dashboard.js` with a style in `dashboard.css`.
- [x] Tests for AC-1 and AC-3 (stalled collection); dashboard.js contract for the notice.
- [x] Rendered check against a scratch-copy dashboard, including the restart clearing the notice.

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| detect | implementer | none | request-time check, response field, tests |
| notice | implementer | detect | dashboard.js notice and contract test |


## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_server.py`, `.wavefoundry/framework/dashboard/dashboard.js`, `.wavefoundry/framework/dashboard/dashboard.css`, `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A: confined to the dashboard server's response and UI; it calls the existing `index_compatibility` check and adds no module boundary or shared seam.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Detection is the change. |
| AC-2 | required | The operator-visible outcome. |
| AC-3 | important | The incident process was stalling; a notice hidden by stalls would miss the motivating case. |
| AC-4 | required | Change-local verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-26 | Planned from the same incident as `21s79-bug`. | Stale dashboard pid 37839 started 2026-10-25; restart cleared the condition. |
| 2026-10-26 | Readiness note: the Platform behavior paragraph (stat signature, `st_ino`) and the Risks row about importing `wf_server` helpers predate the readiness repair; Requirements 1 to 4 govern (uncached request-time check, no `server_impl` reuse). Left unedited to keep the readiness receipt. Platform behavior as delivered: SHA-256 of nine local framework files per request, identical on Windows, macOS, Linux and WSL2. | Council-readiness synthesis residual note 1. |
| 2026-10-26 | Delivered. `dashboard_server.runtime_currency()` (module level) imports `index_compatibility` inside the call and runs `ensure_runtime_current()`; only `index_runtime_stale` reads stale, anything else reads current. The `/api/dashboard` handler adds it beside `watcher_health()` per request. `StaleRuntimeNotice` renders first inside `app-main`, so every view shows it; text is rendered as children only. No runtime flag, endpoint or environment switch can force or suppress staleness. | `test_dashboard_server.DashboardStaleRuntimeReportingTests` through `DashboardHandler.do_GET`. Known-bad: a scratch mutant that reads the flag from the collected snapshot instead of per request fails both request-time tests, including the stalled-collection test. Rendered: `.wavefoundry/work/21s7b/evidence/stale-main.png`, `stale-graph.png` (notice on both views), `restarted-index.png` (gone after restart; `/api/dashboard` `runtime` back to `{"stale": false}`). |
| 2026-10-26 | Latency note: the notice appears on the browser's next `/api/dashboard` fetch. A page load shows it immediately; an already-open page picks it up on the next SSE update or the 90s watchdog refetch. Accepted for an advisory notice. | Code-reviewer readiness note 2. |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-26 | Detect with the existing compatibility check and show a global notice naming **Restart dashboard**. | Smallest mechanism that covers the incident. Efficacy: replaying the incident, the notice would have appeared on every view from the first snapshot after the index was rewritten. It is advisory; the operator acts because it is visible everywhere and names one existing command. It would not flag dashboard-only module edits (accepted, those do not break reads). Existing data gives most of the value: the capture and check already exist and the MCP server already uses them. Success after release: no further "not built with a healthy index" reports from a long-running dashboard. | (B) Re-exec the server when stale: replaces the process silently, needs pid/port metadata handoff and has no true `execv` on Windows, a new supervision mechanism. (C) Collect each snapshot in a fresh subprocess: always current, but spawns a process every poll, which is slow on Windows and heavy for a 5s loop. |
| 2026-10-26 | Readiness repair (red-team F1, F2, F5): check at request time with an uncached `ensure_runtime_current()`, no stat-signature cache, no `server_impl` reuse. | Red-team probe counted `ensure_runtime_current` calls from existing dashboard reads at 3, 5, 7 over three cycles (`graph_snapshot._read_pinned` via `check_connection`, and the `index_state_store` re-exec), so a cache saves nothing and the old AC-3 was unmeetable. Collection stalls keep the last good snapshot (`SnapshotStore._watch_loop`), so a field computed inside collection could be hidden; request time avoids that. New review surface: the request-time call. | Keep the stat-signature cache (saves nothing); derive the flag from 21s79's diagnostics (hidden by stalls, and couples the changes). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Importing `wf_server` helpers into the dashboard pulls in heavy modules. | The dashboard already calls `server.index_build_status_response`; if reuse is heavy, factor the small helper into a module both import. |
| Notice fatigue in this repository, where framework edits are frequent. | That is the true state; the notice clears on restart and never blocks the UI. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
