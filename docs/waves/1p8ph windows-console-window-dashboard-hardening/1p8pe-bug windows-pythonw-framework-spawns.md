# Convert framework python spawns to pythonw on Windows

Change ID: `1p8pe-bug windows-pythonw-framework-spawns`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-28
Wave: `1p8ph windows-console-window-dashboard-hardening`

## Rationale

The post-release native-Windows test of 1.9.5 confirmed: **most** console-window flashes are gone (the 1p8gu multiprocessing-pool fix via `windowless_mp_context`/pythonw + `CREATE_NO_WINDOW` on subprocess spawns), but a **few residual** flashes remain during **upgrade / index / graph** and the **dashboard**. Root cause (operator-confirmed on Windows): a console-subsystem **`python.exe`** still briefly shows/flashes a window for **long-running detached** or **rapid** spawns *even with* `CREATE_NO_WINDOW`. A windows-subsystem **`pythonw.exe`** cannot allocate a console regardless of creation flags — which is exactly why the pool fix worked.

A 4-finder spawn audit + adversarial verify over **117** spawn/launch sites produced a verified convert/keep classification. The fix: route every framework python spawn whose output is **redirected** (DEVNULL / PIPE / log-file) through the existing shared helper **`subprocess_util.windowless_pythonw()`** (returns the tool-venv `pythonw.exe` on Windows, else `None` → graceful fallback to the current interpreter). POSIX behavior is unchanged (`None` → no change). Spawns that need a real console (operator-visible CLI output, JSON-RPC stdio) stay `python3`/`python.exe`.

## Requirements

1. **Resolver-level (safe, covers the bulk):** the two SPAWN-FACING `_preferred_python()` copies — `server_impl.py:148` (10 consumers) and `upgrade_wavefoundry.py:95` (9 consumers) — prefer `windowless_pythonw()` on Windows when a tool-venv pythonw exists, else return the current value. Every consumer of these is non-interactive and redirects output (verified).
2. **Per-site `setup_index.py` (NOT the `:134` resolver — verify caught this):** `setup_index._tool_venv_python()` is **not** spawn-only — `_bootstrap_venv` derives `venv_python.parent.parent` path-math + `.exists()` checks from it and feeds the **console-streaming `pip install`** (a keep). Do **NOT** resolver-convert it. Convert the concrete spawn sites instead: `959`/`976` (background code-build, detached log), `1004`/`1026` (foreground indexer, one-way PIPE), and `214` (import probe, captured). Each: `windowless_pythonw() or <current venv python>`.
3. **Per-site `dashboard_server.py:703`** (`_daemonize` self-respawn uses `sys.executable` directly, no resolver): `windowless_pythonw() or sys.executable`.
4. **Renderer-string (rendered hook bodies the framework owns):** thread `windowless_pythonw()` into the python launch in `render_platform_surfaces.py` for `:379` (maybe_trigger_reindex — detached all-DEVNULL, textbook flasher) **and** the verify-found `:314` (docs-lint, PIPE-captured), `:530` (simulate-hooks, `input=` PIPE), `:626/635` (cursor after-file-edit gates, `input=` PIPE + capture). Preserve all existing stdin/`input=`/capture wiring; keep the guarded `_wf_subprocess_util` import with a `sys.executable` fallback when unavailable.
5. **Never mutate `venv_bootstrap.tool_venv_python()` (`:71`)** — it is shared by in-process, non-spawn callers (`activate_tool_venv`) that need the real `python.exe`. `venv_bootstrap` is stdlib-only and cannot import `windowless_pythonw`.
6. **Hard-exclusions stay `python3`/`python.exe`:** every MCP server command (rendered `.mcp.json` / Junie / Cursor / Antigravity / Codex — JSON-RPC stdio, byte-identical cross-OS), the `wf` POSIX/Windows shims (`render:1174/1185`) + `wf_cli.py:129` re-exec (operator-terminal CLI), console-streaming installs (`setup_index:160/258/299`, `indexer:1127`, `setup_wavefoundry:60`), the `setup_wavefoundry` MCP dry-runs (`77/78`) and `venv_bootstrap:219` version probe (validate the exact `python3` token), `wave_run_sensors:7354` (operator-supplied tokens), and `launcher_command:114` (host hook command). POSIX returns `None` from `windowless_pythonw()` → no behavior change.

## Scope

**Problem statement:** residual Windows console-window flashes from framework python spawns that use console-subsystem `python.exe` despite `CREATE_NO_WINDOW`.

**In scope:** the convert list above (2 resolver edits, the setup_index per-site set, dashboard_server:703, the rendered hook bodies); preserving the hard-exclusions; a source-scan guard extension so future framework python spawns must route through `windowless_pythonw()` or be a documented keep.

**Out of scope:** the dashboard lock/PID race (`1p8pf`), the markdown `---` render (`1p8pg`), the MCP server launch (must stay python3), any host-controlled spawn the framework does not own (the hook *launcher* command), changing `windowless_pythonw()` itself.

## Acceptance Criteria

- [x] AC-1: `server_impl._preferred_python()` and `upgrade_wavefoundry._preferred_python()` return the tool-venv `pythonw.exe` on Windows when present, else the current value; a test asserts pythonw-on-Windows-with-pythonw and graceful fallback (POSIX/no-pythonw → unchanged). (`test_subprocess_util.PreferredPythonResolverTests` + `WindowlessPythonwTests`.)
- [x] AC-2: `setup_index` spawn sites `959`/`1004`/`214` route through `windowless_pythonw()` with fallback; the `:134` resolver and `venv_bootstrap.tool_venv_python()` are UNCHANGED; the venv path-math + the `pip install` console-streaming keep are preserved (test/assertion). (`test_server_tools.test_setup_index_resolver_and_venv_bootstrap_keeps_unchanged` + `test_converted_python_spawns_reference_windowless_pythonw`.)
- [x] AC-3: `dashboard_server._daemonize` (`:703`) launches via `windowless_pythonw() or sys.executable`.
- [x] AC-4: the rendered hook bodies (`render:379`, `:314`, `:530`, `:626/635`) launch python via `windowless_pythonw()` with `sys.executable` fallback, preserving every existing `input=`/`stdin`/`capture_output` wiring; a render-time assertion confirms the body contains the windowless launch + fallback. (`test_render_platform_surfaces.test_hook_helpers_defines_windowless_hook_python` + `test_converted_hook_bodies_launch_via_windowless_pythonw`.)
- [x] AC-5: every hard-exclusion is unchanged — assert the rendered MCP server command stays `python3` (all hosts) and the `wf` shims/console-streaming installs/version probes are untouched. (`test_render_platform_surfaces.test_every_rendered_mcp_command_stays_python3` + the `_PYTHONW_KEEPS` allowlist in `test_server_tools`.)
- [~] AC-6 (Windows-repro-gated `[~]` until the post-release Windows test): no console window flashes during upgrade / index / graph / dashboard on native Windows. (Intentionally not met on this host — macOS cannot exercise pythonw/`CREATE_NO_WINDOW`; confirmable only on a native-Windows post-release test. All mechanism + POSIX-fallback ACs are met and tested.)
- [x] AC-7: full framework suite + docs-lint pass; POSIX behavior provably unchanged (`windowless_pythonw()` returns `None`). (Suite green except a pre-existing, out-of-scope `scan-findings-format.md` template-parity drift; resolver/helper fallback tests prove POSIX returns `None` → no behavior change.)

## Tasks

- [x] Resolver edits: `server_impl._preferred_python` + `upgrade_wavefoundry._preferred_python` → prefer `windowless_pythonw()` on Windows.
- [x] `setup_index` per-site: `959`/`1004`/`214` → `windowless_pythonw()` with venv-python fallback; leave `:134` + `venv_bootstrap.tool_venv_python()` untouched.
- [x] `dashboard_server._daemonize:703` per-site pythonw.
- [x] `render_platform_surfaces` hook bodies `379`/`314`/`530`/`626/635` → thread `windowless_pythonw()` into the rendered launch (via the new `hook_python()` helper for the helper-bearing bodies; inline guarded windowless resolution in `claude_simulate_hooks_source`), preserve wiring.
- [x] Extend the spawn-isolation source-scan guard: framework python spawns must use `windowless_pythonw()` or be a documented keep (`test_server_tools.test_every_framework_python_spawn_uses_windowless_pythonw_or_is_keep` + `_PYTHONW_KEEPS` allowlist + `test_pythonw_keeps_are_real_console_sites`).
- [x] Tests (resolver behavior, setup_index keep-preservation, render-body assertions, MCP-command-stays-python3) + full suite + docs-lint.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| resolver edits (server_impl + upgrade) | implementer | — | covers ~19 sites |
| setup_index per-site + dashboard_server:703 | implementer | — | NOT the :134 resolver |
| rendered hook bodies (render_platform_surfaces) | implementer | — | preserve input=/capture wiring |
| guard + tests | qa-reviewer | all | non-vacuous; POSIX-unchanged proof |

## Serialization Points

- All edits are independent except the shared `subprocess_util.windowless_pythonw()` consumer pattern — no two workstreams edit the same call site.
- Coordinate with `1p8pf`: both touch `server_impl.py` dashboard start (`:6777`/`:6796`) — `1p8pe` swaps the interpreter token, `1p8pf` reworks the readiness/reconcile logic around it. Keep the interpreter swap minimal so it does not collide with the lifecycle rework.

## Affected Architecture Docs

`docs/references/native-windows-support.md` (the pythonw-for-spawns rule + the keep-list rationale). ADR `N/A` (extends the 1p8gu isolation approach).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The bulk of the residual flashes (upgrade/index/graph). |
| AC-2 | required | Correctness — must not break venv bootstrap / hide pip progress. |
| AC-3 | required | Dashboard daemon flasher. |
| AC-4 | required | Rendered-hook flashers; the zero-window goal. |
| AC-5 | required | Must not break the MCP transport / operator CLIs. |
| AC-6 | required (`[~]` Windows-repro-gated) | The operator's actual symptom; confirmable only on Windows. |
| AC-7 | required | Regression + POSIX safety. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-28 | Planned from the 1.9.5 post-release Windows test + a 117-site spawn audit with adversarial verify. Verify corrected the naive plan: setup_index:134 resolver is NOT spawn-only (demoted to per-site); 3 rendered-hook child spawns (314/530/626) were missed converts. | audit run `wf_b4b7cb6a-39c`; `subprocess_util.windowless_pythonw():190`; `server_impl._preferred_python:148`; `upgrade_wavefoundry._preferred_python:95`; `setup_index._tool_venv_python:134` (+ `_bootstrap_venv` path-math). |
| 2026-06-28 | Implemented. Resolver edits in `server_impl._preferred_python` + `upgrade_wavefoundry._preferred_python` (prefer `windowless_pythonw()` on Windows, ~19 redirected consumers each). Per-site converts: `setup_index` background-build / foreground-indexer / import-probe (`windowless_pythonw() or <venv python>`); `dashboard_server._daemonize` (`windowless_pythonw() or sys.executable`). Renderer: new `hook_python()` in `hook_helpers()` threaded into docs-lint + reindex-Popen + cursor gate launches; inline guarded windowless resolution in `claude_simulate_hooks_source` (no shared helpers). Hard-exclusions verified untouched (every MCP command stays `python3`; `setup_index:134` + `venv_bootstrap.tool_venv_python` + console pip/venv installs + `wf` re-exec preserved). New source-scan guard + non-vacuous tests added; AC-6 stays `[~]` (Windows-repro-gated). | `subprocess_util.windowless_pythonw()`; `test_server_tools.FrameworkWideSubprocessIsolationGuard` (new `_PYTHONW_KEEPS` guard); `test_subprocess_util.WindowlessPythonwTests`/`PreferredPythonResolverTests`; `test_render_platform_surfaces` render-body + MCP-stays-python3 assertions. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-28 | pythonw (windows subsystem) over more `CREATE_NO_WINDOW`. | A console-subsystem `python.exe` still flashes for long-running/detached/rapid spawns despite the flag; pythonw cannot allocate a console at all. | More `CREATE_NO_WINDOW` (rejected — already present and insufficient on the residual cases). |
| 2026-06-28 | Resolver-level for the two `_preferred_python()` copies; per-site for setup_index. | The two `_preferred_python` are spawn-only with 100%-redirected consumers (safe blanket switch); setup_index's resolver feeds venv path-math + a console pip-install keep (resolver-convert would break both). | Resolver-convert all four (rejected — unsafe for setup_index per the adversarial verify). |
| 2026-06-28 | Convert the 3 rendered hook-body child spawns (314/530/626). | They are PIPE/capture-redirected (pythonw-safe) and rapid console-python flashers on Windows; needed for the zero-window goal the operator asked for. | Keep them (rejected — leaves residual flashes). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| pythonw + an unredirected stdout → `sys.stdout` is None → child `print()` crash. | Only convert sites with redirected output (DEVNULL/PIPE/log); the keep-list retains every console-needing spawn; AC-7 proves POSIX unchanged. |
| Resolver-converting setup_index breaks venv bootstrap / hides pip progress. | Per-site only; `:134` + `venv_bootstrap.tool_venv_python()` left untouched (AC-2). |
| A future framework spawn re-introduces console `python.exe`. | Source-scan guard requires `windowless_pythonw()` or a documented keep. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
