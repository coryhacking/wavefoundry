# Windows os.kill regression: unguarded liveness probe in upgrade dashboard detection

Change ID: `1p9hi-bug windows-oskill-liveness-regression`
Change Status: `implemented`
Owner: implementer
Status: implemented
Last verified: 2026-07-02
Wave: 1p9hn windows-portability-round-2

## Rationale

`upgrade_wavefoundry.py:192` in `_detect_dashboard` uses a bare `os.kill(pid, 0)` with no `os.name != 'nt'` branch. On Windows, `signal.CTRL_C_EVENT == 0`, so `os.kill(pid, 0)` routes to `GenerateConsoleCtrlEvent(0, pid)` — not a liveness probe. This either raises `OSError` (swallowed by the `except` block → dashboard mis-reported absent → upgrade never pauses it) or fires a spurious Ctrl+C event.

Waves 1p6d6/1p654 migrated three sibling liveness sites to use `upgrade_lib._pid_is_running` (which branches on `os.name=='nt'` and uses `tasklist`). This fourth site was missed. `upgrade_lib` is already imported at the call sites (`:951` and `:1082`), so the correct helper is in scope.

A companion test (`test_upgrade_wavefoundry.py:3278`, `test_scan_unavailable_falls_back_to_oskill`) patches `dashboard_cmdline_pids → None` to simulate the Windows / ps-error fallback, then asserts liveness using `os.getpid()` on the dev host — which only exercises POSIX signal-0 semantics. The test passes on macOS/Linux CI but never validates the Windows-hostile branch.

## Requirements

1. Replace `os.kill(pid, 0)` at `upgrade_wavefoundry.py:191–195` with `upgrade_lib._pid_is_running(pid)` and return `True, pid, url` when it returns `True`.
2. The `except (ProcessLookupError, OSError): pass` block that followed the `os.kill` must be removed or restructured so failure falls through to `return False, None, None` as before.
3. `test_scan_unavailable_falls_back_to_oskill` must be updated: patch `upgrade_lib._pid_is_running` instead of relying on ambient `os.kill`, and assert the correct return value for both the live-PID and dead-PID cases without depending on POSIX signal semantics.
4. POSIX behavior must be unchanged: `_pid_is_running` already uses `os.kill(pid, 0)` on POSIX, so the POSIX path is preserved transparently.

## Scope

**Problem statement:** The upgrade dashboard-liveness probe uses a POSIX-only signal-0 trick that silently misbehaves on Windows, causing the upgrade to mis-report a running dashboard as absent and skip the pause step. One companion test masks this by only exercising the POSIX path.

**In scope:**

- One-line production fix at `upgrade_wavefoundry.py:191–195`
- Update `test_scan_unavailable_falls_back_to_oskill` to assert the correct behavior via `_pid_is_running`

**Out of scope:**

- The other three sibling liveness sites (already using `_pid_is_running`, confirmed correct)
- Changes to `upgrade_lib._pid_is_running` itself (it is already correct)

## Acceptance Criteria

- [x] AC-1: `upgrade_wavefoundry.py:191–195` no longer calls `os.kill`; it calls `upgrade_lib._pid_is_running(pid)` instead (local `import upgrade_lib`, same pattern as the module's other `upgrade_lib` uses)
- [x] AC-2: `_detect_dashboard` returns `True, pid, url` when `_pid_is_running` returns `True`, and `False, None, None` when it returns `False` — asserted by both branches of the rewritten test
- [x] AC-3: The test (renamed `test_scan_unavailable_falls_back_to_pid_liveness_helper`) patches `upgrade_lib._pid_is_running` and asserts both the live and dead PID cases without relying on `os.kill` or `os.getpid()`
- [x] AC-4: All existing upgrade tests pass — `DetectDashboardLivenessTests` (3 tests) green

## Tasks

- [x] Replace `os.kill(pid, 0)` at `upgrade_wavefoundry.py:191–195` with `upgrade_lib._pid_is_running(pid)` call
- [x] Update `test_upgrade_wavefoundry.py:3278` (renamed to `test_scan_unavailable_falls_back_to_pid_liveness_helper`) to patch `_pid_is_running` and assert both branches

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| fix-oskill | implementer | — | Single-site change in upgrade_wavefoundry.py |
| fix-test | implementer | fix-oskill | Update test to match new implementation |

## Serialization Points

- None. Both workstreams touch different files.

## Affected Architecture Docs

N/A — confined to a single function in `upgrade_wavefoundry.py` and its companion test. No boundary or flow change.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Removes the Windows-hostile os.kill call |
| AC-2 | required | Preserves the return contract of _detect_dashboard |
| AC-3 | required | Closes the test gap that masks the regression |
| AC-4 | required | Non-regression |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-07-02 | Change doc created from 10-dimension Windows audit | audit workflow wf_51bd40fe-082 |
| 2026-07-02 | Implemented: os.kill(pid,0) → upgrade_lib._pid_is_running(pid) in _detect_dashboard; masking test rewritten to assert both branches via patched helper | `DetectDashboardLivenessTests` 3/3 green |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-07-02 | Reuse existing `upgrade_lib._pid_is_running` rather than inlining a Windows branch | Keeps logic in one place; the helper is already in scope at both call sites | Inline os.name check (more code, more drift risk) |

## Risks

| Risk | Mitigation |
| --- | --- |
| `_pid_is_running` has different timeout behavior than os.kill | `_pid_is_running` already used at 3 other upgrade sites without issue; verified correct |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
