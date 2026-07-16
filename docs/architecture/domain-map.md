# Domain Map

Owner: Engineering
Status: active
Last verified: 2026-07-15

## Domains

| Domain | Path | Owned Responsibilities | Inbound Deps | Outbound Deps |
|--------|------|----------------------|-------------|---------------|
| **Framework Seeds** | `.wavefoundry/framework/seeds/` | Canonical prompt source; numbered seed prompts; overview docs; reference appendices | None — canonical source | Consumed by target repositories via install/upgrade; indexed by `indexer.py` |
| **Framework Scripts** | `.wavefoundry/framework/scripts/` | Lifecycle ID generation; docs linting; docs gardening; platform and framework-owned review-carrier rendering; executable-review validation/adoption; packaging; test running; MCP server | `docs/workflow-config.json` (config read); `docs/` tree (lint/gardener and explicitly marked lifecycle/carrier regions) | `.wavefoundry/framework/VERSION` (write); zip archives (write); `.claude/`, `.cursor/`, `.github/hooks/` (render writes); marker-bounded review carriers under `docs/` and explicitly enabled native roles under `.claude/agents/` / `.codex/skills/`; review-adoption state; MCP tool responses (stdio) |
| **MCP Server** | `.wavefoundry/framework/scripts/server.py` | Tool and resource surface for MCP clients: wave lifecycle, search, code navigation, session handoff, index management | `.wavefoundry/index/` (search reads); `docs/` (wave/change/prompt reads and lifecycle writes); `chunker.py` tree-sitter parser stack (lazy-loaded at query time for two-hop symbol extraction in `search_combined`); `lancedb` (embedded vector store, primary semantic search backend); `fastembed`, `numpy` (embedding and numpy fallback) | MCP client responses (stdio); background index refresh requests |
| **Dashboard Surface** | `.wavefoundry/framework/dashboard/` + `.wavefoundry/framework/scripts/dashboard_{lib,server}.py` | Local operational dashboard assets, loopback HTTP serving, shared repository-state snapshot readers | `docs/` tree (read); `.wavefoundry/framework/VERSION` (read); `docs/workflow-config.json` dashboard settings | Browser responses over localhost HTTP; `.wavefoundry/dashboard-server.json` (host-local metadata write) |
| **Semantic Index** | `.wavefoundry/index/` | Embedding vectors and chunk metadata for docs and code semantic search; incremental rebuild via file hashes | Repository files (read); `indexer.py` (write) | `server.py` search tools (read) |
| **Self-Hosted Docs** | `docs/` | Wavefoundry project operating surface: plans, waves, architecture, contributing, prompts, agent roles, journals | None | Consumed by framework scripts (lint/gardener); read by MCP server tools |
| **Wave Framework Distribution** | Root zip archives | Packaged distribution for target repositories | `.wavefoundry/framework/` tree | Target repository `.wavefoundry/framework/` after unpack |

## Dependency Direction Rules

1. `.wavefoundry/framework/seeds/` is source of truth for generic framework behavior — no domain modifies it except Wavefoundry maintainers through an explicit wave (requires `seed_edit_allowed` guard).
2. `.wavefoundry/framework/scripts/` does not own whole project docs. It owns only explicit lifecycle records and framework marker-bounded carrier regions; renderer updates preserve every project-authored byte outside those regions.
3. `docs/` is tool-independent — it does not import or reference script internals. The MCP server reads `docs/` but `docs/` has no knowledge of the server.
4. Executable-review lifecycle validation may write outside `docs/` only to its bounded ignored host-local coordination state (`.wavefoundry/review-evidence-adoptions.lock`). Other MCP mutations—such as index state, edit-gate overrides, and platform rendering—remain limited to their explicitly documented tool scopes; this rule does not redefine those separate boundaries.
5. The local dashboard server is loopback-only and read-mostly: it may write host-local endpoint metadata under `.wavefoundry/`, but it must not mutate project docs, wave state, or git-tracked product state.
6. The semantic index (`.wavefoundry/index/`) is a derived artifact — it can always be deleted and rebuilt from source. Nothing outside `server.py` reads it directly.

## Interaction Edges

| Edge | Type | Stability | Owner |
|------|------|-----------|-------|
| `build_pack.py` → `.wavefoundry/framework/VERSION` | file write | stable | Engineering (packaging) |
| `lifecycle_id.py` → `docs/workflow-config.json` | file read | stable | Engineering |
| `docs_lint.py` / `docs_gardener.py` → `docs/` | file read/write | stable | Engineering |
| `render_platform_surfaces.py` → `.claude/`, `.cursor/`, `.github/hooks/`, `.mcp.json` | file write | stable | Engineering |
| `render_agent_surfaces.py` → framework-marked regions in registered `docs/agents/`, `docs/prompts/`, `docs/contributing/`, and explicitly enabled native `.claude/agents/` / `.codex/skills/` carriers | bounded file write | stable | Engineering (framework renderer) |
| `review_evidence.py` → `docs/waves/review-evidence-adoptions.json` | bounded canonical-prefix count/hash proof write | stable | MCP lifecycle validator |
| `wave_record_review_evidence` → `docs/waves/<wave>/events.jsonl` + `wave.md` | locked canonical event append plus generated Markdown current-head projection | stable | MCP lifecycle authoring tool |
| `review_evidence.py` → `.wavefoundry/review-evidence-adoptions.lock` | host-local coordination write | stable | MCP lifecycle validator |
| `indexer.py` → `.wavefoundry/index/` | file write | stable | Engineering (setup/incremental) |
| `server.py` → `.wavefoundry/index/` | file read | stable | MCP server (search tools) |
| `server.py` → `docs/waves/`, `docs/plans/`, `docs/prompts/` | file read/write | stable | MCP server (lifecycle + inspection tools) |
| `server.py` → `docs/agents/session-handoff.md` | file read/write | stable | MCP server (handoff tools) |
| `dashboard_server.py` → `docs/waves/`, `docs/plans/`, `docs/prompts/prompt-surface-manifest.json`, `docs/agents/session-handoff.md` | file read | stable | Dashboard server |
| `dashboard_server.py` → `.wavefoundry/dashboard-server.json` | file write | stable | Dashboard server |
| MCP client → `server.py` | stdio (FastMCP protocol) | stable | MCP client (Claude Code, Cursor, etc.) |
| Browser → `dashboard_server.py` | loopback HTTP | stable | Operator browser |
| Zip distribution → target repo `.wavefoundry/framework/` | file unpack | stable | Operator |
