# Antigravity host support — workspace-local MCP configuration

Change ID: `1p6l4-enh antigravity-host-support`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-19
Wave: `1p6l5 antigravity-host-support`

## Rationale

Google **Antigravity** (agentic IDE/CLI) is a new host operators want to use with Wavefoundry. Two facts shape the integration:

1. **It reads the project-root `AGENTS.md` natively** (v1.20.3+, alongside `GEMINI.md`; `GEMINI.md` wins on conflict), plus `.agents/rules/*.md`. So Wavefoundry's **Tier-1 canonical agent guide is consumed with no new file** — the guru workflow + MCP-first guidance already apply (same as Codex/Windsurf/Air, whose entry file is `AGENTS.md`).
2. **It supports workspace-local configuration** — Antigravity discovers and loads MCP servers defined in `.agents/mcp_config.json` relative to the active workspace root.

By writing directly to `.agents/mcp_config.json` using the platform surface renderer, we avoid modifying the operator's global config, and we can use the portable `.wavefoundry/bin/mcp-server` wrapper command to keep the configuration clean and machine-independent.

## Requirements

1. **Auto-render `.agents/mcp_config.json`** via `render_platform_surfaces.py`. Command: `.wavefoundry/bin/mcp-server`.
2. **Auto-detection.** Trigger the renderer automatically when the `.agents` folder is present in the workspace.
3. **Renderer wiring.** Add `"antigravity"` to the `--platform` choices in `render_platform_surfaces.py`.
4. **Tier 1 is native; no Tier-2 file.** Antigravity reads the project-root `AGENTS.md`, so no separate thin-pointer entry file is rendered (unlike Junie/Copilot). It joins the `AGENTS.md`-entry-file group (Codex/Windsurf/Air).
5. **Docs.** Add Antigravity to: the `AGENTS.md` MCP-enabling-per-host table, the `README.md` host-support list, and the `docs/agents/platform-mapping.md` table.
6. **Tests.** Verify that rendering the Antigravity configuration outputs a correct, portable MCP server stanza.

## Scope

**Problem statement:** Antigravity needs a workspace-local Wavefoundry MCP configuration.

**In scope:** `.agents/mcp_config.json` auto-rendering; host docs (AGENTS.md / README / platform-mapping); tests.

**Out of scope (candidate follow-ups):**
- Tier-3 native Skill (`1p6lp`).
- Native-Windows `.cmd` twin of the hook wrappers (Area-1).

## Resolved questions

1. **Workspace-local config support:** Confirmed. Antigravity IDE and CLI automatically discover and load workspace-level MCP definitions in `.agents/mcp_config.json`.
2. **Command portability:** Using `.wavefoundry/bin/mcp-server` wrapper matches Claude/Junie, preventing local/absolute python path leaks.

## Acceptance Criteria

- [x] AC-1: `render_platform_surfaces.py` auto-detects `antigravity` platform when `.agents/` is present.
- [x] AC-2: `render_antigravity_mcp_json()` writes/merges the Wavefoundry server stanza into `.agents/mcp_config.json` using `.wavefoundry/bin/mcp-server` as the command.
- [x] AC-3: Config is workspace-local and portable (no absolute python/repo paths).
- [x] AC-4: Docs updated: `AGENTS.md` (shows `.agents/mcp_config.json` auto-rendering), `README.md` host-support, `docs/agents/platform-mapping.md`.
- [x] AC-5: Tests cover `render_antigravity_mcp_json()` rendering output.

## Tasks

- [x] Implement `.agents/mcp_config.json` auto-rendering in `render_platform_surfaces.py`.
- [x] Update platform choices and auto-detection.
- [x] Update docs (`AGENTS.md`, `README.md`, `platform-mapping.md`).
- [x] Add unit tests in `test_render_platform_surfaces.py`.
- [x] Remove obsolete `register_antigravity_mcp.py` script and tests.
- [~] Tier-3 auto-guru Skill — **moved to the skills wave `1p6lp` (`1p6lo`)**; out of scope here.

## Affected Architecture Docs

`N/A`

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Essential for auto-detection in projects using `.agents/`. |
| AC-2 | required | Correctly writes the workspace configuration. |
| AC-3 | required | Portability (no absolute path leaks). |
| AC-4 | important| Operator discoverability. |
| AC-5 | required | Tested and verified. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-19 | In-flight change to workspace-local `.agents/mcp_config.json` rendering. Replaced global helper registration script with automatic platform surface rendering. Removed obsolete global helper files, added tests, and updated documentation. | `render_platform_surfaces.py`, `test_render_platform_surfaces.py`, `AGENTS.md`, `README.md`, `platform-mapping.md`. Full suite passes. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-19 | Workspace-local `.agents/mcp_config.json` rendering. | Antigravity supports workspace-level configuration natively. Keeps setups clean, portable, and aligned with Claude/Junie. | Global registration helper (implemented initially, now retired as invasive/unnecessary). |
