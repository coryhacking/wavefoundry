# Dashboard Start Hides the Child's Startup Failure

Change ID: `21ilg-bug dashboard-start-hides-child-startup-failure`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-24

## Rationale

A downstream distribution's `DashboardManagedIdentityTests.test_mcp_start_confirms_serving_own_child` failed with only `dashboard_child_exited`. They captured the child's output in their own driver and found the cause:

```
RuntimeError: No free dashboard port available on 127.0.0.1 in configured range 43127-43129.
```

Leftover dashboards from an earlier sandboxed run held all three ports. Two defects on our side made this hard to see:

1. **The reason is lost.** `wf_start_dashboard_response` (`wf_server/dashboard_handlers.py`) spawns the child with stdin, stdout and stderr on `DEVNULL`. On Windows it also passes `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`. The child does have a persistent log, `_dashboard_log` writing to `.wavefoundry/logs/dashboard.log`, set up in `dashboard_server.main` before startup. But `choose_port`'s `RuntimeError` and a bind `OSError` are uncaught: they go only to the discarded stderr, never to the log. So the start response cannot say why the child exited.
2. **The test uses the real default range.** The test fixture `_make_repo` pins the dashboard range to 43127-43129, the same as a real dashboard. The test calls `wf_start_dashboard_response(self.root)` without a port, so any dashboard already running on the machine makes it fail. That includes a developer's own dashboard or a leftover.

Investigating also found a latent defect. When `main` is given `--port 0`, it records and prints a URL ending `:0/`, because it uses the requested port rather than the bound one. Today only the daemon tests use port 0, and they read the metadata pid, not the URL.

## Product Intent

Operators and maintainers see why a dashboard failed to start, and the suite stops failing on machines that already run a dashboard.

- **Before:** `wf_start_dashboard_response` reports only `dashboard_child_exited`, and the identity test fails whenever ports 43127-43129 are busy.
- **After:** the response names the child's startup error (for example, no free port in the configured range), and the test binds an ephemeral port.

**Boundaries:** the child's spawn stays exactly as it is on every platform, with all-DEVNULL stdio and the Windows detach and no-window flags. No pipe is added, and the dashboard's normal serving behaviour does not change.

## Requirements

1. `dashboard_server.main` wraps its whole pre-serve section, from acquiring `server_lock` up to `serve_forever`, in `except Exception`. That covers `choose_port`'s `RuntimeError`, a bind `OSError` (including Windows `WSAEADDRINUSE` and `WSAEACCES`), the metadata write and the `SnapshotStore` start. On failure it writes one line through `_dashboard_log`: `startup failed: <ExceptionType>: <message>`. It then releases `server_lock` explicitly and returns 1, with no traceback. The lock-busy return stays as today: that case is "already running", not a failure. Failures before `main` runs, such as an import or venv-activation error, cannot reach the log; that residual is stated, not fixed.
2. `wf_start_dashboard_response` records the size of `.wavefoundry/logs/dashboard.log` before it spawns the child. If the child exits before serving, it reads the log from that offset, bounded to the last 8 KiB and decoded as UTF-8 with replacement. It splits the text with `splitlines()`, so a Windows CRLF leaves no stray `\r`. It takes the last line that starts with `[dashboard] ` and contains ` - startup failed: `, which is the child's own format. It caps that line at 500 characters and appends it, as data, to the `dashboard_child_exited` message. If the log shrank, which happens only by manual truncation since nothing rotates it, it reads from the start.
   - When there is no such line, or the log cannot be read, the message stays as today.
   - The read happens only after the child has exited, so no file is held open across processes.
3. The spawn kwargs are unchanged: stdin, stdout and stderr stay `DEVNULL`, and on Windows the creation flags stay `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` plus no-window.
   - **Why no pipe:** a pipe to a long-lived detached child can fill and block the child, or leave an inherited handle that keeps the parent waiting on Windows. Wave 2134v fixed that class.
   - **Log access:** the child's log writes open, append and close per line, so the parent's read after exit meets no sharing conflict on Windows.
4. `main` records and prints the port the server actually bound, `httpd.server_address[1]`, so `--port 0` advertises a real URL.
5. `test_mcp_start_confirms_serving_own_child` starts the dashboard with `port=0`, so a dashboard on the default range cannot fail it.
6. Platforms:
   - Windows, macOS, Linux and WSL2 keep the same spawn and get the same log read.
   - The log path is built from the repository root with `pathlib`.
   - No existing test pins the dashboard-start spawn kwargs. The DEVNULL and creationflags pins in `test_server_tools.py` cover `_mcp_subprocess_run` and the background index refresh, and `test_dashboard_server.py` pins only `_daemonize`. AC-2 is therefore the pin for this spawn.

## Scope

**Problem statement:** dashboard start loses the child's startup error, the identity test depends on a free default port range, and `--port 0` advertises a wrong URL.

**In scope:**

- `dashboard_server.main` startup-failure logging and bound-port recording.
- The `wf_start_dashboard_response` log read on child exit.
- The identity test's port.
- New tests.

**Out of scope:**

- Changing the spawn stdio or creation flags.
- Reaping leftover dashboards from other repositories.
- Changing the shipped default port range.

## Acceptance Criteria

- [x] AC-1: The test binds a listener to exactly `127.0.0.1:0`, the configured host, so the child's bind collides on Windows as on POSIX. It keeps that socket open and sets `preferred_port`, `port_range_start` and `port_range_end` all to the held port, with no recorded metadata port. Then it calls `wf_start_dashboard_response` with the real child. The result is `dashboard_child_exited`, and its message contains `No free dashboard port available`. Known-bad: before the change the message is only `Dashboard child exited before serving.`
- [x] AC-2: A test pins the dashboard-start spawn kwargs with `Popen` mocked: stdin, stdout and stderr are `subprocess.DEVNULL`. Windows is simulated by patching the handler module's `os` (a `SimpleNamespace(name='nt')`, as the existing taskkill test does) rather than the global `os.name`, with the `subprocess` constants patched `create=True` and `_windows_no_window_flag` stubbed. Under that simulation the creation flags include `DETACHED_PROCESS` and `CREATE_NEW_PROCESS_GROUP`; on POSIX `start_new_session` is set. It fails if the change adds a pipe or a file handle to the spawn.
- [x] AC-3: `main(['--root', ..., '--port', '0'])` records metadata whose `port` field and URL port both equal the bound port, which is not 0. The test patches `serve_forever` or runs `main` on a thread with shutdown. Known-bad: today `port` is 0 and the URL ends `:0/`. A failure test also covers the broad catch: an exception raised inside the pre-serve section logs the `startup failed:` line, releases `server_lock` (a second acquire succeeds) and returns 1.
- [x] AC-4: `test_mcp_start_confirms_serving_own_child` passes while 43127, 43128 and 43129 on `127.0.0.1` are taken. The test binds them itself inside try/finally, counting an `EADDRINUSE` (another dashboard already holding a port) as taken. Known-bad: today it fails with `dashboard_child_exited`.
- [x] AC-5: The log read is bounded and tolerant. A test covers a missing log, a log that shrank, a log over 8 KiB, and non-UTF-8 bytes; each yields either the plain message or the last `startup failed:` line, and never an exception.
- [x] AC-6: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Catch startup failures in `dashboard_server.main`, log the `startup failed:` line, and record the bound port.
- [x] Read the log tail on child exit in `wf_start_dashboard_response`.
- [x] Give the identity test `port=0`; add the AC-1 to AC-5 tests.
- [x] CHANGELOG Unreleased entry (Fixed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| dashboard  | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/dashboard_server.py`, `.wavefoundry/framework/scripts/wf_server/dashboard_handlers.py`, `.wavefoundry/framework/scripts/tests/test_dashboard_server.py`

## Affected Architecture Docs

N/A: dashboard start diagnostics and a test port; no boundary, flow or verification-topology change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | the reported missing reason |
| AC-2 | required  | the Windows-safe spawn must not change |
| AC-3 | important | the latent `--port 0` URL defect the test fix depends on |
| AC-4 | required  | the reported test failure |
| AC-5 | important | the read must never break start |
| AC-6 | required  | change-local suites and docs |


## Progress Log


| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-10-24 | Planned | Waveforge dashboard follow-up (child traceback: no free port in 43127-43129); `dashboard_handlers.wf_start_dashboard_response` spawn kwargs, `dashboard_server.main` and `choose_port` read |
| 2026-10-24 | Readiness round 1 amendments. From red-team's strongest challenge: the catch widened to the whole pre-serve section, with an explicit lock release; the residual import-time failures are stated. From security: exact line format, 500-character cap, line treated as data. From qa and code: AC-1 sets `preferred_port` and the range to a held `127.0.0.1` port with no metadata port; AC-2 simulates Windows on the handler module's `os`, with `create=True` constants; AC-3 also checks the metadata `port` and the catch's lock release; AC-4 holds ports in try/finally and accepts `EADDRINUSE`. Requirement 6's claim of existing spawn pins was corrected: none exist. The leaked dashboards came from cleanup that Waveforge's sandbox could not complete, which is out of scope. | readiness red-team, security, qa, code |
| 2026-10-24 | Readiness round 2 clarifications (Progress Log only; they bind the implementation). AC-3's lock-release oracle: spy on the server lock's release, i.e. `__exit__`, and assert it ran before `main` returned. A second in-process acquire cannot fail: CPython finalizes the generator on return, and macOS `lockf` is per-process. AC-3's in-process test restores `_LOG_ROOT` and stops any `SnapshotStore` it started. AC-4 counts any `OSError` from binding a held port as taken, because Windows reports `WSAEADDRINUSE` (10048) or `WSAEACCES` for excluded ranges, not `errno.EADDRINUSE`. AC-4's known-bad is today's test failing with `dashboard_child_exited`; with `port=0` but without the bound-port fix the result is `url_not_ready`, so AC-3 and AC-4 depend on each other. AC-2's faked `os` lacks `kill` and `waitpid`, so the test stubs `_dashboard_cmdline_pids`, `_dashboard_already_serving` and `_terminate_dashboard_pid`. Implementation: the `try` opens after the lock is acquired and returns before the serve `try/finally`, and a post-bind failure closes `httpd`. | readiness qa-reviewer and code-reviewer recheck |
| 2026-10-24 | Readback: `dashboard_server.main` guards its pre-serve section (after the lock acquire, before the serve try/finally) with `except Exception`, logs `startup failed: <Type>: <msg>`, closes `httpd` if bound, releases the lock and returns 1; it records `httpd.server_address[1]` as the port. `wf_start_dashboard_response` records the log size before an unchanged all-DEVNULL detached spawn and, on child exit, appends the last `[dashboard] ... - startup failed:` line (bounded, capped, read with `Path` methods) to the message. Tests: AC-1 real child with a held port, AC-2 spawn pin with POSIX and simulated Windows, AC-3 bound port plus the failure path's lock release, AC-4 identity test on `port=0` with 43127-43129 held, AC-5 log-read edges. Files: `dashboard_server.py`, `wf_server/dashboard_handlers.py`, `tests/test_dashboard_server.py`, CHANGELOG. Before: `dashboard_child_exited` with no reason; after: the same code with the no-free-port line. | implementation |
| 2026-10-24 | Implemented. `dashboard_server.main` guards the pre-serve section and records `httpd.server_address[1]`; `wf_start_dashboard_response` reads the log tail after the child exits through `_dashboard_log_size` and `_startup_failure_line`, using `Path` methods only. The spawn kwargs are unchanged. Tests: `test_mcp_start_reports_the_child_startup_failure` (AC-1), `DashboardStartSpawnTests` (AC-2), `DashboardMainStartupTests` (AC-3), `test_mcp_start_confirms_serving_own_child` on `port=0` with 43127-43129 held (AC-4), and `StartupFailureLineTests` (AC-5). `test_dashboard_server.py`: 239 OK on 3.14, 239 OK (1 skip) on 3.11. Known-bad: with the committed product code the 10 behaviour tests fail (3 failures, 7 errors); a stderr-PIPE mutant fails both spawn pins. | implementation |
| 2026-10-24 | Delivery repair RED-DEL-1 (red-team; code-reviewer and qa-reviewer test-strength notes folded in). A lock acquire that fails for a reason other than busy now logs `startup failed:` and returns 1. On the failure path the lock release sits in a `finally`, so a failing `server_close` cannot skip it. Tests: the Windows pin asserts the exact creation flags, including no-window; the failure test injects a `ValueError` and asserts `server_close` ran; a new test covers the unacquirable lock. `test_dashboard_server.py` 240 OK. The full suite before the repair: 12111 tests OK. | delivery review |
| 2026-10-24 | Delivery complete. RED-DEL-1 reverified by a distinct code-reviewer context; code-reviewer and qa-reviewer approvals post-date the repair; delivery Wave Council PASS. Final full suite (`run_tests.py --no-cache`): 12113 tests OK. | delivery review |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-24 | Keep the all-DEVNULL detached spawn; surface the reason through the existing `dashboard.log` | The child already persists `_dashboard_log` lines there; reading after exit needs no new handle, pipe or inheritance on Windows | Pipe stderr (can block a long-lived child and keeps an inherited handle on Windows); redirect stderr to a new file handle in the spawn (an inherited handle the 2134v class warns about) |
| 2026-10-24 | Fix the identity test with `port=0` and record the bound port | Port 0 removes the dependency on any machine port; the bound-port fix makes the advertised URL real | A non-default fixed range (still collides with anything else on that range) |
| 2026-10-24 | Mechanism efficacy | Replay: Waveforge's run would report "No free dashboard port available on 127.0.0.1 in configured range 43127-43129" in the start response, and the test would bind an ephemeral port. Control: the start response carries the line directly. Wrong flags: an unrelated earlier `startup failed:` line could be shown; reading only bytes appended after the spawn rules that out. Cheaper path: none smaller. Measure: the next distribution report shows no unexplained `dashboard_child_exited`. | — |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Two dashboards for the same repository append to the log concurrently | The read takes only bytes appended after this spawn, and only after this child exited; the line is a diagnostic hint, never a decision |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
