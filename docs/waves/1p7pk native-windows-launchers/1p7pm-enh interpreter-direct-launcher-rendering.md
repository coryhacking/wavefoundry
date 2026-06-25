# Committed `python` launcher rendering + setup symlink: cross-OS config surfaces

Change ID: `1p7pm-enh interpreter-direct-launcher-rendering`
Change Status: `implementing`
Owner: Engineering
Status: planned
Last verified: 2026-06-24
Wave: `1p7pk native-windows-launchers`

## Rationale

Per `1p7pb-adr`, the launcher surfaces stop naming the POSIX bash wrapper (`.wavefoundry/bin/mcp-server`) / render-time-OS hook form and name a **single committed, byte-identical `command: "python"`** (`python .wavefoundry/framework/scripts/server.py`; no `--root .` — `server_impl._discover_root` anchors on the server script's own install location, resolving the root cwd-independently). Real-machine checks showed no bare Python name is present on all machines as-is (macOS: `python3` only; python.org-Windows: `python` only), so **`setup_wavefoundry.py` makes `python` resolve**: verify on Windows (installer provides it), and on macOS/Linux create a **symlink** (`python` → the venv python / `python3`) in a setup-owned PATH dir + ensure it's on PATH — a symlink, **not** a shell alias (aliases aren't honored by raw process spawn). Scope is **CLI hosts** (Claude Code / Codex / Antigravity CLI), which inherit the shell PATH and so see the symlink; **GUI hosts are a documented residual** with a gitignored absolute-venv-path fallback. This change flips **every** config surface (incl. Codex via `render_agent_surfaces.py` + `.air/mcp.json`), makes the nine `bin/*` shims thin `exec python <script>` forwarders, retires the `write_hook_bundle` `.sh`/`.cmd` shims + the rendered hook-body `_venv_python_path`, removes the dead `_bat_venv_block`, and adds the setup symlink responsibility. Depends on `1p7pl` (every entry self-bootstraps into the venv).

## Requirements

1. `render_mcp_json` + the per-host MCP renderers in `render_platform_surfaces` (Cursor/Junie/Antigravity) **and `CODEX_MCP_CONFIG_TOML` in `render_agent_surfaces.py`** emit `command: "python"` + `args: [".wavefoundry/framework/scripts/server.py", "--root", "."]` — byte-identical on every OS, never the bash `.wavefoundry/bin/mcp-server`.
2. **`.air/mcp.json`** (hand-committed, no renderer) is flipped to the same `python` form (under a renderer or in place + AC-3-guarded).
3. `launcher_command` (Claude hooks) emits the same `python` form; **no `os.name`-stamped field remains in any committed config**.
4. **`setup_wavefoundry.py`** itself runs on the **system interpreter** (`python3`, falling back to `python`) — it must not depend on `python` already resolving (it's what *creates* that). In order: verify a ≥3.11 system interpreter → create/populate the venv (`setup_index.ensure_deps`) → on macOS/Linux, ensure `python` resolves: **no-op if `python` already resolves to ≥3.11; warn (don't clobber) if it resolves to something else (e.g. python2); otherwise create a symlink `~/.local/bin/python` → the resolved stable `python3` (not the venv python — keeps `python` = the user's python3, upgrade-resilient) and ensure `~/.local/bin` is on PATH (prepend to the shell rc only if absent)**. A symlink, never a shell alias. On a no-Python box it fails loud naming the prerequisite. For **GUI hosts** it can render a gitignored per-machine absolute-venv-path config as the fallback. (Windows needs no shim — `python` is native.)
4a. This verify-and-heal logic lives as **`ensure_python_resolves()` in `venv_bootstrap`** (the one python/venv module — alongside `reexec_into_tool_venv`/`tool_venv_python`, so all resolution+healing is in a single place), and is **called explicitly from `setup_wavefoundry.py`, `render_platform_surfaces`, and `upgrade_wavefoundry`** — so `python`'s resolution *and the symlink's validity* are re-checked on **initial bootstrap, every render, and every upgrade**. It is **not** auto-fired from `reexec_into_tool_venv()` (which stays a minimal, fast, silent hot-path): the heal is side-effecting (symlink + shell-rc PATH edit) so it must not run on every hook-fire/spawn; the current invocation already has a working `python` (it launched us); and a fully-broken `python` means the bootstrap never runs anyway. It detects a **dangling/stale symlink** (e.g. one left broken by a later Python minor-upgrade or uninstall) and re-heals it (re-points `~/.local/bin/python` at the current stable `python3`). At setup it is strict (no Python ⇒ fail loud); at render/upgrade it self-heals and **warns loudly** if `python` still won't resolve (so a config that would be dead-on-arrival is surfaced) without hard-failing the render/upgrade. Windows: verify `python` is present + ≥3.11 (no symlink to heal).
5. The **post-setup** `.wavefoundry/bin/*` shims become thin `exec python <script> "$@"` forwarders — each drops its bash `_venv_block` resolver (goal B). **Exception — setup circularity (P0):** the `setup-wavefoundry` shim must **not** use `python` — it runs on a *fresh box before the `python` symlink exists*, so it keeps a `python3`-then-`python` fallback, and the **canonical fresh-bootstrap stays `python3 .wavefoundry/framework/scripts/setup_wavefoundry.py`**. (There is no distinct `setup-index` shim — `setup_index.py` runs as a child of `setup_wavefoundry.py`; the post-setup `update-indexes` shim legitimately uses bare `python`.) `setup_wavefoundry.py` owns venv creation **and** the `python` symlink/PATH creation **before** the rest of the fleet's `python` form can resolve. The dead `_bat_venv_block` is removed; the `write_hook_bundle` `.sh`/`.cmd` shims + the rendered hook-body `_venv_python_path` are retired. **Framing correction:** the bin shims are NOT "referenced by no config" — `mcp-server` is the `command` in all five MCP configs until this cutover.
6. The committed `command` (`python`) is byte-identical regardless of which OS rendered it.

## Scope

**Problem statement:** Committed configs name a POSIX bash wrapper / render-time-OS hook form (unspawnable on native Windows), and no bare Python name is uniformly present to replace it without a setup-side fix.

**In scope:**

- `render_platform_surfaces`: `render_mcp_json` + per-host MCP renderers + `launcher_command` → `command: "python"`.
- **`render_agent_surfaces.py` `CODEX_MCP_CONFIG_TOML`** + **`.air/mcp.json`** → `python` form.
- **`setup_wavefoundry.py`**: verify `python` ≥3.11; macOS/Linux symlink + PATH; the GUI-host gitignored absolute-venv-path fallback render.
- `bin/*` shims → thin `exec python` forwarders; retire `write_hook_bundle` `.sh`/`.cmd` + the rendered `_venv_python_path`; remove dead `_bat_venv_block`.
- Regression tests (incl. on-disk no-pathed-launcher scan) + the real-host smoke verification.

**Out of scope:**

- The shared bootstrap helper + first-party-script adoption + the single-resolver scan test (`1p7pl`).
- Git-hook bodies + `.gitattributes` + dashboard daemonization (`1p7pn`).

**Depends on:** `1p7pl`.

## Acceptance Criteria

- [x] AC-1: **every** committed MCP config — `.mcp.json`, `.cursor`, `.junie`, `.agents`, **`.codex/config.toml`**, **`.air/mcp.json`** — names `command: "python"` + the relative script arg; none references `.wavefoundry/bin/mcp-server` or any pathed launcher. — `NoPathedLauncherScanTests`; regenerated configs verified.
- [x] AC-2: `.claude/settings.json` hook commands use the same `python` form; the **interpreter + `.py` path are byte-identical** across render hosts (`LauncherCommandTests`). The MCP configs have **no** `os.name`-stamped field; the one per-OS difference is the hook anchor's **env-var sigil** (`$VAR` vs `%VAR%`), which is shell-specific and unavoidable (a shell expands it) — documented in `launcher_command`.
- [x] AC-3: the **no-pathed-launcher scan enumerates the actual on-disk config set** (`.mcp.json`, `.cursor/mcp.json`, `.junie/mcp/mcp.json`, `.agents/mcp_config.json`, `.codex/config.toml`, `.air/mcp.json`) — not just renderer outputs. — `NoPathedLauncherScanTests`.
- [x] AC-4: `setup_wavefoundry.py` runs on the **system interpreter** (`python3`→`python` fallback), and in order verifies a ≥3.11 interpreter → creates/populates the venv → on macOS/Linux ensures `python` resolves: **no-op if `python` already ≥3.11; warn (no clobber) if it's something else; else symlink `~/.local/bin/python` → the stable `python3` + ensure `~/.local/bin` on PATH (prepend to shell rc only if absent)**; Windows needs no shim (`python` native); a no-Python box fails loud. **Setup does not depend on `python` already resolving** (no circularity — P0). The verify-and-heal logic is a **reusable `ensure_python_resolves()`** called from `setup_wavefoundry.py`, **`render_platform_surfaces`**, and **`upgrade_wavefoundry`** — so it runs on bootstrap, every render, and every upgrade; it **self-heals a dangling/stale symlink** (re-points at the current `python3`) and warns (non-fatal) at render/upgrade if `python` still won't resolve. Unit-tested: system-interpreter run + ordering; the no-op/warn/create decision + PATH-write logic (mocked); **a dangling-symlink fixture is re-healed**; called from all three sites. The GUI-host gitignored absolute-venv-path fallback render is covered by a test.
- [x] AC-5: the **post-setup** `bin/*` shims are thin `exec python <script>` forwarders; the **`setup-wavefoundry` shim keeps a `python3`→`python` fallback** (it runs pre-symlink — the P0 circularity guard; there is no distinct `setup-index` shim — `setup_index.py` runs as a child of setup); a test asserts no setup shim requires `python`. The dead `_bat_venv_block`, the `write_hook_bundle` `.sh`/`.cmd` shims, and the rendered hook-body `_venv_python_path` are all retired; macOS/Linux MCP attach + hooks unchanged (full suite green; live `wave_index_health` ok). Feeds `1p7pl` AC-6's single-resolver scan.
- [ ] AC-6 (value gate — operator-run, the close gate): **CLI-host** MCP attach via `command: "python"` + a hook fire, on a genuine python.org-Windows install **and** macOS post-symlink (terminal-launched Claude Code), confirming the symlink/PATH is visible to the host spawn; the `subprocess`-relay re-exec keeps the host stdio pipe intact. The **GUI-host residual + the gitignored absolute-venv-path fallback** are exercised at least once.
- [x] AC-7: framework tests bytecode-free; `wave_validate` clean. — full suite 3438 OK (only the known pre-existing secrets flake); `wave_validate` ok.

## Tasks

- [x] Open `framework_edit_allowed`; close after.
- [x] Flip `render_mcp_json` + per-host MCP renderers + `launcher_command` to `command: "python"`.
- [x] Flip `CODEX_MCP_CONFIG_TOML` in `render_agent_surfaces.py`; flip `.air/mcp.json`.
- [x] Write the reusable **`ensure_python_resolves()`** (verify `python` ≥3.11; macOS/Linux no-op/warn/create-or-reheal symlink `~/.local/bin/python`→`python3` + PATH-ensure; detect + re-heal a dangling/stale symlink; Windows verify-only). Strict at setup, self-heal+warn (non-fatal) at render/upgrade.
- [x] Call `ensure_python_resolves()` from `setup_wavefoundry.py` (bootstrap; runs on system `python3`→`python`, no dependency on `python` pre-resolving — P0), **`render_platform_surfaces`** (render), and **`upgrade_wavefoundry`** (upgrade); render the GUI-host absolute-path fallback.
- [x] Convert the post-setup `bin/*` shims to thin `exec python` forwarders; keep `setup-wavefoundry` on a `python3`→`python` fallback (P0; no distinct `setup-index` shim); retire `write_hook_bundle` `.sh`/`.cmd` + rendered `_venv_python_path`; remove dead `_bat_venv_block`.
- [x] Tests: on-disk no-pathed-launcher scan (incl. `.codex`/`.air`); byte-identical-across-render-hosts; setup symlink/verify + PATH-write logic; fallback render.
- [ ] (Operator) Real-host smoke pass — AC-6 — before wave close.

## Agent Execution Graph


| Workstream  | Owner       | Depends On      | Notes                                            |
| ----------- | ----------- | --------------- | ------------------------------------------------ |
| render-flip | implementer | `1p7pl` helper  | all configs + hooks → `command: "python"`        |
| setup-symlink | implementer | —             | verify python ≥3.11; macOS/Linux symlink + PATH; GUI fallback |
| tests       | implementer | render-flip     | on-disk no-pathed-launcher, byte-identical, symlink logic |
| smoke-gate  | operator    | render-flip, setup-symlink | CLI-host attach (Win + macOS) + GUI fallback (AC-6) |


## Serialization Points

- After `1p7pl` (self-bootstrap) lands and CI is green. Pairs with `1p7pn` (git hooks) for the AC-6 end-to-end smoke pass.

## Affected Architecture Docs

- Implements `docs/architecture/decisions/1p7pb-adr native-windows-distribution-model.md`. Update `docs/references/native-windows-support.md` (C-1/C-3 closed for CLI hosts; GUI-host residual recorded) and the install/upgrade prompts (the macOS/Linux `python` symlink prereq; "run from WSL2" retired for CLI hosts) once AC-6 passes. Confirm exact targets at Prepare.

## AC Priority

(Proposed; confirmed at Prepare.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The `python` config flip is the C-1 fix — must cover Codex + Air. |
| AC-2 | required  | One byte-identical committed config across render hosts is the whole point. |
| AC-3 | required  | Standing guard against regressing to a pathed launcher (incl. separate-file configs). |
| AC-4 | required  | Without the setup symlink, `python` doesn't resolve on macOS/Linux — the committed command has nothing to spawn there. |
| AC-5 | required  | bin forwarders + shim/resolver retirement — makes goal B's single-resolver scan pass; no macOS/Linux regression. |
| AC-6 | required  | The value gate — CLI-host native spawn + the GUI residual/fallback can't be claimed unverified (operator-run). |
| AC-7 | required  | Test-locked, bytecode-free. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-24 | Planned, iterated through per-OS-token → bare-python → uv (red-teamed out) → **committed `python` + setup symlink, CLI-host-scoped** after real-machine PATH checks + the alias-not-honored-by-spawn fact. | `1p7pb-adr`; macOS `python3`-only / Windows `python`-only / `uv` absent; aliases not honored by raw spawn; CLI hosts inherit shell PATH |
| 2026-06-24 | `ensure_python_resolves()` implemented in `venv_bootstrap` (no-op / warn-no-clobber-python2 / create-or-reheal `~/.local/bin/python`→`python3` + PATH; strict@setup, heal+warn@render/upgrade). 20 bootstrap tests green incl. the python2-no-clobber guard. Remaining: wire call sites, flip config renderers + Codex/`.air`, bin forwarders, retire rendered `_venv_python_path`, AC-2/AC-3 tests. | `venv_bootstrap.ensure_python_resolves`; `test_venv_bootstrap.py` 20 OK |
| 2026-06-24 | GUI-host fallback (AC-4/AC-5): `venv_bootstrap.gui_fallback_mcp_stanza(repo_root)` returns the absolute-tool-venv-python + absolute-server.py stanza (no relative `python`, no PATH dependency). `setup_wavefoundry.py` PRINTS it as per-machine guidance after the heal — it does **not** auto-overwrite the committed `.mcp.json` (the GUI override path is host-specific). Tested: helper asserts absolute paths + no relative `python`; setup asserts the guidance print. | `venv_bootstrap.gui_fallback_mcp_stanza`; `setup_wavefoundry._print_gui_fallback_guidance`; `test_venv_bootstrap.GuiFallbackStanzaTests`; `test_setup_wavefoundry.test_prints_gui_fallback_guidance_after_heal` |
| 2026-06-24 | Root made cwd-independent — `_discover_root` anchors on the server script's own location (marker-validated), `--root .` dropped from all configs; host env vars (CLAUDE_PROJECT_DIR/PROJECT_ROOT/REPO_ROOT) are marker-validated candidates. | `server_impl._discover_root` (script-location → env → cwd, each marker-gated); `.mcp.json`/`.cursor`/`.junie`/`.agents`/`.codex`/`.air` args = just `server.py`; `test_server_tools.RootDiscoveryTests` (script-location/env/cwd/override) |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-24 | Committed `command: "python"`; setup symlinks `python`→venv on macOS/Linux, verifies on Windows; CLI-host-scoped | `python` is present-but-misnamed (network-free symlink fix); committed byte-identical config preserved; CLI hosts inherit the shell PATH so the symlink is visible. | `uv` (red-teamed out — absent/network/SPOF/throwaway, worst on GUI PATH); absolute-venv-path default (gitignored, sacrifices committed config — kept as the GUI fallback); shell alias (not honored by raw spawn). |
| 2026-06-24 | Scope = ALL config surfaces + bin forwarders (single-runtime-surface goal) | The runtime-entry sweep found the original 3-change plan converged 12/38 and MISSED `.codex/config.toml` (separate `render_agent_surfaces.py`) + `.air/mcp.json` (no renderer). | Config-cutover-only — rejected. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| GUI-launched host doesn't inherit the shell PATH → the symlink is invisible | Scoped out as the documented residual; setup renders a gitignored per-machine absolute-venv-path config as the fallback for those hosts (AC-6 exercises it). |
| Setup symlink conflicts with an existing `python` (e.g. python2) or the dir isn't on PATH | AC-4: verify `python` ≥3.11 before/after; create in a setup-owned dir + ensure on PATH; fail loud on conflict. |
| Green macOS/Linux CI mistaken for Windows-verified | `WindowsPath` uninstantiable on POSIX CI → unit tests verify branch selection via mocks; real coverage is AC-6 (operator smoke). |
| AC-6 deferred indefinitely | Operator confirmed a Windows host; AC-6 is a hard close gate. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
