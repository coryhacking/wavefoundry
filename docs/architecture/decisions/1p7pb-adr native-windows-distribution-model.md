# 1p7pb-adr — Native-Windows Distribution Model: Committed `python3` Command

Owner: Engineering
Status: amended
Last verified: 2026-06-27

## Context

Wavefoundry's stated support boundary is macOS + Linux native, **Windows via WSL2** — because the launcher/entry-point surface assumes a POSIX shell. The Python *engine* layer was hardened for native Windows in waves 1p6d5/1p6d6 (process kill via `taskkill`, locking via `msvcrt`, detached spawn via `CREATE_NEW_PROCESS_GROUP`, per-OS venv resolution, path normalization), so it already runs natively once started. What remains WSL2-only is **how the launcher/config surfaces are distributed** so a single committed repo works on macOS, Linux, *and* native Windows.

At the time of this decision, `.mcp.json` (+ per-host MCP configs) pointed `command` at a bash MCP-server wrapper under `.wavefoundry/bin/`, which native Windows cannot spawn; `.claude/settings.json` hook commands were emitted in the render-time OS's form. This was gap **C-3** in `docs/references/native-windows-support.md`. The wrapper was retired in wave 1p7tz when the `bin/*` shims consolidated into the cross-OS `wf` dispatcher. Wave 1p88t amended the command token to `python3` after native-Windows field feedback showed that Windows installs may provide `python3` and that standardizing on `python3` gives a cleaner committed surface.

**Forces & evidence** (a host/git spawns `command` via raw process spawn — no shell):

- A raw spawn resolves a **bare name on PATH** (Windows via PATHEXT) but **not** an explicit path, and **does not honor shell aliases** (aliases are interactive-shell-only; never consulted by `execvp`/`CreateProcess`/libuv).
- Real-machine checks: **macOS** has `python3`, not `python`, and no `uv` on PATH; native-Windows field testing showed `python3` can be the available command. The committed surface standardizes on `python3`; setup verifies it resolves and **fails clearly with guidance** when it does not (it does not create a shim or modify the Python install — amended wave 1p88t).
- **Project-local MCP works best in CLI hosts** (Claude Code, Codex, Antigravity CLI), which are terminal-launched and therefore **inherit the shell PATH**. GUI-launched hosts (Claude Desktop, Cursor.app) inherit only a minimal launchd/registry PATH.

This ADR was produced via `Evaluate decision` (red-team, three-stance comparison, adversarial refutation) plus a dedicated red-team of an interim `uv` proposal and real-machine PATH checks.

## Decision

Distribute launchers as a **single committed, byte-identical `python3` command**, backed by the shared Windows-safe bootstrap. Setup **verifies** `python3` resolves and **guides** the operator when it does not — it does not heal the environment.

> **Amendment (wave 1p88t):** the original decision had `wf setup` *create* a `python3` shim/symlink when only `python` existed. A full implementation review found that approach invasive and fragile (a Windows `.cmd` is not raw-spawnable by the host; a sibling `python3.exe` copy mutates the user's Python install; a POSIX symlink still needs PATH cooperation and a fresh shell). **Setup no longer creates a shim, symlink, copy, or PATH edit.** It is now **detect + guide only**: verify `python3` resolves to ≥3.11 and, if not, fail closed (setup) / warn (render, upgrade) with platform-aware guidance. Making `python3` resolvable is the operator's step. The committed-`python3` + byte-identical-config core of this decision is unchanged.

- Config-referenced launchers (`.mcp.json` + per-host MCP configs, `.claude/settings.json` hooks) name `command: "python3"` with the entry script as a project-root-relative arg — `python3 .wavefoundry/framework/scripts/server.py`. **Byte-identical on every OS** and committed (preserving zero-config attach + Codex auto-trust). (Git hooks were dropped in wave 1p88t — see the native-Windows reference M-3.)
- **`wf setup` verifies `python3` resolves to a ≥3.11 interpreter (detect + guide, amended wave 1p88t):** if `python3` already resolves, setup proceeds; if it does not, setup **fails closed** with concrete, platform-aware guidance (install via Scoop/Microsoft Store on Windows, your package manager or a symlink on POSIX) and does **not** modify the Python install or PATH. It never creates a `python3` or plain-`python` launcher.
- **Scope: CLI hosts.** Terminal-launched CLI hosts inherit the shell PATH, so a `python3` the operator has made resolvable is visible to them. **GUI-launched hosts are a documented residual** — they inherit a minimal PATH; for those (and for any host where `python3` is not on PATH), setup prints a **gitignored, per-machine absolute-venv-path config** as the fallback (`~/.wavefoundry/venv/bin/python` | `…\Scripts\python.exe`), which needs nothing on PATH.
- All OS-specific venv logic (`bin/python` vs `Scripts\python.exe`, activation into `~/.wavefoundry/venv`) collapses into **one stdlib-only bootstrap helper, first-line in every entry script**. `python3` may resolve to a system interpreter; the bootstrap activates the tool venv underneath.

**The decision serves two co-equal goals:**

- **(A) native cross-OS spawnability** — one committed checkout is correct on macOS, Linux, and native Windows (for CLI hosts);
- **(B) a single runtime execution surface** — *exactly one* venv-resolution implementation (`activate_tool_venv`; wave 1p802 replaced the original `reexec_into_tool_venv` with in-process activation), with **no config, launcher, hook body, or spawner re-deriving the venv path**. Goal B's success test is a **standing scan that fails if any file other than the shared helper contains a `Scripts`-vs-`bin` / `WAVEFOUNDRY_TOOL_VENV` branch**.

Every runtime-entry surface converges on the one helper + the `python3` command — the `render_platform_surfaces` MCP/hook configs, the Codex config in **`render_agent_surfaces.py`** (`CODEX_MCP_CONFIG_TOML`, a *separate* file), the hand-committed `.air/mcp.json`, the `wf` shim pair, and the dev-facing `run_tests.py` + `wave-dashboard`. (Git hooks were dropped in wave 1p88t.)

## Consequences

**Positive:**

- One **committed, byte-identical** config (`command: "python3"`) — zero-config attach + Codex auto-trust preserved; nothing to re-render per OS.
- `python3` is standard on macOS/Linux and the chosen native-Windows standard for Wavefoundry installs. Setup verifies it resolves and guides the operator if not; it does not create a shim or modify the Python install (amended wave 1p88t).
- The bootstrap activation is PATH-independent and authoritative, so even if `python3` resolves to a system interpreter, the tool venv packages are used.
- The scattered venv resolvers + the `launcher_command` `os.name` branch consolidate into one bootstrap; the dead `_bat_venv_block` is removed. Net maintenance burden goes **down**.

**Negative / tradeoffs:**

- **Setup never mutates the environment** (no `python3` shim/symlink, no copy into a Python install, no PATH edit) — amended wave 1p88t. The cost moves to the operator: when `python3` does not resolve, setup fails closed with guidance and the operator must make `python3` resolve (or adopt the per-machine absolute-venv-path fallback) before setup completes.
- **GUI-launched hosts are a residual**: they don't inherit the shell PATH, so an operator-provided `python3` may be invisible. The fallback is a gitignored, per-machine absolute-venv-path config for those hosts/machines — which trades the committed string for PATH-independence on that machine.
- `python3` must be ≥3.11 — setup verifies and fails loud otherwise.
- Net-new load-bearing code: the stdlib-only self-bootstrap (a footgun if an entry forgets the first-line import — mitigated by the adoption-scan test).

**Constraints imposed:**

- **Three interpreter tiers (avoids the setup circularity):** (1) **setup** runs on the **system `python3` interpreter** and creates the venv; (2) **committed configs + post-setup bin shims** name `python3`, which **activates the venv in-process** (wave 1p802: `site.addsitedir`, not a re-exec — see below); (3) every **inner/child spawn after bootstrap** uses `sys.executable` (after in-process activation this is the system interpreter — the re-spawned framework script self-activates first-line, so it reaches the venv packages too), never a re-resolved interpreter token. The first-line bootstrap **no-ops when the venv is absent** and never blocks `setup_index.ensure_deps()` from creating it.
- When the **operator** makes `python3` resolve, it must be a **real executable on PATH (shim/symlink), never a shell alias** — aliases are not honored by raw process spawn. (Setup itself no longer creates this — amended wave 1p88t — it only verifies and guides.)
- **Tier-2 mechanism — in-process activation, no re-exec (amended wave 1p802).** The original bootstrap **re-exec'd** into the venv interpreter — `os.execv` on POSIX (in-place, same PID) but a `subprocess` child on Windows (no in-place exec). An MCP host spawns ONE process and owns its stdio; the Windows child became a second process holding the same stdout pipe → broken pipe / orphan on reconnect (1.9.0 field report). The bootstrap now **activates the venv in the already-running process** (`venv_bootstrap.activate_tool_venv` → `site.addsitedir` of the venv site-packages), keeping a SINGLE host-spawned process on every OS — the `os.execv`-vs-`subprocess` per-OS split is gone. Trade-off: the re-exec was robust to a Python-version upgrade for free; in-process activation cannot load ABI-incompatible compiled deps, so a **version guard** (read `pyvenv.cfg`; mismatch ⇒ "run `wf setup`" + `sys.exit`) fails loud instead of crashing.
- The bootstrap is **stdlib-only**, runs as the genuine first statement **before** `import server_impl`, and writes diagnostics to **stderr only** (any stdout byte before `mcp.run()` corrupts the JSON-RPC handshake); no-op when already the venv python.
- `python3` resolution is **verified** (not healed) by a **reusable `ensure_python_resolves()`** run at **setup, every render, and every upgrade** (called from `setup_wavefoundry.py`, `render_platform_surfaces`, and `upgrade_wavefoundry`): no-op if `python3` already resolves to ≥3.11; otherwise it emits platform-aware guidance and **fails closed at setup (strict)** / warns non-fatally at render/upgrade. It does **not** create a shim/symlink, copy into a Python install, or edit PATH (amended wave 1p88t).
- Git-hook bodies migrate onto the same bootstrap; add a `.gitattributes` pinning `*.py` + launchers to `eol=lf` (autocrlf shebang corruption).
- **Single-resolver scan test (goal B invariant):** a standing test fails if any file other than the shared bootstrap resolves the venv path; intentional exceptions are explicit allowlist entries with rationale.
- A test asserts no committed config references a pathed launcher — **scanning the on-disk config set** (`.mcp.json`, `.cursor`, `.junie`, `.agents`, **`.codex/config.toml`**, **`.air/mcp.json`**) — and that the committed `command` (`python3`) is byte-identical across render hosts.
- The Codex config is emitted from `render_agent_surfaces.py`, a *different* file from `render_platform_surfaces.py`; both must be flipped. `.air/mcp.json` has no renderer — bring it under one (or flip + guard the committed file).

## Open Verification (hard gate before claiming native-Windows support)

- CLI-host MCP attach via `command: "python3"` on native Windows and macOS/Linux, confirming the setup command/PATH is visible to the host spawn. (Git hooks were dropped in wave 1p88t, so the former git-hook-fire check no longer applies.)
- The `subprocess`-relay re-exec preserves the host stdio pipe (handshake uncorrupted; `os.execv` not used on Windows).
- `python3` resolves to ≥3.11; the no-Python case fails loud.
- The GUI-host residual + the gitignored absolute-venv-path fallback are exercised at least once (a GUI host where the symlink is invisible → fallback config works).

## Revisit When

- GUI hosts become the primary use and the launchd-PATH residual bites broadly — promote the gitignored absolute-venv-path config to the default for those, accepting the per-machine render.
- A different single cross-OS Python entry becomes more reliable than `python3`.
- A host appears that can only spawn a single repo-relative executable (not a PATH token), or a `wf serve` entry becomes necessary for another reason — then reconsider a per-OS launcher, accepting the loss of a byte-identical committed `command` and a Windows `cmd.exe` hop.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| **`uv` as the universal command (setup installs uv on PATH)** | Red-teamed and rejected: `uv` is *absent* on the team's machines and is a network-installed runtime dependency. The committed-string benefit is delivered by `python3` without making uv a startup prerequisite. |
| **Per-machine absolute-venv-path as the *default*** | Strictly robust (no PATH dependency, works on GUI hosts) but **gitignored/per-machine** — sacrifices the committed shared config + Codex auto-trust. **Retained as the GUI-host *fallback*, not the default.** |
| **Single bare `py -3` token** | Windows-only; a committed config holds one cross-OS command. |
| **Shell alias for `python3`** | Not honored by raw process spawn (interactive-shell-only). When an operator makes `python3` resolve, a real shim/symlink on PATH is required — an alias will not work. |
| **Route the committed MCP `command` through the `wf` dispatcher (`wf serve`) instead of `python3 server.py`** | Rejected; re-confirmed wave 1p88t. (1) **Not a portable token:** `wf` is two per-OS repo-relative files — `.wavefoundry/bin/wf` (bash shebang) vs `.wavefoundry\bin\wf.cmd` — so one byte-identical committed `command` cannot name it across macOS/Linux/Windows (defeats Goal A); neither is a PATH token the way `python3` is. (2) **Adds a Windows process hop:** `wf.cmd` runs under `cmd.exe`, which then spawns `python3` — a second process that reintroduces the Windows extra-process class wave 1p802 eliminated, plus a `cmd.exe` console window working against the 1p88t console-suppression goal. (3) **No venv benefit:** `wf_cli.py` calls the *same* in-process `activate_tool_venv()`; there is no re-exec / "venv reload" left to avoid since 1p802, and interpreter/venv resolution is already centralized in that one helper called by **both** `server.py` and `wf_cli.py`, so there is no duplication to consolidate. (4) **`wf` is the no-MCP fallback by design** — terminal/CI use when no MCP host is attached; it has no `serve`/`mcp` subcommand, and adding one would only wrap the shared bootstrap in an extra layer. |

## References

- `docs/references/native-windows-support.md` — gap taxonomy (C-1…C-3, M-1…M-3, L-1…L-4)
- `.wavefoundry/framework/scripts/setup_wavefoundry.py` — verifies `python3` resolution (detect + guide; no shim creation) and prints the GUI-host gitignored absolute-path fallback render
- `.wavefoundry/framework/scripts/render_platform_surfaces.py` — `launcher_command`, `render_mcp_json` + per-host MCP renderers, `render_bin_launchers`, `write_hook_bundle` (agent-host hooks). (Git-hook rendering was removed in wave 1p88t; `remove_git_hooks` cleans up prior renders.)
- `.wavefoundry/framework/scripts/render_agent_surfaces.py` — `CODEX_MCP_CONFIG_TOML` (separate render path); `.air/mcp.json` has no renderer
- Scattered venv resolvers to consolidate: `server_impl._preferred_python`, `upgrade_wavefoundry._preferred_python`, `indexer` (lancedb), `build_pack._reexec_with_venv_if_needed`, `run_tests._test_runner_python`, the rendered hook-body `_venv_python_path`
- `.wavefoundry/framework/scripts/server.py` — entry to gain the first-line bootstrap; `setup_index._reexec_with_venv_if_needed` — the re-exec pattern to generalize
- Waves 1p6d5 / 1p6d6 — native-Windows exec hardening (engine layer)
- `.wavefoundry/framework/seeds/176-evaluate-decision.prompt.md` — the decision process used
