# Codex Project-Local Bootstrap

Change ID: `12jt2-feat codex-project-local-bootstrap`
Change Status: `complete`
Owner: Engineering
Status: ready
Last verified: 2026-05-12
Wave: `12jt2 codex-project-local-bootstrap`

## Rationale

Codex does not auto-discover a repo-local MCP config the way Claude Code does. A project-local launcher is the cleanest way to keep the startup command and path derivation owned by each Wavefoundry repo while still registering the server with the user's Codex config.

## Requirements

1. Generate a repo-local launcher that registers the Wavefoundry MCP server with Codex for the current repository.
2. Derive the Codex server name from the repository root: use `wavefoundry-<hash>` for every checkout.
3. Keep the server command and `--root` path absolute so the launcher works regardless of the current shell directory.
4. Add a read-only server identity surface so attached agents can confirm the repository root directly from MCP responses.
5. Update operator-facing docs so the checkout-path bootstrap and identity check are discoverable from `AGENTS.md` and the install prompt.
6. Add tests that prove the launcher is emitted, the derived server name is stable, and the server identity surface returns the active repository root.

## Scope

**Problem statement:** Codex currently requires a global config entry, which makes manual per-project setup repetitive and error-prone. Wavefoundry needs a repo-owned bootstrap command that turns a project path into a registered Codex MCP server entry with consistent naming.

**In scope:**

- `render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/server.py`
- `docs/prompts/install-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`
- `AGENTS.md`
- framework script tests for launcher generation

**Out of scope:**

- Adding a repo-local Codex config discovery mechanism to Codex itself
- Changing Claude Code's `.mcp.json` auto-discovery model
- Adding a networked MCP transport

## Acceptance Criteria

- `render_platform_surfaces.py` emits a repo-local Codex bootstrap launcher under `.wavefoundry/bin/`.
- The launcher names every checkout `wavefoundry-<hash>`.
- The launcher invokes `codex mcp add` with the repository's absolute server path and `--root` path.
- `wave_server_info` returns the attached repository root and deterministic Codex server label for that checkout path.
- Install docs describe the launcher and the global Codex config limitation clearly.
- Tests cover launcher rendering, naming behavior, and the identity surface.

## Tasks

- Add a Codex bootstrap launcher to `.wavefoundry/bin/` generation.
- Derive the server name from the absolute checkout path hash.
- Keep the command path absolute so startup is reproducible.
- Add a read-only identity tool that returns the attached repository root.
- Update the install doc and AGENTS matrix with the launcher flow.
- Add unit tests for launcher generation, checkout-path derivation, and server identity.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| launcher generation | implementer | — | Script emission and naming logic |
| server identity | implementer | — | Read-only tool that reports repo root and codex label |
| docs | implementer | launcher generation, server identity | Install prompt and AGENTS matrix |
| tests | implementer | launcher generation, server identity | Validate script content, derived names, and identity response |

## Serialization Points

- `.wavefoundry/framework/scripts/render_platform_surfaces.py`
- `.wavefoundry/framework/scripts/server.py`
- `docs/prompts/install-wavefoundry.prompt.md`
- `AGENTS.md`

## Affected Architecture Docs

- `docs/architecture/current-state.md`

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Repo-local launcher exists and is emitted by the renderer |
| AC-2 | required | Root repo vs other repo naming is deterministic |
| AC-3 | required | Absolute command/root path keeps Codex startup reliable |
| AC-4 | important | The server identity surface returns the active repository root |
| AC-5 | important | Docs explain the project-local bootstrap path and identity check |
| AC-6 | required | Tests cover launcher generation, naming, and identity |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-12 | Change authored for project-local Codex bootstrap launcher, per-repo naming, and server identity surface. | This wave record |
| 2026-05-12 | Change marked complete after implementation, review, and docs cleanup. | This wave record |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-12 | Use a repo-local bootstrap launcher instead of repo-local Codex discovery | Codex currently reads the shared `~/.codex/config.toml`, so the repo needs to own the startup command while Codex retains the global attachment file | Try to force a repo-local Codex config file |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Global Codex config still exists | Keep the bootstrap launcher project-local and make the naming rule deterministic |
| Checkout-path drift | Prefix every checkout with `wavefoundry-<hash>` so the label changes when the folder path changes |
| Launcher drift | Add unit tests for emitted script content |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
