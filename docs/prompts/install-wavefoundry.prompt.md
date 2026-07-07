# Init Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-07-06

Shortcut: **`Init Wavefoundry`** | Legacy: **`Install Wavefoundry`** / **`Init wave framework`** / **`Install wave framework`** / **`Init wave context`** / **`Install wave context`**

## Purpose

Initialize a target repository with the Wave Framework operating surface. Detects existing state first: if the repository is already seeded, hands off to **Upgrade Wavefoundry** instead of re-running init.

## What Init Does

1. Reads the run contract (seed-020) and builds an evidence base (seed-030): `docs/repo-index.md`, `docs/repo-profile.json`.
2. Detects existing Wave Framework state. If already installed, routes to **Upgrade Wavefoundry**.
3. For greenfield repos (no prior context): skips baseline wave; proceeds directly to bootstrap.
4. For repos with legacy corpus (pre-wave plans/specs): captures and closes a `00000 wave-zero-plans-and-specs` baseline wave before bootstrapping.
5. Bootstraps the full Wave Framework operating surface: docs structure, agent entry files, architecture docs, quality posture, prompt surface, wave artifacts, personas, and journals.
6. Delivers an operator summary covering what was seeded, the workflow, commands, roles, and docs gate.
7. Removes the single-use bootstrap file `install-wavefoundry.md` from the project root once install completes — it ships at the zip root only so the agent can discover the install instructions before `.wavefoundry/` exists; afterwards it is consumed (the canonical instructions live in this doc). Delete it (`rm -f install-wavefoundry.md`), do not move it.

## Required Outputs

See `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md` for the complete required output list.

## Git Commits

**Operator-owned.** Agent hands off diff + suggested message. Operator commits.

## MCP / Wavefoundry Server

After installing Wave Framework, enable the local MCP server in your agent host so tools like `wave_help`, `docs_search`, `code_ask`, `wave_audit`, and `wave_index_health` are available.

**Supported operator environments:** macOS and Linux are supported natively. Windows is currently supported through **WSL2** for install and operator workflows because some bootstrap and launcher surfaces still assume a POSIX shell.

**Python requirement:** Python 3.11 or later must be resolvable as `python3` on your PATH — Wavefoundry does not modify your Python installation or PATH. Before proceeding, `python3 --version` must work from the command line and report Python 3.11 or newer. If `python3` is missing or reports an older version, stop and fix Python/PATH first (for example, install via Scoop/Microsoft Store on Windows, use your package manager on macOS/Linux, or add a `python3` shim/symlink to a Python 3.11+ interpreter). `wf setup` creates a shared tool environment at `~/.wavefoundry/venv` (or `$WAVEFOUNDRY_TOOL_VENV` to override), installs all framework dependencies into it, verifies the same `python3` prerequisite, and runs the index setup flow. No system-level or project-level Python environment is modified.

**Versioning:** Wavefoundry uses `MAJOR.MINOR.PATCH` semver internally. Distribution zips use `wavefoundry-MAJOR.MINOR.PATCH.<build>.zip` and land in `~/.wavefoundry/dist/` after packaging.

**Step 1 — Build the semantic index:**

```bash
wf setup
```

If this setup step fails specifically because a required model cannot be downloaded, keep recovery on the canonical setup path. In agent-driven sessions, the agent should ask the operator for permission to rerun the same setup command with network access or host escalation enabled instead of switching to an out-of-band manual model download.

After setup, MCP host configs should launch the PATH `python3` command on Wavefoundry's `server.py`. Do not point MCP config at `.wavefoundry/venv/Scripts/python.exe`, `.wavefoundry/venv/bin/python`, or another project-local venv interpreter as a workaround for a missing or too-old `python3`; fix `python3 --version` first. The server activates the shared tool environment itself.

`wf setup` smoke-tests the same launch shape the host will use: `python3 .wavefoundry/framework/scripts/server.py --dry-run`. If that fails, fix the reported Python/PATH/dependency issue before restarting the host.

**Step 2 — Register the server in your host:**

| Host | Registration surface | What to do |
|------|----------------------|------------|
| **Claude Code** | `.mcp.json` (auto-generated) | Run `render_platform_surfaces --platform claude`. Open the project - Claude Code discovers `.mcp.json` automatically. |
| **Cursor** | `.cursor/mcp.json` (auto-generated) | Run `render_platform_surfaces --platform cursor`. Enable under **Cursor -> Settings -> MCP** if not auto-loaded. |
| **Junie** | `.junie/mcp/mcp.json` (auto-generated) | Run `render_platform_surfaces --platform junie`. Junie discovers this on project open. |
| **GitHub Copilot** | VS Code MCP settings | Open **VS Code -> Settings -> MCP servers** and add the stdio entry below. |
| **Codex** | `.codex/config.toml` (committed) | Project-local `.codex/config.toml` is committed to the repo. Codex loads the `wavefoundry` MCP server automatically for trusted projects. Trust the project when Codex prompts on first clone. |
| **Antigravity** | `.agents/mcp_config.json` (auto-generated) | Run `render_platform_surfaces --platform antigravity`. The `ag` CLI loads `.agents/mcp_config.json` automatically. (The app/IDE uses the global `~/.gemini/…` config — add the stdio entry below there.) |
| **Windsurf / Air / Warp / other** | Host UI / settings | Add the stdio entry below via your host's MCP settings. Windsurf also gets auto-rendered hooks via `render_platform_surfaces --platform windsurf`; its MCP attachment is still manual. See your host's MCP documentation. |

After connecting, call `wave_server_info()` once to confirm the attached `repo_root` before you rely on any other MCP tools.

**Copy-ready stdio entry** for hosts that accept a direct MCP command block:

```json
{
  "command": "python3",
  "args": [
    "<repo>/.wavefoundry/framework/scripts/server.py",
    "--root",
    "<repo>"
  ]
}
```

See `AGENTS.md → MCP / Wavefoundry server — enabling per host` for the full matrix with UI paths and vendor links.

**Codex config** (`~/.codex/config.toml`):

```toml
[mcp_servers.wavefoundry]
command = "python3"
args = [
  "<repo>/.wavefoundry/framework/scripts/server.py",
  "--root",
  "<repo>"
]
cwd = "<repo>"
```

Register each additional Wavefoundry repo with its own project-local MCP config so the command points at that repo root. Do not rely on hashed Codex server labels as the routing contract. After changing MCP config or fixing Python on PATH, fully quit and reopen the host or start a fresh conversation; do not resume an old session that started before setup completed, because existing sessions may keep the toolset from the failed startup.

**Docs validation (agents):** After MCP is enabled, use **`wave_validate`** and **`wave_garden`** for the docs gate instead of shelling out to the dispatcher. Use the no-PATH fallback only when MCP is not attached: POSIX `./.wavefoundry/bin/wf docs-lint` / `./.wavefoundry/bin/wf docs-gardener`; native Windows `.\\.wavefoundry\\bin\\wf.cmd docs-lint` / `.\\.wavefoundry\\bin\\wf.cmd docs-gardener`.

**Optional local dashboard:** After install, the repository can expose the local dashboard surface with **`Start dashboard`**, **`Stop dashboard`**, and **`Restart dashboard`**. The start command runs:

```bash
wf dashboard --root . --open
```

**Step 3 — Restart MCP and update indexes:**

After registration, restart the MCP server in your host so the newly installed server picks up all rendered surfaces. Then update the semantic index so docs_search reflects the installed content:

```
wave_index_build(content="docs", mode="update")   ← the single project index
```

The framework's seeds fold into this project docs index — there is no separate framework index to build.

See `docs/contributing/build-and-verification.md` **Update vs rebuild — decision table** for when to use `mode="update"` vs `mode="rebuild"`.

If you launched a detached background setup build, poll `wave_index_build_status(layer?)` until it finishes before assuming that layer's search is current.

## Aliases

- **Install Wavefoundry** / **Install wave framework** / **Install wave context** — accepted; routes to init (greenfield) or upgrade (already seeded)
- **Init wave framework** / **Init wave context** — legacy alias; identical behavior
