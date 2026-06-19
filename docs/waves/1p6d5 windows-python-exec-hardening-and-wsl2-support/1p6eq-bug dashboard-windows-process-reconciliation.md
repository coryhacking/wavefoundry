# Windows dashboard process reconciliation (complete the liveness story)

Change ID: `1p6eq-bug dashboard-windows-process-reconciliation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-18
Wave: `1p6d5 windows-python-exec-hardening-and-wsl2-support`

## Rationale

The Windows-compat audit's **M-1**: `dashboard_lib.dashboard_cmdline_pids` (the cmdline-scan that powers the `1p654` dashboard orphan-reconciliation) does `if os.name == "nt": return None` (`dashboard_lib.py:244-245`) — so on native Windows the reconciliation falls back to bare recorded-PID liveness, and orphaned dashboards from drifted/removed metadata re-accumulate (the exact failure the `1p654` cmdline scan was built to prevent).

`1p6d6` fixed the related `_pid_is_running` liveness check on Windows but did **not** touch `dashboard_lib` (out of its stated file scope), leaving the Windows liveness/reconciliation story half-done. This change completes it: give `dashboard_cmdline_pids` a Windows cmdline scan so the orphan reconciliation works on native Windows too.

Forward-compat (native Windows is Area-1/not-yet-running) and POSIX/WSL2-unchanged. The one wrinkle: Windows has **no lightweight built-in** that lists full command lines — `tasklist` only gives image name + PID. The only built-in that exposes `CommandLine` is PowerShell + CIM (`Get-CimInstance Win32_Process`). So the `nt` branch shells out to PowerShell, best-effort: **any failure returns `None`** so the caller falls back to bare-PID liveness exactly as today (no regression). Its correctness on a real Windows host is **unverified here** (no Windows box) and is Windows-smoke-deferred with the rest of the wave's `nt` branches.

## Requirements

1. **Windows cmdline scan.** `dashboard_cmdline_pids` must, on `nt`, list `dashboard_server.py --root <root>` PIDs by full command line (so the `1p654` reconciliation works), instead of returning `None`. Use PowerShell + `Get-CimInstance Win32_Process` (the only built-in exposing `CommandLine`), filtered to `dashboard_server.py`.
2. **Reuse the POSIX matching loop.** The `nt` branch must produce the same `<pid> <command line>` line format the existing POSIX `ps` path produces, then fall through to the **existing** shared root-matching loop (which tokenizes `--root`, resolves it against the target, and excludes the current PID). No duplicated matching logic.
3. **Best-effort, no regression.** Any failure (PowerShell absent, non-zero exit, timeout, parse miss) returns `None` → the caller falls back to bare recorded-PID liveness, identical to today's Windows behavior. POSIX/WSL2 path byte-identical.
4. **Honest verification boundary.** The `nt` scan is unverified on a real Windows host; mark it Windows-smoke-deferred (consistent with `1p6d6`/`1p6dx`). Unit tests mock the PowerShell output to prove the parse/match, and assert POSIX is unchanged.

## Scope

**Problem statement:** Windows dashboard orphan reconciliation (`1p654`) is disabled because `dashboard_cmdline_pids` returns `None` on `nt`.

**In scope:** the `nt` branch of `dashboard_cmdline_pids` in `dashboard_lib.py` + a small `_windows_process_cmdlines` helper; unit tests (mocked PowerShell output + POSIX-unchanged); no change to the shared matching loop or any caller.

**Out of scope:**

- End-to-end native-Windows verification (needs Area-1 + a Windows host) — Windows-smoke-deferred.
- Any change to the POSIX `ps` path or to callers (`server_impl` lifecycle, upgrade detection).
- A non-PowerShell Windows mechanism (WMIC is deprecated/removed on recent Windows; not worth a second path).

## Acceptance Criteria

- [x] AC-1: on `nt`, `dashboard_cmdline_pids` now calls `_windows_process_cmdlines()` (PowerShell + `Get-CimInstance Win32_Process`) and feeds its `<pid> <cmdline>` output to the **existing shared matching loop** (same `--root` resolution + current-PID exclusion). **Test note:** the helper is unit-tested directly (`test_windows_process_cmdlines_helper` — argv is `powershell … Get-CimInstance Win32_Process`, returns stdout on rc 0); the parse/match is covered by the POSIX `test_cmdline_scan_parses_and_matches_root` (same loop). The full nt end-to-end (selection + match under `os.name='nt'`) can't run on a POSIX host — the loop's `Path(...).resolve()` instantiates `WindowsPath` — so it's Windows-smoke-deferred (same boundary as `1p6d6`).
- [x] AC-2: any `nt` scan failure (exception, non-zero exit) returns `None` → caller falls back to bare-PID liveness. Tested (`test_cmdline_scan_windows_returns_none_on_failure` via the nt branch + the helper's rc≠0 / OSError cases).
- [x] AC-3: POSIX path byte-identical (still `ps`); the shared matching loop is untouched and serves both — only an additive `nt` branch + a new helper were added. Existing POSIX `test_cmdline_scan_parses_and_matches_root` still green.
- [x] AC-4: **No POSIX/WSL2 regression** — full framework suite green (**3328**, +2); the testable nt parts (helper + failure→None) covered; full nt match Windows-smoke-deferred (pathlib `WindowsPath` constraint), documented.

## Tasks

- [x] Added `_windows_process_cmdlines()` — best-effort PowerShell + `Get-CimInstance Win32_Process` (filtered to `dashboard_server.py`), `timeout=10`, returns stdout on rc 0 else `None`.
- [x] Refactored `dashboard_cmdline_pids`: `nt` branch sets `out` from the helper (was `return None`); POSIX branch unchanged; both fall through to the existing matching loop; docstring updated.
- [x] Tests: `test_windows_process_cmdlines_helper` (argv + stdout/None) + `test_cmdline_scan_windows_returns_none_on_failure` (nt branch fallback); POSIX `test_cmdline_scan_parses_and_matches_root` unchanged. Full nt match is Path-flavour-blocked → Windows-smoke-deferred (documented).

## Affected Architecture Docs

`N/A` — single-function Windows branch in `dashboard_lib`; no boundary/flow/verification-contract change. (Updates `docs/references/native-windows-support.md` M-1 status as resolved-in-execution / Windows-verification-deferred.)

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The fix itself — Windows reconciliation works. |
| AC-2 | required | Graceful fallback is the no-regression guarantee. |
| AC-3 | required | POSIX byte-identical (the wave's load-bearing gate). |
| AC-4 | required | No POSIX/WSL2 regression; honest Windows-deferred verification. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-18 | Pulled in from audit M-1 (operator-directed) to complete the Windows liveness/reconciliation story `1p6d6` started. `1p6d6` fixed `_pid_is_running` but not `dashboard_cmdline_pids` (different file). | `dashboard_lib.py:244-245` (`return None` on nt); `1p6d6` `_pid_is_running` |
| 2026-06-18 | Implemented. Added `_windows_process_cmdlines()` (PowerShell/CIM, timeout 10, rc-gated, filtered to dashboard_server.py); `nt` branch now feeds the shared matching loop; POSIX `ps` path + matching loop unchanged. Helper + nt-fallback unit-tested; full nt match Path-flavour-blocked → Windows-smoke-deferred. | `dashboard_lib.py` (`_windows_process_cmdlines`, refactored `dashboard_cmdline_pids`); +2 tests; full suite 3328 green |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-18 | Pull M-1 into `1p6d5` now rather than leaving it in Bucket 3. | Operator-directed; same theme as `1p6d6`'s liveness fix; small, forward-compat, POSIX-neutral; leaving a known half-fix (liveness fixed, reconciliation not) is a footgun. | Leave bucketed for the Windows-smoke wave (rejected per operator). |
| 2026-06-18 | Use PowerShell + `Get-CimInstance Win32_Process` for the cmdline scan. | The only Windows built-in exposing full `CommandLine`; `tasklist` lacks it. | WMIC (rejected — deprecated/removed on recent Windows); a second native path (rejected — scope). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| PowerShell invocation/parse is wrong on a real Windows host (unverifiable here). | Best-effort: any failure → `None` → bare-PID liveness (today's behavior); no regression. Windows-smoke-deferred verification, flagged honestly. |
| The `nt` branch accidentally changes POSIX behavior. | `nt` branch is additive; POSIX still uses `ps`; the shared matching loop is untouched; full suite on macOS/Linux. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
