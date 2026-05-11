# Init Wave Framework

Owner: Engineering
Status: active
Last verified: 2026-05-04

Shortcut: **`Install Wavefoundry`** | Legacy: **`Init wave framework`** / **`Init wave context`**

## Purpose

Initialize a target repository with the Wave Framework operating surface. Detects existing state first: if the repository is already seeded, hands off to **Upgrade wave framework** instead of re-running init.

## What Init Does

1. Reads the run contract (seed-020) and builds an evidence base (seed-030): `docs/repo-index.md`, `docs/repo-profile.json`.
2. Detects existing Wave Framework state. If already installed, routes to **Upgrade wave framework**.
3. For greenfield repos (no prior context): skips baseline wave; proceeds directly to bootstrap.
4. For repos with legacy corpus (pre-wave plans/specs): captures and closes a `00000 wave-zero-plans-and-specs` baseline wave before bootstrapping.
5. Bootstraps the full Wave Framework operating surface: docs structure, agent entry files, architecture docs, quality posture, prompt surface, wave artifacts, personas, and journals.
6. Delivers an operator summary covering what was seeded, the workflow, commands, roles, and docs gate.

## Required Outputs

See `.wavefoundry/framework/seeds/010-install-wavefoundry.prompt.md` for the complete required output list.

## Git Commits

**Operator-owned.** Agent hands off diff + suggested message. Operator commits.

## MCP / Wavefoundry Server

After installing Wave Framework, enable the local MCP server in your agent host so tools like `wave_help`, `docs_search`, and `wave_audit` are available.

**Step 1 — Build the semantic index:**

```bash
python3 .wavefoundry/framework/scripts/setup_index.py
```

**Step 2 — Register the server in your host:**

| Host | Registration surface | What to do |
|------|----------------------|------------|
| **Claude Code** | `.mcp.json` (auto-generated) | Run `render_platform_surfaces --platform claude`. Open the project — Claude Code discovers `.mcp.json` automatically. |
| **Cursor** | `.cursor/mcp.json` (auto-generated) | Run `render_platform_surfaces --platform cursor`. Enable under **Cursor → Settings → MCP** if not auto-loaded. |
| **Junie** | `.junie/mcp/mcp.json` (auto-generated) | Run `render_platform_surfaces --platform junie`. Junie discovers this on project open. |
| **GitHub Copilot** | VS Code MCP settings | Open **VS Code → Settings → MCP servers** and add the stdio entry below. |
| **Codex / Air / other** | Host UI | Add the stdio entry below via your host's MCP attachment UI. See your host's MCP documentation. |

**Copy-ready stdio entry** (replace `<repo>` with the absolute path to this repository):

```json
{
  "command": "python3",
  "args": [
    ".wavefoundry/framework/scripts/server.py",
    "--root", "<repo>"
  ]
}
```

See `AGENTS.md → MCP / Wavefoundry server — enabling per host` for the full matrix with UI paths and vendor links.

**Docs validation (agents):** After MCP is enabled, use **`wave_validate`** and **`wave_garden`** for the docs gate instead of shelling out to `.wavefoundry/bin/docs-lint` / `.wavefoundry/bin/docs-gardener`. Use the bin launchers only when MCP is not attached (CI, hooks, bare terminal).

**Optional local dashboard:** After install, the repository can expose the local dashboard surface with **`Start dashboard`**, which runs:

```bash
python3 .wavefoundry/framework/scripts/dashboard_server.py --root . --open
```

**Step 3 — Restart MCP and update indexes:**

After registration, restart the MCP server in your host so the newly installed server picks up all rendered surfaces. Then update the semantic index so docs_search reflects the installed content:

```
wave_index_build(content="docs", mode="update")   ← project layer
```

If the repository self-hosts the framework index, also run:

```
wave_index_build(content="docs", mode="update", layer="framework")
```

See `docs/contributing/build-and-verification.md` **Update vs rebuild — decision table** for when to use `mode="update"` vs `mode="rebuild"`.

## Aliases

- **Install wave framework** / **Install wave context** — accepted; routes to init (greenfield) or upgrade (already seeded)
- **Init wave context** — legacy alias; identical behavior
