# 1p7pb-adr — Native-Windows Distribution Model: Committed `python` Command, Setup-Symlinked

Owner: Engineering
Status: accepted
Last verified: 2026-06-25

## Context

Wavefoundry's stated support boundary is macOS + Linux native, **Windows via WSL2** — because the launcher/entry-point surface assumes a POSIX shell. The Python *engine* layer was hardened for native Windows in waves 1p6d5/1p6d6 (process kill via `taskkill`, locking via `msvcrt`, detached spawn via `CREATE_NEW_PROCESS_GROUP`, per-OS venv resolution, path normalization), so it already runs natively once started. What remains WSL2-only is **how the launcher/config surfaces are distributed** so a single committed repo works on macOS, Linux, *and* native Windows.

At the time of this decision, `.mcp.json` (+ per-host MCP configs) pointed `command` at a bash MCP-server wrapper under `.wavefoundry/bin/`, which native Windows cannot spawn; `.claude/settings.json` hook commands were emitted in the render-time OS's form. This was gap **C-3** in `docs/references/native-windows-support.md`. (The wrapper was retired in wave 1p7tz when the `bin/*` shims consolidated into the cross-OS `wf` dispatcher; the MCP configs now name `python` directly per this ADR.)

**Forces & evidence** (a host/git spawns `command` via raw process spawn — no shell):

- A raw spawn resolves a **bare name on PATH** (Windows via PATHEXT) but **not** an explicit path, and **does not honor shell aliases** (aliases are interactive-shell-only; never consulted by `execvp`/`CreateProcess`/libuv).
- Real-machine checks: **macOS** has `python3`, not `python`, and no `uv` on PATH; python.org-**Windows** has `python`, not `python3`. No bare Python name is present on *all* machines as-is.
- **Project-local MCP works best in CLI hosts** (Claude Code, Codex, Antigravity CLI), which are terminal-launched and therefore **inherit the shell PATH**. GUI-launched hosts (Claude Desktop, Cursor.app) inherit only a minimal launchd/registry PATH.

This ADR was produced via `Evaluate decision` (red-team, three-stance comparison, adversarial refutation) plus a dedicated red-team of an interim `uv` proposal and real-machine PATH checks.

## Decision

Distribute launchers as a **single committed, byte-identical `python` command, made resolvable per-OS at setup**, backed by the shared Windows-safe bootstrap.

- Config-referenced launchers (`.mcp.json` + per-host MCP configs, `.claude/settings.json` hooks, git hooks) name `command: "python"` with the entry script as a project-root-anchored relative arg — `python .wavefoundry/framework/scripts/server.py --root .`. **Byte-identical on every OS** and committed (preserving zero-config attach + Codex auto-trust).
- **`setup_wavefoundry.py` makes `python` resolve to a ≥3.11 interpreter:** on Windows the python.org installer already provides it (verify); on macOS/Linux, where only `python3` exists, setup creates a **symlink** (`python` → the tool venv's `python`, or → `python3`) in a setup-owned PATH dir and ensures that dir is on PATH. **A symlink, not a shell alias** — aliases are not honored by a raw spawn.
- **Scope: CLI hosts.** Terminal-launched CLI hosts inherit the shell PATH, so the setup symlink is visible to them. **GUI-launched hosts are a documented residual** — they inherit a minimal PATH; for those, setup can render a **gitignored, per-machine absolute-venv-path config** as the fallback (`~/.wavefoundry/venv/bin/python` | `…\Scripts\python.exe`), which needs nothing on PATH.
- All OS-specific venv logic (`bin/python` vs `Scripts\python.exe`, re-exec into `~/.wavefoundry/venv`) collapses into **one stdlib-only bootstrap helper, first-line in every entry script**. `python` may resolve to a system interpreter (esp. on Windows); the bootstrap re-execs into the tool venv underneath.

**The decision serves two co-equal goals:**

- **(A) native cross-OS spawnability** — one committed checkout is correct on macOS, Linux, and native Windows (for CLI hosts);
- **(B) a single runtime execution surface** — *exactly one* venv-resolution implementation (`activate_tool_venv`; wave 1p802 replaced the original `reexec_into_tool_venv` with in-process activation), with **no config, launcher, hook body, or spawner re-deriving the venv path**. Goal B's success test is a **standing scan that fails if any file other than the shared helper contains a `Scripts`-vs-`bin` / `WAVEFOUNDRY_TOOL_VENV` branch**.

Every runtime-entry surface converges on the one helper + the `python` command — the `render_platform_surfaces` MCP/hook configs, the Codex config in **`render_agent_surfaces.py`** (`CODEX_MCP_CONFIG_TOML`, a *separate* file), the hand-committed `.air/mcp.json`, the nine `bin/*` shims (thin `exec python <script>` forwarders), the git hooks, and the dev-facing `run_tests.py` + `wave-dashboard`.

## Consequences

**Positive:**

- One **committed, byte-identical** config (`command: "python"`) — zero-config attach + Codex auto-trust preserved; nothing to re-render per OS.
- `python` is *present-but-misnamed* on macOS/Linux, so the fix is a network-free **symlink** (a rename), not a network-installed runtime dependency — lighter than `uv`, no new SPOF, no throwaway resolution hop.
- The bootstrap re-exec is PATH-independent and authoritative, so even if `python` resolves to a system interpreter, the venv is used.
- The scattered venv resolvers + the `launcher_command` `os.name` branch consolidate into one bootstrap; the dead `_bat_venv_block` is removed. Net maintenance burden goes **down**.

**Negative / tradeoffs:**

- **Setup mutates the shell environment** (creates a `python` symlink + ensures its dir is on PATH) on macOS/Linux — idempotent, transparent, network-free, but a new setup responsibility, and it requires a new shell session to take effect.
- **GUI-launched hosts are a residual**: they don't inherit the shell PATH, so the symlink may be invisible. The fallback is a gitignored, per-machine absolute-venv-path config for those hosts/machines — which trades the committed string for PATH-independence on that machine.
- `python` must be ≥3.11 and not python2 — setup verifies before/after symlinking and fails loud otherwise.
- Net-new load-bearing code: the stdlib-only self-bootstrap (a footgun if an entry forgets the first-line import — mitigated by the adoption-scan test).

**Constraints imposed:**

- **Three interpreter tiers (avoids the setup circularity):** (1) **setup** runs on the **system interpreter** (`python3`→`python` fallback) *before* the symlink exists — it creates the venv *then* the `python` symlink, so `setup-wavefoundry`/`setup-index` must **not** be flipped to bare `python` (the canonical fresh-bootstrap is `python3 setup_wavefoundry.py`); (2) **committed configs + post-setup bin shims** name `python`, which **activates the venv in-process** (wave 1p802: `site.addsitedir`, not a re-exec — see below); (3) every **inner/child spawn after bootstrap** uses `sys.executable` (after in-process activation this is the *system* interpreter — the re-spawned framework script self-activates first-line, so it reaches the venv packages too), never a re-resolved `python3`/`python` token. The first-line bootstrap **no-ops when the venv is absent** and never blocks `setup_index.ensure_deps()` from creating it.
- A **symlink (real executable on PATH), never a shell alias** — aliases are not honored by raw process spawn.
- **Tier-2 mechanism — in-process activation, no re-exec (amended wave 1p802).** The original bootstrap **re-exec'd** into the venv interpreter — `os.execv` on POSIX (in-place, same PID) but a `subprocess` child on Windows (no in-place exec). An MCP host spawns ONE process and owns its stdio; the Windows child became a second process holding the same stdout pipe → broken pipe / orphan on reconnect (1.9.0 field report). The bootstrap now **activates the venv in the already-running process** (`venv_bootstrap.activate_tool_venv` → `site.addsitedir` of the venv site-packages), keeping a SINGLE host-spawned process on every OS — the `os.execv`-vs-`subprocess` per-OS split is gone. Trade-off: the re-exec was robust to a Python-version upgrade for free; in-process activation cannot load ABI-incompatible compiled deps, so a **version guard** (read `pyvenv.cfg`; mismatch ⇒ "run `wf setup`" + `sys.exit`) fails loud instead of crashing.
- The bootstrap is **stdlib-only**, runs as the genuine first statement **before** `import server_impl`, and writes diagnostics to **stderr only** (any stdout byte before `mcp.run()` corrupts the JSON-RPC handshake); no-op when already the venv python.
- `python` resolution is verified-and-healed by a **reusable `ensure_python_resolves()`** run at **setup, every render, and every upgrade** (called from `setup_wavefoundry.py`, `render_platform_surfaces`, and `upgrade_wavefoundry`): no-op if `python` already resolves to ≥3.11; warn (don't clobber) if it resolves to something else; else (macOS/Linux) symlink `~/.local/bin/python` → the stable `python3` + ensure `~/.local/bin` on PATH; **re-heal a dangling/stale symlink** so `python` stays correct across Python upgrades. Strict at setup (no Python ⇒ fail loud); self-heal + non-fatal warn at render/upgrade. Windows needs no shim (`python` native, installer-maintained).
- Git-hook bodies migrate onto the same bootstrap; add a `.gitattributes` pinning `*.py` + launchers to `eol=lf` (autocrlf shebang corruption).
- **Single-resolver scan test (goal B invariant):** a standing test fails if any file other than the shared bootstrap resolves the venv path; intentional exceptions are explicit allowlist entries with rationale.
- A test asserts no committed config references a pathed launcher — **scanning the on-disk config set** (`.mcp.json`, `.cursor`, `.junie`, `.agents`, **`.codex/config.toml`**, **`.air/mcp.json`**) — and that the committed `command` (`python`) is byte-identical across render hosts.
- The Codex config is emitted from `render_agent_surfaces.py`, a *different* file from `render_platform_surfaces.py`; both must be flipped. `.air/mcp.json` has no renderer — bring it under one (or flip + guard the committed file).

## Open Verification (hard gate before claiming native-Windows support)

- CLI-host MCP attach via `command: "python"` + a git-hook fire, on a genuine python.org-Windows install **and** macOS post-symlink (terminal-launched Claude Code), confirming the setup symlink/PATH is visible to the host spawn.
- The `subprocess`-relay re-exec preserves the host stdio pipe (handshake uncorrupted; `os.execv` not used on Windows).
- `python` resolves to ≥3.11 with the symlink in place; the no-Python case fails loud.
- The GUI-host residual + the gitignored absolute-venv-path fallback are exercised at least once (a GUI host where the symlink is invisible → fallback config works).

## Revisit When

- GUI hosts become the primary use and the launchd-PATH residual bites broadly — promote the gitignored absolute-venv-path config to the default for those, accepting the per-machine render.
- A single cross-OS Python entry becomes reliably present without a setup symlink.

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| **`uv` as the universal command (setup installs uv on PATH)** | Red-teamed and rejected: `uv` is *absent* on the team's machines (a network install of a new runtime SPOF), is a throwaway resolution hop (the bootstrap re-execs into the venv anyway), and is **worst on the GUI-host PATH axis** while `python` is merely present-but-misnamed (a network-free symlink). uv's only net gain — a committed string — is also delivered by `python` without uv's costs. |
| **Per-machine absolute-venv-path as the *default*** | Strictly robust (no PATH dependency, works on GUI hosts) but **gitignored/per-machine** — sacrifices the committed shared config + Codex auto-trust. **Retained as the GUI-host *fallback*, not the default.** |
| **Single bare `python3`/`py -3` token** | No single bare token works on all machines (`python3` absent on Windows; `py` Windows-only); a committed config holds one `command`. |
| **Shell alias `python=python3`** | Not honored by raw process spawn (interactive-shell-only). A symlink is required. |

## References

- `docs/references/native-windows-support.md` — gap taxonomy (C-1…C-3, M-1…M-3, L-1…L-4)
- `.wavefoundry/framework/scripts/setup_wavefoundry.py` — gains the `python` verify + symlink + PATH responsibility (macOS/Linux); the GUI-host gitignored absolute-path fallback render
- `.wavefoundry/framework/scripts/render_platform_surfaces.py` — `launcher_command`, `render_mcp_json` + per-host MCP renderers, `render_bin_launchers` (the dead `_bat_venv_block`), `write_hook_bundle` (the `.sh`/`.cmd` shims to retire), git-hook source
- `.wavefoundry/framework/scripts/render_agent_surfaces.py` — `CODEX_MCP_CONFIG_TOML` (separate render path); `.air/mcp.json` has no renderer
- Scattered venv resolvers to consolidate: `server_impl._preferred_python`, `upgrade_wavefoundry._preferred_python`, `indexer` (lancedb), `build_pack._reexec_with_venv_if_needed`, `run_tests._test_runner_python`, the rendered hook-body `_venv_python_path`
- `.wavefoundry/framework/scripts/server.py` — entry to gain the first-line bootstrap; `setup_index._reexec_with_venv_if_needed` — the re-exec pattern to generalize
- Waves 1p6d5 / 1p6d6 — native-Windows exec hardening (engine layer)
- `.wavefoundry/framework/seeds/176-evaluate-decision.prompt.md` — the decision process used
