# Windows console-window suppression

Change ID: `1p88t-enh windows-console-window-suppression`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p88t windows-mcp-host-hardening`

## Rationale

During native-Windows testing, a blank Python console window appeared while the Wavefoundry MCP server was running and disappeared when Claude Code shut down. Other Python MCP tools reportedly do not show the same window, so Wavefoundry should not assume this is unavoidable.

There are two plausible sources. First, Wavefoundry may be spawning a helper child process without a no-window creation flag. Second, the visible window may be the main host-launched MCP process, which cannot be hidden from inside `server.py` after process creation. This change first eliminates the controllable child-process source; if the window remains, it records evidence for a future no-console MCP launcher strategy.

## Requirements

1. Add Windows `CREATE_NO_WINDOW` to Wavefoundry-spawned helper subprocesses that do not need an interactive console, including synchronous validation/garden/render/upgrade helpers and detached background jobs where compatible.
2. Keep `DETACHED_PROCESS` / `CREATE_NEW_PROCESS_GROUP` behavior for truly detached background jobs where lifecycle independence is required; combine with no-window flags only when safe.
3. Add tests that simulate Windows and assert no-window flags on affected helper paths.
4. Document the boundary: Wavefoundry can hide its own child processes, but the main MCP server window is controlled by the MCP host unless Wavefoundry ships a no-console launcher.
5. If evidence indicates the main MCP process is the window, record a follow-up design option for a tiny no-console launcher executable or host-specific guidance.

## Scope

**Problem statement:** native-Windows MCP use shows a blank console window, reducing confidence and polish.

**In scope:**

- Wavefoundry-spawned subprocess creation flags.
- Tests for no-window flags.
- Native Windows support notes and changelog.
- Evidence collection to distinguish child-process windows from the main MCP process.

**Out of scope:**

- Using `pythonw.exe` for MCP stdio.
- Replacing stdio transport.
- Building a native launcher executable in this wave unless the child-process fix proves insufficient and the operator explicitly expands scope.

## Acceptance Criteria

- [x] AC-1: all MCP-reachable Wavefoundry-spawned helper subprocesses isolate stdio and suppress the console window on Windows. The bounded helpers route through the shared `_mcp_subprocess_run` (docs-lint, gardener, sync-surfaces, upgrade phases, sensors, **and the git-audit probes** — `_audit_commit_governance` / `_audit_harnessability`, converted post-review); detached background jobs are window-free via `DETACHED_PROCESS`. The remaining direct probes are isolated inline — `tasklist` (`server_impl._pid_is_running`), `nvidia-smi` (`provider_policy.nvidia_gpu_present`), `ldconfig`, and the dashboard PowerShell/`ps` cmdline scans (`dashboard_lib`) now pass `stdin=subprocess.DEVNULL` and `CREATE_NO_WINDOW` (via a module-local guard). A breadth source-scan test (`test_no_raw_subprocess_in_server_impl_lacks_stdin_isolation`) plus behavioral tests (`_pid_is_running`, nvidia-smi, PowerShell) prevent regressions, including the aliased `_sp.run` / `__import__("subprocess").run` forms that evaded the first review.
- [x] AC-2: detached background jobs preserve required lifecycle behavior while suppressing visible windows when safe.
- [x] AC-3: tests cover Windows flag construction for synchronous helpers and detached helpers.
- [x] AC-4: native-Windows docs explain what Wavefoundry suppresses and what remains controlled by the MCP host. Added the **Console windows (native Windows)** section to `docs/references/native-windows-support.md` and a CHANGELOG `[Unreleased]` entry (post-review).
- [~] AC-5: if the blank MCP-window field report persists after child-process suppression, a follow-up launcher decision is recorded with evidence. Status: intentionally deferred until the downstream native-Windows tester reruns after this child-process suppression build; no persistence evidence exists yet.
- [x] AC-6: full framework suite and docs-lint pass.

## Tasks

- [x] Inventory all `Popen` and server-side `subprocess.run` calls for Windows console behavior.
- [x] Add no-window flags through the shared helper from `mcp-subprocess-isolation` where possible.
- [x] Patch detached background spawns that still construct flags locally.
- [x] Add tests for flag combinations.
- [x] Update native-Windows support docs and changelog.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Audit | implementer | — | Classify child vs main process. |
| Helper integration | implementer | mcp-subprocess-isolation | Reuse shared subprocess policy where possible. |
| Detached spawns | implementer | Audit | Preserve detach semantics. |
| Docs/evidence | docs-contract-reviewer | implementation | Record boundary and follow-up if needed. |

## Serialization Points

- Coordinate with `mcp-subprocess-isolation`; both changes touch subprocess helpers and Windows creation flags.

## Affected Architecture Docs

`docs/references/native-windows-support.md`; architecture docs likely `N/A` unless a new launcher artifact is introduced.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Eliminates controllable window sources. |
| AC-2 | required | Avoids regressing background process lifecycle. |
| AC-3 | required | Windows behavior must be test-covered off Windows. |
| AC-4 | important | Sets operator expectations. |
| AC-5 | important | Captures evidence if main host process is responsible. |
| AC-6 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from native-Windows MCP field report. | Blank Python console appears while Wavefoundry MCP is active and disappears when Claude shuts down. |
| 2026-06-27 | Implemented child-process console suppression. | MCP helper subprocesses and detached Wavefoundry child spawns use `CREATE_NO_WINDOW` on Windows where available; full suite 3510 tests OK; docs-lint OK. |
| 2026-06-27 | Post-review: AC-4 docs added; AC-1 scope made honest. | Added the **Console windows (native Windows)** boundary section to `native-windows-support.md` + CHANGELOG `[Unreleased]`. AC-1 reworded to reflect the real surface (shared-helper sync subprocesses + `DETACHED_PROCESS` background jobs) and to record the bounded residual MCP-reachable probes (`tasklist`, `git log`/`git grep`, dashboard PowerShell/`ps`, `nvidia-smi`) still to be routed through the helper. Full suite 3521 tests OK. |
| 2026-06-27 | Residual resolved — all MCP-reachable probes isolated. | Routed the git audits through `_mcp_subprocess_run`; isolated `tasklist`, `nvidia-smi`, `ldconfig`, and the dashboard PowerShell/`ps` scans inline (`stdin=DEVNULL` + `CREATE_NO_WINDOW`). Added a breadth source-scan guard (catches aliased `_sp.run`/`__import__` forms) + behavioral tests. AC-1 now genuinely "all". |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | First suppress Wavefoundry child-process windows; treat main MCP window as separate evidence-gated follow-up. | Child processes are under Wavefoundry control; main process creation is host-owned. | Switch to `pythonw.exe` immediately (rejected: stdio risk); build launcher immediately (deferred pending evidence). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `CREATE_NO_WINDOW` combined with detach flags behaves differently across Python/Windows versions. | Unit-test flag composition; preserve existing detach flags; field-test native Windows before release. |
| Window is the main MCP server process, not a child. | AC-5 records evidence and follow-up; do not over-claim fix. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
