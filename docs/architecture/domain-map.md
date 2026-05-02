# Domain Map

Owner: Engineering
Status: active
Last verified: 2026-05-01

## Domains

| Domain | Path | Owned Responsibilities | Inbound Deps | Outbound Deps |
|--------|------|----------------------|-------------|---------------|
| **Framework Seeds** | `.wavefoundry/framework/seeds/` | Canonical prompt source; numbered seed prompts; overview docs; reference appendices | None — canonical source | Consumed by target repositories via install/upgrade; indexed by `indexer.py` |
| **Framework Scripts** | `.wavefoundry/framework/scripts/` | Lifecycle ID generation; docs linting; docs gardening; platform surface rendering; packaging; test running; MCP server | `docs/workflow-config.json` (config read); `docs/` tree (lint/gardener read/write) | `.wavefoundry/framework/VERSION` (write); zip archives (write); `.claude/`, `.cursor/`, `.github/hooks/` (render writes); MCP tool responses (stdio) |
| **MCP Server** | `.wavefoundry/framework/scripts/server.py` | Tool and resource surface for MCP clients: wave lifecycle, search, code navigation, session handoff, index management | `.wavefoundry/index/` (search reads); `docs/` (wave/change/prompt reads and lifecycle writes); `.wavefoundry/framework/index/` (framework seed reads) | MCP client responses (stdio); background index refresh requests |
| **Semantic Index** | `.wavefoundry/index/` | Embedding vectors and chunk metadata for docs and code semantic search; incremental rebuild via file hashes | Repository files (read); `indexer.py` (write) | `server.py` search tools (read) |
| **Framework Index** | `.wavefoundry/framework/index/` | Packaged embedding index for framework seeds and prompts; shipped in the framework zip | `.wavefoundry/framework/seeds/` (read) | `server.py` search tools (read, merged with project index at query time) |
| **Self-Hosted Docs** | `docs/` | Wavefoundry project operating surface: plans, waves, architecture, contributing, prompts, agent roles, journals | None | Consumed by framework scripts (lint/gardener); read by MCP server tools |
| **Wave Framework Distribution** | Root zip archives | Packaged distribution for target repositories | `.wavefoundry/framework/` tree | Target repository `.wavefoundry/framework/` after unpack |

## Dependency Direction Rules

1. `.wavefoundry/framework/seeds/` is source of truth for generic framework behavior — no domain modifies it except Wavefoundry maintainers through an explicit wave (requires `seed_edit_allowed` guard).
2. `.wavefoundry/framework/scripts/` reads `docs/` but does not own it; the docs tree is owned by the Wave Framework seeding process.
3. `docs/` is tool-independent — it does not import or reference script internals. The MCP server reads `docs/` but `docs/` has no knowledge of the server.
4. The MCP server must not write outside `docs/` except for index state (`.wavefoundry/index/background-refresh.json`) and platform surface rendering. All mutation tools are explicitly scoped.
5. The semantic index (`.wavefoundry/index/`) is a derived artifact — it can always be deleted and rebuilt from source. Nothing outside `server.py` reads it directly.

## Interaction Edges

| Edge | Type | Stability | Owner |
|------|------|-----------|-------|
| `build_pack.py` → `.wavefoundry/framework/VERSION` | file write | stable | Engineering (packaging) |
| `lifecycle_id.py` → `docs/workflow-config.json` | file read | stable | Engineering |
| `docs_lint.py` / `docs_gardener.py` → `docs/` | file read/write | stable | Engineering |
| `render_platform_surfaces.py` → `.claude/`, `.cursor/`, `.github/hooks/`, `.mcp.json` | file write | stable | Engineering |
| `indexer.py` → `.wavefoundry/index/` | file write | stable | Engineering (setup/incremental) |
| `server.py` → `.wavefoundry/index/` + `.wavefoundry/framework/index/` | file read | stable | MCP server (search tools) |
| `server.py` → `docs/waves/`, `docs/plans/`, `docs/prompts/` | file read/write | stable | MCP server (lifecycle + inspection tools) |
| `server.py` → `docs/agents/session-handoff.md` | file read/write | stable | MCP server (handoff tools) |
| MCP client → `server.py` | stdio (FastMCP protocol) | stable | MCP client (Claude Code, Cursor, etc.) |
| Zip distribution → target repo `.wavefoundry/framework/` | file unpack | stable | Operator |
