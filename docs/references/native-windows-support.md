# Native Windows Support — Scoping & Decision Assessment

Owner: Engineering
Status: supported
Last verified: 2026-07-20

## Context

Downstream users are running the Claude Code CLI on **native Windows** (standard Windows Terminal with PowerShell/cmd, **not** WSL) and asking whether Wavefoundry supports that environment. This document records what an investigation of the current code found, the work completed across multiple waves, and known remaining limitations. Native Windows is now **supported** — the blocking gaps identified in this scoping artifact have been resolved.

All findings below are cited to `file:line` from a read of the actual sources.

## Headline

Native-Windows support is **more than the bin shell scripts, but less than a rewrite.** The codebase already carries substantial, partially-finished Windows awareness; the blocking gaps are concentrated in the agent entry points (MCP server + bin launchers) and in one architectural decision about how a single repo serves both macOS/Linux and Windows developers.

## What already works (the foundation)

Windows was considered — and handled correctly — in several places:

- Process termination branches to `taskkill /PID <pid> /T /F` on `os.name == "nt"` (`server_impl.py:6735`).
- Process liveness uses `tasklist` on Windows (`indexer.py:192`, `upgrade_lib.py:121`).
- File locking branches between `msvcrt.locking` (Windows) and `fcntl.flock` (POSIX) (`indexer.py:1906`, `dashboard_lib.py:171`).
- Most background spawns set `creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP` on Windows (`server_impl.py:3440`, `setup_index.py:771`, dashboard spawn `server_impl.py:6594`).
- Path strings are normalized through `replace("\\", "/")` before posix-path operations (`chunker.py:375` `_normalize_path`; `dashboard_lib.py` multiple sites).
- The platform renderer already emits `cmd.exe /c …` launcher commands and **`.cmd` companions already exist for every `.claude/hooks/` file** (`render_platform_surfaces.py:101` `launcher_command`).
- `DmlExecutionProvider` (DirectML) is auto-detected and selected when available — it is in `PROVIDER_PRIORITY` (`provider_policy.py:26`) so no manual `WAVEFOUNDRY_EMBED_PROVIDER=dml` override is needed.
- macOS-only shell-outs (`sysctl`, `.DS_Store` cleanup) are correctly guarded with `sys.platform != "darwin"` (`graph_indexer.py:7766`, `render_platform_surfaces.py:1382`).

The floor is not zero. The work is finishing and verifying, not starting from scratch.

## Console windows (native Windows)

On native Windows a Python process spawned without a no-window flag can flash a blank console. Wavefoundry suppresses the windows it controls and documents the one it does not:

- **Synchronous helper subprocesses** launched by the MCP server (docs-lint, docs-gardener, sync-surfaces, upgrade phases, sensors, and similar bounded calls) go through one shared helper that sets `stdin=subprocess.DEVNULL`, captures/redirects stdout/stderr, and adds `CREATE_NO_WINDOW` on Windows. This both eliminates their console flash and keeps them from inheriting the MCP server's JSON-RPC stdio (the cause of the `wf_validate_docs`/docs-lint-over-MCP timeout).
- **Detached background jobs** (the index refresh, the dashboard daemon) already run window-free: `DETACHED_PROCESS` does not allocate a console, so they show no window regardless. `CREATE_NO_WINDOW` is additionally applied where it composes safely; on already-detached paths it is defensive, not load-bearing.
- **The main MCP server window is host-controlled, not Wavefoundry-controlled.** The MCP host (Claude Code, Cursor, …) creates the `python3 server.py` process; nothing inside `server.py` can hide that window after the host has created it. If a blank window persists after child-process suppression, the visible process is the host-launched server, and the remedy is a host-side no-console launcher strategy (e.g. a `pythonw`-style launcher) — tracked as an evidence-gated follow-up, not something the framework can fix from inside the server.

## Gap inventory (by severity)

### Critical — a native-Windows user is blocked

| ID | Gap | Evidence | What breaks |
| --- | --- | --- | --- |
| ~~C-1~~ | ~~`.mcp.json` sets `command` to a bash MCP-server wrapper with no `.cmd` sibling~~ — **RESOLVED:** every committed MCP config now names `command: "python3"` + `args: [".wavefoundry/framework/scripts/server.py"]` (byte-identical cross-OS; `setup` makes `python3` resolvable). The bash `bin/mcp-server` wrapper was retired (1p7tz). | `.mcp.json`; `render_platform_surfaces.render_mcp_json` | No action — MCP spawns natively on Windows. |
| ~~C-2~~ | ~~All 9 `.wavefoundry/bin/` launchers are bash-only~~ — **RESOLVED (wave 1p7tz):** the nine POSIX-only wrappers were replaced by one cross-OS `wf` dispatcher (`wf_cli.py`) behind a `wf` (bash) + `wf.cmd` (Windows) shim pair; `wf docs-lint`, `wf docs-gardener`, `wf gate`, `wf setup`, `wf upgrade`, `wf update-indexes`, `wf dashboard`, `wf lifecycle-id` run on every OS. | `render_platform_surfaces.render_bin_launchers`; `wf_cli.py` | No action — operator CLI is cross-OS. |
| ~~C-3~~ | ~~One committed `.mcp.json` / `.claude/settings.json` reflects **whichever OS last ran the renderer**; a Windows clone of a Mac-rendered repo gets POSIX hook forms~~ — **RESOLVED (wave 1p88t):** `launcher_command` returns one unconditional `python3 "<script>.py"` form (no OS branch), so the committed MCP/hook command surfaces are **byte-identical regardless of the rendering OS**. A Windows clone of a Mac-rendered repo gets the same working `python3` forms; the host spawns them via raw process spawn (no shell), so they run in any session. | `render_platform_surfaces.launcher_command` (unconditional `python3`); `.claude/settings.json` | No action — committed command surfaces are cross-OS identical. |

Native Windows MCP configs should use `command: "python3"` with `args: [".wavefoundry/framework/scripts/server.py"]` for generated repo-local configs, or `args: ["<repo>/.wavefoundry/framework/scripts/server.py", "--root", "<repo>"]` for manual host entries. Before proceeding, `python3 --version` must work from the command line and report Python 3.11 or newer; if Windows has `python` but not `python3`, stop and fix PATH or install a Python distribution that provides `python3`. Do not configure MCP to run `.wavefoundry\venv\Scripts\python.exe` directly as a workaround; `server.py` owns shared tool-venv activation. After fixing Python on PATH or changing MCP config, start a fresh host session because an already-open conversation may keep the toolset from the earlier failed startup.

### Moderate — degrades behavior; MCP server itself survives

| ID | Gap | Evidence | What breaks |
| --- | --- | --- | --- |
| ~~M-1~~ | ~~`dashboard_cmdline_pids` returns `None` on `os.name == "nt"` — no scan~~ — **RESOLVED (wave 1p6eq):** native Windows now gets a PowerShell/CIM cmdline scan (`_windows_process_cmdlines`); the probe also isolates `stdin` and suppresses the console window (wave 1p88t). | `dashboard_lib.py` (`_windows_process_cmdlines`, `dashboard_cmdline_pids`) | No action — orphan reconciliation runs on Windows. |
| ~~M-2~~ | ~~One background reindex spawn sets `start_new_session=True` without the Windows `creationflags`~~ — **RESOLVED (wave 1p7pn/1p88t):** all detached reindex/dashboard spawns set `creationflags = DETACHED_PROCESS \| CREATE_NEW_PROCESS_GROUP \| CREATE_NO_WINDOW` on Windows and `stdin=DEVNULL`. | `server_impl.py` (`_start_background_index_refresh` + sibling spawns) | No action — background reindex detaches correctly on Windows. |
| ~~M-3~~ | ~~Git hooks rendered as `#!/usr/bin/env python3`; native Windows git can't run shebang Python directly~~ — **REMOVED (wave 1p88t): the git hooks were dropped entirely.** They only spawned a background incremental reindex and were opt-in/inactive-by-default; the in-session staleness monitor (wave 1p5xu) already hash-detects and refreshes VCS-driven index staleness within ~20s of an agent session, and `indexer.py`'s incremental diff is global so any trigger catches up `git pull`/`merge`/`checkout` changes. `render_git_hooks`/`git_hook_source` were removed and `remove_git_hooks` cleans up prior renders. The git-bash/`python3` execution concern is therefore moot. | `render_platform_surfaces.remove_git_hooks` (cleanup) | No action — git operations were never blocked; freshness is covered by the staleness monitor + global incremental reindex. |

### Low / pre-existing (not Windows-specific regressions)

| ID | Gap | Evidence | Note |
| --- | --- | --- | --- |
| ~~L-1~~ | ~~No `.gitattributes` for line-ending control~~ — **RESOLVED (wave 1p9hm):** `.gitattributes` now pins `*.py`, launchers, and text assets to `eol=lf`, guarding against `core.autocrlf` shebang corruption on git-for-Windows. | `.gitattributes` | No action. |
| ~~L-2~~ | ~~Secrets scan is a no-op off macOS~~ — **CORRECTED (wave 1p6d5): not a bug.** The `if sys.platform != "darwin": return` at the cited lines is inside `_physical_perf_core_count()` (a perf-core-count helper that gracefully returns `None` off macOS so the scan uses a default core count). The **secrets scan itself runs on Linux, WSL2, and Windows** — it is not gated by platform. | `scan_secrets.py:40-45`, `run_secrets_scan.py:32-33` (the helper, verified) | No action — the original claim misread the perf helper as a scan gate. |
| ~~L-3~~ | ~~DirectML accepted but never auto-detected~~ — **RESOLVED:** `DmlExecutionProvider` is in `PROVIDER_PRIORITY` (`provider_policy.py:26`) and is auto-selected when available in the ONNX Runtime install. No manual `WAVEFOUNDRY_EMBED_PROVIDER=dml` override needed. | `provider_policy.py:26` | No action. |
| L-4 | `PurePosixPath` used on real filesystem path strings | `chunker.py:10` and call sites | Safe in practice — every call site routes through `_normalize_path` (backslash → forward slash) first. Theoretical fragility if a raw Windows path bypasses normalization, but no known path does. |

## Work buckets

### Bucket 1 — Portable entry points (the hard blocker)

The MCP launcher (C-1) and bin launchers (C-2) need a Windows-runnable form. The recommended approach is **not** `.cmd` twins of every bash script (two parallel script families to maintain), but to **bypass the shell wrapper**: point `.mcp.json` at `python3` running `server.py`, and have the entry scripts self-bootstrap into the tool venv (`~/.wavefoundry/venv/bin/python` on POSIX, `Scripts\python.exe` on Windows). One portable mechanism instead of two. This is the gate — until the server starts and `docs-lint`/`wave-gate` run, nothing else is reachable.

### Bucket 2 — The per-OS distribution model (the gating decision)

A single committed `.mcp.json` / `.claude/settings.json` **cannot simultaneously serve** a mixed macOS/Linux + Windows team from one repo (C-3): the committed file reflects whichever OS last rendered it. The options:

- **(a) Re-render on first checkout per OS** — documented step; the renderer already supports per-OS hook forms, it only needs MCP + bin coverage added (Bucket 1). Simple, but a manual step and a source of "works on my machine" drift.
- **(b) Commit OS-suffixed surfaces** — e.g. ship both forms; the host picks. More files; depends on what Claude Code will read.
- **(c) Make the launchers identical cross-OS** — so the one committed file works everywhere. The bypass-the-wrapper approach in Bucket 1 (interpreter-direct command + self-bootstrapping scripts) is what makes (c) viable, and it is the most robust for mixed teams.

This is an ADR-shaped choice and should be run through **Evaluate decision** / recorded as an ADR before a wave is opened — it drives the shape of everything else.

### Bucket 3 — Process / dashboard lifecycle parity

**Fully landed.** M-1 (Windows `dashboard_cmdline_pids` scan, via PowerShell/CIM) and M-2 (`creationflags` on the detached reindex spawns) are resolved; M-3 is moot — the git hooks were **dropped** (wave 1p88t), since the in-session staleness monitor + global incremental reindex already cover VCS-driven freshness. L-1 (`.gitattributes` line-ending control) was resolved in wave 1p9hm.

### Bucket 4 — Verification you can trust

None of the existing `taskkill` / `tasklist` / `msvcrt` / `creationflags` branches have ever run on a real Windows host in CI — they are **unverified**. Credible Windows support requires a Windows smoke path (CI runner or, at minimum, a documented manual checklist exercising: MCP server start, `docs-lint`, a wave-gate open/close, a dashboard start/stop, an index build). The biggest hidden risk in this whole effort is shipping Windows branches that have never executed on Windows.

## Status summary

All critical (C), medium (M), and low (L) items identified in this scoping assessment are resolved or closed. Native Windows is supported. The one remaining theoretical concern is L-4 (`PurePosixPath` fragility), which is safe in practice given universal `_normalize_path` call coverage.

## References

- Investigation date: 2026-06-17 (against framework `1.7.0`).
- Renderer: `render_platform_surfaces.py` (`launcher_command`, `render_mcp_json`, `render_bin_launchers`, `remove_git_hooks` — git hooks dropped in wave 1p88t).
- Platform mapping: `docs/agents/platform-mapping.md`.
