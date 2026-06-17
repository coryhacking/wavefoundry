# Native Windows Support — Scoping & Decision Assessment

Owner: Engineering
Status: scoping (not yet admitted to a wave)
Last verified: 2026-06-17

## Context

Downstream users are running the Claude Code CLI on **native Windows** (standard Windows Terminal with PowerShell/cmd, **not** WSL) and asking whether Wavefoundry supports that environment. This document records what an investigation of the current code found, the work required, and the one architectural decision that gates the rest. It is a pre-wave scoping artifact: no code has changed. The distribution-model question in [Bucket 2](#bucket-2--the-per-os-distribution-model-the-gating-decision) is ADR-shaped and should go through **Evaluate decision** before a wave is opened.

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
- `DmlExecutionProvider` (DirectML) is an accepted embedding provider via `WAVEFOUNDRY_EMBED_PROVIDER=dml` (`provider_policy.py:17`).
- macOS-only shell-outs (`sysctl`, `.DS_Store` cleanup) are correctly guarded with `sys.platform != "darwin"` (`graph_indexer.py:7766`, `render_platform_surfaces.py:1382`).

The floor is not zero. The work is finishing and verifying, not starting from scratch.

## Gap inventory (by severity)

### Critical — a native-Windows user is blocked

| ID | Gap | Evidence | What breaks |
| --- | --- | --- | --- |
| C-1 | `.mcp.json` sets `command: ".wavefoundry/bin/mcp-server"`, a `#!/usr/bin/env bash` script with **no `.cmd` sibling**; the renderer never emits a Windows form for the MCP entry | `.mcp.json:1`; `render_platform_surfaces.py:896` (`render_mcp_json`) | **Total MCP blackout** — the server process cannot spawn, so every `wave_*`, `code_*`, `docs_*` tool is unavailable |
| C-2 | All 9 `.wavefoundry/bin/` launchers are bash-only (`set -euo pipefail`, `${BASH_SOURCE[0]}`, `exec`); `render_bin_launchers` never emits `.cmd` equivalents (unlike hooks) | `render_platform_surfaces.py:1038`; `wave-dashboard` also uses `nohup … &` (`:1089`) | `docs-lint`, `docs-gardener`, `wave-gate`, `setup-wavefoundry`, `upgrade-wavefoundry`, `update-indexes`, `wave-dashboard`, `lifecycle-id`, `mcp-server` all unrunnable from the standard terminal |
| C-3 | One committed `.mcp.json` / `.claude/settings.json` reflects **whichever OS last ran the renderer**; a Windows clone of a Mac-rendered repo gets POSIX hook forms | `.claude/settings.json:9,17,29` (extension-less POSIX launcher form); `render_platform_surfaces.py:101` | Seed-edit gate (pre-edit), post-edit docs-lint trigger, and session-capture all fail or hard-error on Windows |

### Moderate — degrades behavior; MCP server itself survives

| ID | Gap | Evidence | What breaks |
| --- | --- | --- | --- |
| M-1 | `dashboard_cmdline_pids` returns `None` on `os.name == "nt"` — no `tasklist`-based scan | `dashboard_lib.py:244` | Dashboard orphan reconciliation (the 1p654 fix) is silently disabled on Windows; stop falls back to bare PID liveness (`server_impl.py:6706`) |
| M-2 | One background reindex spawn sets `start_new_session=True` without the Windows `creationflags` | `server_impl.py:4624` | Background reindex stays attached to the server process on Windows; dies if the server exits |
| M-3 | Git hooks rendered as `#!/usr/bin/env python3` with exec-bit; native Windows git can't run shebang Python directly | `render_platform_surfaces.py:1169` (`render_git_hooks`) | post-commit / post-merge incremental reindex does not fire under native Windows git |

### Low / pre-existing (not Windows-specific regressions)

| ID | Gap | Evidence | Note |
| --- | --- | --- | --- |
| L-1 | No `.gitattributes` for line-ending control | repo root (absent) | With git-for-Windows `core.autocrlf=true`, CRLF can corrupt `#!/usr/bin/env bash` shebangs and is fragile for scripts that read their own source |
| L-2 | Secrets scan is a no-op off macOS: `if sys.platform != "darwin": return` | `scan_secrets.py:45`, `run_secrets_scan.py:33` | Affects **Windows and Linux** — broader than this initiative; track separately |
| L-3 | DirectML accepted but never auto-detected/installed; `_should_plan_gpu_accel_dependencies` only checks Apple Silicon / NVIDIA | `setup_index.py:168`; `provider_policy.py:93` (`apple_silicon_present`, no `windows_gpu_present`) | Windows-GPU users fall to CPU unless they set `WAVEFOUNDRY_EMBED_PROVIDER=dml` manually |
| L-4 | `PurePosixPath` used on real filesystem path strings | `chunker.py:10` and call sites | Functional **only because** callers route through `_normalize_path` first; fragile if a raw Windows path ever bypasses it |

## Work buckets

### Bucket 1 — Portable entry points (the hard blocker)

The MCP launcher (C-1) and bin launchers (C-2) need a Windows-runnable form. The recommended approach is **not** `.cmd` twins of every bash script (two parallel script families to maintain), but to **bypass the shell wrapper**: point `.mcp.json` at a Python interpreter directly (`py -3` / `python`) running `server.py`, and have the entry scripts self-bootstrap into the tool venv (`~/.wavefoundry/venv/bin/python` on POSIX, `Scripts\python.exe` on Windows). One portable mechanism instead of two. This is the gate — until the server starts and `docs-lint`/`wave-gate` run, nothing else is reachable.

### Bucket 2 — The per-OS distribution model (the gating decision)

A single committed `.mcp.json` / `.claude/settings.json` **cannot simultaneously serve** a mixed macOS/Linux + Windows team from one repo (C-3): the committed file reflects whichever OS last rendered it. The options:

- **(a) Re-render on first checkout per OS** — documented step; the renderer already supports per-OS hook forms, it only needs MCP + bin coverage added (Bucket 1). Simple, but a manual step and a source of "works on my machine" drift.
- **(b) Commit OS-suffixed surfaces** — e.g. ship both forms; the host picks. More files; depends on what Claude Code will read.
- **(c) Make the launchers identical cross-OS** — so the one committed file works everywhere. The bypass-the-wrapper approach in Bucket 1 (interpreter-direct command + self-bootstrapping scripts) is what makes (c) viable, and it is the most robust for mixed teams.

This is an ADR-shaped choice and should be run through **Evaluate decision** / recorded as an ADR before a wave is opened — it drives the shape of everything else.

### Bucket 3 — Process / dashboard lifecycle parity

A `tasklist /FI …`-based Windows branch for `dashboard_cmdline_pids` (M-1) and the missing `creationflags` on the one reindex spawn (M-2). Mechanical and low-risk — it mirrors patterns already present in `indexer.py` / `upgrade_lib.py`. Add `.gitattributes` (`* text=auto`, `*.py text eol=lf`, bash launchers `eol=lf`) (L-1) and a git-hook trampoline for Windows (M-3) in the same bucket.

### Bucket 4 — Verification you can trust

None of the existing `taskkill` / `tasklist` / `msvcrt` / `creationflags` branches have ever run on a real Windows host in CI — they are **unverified**. Credible Windows support requires a Windows smoke path (CI runner or, at minimum, a documented manual checklist exercising: MCP server start, `docs-lint`, a wave-gate open/close, a dashboard start/stop, an index build). The biggest hidden risk in this whole effort is shipping Windows branches that have never executed on Windows.

## Recommended sequencing

1. **Decide Bucket 2** (Evaluate decision → ADR). Everything else is shaped by it.
2. **Bucket 1** — portable entry points; this is what unblocks a Windows user at all.
3. **Bucket 3** — lifecycle parity + `.gitattributes` + git-hook trampoline.
4. **Bucket 4** — stand up the Windows smoke path; re-validate buckets 1–3 on a real host.
5. Track **L-2 (secrets scan off-macOS)** and **L-3 (DirectML auto-detect)** as separate, independently-valuable items — L-2 in particular also fixes Linux.

## Open questions for the operator

- Which Bucket-2 distribution model? (re-render-per-OS / OS-suffixed surfaces / portable-identical launchers)
- Is a Windows CI runner available, or is a manual smoke checklist the realistic verification path for now?
- Scope of the first wave: blocker-only (Buckets 1–2, "a Windows user can run it") vs. full parity (Buckets 1–4)?

## References

- Investigation date: 2026-06-17 (against framework `1.7.0`).
- Renderer: `render_platform_surfaces.py` (`launcher_command:101`, `render_mcp_json:896`, `render_bin_launchers:1038`, `render_git_hooks:1169`).
- Platform mapping: `docs/agents/platform-mapping.md`.
