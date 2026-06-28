# MCP subprocess isolation

Change ID: `1p88t-enh mcp-subprocess-isolation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-27
Wave: `1p88t windows-mcp-host-hardening`

## Rationale

Native-Windows testing showed `wave_validate` / MCP docs-lint timing out at 30 seconds while the same docs-lint command completed in about 6 seconds from a terminal. The operator's downstream test found the subprocess became reliable when launched with stdio redirected to `DEVNULL`. That points at a subprocess isolation defect: helper processes launched from the MCP server must not inherit or contend with the JSON-RPC stdio streams.

The current `run_validate` captures stdout/stderr but does not explicitly close/redirect stdin. In an MCP stdio server, inherited stdin is the JSON-RPC input stream. Even a child that only accidentally probes stdin can disrupt or block the transport.

## Requirements

1. Add a shared helper for server-side subprocess calls that sets `stdin=subprocess.DEVNULL` by default.
2. The helper must require intentional stdout/stderr behavior: capture text output, redirect to a log file, or redirect to `DEVNULL`; never inherit the MCP server's stdout/stderr implicitly.
3. On Windows, the helper adds `CREATE_NO_WINDOW` for synchronous helper subprocesses where no visible console is intended.
4. Apply the helper to MCP/server-side docs-lint, docs-gardener, render/sync surfaces, upgrade phases, lifecycle sensors, install audit helpers, and other bounded subprocess calls where output is consumed by the tool response.
5. Preserve behavior for intentionally detached/background jobs that already redirect output and record logs, while adding no-window flags where appropriate.

## Scope

**Problem statement:** MCP helper subprocesses can inherit MCP stdio streams and behave differently from terminal execution, causing timeouts or visible process artifacts.

**In scope:**

- Subprocess hygiene inside `server_impl.py` and other MCP/server-side helpers.
- Tests proving `stdin=DEVNULL` and no-window flags are applied.
- Minimal docs/changelog note.

**Out of scope:**

- Changing the MCP transport away from stdio.
- Changing docs-lint algorithm or timeout duration unless evidence shows it is still needed after isolation.
- Main MCP server launch window; tracked separately in `windows-console-window-suppression`.

## Acceptance Criteria

- [x] AC-1: `run_validate`, `run_garden`, and `run_sync_surfaces` use a shared subprocess helper that passes `stdin=DEVNULL` and intentional stdout/stderr handling.
- [x] AC-2: all MCP-reachable subprocess paths isolate stdin from the JSON-RPC stream. The upgrade/sensor paths and the git-audit probes (`_audit_commit_governance` git log, `_audit_harnessability` git grep — converted post-review) route through `_mcp_subprocess_run`; the remaining direct probes (`tasklist`, `nvidia-smi`, `ldconfig`, dashboard PowerShell/`ps`, and the in-process secrets-scan fallback's 8 git probes in `wave_lint_lib/secrets_validators.py` reached via `wave_scan_secrets`) pass `stdin=subprocess.DEVNULL` (the `git check-ignore` probe feeds stdin via `input=`). A breadth source-scan test enforces this for **both** `server_impl.py` **and** `secrets_validators.py` — every `subprocess.run`/`Popen`, including the aliased `_sp.run` / `__import__("subprocess").run` forms that evaded the first review.
- [x] AC-3: Windows helper subprocesses that do not need a console include `CREATE_NO_WINDOW`; tests cover the flag without requiring Windows.
- [x] AC-4: timeout behavior is unchanged or improved; docs-lint failures still return bounded structured diagnostics.
- [x] AC-5: full framework suite and docs-lint pass.

## Tasks

- [x] Inventory MCP/server-side `subprocess.run` and `Popen` call sites.
- [x] Add a shared subprocess helper with stdin/stdout/stderr/no-window policy.
- [x] Migrate validation/gardening/sync/upgrade/sensor call sites.
- [x] Add tests for stdin isolation and Windows no-window flags.
- [x] Run full suite and docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| Audit | implementer | — | Enumerate call sites and classify output policy. |
| Helper | implementer | Audit | Centralize subprocess defaults. |
| Migration | implementer | Helper | Update call sites incrementally. |
| QA | qa-reviewer | Migration | Regression and Windows-flag tests. |

## Serialization Points

- `server_impl.py` subprocess helper and tests should be updated before migrating scattered call sites to avoid inconsistent policy.

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` may need a short note if a shared subprocess policy is introduced; otherwise `N/A` with rationale.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Directly addresses docs-lint timeout feedback. |
| AC-2 | required | Prevents the same defect on sibling MCP subprocesses. |
| AC-3 | important | Reduces Windows console artifacts from children. |
| AC-4 | required | Maintains current structured diagnostics. |
| AC-5 | required | Regression safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-27 | Planned from native-Windows field feedback. | MCP docs-lint timed out at 30s; terminal docs-lint completed around 6s; DEVNULL subprocess test completed reliably. |
| 2026-06-27 | Implemented MCP helper subprocess isolation. | `server_impl._mcp_subprocess_run` sets `stdin=DEVNULL`, intentional stdout/stderr policy, and Windows no-window flag; full suite 3510 tests OK; docs-lint OK. |
| 2026-06-27 | Post-review: AC-2 scope made honest. | Recorded the bounded residual of pre-existing MCP-reachable probes (`tasklist`, `git log`/`git grep`, dashboard PowerShell/`ps`, `nvidia-smi`) that still call `subprocess.run` directly; they `capture_output` and don't read stdin so impact is a possible Windows console flash, not a JSON-RPC hang. Routing them through the helper is a tracked follow-up. Full suite 3521 tests OK. |
| 2026-06-27 | Residual resolved — all MCP-reachable subprocesses isolated. | Git audits routed through `_mcp_subprocess_run`; `tasklist`/`nvidia-smi`/`ldconfig`/dashboard PowerShell+`ps` isolated inline (`stdin=DEVNULL`, +`CREATE_NO_WINDOW` where a console can appear). Added a breadth source-scan guard over `server_impl` (non-vacuous; catches aliased `_sp.run`/`__import__` forms) + behavioral tests. |
| 2026-06-27 | Final-review fix — secrets-scan fallback git probes isolated (AC-2 was overclaimed). | The `wave_scan_secrets` in-process fallback (`check_hardcoded_secrets`) reaches 8 raw git probes in `wave_lint_lib/secrets_validators.py` that the server_impl-only guard could not see. Added `stdin=DEVNULL` + `CREATE_NO_WINDOW` to all 8 and extended the breadth guard to scan `secrets_validators.py` too (accepting `input=` as isolation). AC-2 "all MCP-reachable" is now genuinely true + enforced. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-27 | Isolate helper subprocess stdio instead of raising timeout. | Terminal timing shows docs-lint is not inherently slow; inherited MCP stdio is the suspect. | Increase timeout (rejected as masking); remove MCP docs-lint (rejected). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Redirecting output hides useful diagnostics. | Capture output for command responses; use DEVNULL only where output is not consumed or is separately logged. |
| Central helper changes many call sites. | Start with validation/garden/sync, then migrate other bounded calls with focused tests. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
