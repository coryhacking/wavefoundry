# Git-hook bootstrap migration + `.gitattributes` line-ending pin

Change ID: `1p7pn-enh git-hook-bootstrap-and-gitattributes`
Change Status: `complete`
Owner: Engineering
Status: completed
Last verified: 2026-06-25
Wave: `1p7pk native-windows-launchers`

## Rationale

Three `1p7pb-adr` items remain after the bootstrap (`1p7pl`) and the config cutover (`1p7pm`): the git hooks, line-endings, and the dashboard daemon. Today the rendered git hooks are `#!/usr/bin/env python3` bodies that resolve `bin/python` with a `python3` fallback — these independently break on stock python.org-Windows under git-bash (POSIX `bin/python` layout, no `python3.exe`), so commit/merge incremental reindex silently dies on native Windows (gap M-3). The repo has no `.gitattributes`, so git-for-Windows `autocrlf=true` can rewrite LF→CRLF on checkout and corrupt the `#!/usr/bin/env bash`/python shebang lines, breaking launchers and hooks even under WSL2/git-bash (gap L-1). And `bin/wave-dashboard` daemonizes with bash `nohup … &` — bash-only, no native-Windows path — so for its `1p7pm` thin-forwarder (`exec python dashboard_server.py`) to work cross-OS, the daemonization must move **into** `dashboard_server.py` (Python), and the self-detach **child** spawn must use `sys.executable` (the running venv python), never `python3` (absent on python.org-Windows). This change routes the git-hook bodies through the shared bootstrap (`1p7pl`), adds a `.gitattributes` pinning shebang-bearing files to `eol=lf`, and moves the dashboard self-detach into Python.

## Requirements

1. The rendered git hooks (post-commit/post-merge/post-rewrite/post-checkout) invoke their `.py` body via the shared `activate_tool_venv` bootstrap (so venv discovery/activation is Python's job), rather than hardcoding `bin/python`/`python3`. The git-hook spawn never uses `os.execv` or a Windows re-exec subprocess; it uses `sys.executable` and the spawned script self-activates.
2. Add a repo-root `.gitattributes` that pins shebang-bearing files to LF: `*.py text eol=lf`, the `.wavefoundry/bin/*` launchers and `.wavefoundry/git-hooks/*` / `.claude/hooks/*` POSIX bodies `eol=lf`, with `* text=auto` as the baseline — so git-for-Windows `autocrlf` cannot corrupt shebangs on checkout.
3. `dashboard_server.py` self-daemonizes when launched directly (a `--daemon`/detach mode replacing `bin/wave-dashboard`'s bash `nohup … &`), so the `1p7pm` thin forwarder `exec python dashboard_server.py --open` survives shell exit on macOS/Linux *and* native Windows. The detached **child** spawn uses **`sys.executable`** (the running venv python), not `python3`. Reuse the OS-correct detach already used for the MCP server's dashboard spawn (`start_new_session` POSIX / `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` Windows).
4. No behavior change on macOS/Linux (hooks still fire the incremental reindex; the dashboard still backgrounds + logs; line endings already LF there).

## Scope

**Problem statement:** Git hooks hardcode the POSIX venv layout (M-3, breaks native-Windows git) and the repo has no line-ending policy (L-1, `autocrlf` can corrupt shebangs).

**In scope:**

- Render git-hook bodies onto the shared bootstrap (`render_git_hooks` in `render_platform_surfaces`).
- Add `.gitattributes` (eol=lf pins).
- Move dashboard daemonization into `dashboard_server.py` (self-detach mode) so `bin/wave-dashboard`'s forwarder is cross-OS.
- Tests for the hook-body rendering, the `.gitattributes` content, and the dashboard self-detach.

**Out of scope:**

- The shared bootstrap (`1p7pl`) and the MCP/Claude-hook config rendering (`1p7pm`).
- The real-Windows smoke verification (carried as `1p7pm` AC-6; this change's hook fire is exercised there).

**Depends on:** `1p7pl` (the shared bootstrap the hook bodies route through). Coordinates with `1p7pm` for the AC-6 end-to-end smoke pass.

## Acceptance Criteria

- [x] AC-1: rendered git hooks activate the venv via the shared bootstrap (`activate_tool_venv`) instead of hardcoding `bin/python`/`python3` or a `Scripts`/`bin` branch; hook spawns never use `os.execv` or a Windows re-exec subprocess. Verified by render tests. — `git_hook_source` routes through `HOOK_BOOTSTRAP` + `#!/usr/bin/env python`; spawn uses `sys.executable`; `tests/test_render_platform_surfaces.GitHookBootstrapTests`.
- [x] AC-2: a repo-root `.gitattributes` exists pinning `*.py` and the POSIX launcher/hook bodies to `eol=lf` with `* text=auto` baseline; verified by a content test. — `.gitattributes` added; `tests/test_render_platform_surfaces.GitAttributesTests`.
- [x] AC-3: `dashboard_server.py` self-daemonizes when launched directly (OS-correct detach: `start_new_session` POSIX / `DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` Windows; the detached child spawn uses `sys.executable`, not `python3`), so `exec python dashboard_server.py --open` survives shell exit; `bin/wave-dashboard` drops its bash `nohup … &`. Unit-tested for the detach-mode branch; the dashboard still backgrounds + logs on macOS/Linux. — `dashboard_server._daemonize` + `--daemon`; `tests/test_dashboard_server.DashboardDaemonModeTests`.
- [x] AC-4: no macOS/Linux behavior change — hooks still fire incremental reindex; full suite green.
- [x] AC-5: framework tests bytecode-free; `wave_validate` clean. (End-to-end native-Windows hook-fire + dashboard launch are covered by `1p7pm` AC-6.)

## Tasks

- [x] Open `framework_edit_allowed`; close after.
- [x] Route `render_git_hooks` bodies through the shared bootstrap (Windows-safe re-exec; venv layout in Python).
- [x] Add repo-root `.gitattributes` (eol=lf pins + `* text=auto`).
- [x] Add `dashboard_server.py` self-detach mode; drop `bin/wave-dashboard`'s bash `nohup … &`.
- [x] Tests (hook-body bootstrap rendering; `.gitattributes` content; dashboard self-detach) bytecode-free.

## Agent Execution Graph


| Workstream | Owner       | Depends On     | Notes                                   |
| ---------- | ----------- | -------------- | --------------------------------------- |
| git-hooks  | implementer | `1p7pl` helper | render bodies onto the shared bootstrap |
| gitattrs   | implementer | —              | repo-root `.gitattributes` eol=lf pins  |
| tests      | implementer | git-hooks      | render test + `.gitattributes` content  |


## Serialization Points

- After `1p7pl`. The native-Windows hook fire is verified as part of `1p7pm` AC-6 (the shared smoke pass).

## Affected Architecture Docs

- Implements `docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md` (M-3, L-1). No boundary/flow change. Note the L-1/M-3 closure in `docs/references/native-windows-support.md` at close.

## AC Priority

(Proposed; confirmed at Prepare.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | M-3: the native-Windows git-hook reindex fix. |
| AC-2 | required  | L-1: prevents `autocrlf` shebang corruption (affects all launchers/hooks, even WSL2). |
| AC-3 | required  | Without Python self-detach, `wave-dashboard`'s cross-OS forwarder can't persist (the bash `nohup` has no Windows peer). |
| AC-4 | required  | No macOS/Linux regression. |
| AC-5 | required  | Test-locked, bytecode-free. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-24 | Planned from `1p7pb-adr` (M-3 git hooks + L-1 line-endings); rides along with the cutover. | `1p7pb-adr`; `render_git_hooks` (`#!/usr/bin/env python3`, no `.cmd`/bootstrap); no `.gitattributes` at repo root |
| 2026-06-24 | Implemented. Git-hook bodies route through `HOOK_BOOTSTRAP` (`#!/usr/bin/env python` shebang; `sys.executable` spawn; no `os.execv`/TOOL_VENV). `.gitattributes` added (`* text=auto` + `*.py`/launcher/hook `eol=lf`). `dashboard_server.py` gains `--daemon` self-detach (OS-correct, `sys.executable` child); `bin/wave-dashboard` → thin `exec python … --daemon` forwarder. Single-resolver scan allowlist now EMPTY (goal B closed). Full suite green bar the known secrets flake; machine not mutated. | `git_hook_source`; `.gitattributes`; `dashboard_server._daemonize`; `test_render_platform_surfaces.GitHookBootstrapTests`/`GitAttributesTests`; `test_dashboard_server.DashboardDaemonModeTests`; `test_venv_bootstrap.SingleResolverScanTests` (empty allowlist) |
| 2026-06-24 | Pre-close review fix (AC-1 M-3 faithfulness): the TWO rendered reindex `Popen` spawns — `git_hook_source` AND `hook_helpers.maybe_trigger_reindex` — used POSIX-only `start_new_session=True` with NO Windows `creationflags`, so on native Windows the child would die with the hook (the exact M-3 failure this change fixes). Both now render the per-OS detach (`os.name=='nt'` → `DETACHED_PROCESS \| CREATE_NEW_PROCESS_GROUP`, else `start_new_session=True`; `close_fds=os.name!='nt'`), matching `server_impl`/`dashboard_server._daemonize`. Re-added `import os` to the git-hook body. New assertion `test_reindex_spawns_have_per_os_detach_branch` covers both bodies. | `git_hook_source`/`hook_helpers` Popen; `test_render_platform_surfaces.GitHookBootstrapTests.test_reindex_spawns_have_per_os_detach_branch` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-24 | Route git-hook bodies through the shared bootstrap rather than a `.cmd` trampoline | Keeps the `bin`-vs-`Scripts` venv decision in one Python place; native git-for-Windows runs the hook via its MSYS2 sh, so the POSIX trampoline + bare interpreter + bootstrap is sufficient. | Per-OS `.cmd` git-hook trampolines — rejected: duplicates venv logic, more files to sync. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Adding `.gitattributes eol=lf` renormalizes existing CRLF files in a contributor's working tree | Baseline `* text=auto` + targeted `eol=lf` only on shebang-bearing files; the repo is LF today, so no renormalization churn on macOS/Linux. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
