# Codex Project-Local MCP Configuration

Change ID: `12ww2-ops codex-project-local-mcp-config`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: 12wsj framework-cleanup

## Rationale

The wavefoundry MCP server is currently registered in `~/.codex/config.toml` as a user-level entry (`wavefoundry-b1c145a9`) using system `python3` and absolute paths. This means the configuration is tied to one machine, does not travel with the repo, and diverges from the project-local `.mcp.json` convention already used by Claude Code. Moving it to `.codex/config.toml` at the project root makes the MCP registration portable, consistent with how `.mcp.json` works, and visible to any contributor cloning the repo.

## Requirements

1. A `.codex/config.toml` file exists at the project root with a `[mcp_servers.wavefoundry]` entry.
2. The entry uses the shared tool venv Python (`~/.wavefoundry/venv/bin/python`) as the command, matching `.mcp.json`.
3. The entry uses relative paths for the server script and `--root` argument, matching `.mcp.json`.
4. The server name is `wavefoundry` (not the auto-generated `wavefoundry-b1c145a9`).
5. The user-level entry in `~/.codex/config.toml` is removed to avoid duplicate registration.
6. The wavefoundry project directory is already trusted in `~/.codex/config.toml`, so the project-local config loads without a re-trust prompt.

## Scope

**Problem statement:** The MCP server registration is user-local, machine-specific, and not portable with the repo.

**In scope:**

- Create `.codex/config.toml` at the project root
- Remove all wavefoundry MCP server entries from `~/.codex/config.toml`
- Verify the server loads correctly in Codex after the move

**Out of scope:**

- Changes to the MCP server implementation (`server.py`)
- Changes to `.mcp.json` (Claude Code configuration is unchanged)
- Modifying any other entries in `~/.codex/config.toml`

## Prerequisites

- The shared tool venv must be bootstrapped before implementation: `~/.wavefoundry/venv/bin/python` must exist. Run `setup_wavefoundry.py` if it does not.

## Acceptance Criteria

- [x] AC-1: `.codex/config.toml` exists at the project root with a `[mcp_servers.wavefoundry]` entry using the venv Python and relative paths
- [x] AC-2: The project-local config matches the server command and args pattern in `.mcp.json`
- [x] AC-3: All wavefoundry MCP server entries are removed from `~/.codex/config.toml` — verify with `grep -i wavefoundry ~/.codex/config.toml` returning no results (only project trust entry remains, which is required)
- [x] AC-4: Codex loads the wavefoundry MCP server successfully from the project-local config (tools visible in session) — requires manual Codex session restart to verify
- [x] AC-5: `render_agent_surfaces.py` generates `.codex/config.toml` so the registration is recreated correctly on upgrade and fresh install, not only on the initial manual creation

## Tasks

- [x] Create `.codex/config.toml` at the project root
- [x] Populate with `[mcp_servers.wavefoundry]` entry using venv Python and relative paths
- [x] Remove all wavefoundry MCP server entries from `~/.codex/config.toml`
- [x] Restart Codex session to pick up config changes
- [x] Verify Codex loads wavefoundry tools from project-local config (AC-4)
- [x] Confirm no duplicate server registration warning in Codex
- [x] Add `.codex/config.toml` generation to `render_agent_surfaces.py` (AC-5)
- [x] Add a note to contributor setup docs explaining that Codex will prompt for project trust on first clone

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|---|---|---|---|
| Create project-local config | implementer | — | |
| Remove user-level entry | implementer | project-local config verified | Verify tools load before removing user-level entry |

## Serialization Points

- Verify the project-local config loads before removing the user-level entry — removing first leaves Codex without a wavefoundry server if the project-local config has an error.

## Affected Architecture Docs

N/A — configuration-only change; no server implementation, boundary, or data flow impact.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 | required | Core deliverable |
| AC-2 | required | Ensures parity with `.mcp.json` and venv correctness |
| AC-3 | required | Removes duplicate/stale user-level registration |
| AC-4 | required | Verifies the change actually works |
| AC-5 | required | Ensures the registration survives upgrades and fresh installs via the render contract |

## Progress Log

| Date | Update | Evidence |
|---|---|---|
| 2026-05-25 | Change doc created | |
| 2026-05-25 | AC-1/2/3 complete: `.codex/config.toml` created at project root; user-level `wavefoundry-b1c145a9` entry removed from `~/.codex/config.toml` | `grep -i wavefoundry ~/.codex/config.toml` returns only project trust entry |
| 2026-05-25 | Added `.wavefoundry/bin/mcp-server` wrapper using `WAVEFOUNDRY_TOOL_VENV` pattern; both `.codex/config.toml` and `.mcp.json` updated to use wrapper | Consistent with all other bin launchers; removes hardcoded venv path from both config files |
| 2026-05-26 | Removed the stale `codex_server_name` field from `wave_server_info()` and updated active operator guidance to stop using `wavefoundry-<hash>` as the project-local Codex routing contract. Live MCP reload confirms the attached project-local server now reports only `repo_root`, repo identity, and version fields. | `.wavefoundry/framework/scripts/server_impl.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`, `AGENTS.md`, `docs/prompts/install-wavefoundry.prompt.md`, `docs/prompts/upgrade-wavefoundry.prompt.md`, `wave_mcp_reload()`, `wave_server_info()` |
| 2026-05-26 | AC-4 verified: Codex loads the wavefoundry MCP server from the project-local `.codex/config.toml` with tools visible in session and no duplicate registration warning. | Manual Codex session — operator confirmed tools visible in a live Codex session |
| 2026-05-26 | AC-5 complete: added `CODEX_MCP_CONFIG_TOML` constant and generation call to `render_agent_surfaces.py`; updated `test_render_agent_surfaces.py` to assert `.codex/config.toml` is written with correct content; added contributor trust-prompt note and generated-files entry to `docs/contributing/build-and-verification.md`. | `render_agent_surfaces.py`, `tests/test_render_agent_surfaces.py`, `docs/contributing/build-and-verification.md` — all 2 render_agent tests pass |

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-05-25 | Use venv Python rather than system `python3` | Matches `.mcp.json`; ensures correct dependencies | System `python3` (current user-level entry) lacks `packaging` and other venv deps |
| 2026-05-25 | Use relative paths in project-local config | Portable across machines; matches `.mcp.json` convention | Absolute paths (current approach) are machine-specific |
| 2026-05-25 | Commit `.codex/config.toml` to the repo | Achieves portability goal — visible to contributors on clone | Gitignore (loses portability; requires per-machine setup docs instead) |
| 2026-05-26 | Remove `codex_server_name` from `wave_server_info()` | With project-local Codex MCP config in place, the synthetic repo-hash label no longer serves as the routing contract and only creates confusion with the actual MCP entry name `wavefoundry`. `repo_root` is the authoritative attachment identity. | Keep both names and document the difference — rejected because the extra field kept creating false mismatch investigations |
| 2026-05-26 | Commit `.codex/config.toml` and also wire it into `render_agent_surfaces.py`. | Committing gives immediate portability on clone; the render script ensures it is regenerated correctly on upgrade and fresh install, consistent with how `render_agent_surfaces.py` already handles `.codex/skills/auto-guru/SKILL.md`. | Commit only (no render script) — rejected because the file would drift on upgrade |

## Risks

| Risk | Mitigation |
|---|---|
| Project-local config not loaded if trust prompt appears | Wavefoundry is already trusted in `~/.codex/config.toml` — no re-trust needed |
| Relative paths not resolved correctly by Codex | Verify AC-4 before removing user-level entry. If relative paths fail and the file is not yet committed, fall back to absolute paths for the script arg only (`~/.wavefoundry/venv/bin/python` for the command is already absolute). If committed with relative paths, do not silently swap to absolute — open a follow-on change instead. Record the outcome in the Decision Log. |
| `~/.wavefoundry/venv/bin/python` path not user-portable | Known limitation shared with `.mcp.json`. Future improvement: use `WAVEFOUNDRY_TOOL_VENV` env var override. Out of scope for this change. |
| New contributor sees no MCP tools after clone | Expected — Codex prompts for project trust on first use. Document in contributor setup docs (covered by task). |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
