# Domain Map

Owner: Engineering
Status: active
Last verified: 2026-08-21

## Domains

| Domain | Path | Owned Responsibilities | Inbound Deps | Outbound Deps |
|--------|------|----------------------|-------------|---------------|
| **Framework Seeds** | `.wavefoundry/framework/seeds/` | Canonical prompt source; numbered seed prompts; overview docs; reference appendices | None — canonical source | Consumed by target repositories via install/upgrade; indexed by `indexer.py` |
| **Framework Scripts** | `.wavefoundry/framework/scripts/` | Lifecycle ID generation; docs linting; docs gardening; platform and framework-owned review-carrier rendering; executable-review validation/adoption; packaging; test running; MCP server | `docs/workflow-config.json` (config read); `docs/` tree (lint/gardener and explicitly marked lifecycle/carrier regions) | `.wavefoundry/framework/VERSION` (write); zip archives (write); `.claude/`, `.cursor/`, `.github/hooks/` (render writes); marker-bounded review carriers under `docs/` and explicitly enabled native roles under `.claude/agents/` / `.codex/skills/`; review-adoption state; MCP tool responses (stdio) |
| **MCP Server** | `.wavefoundry/framework/scripts/server.py` | Tool and resource surface for MCP clients: wave lifecycle, search, code navigation, typed memory plus physical archival, session handoff, index management, and context-efficiency response telemetry | `.wavefoundry/index/` (search reads); `docs/` (wave/change/prompt/memory reads and bounded lifecycle writes); the missing-only Backstage/TechDocs trio (`catalog-info.yaml`, `mkdocs.yml`, `docs/index.md`) through `wf_techdocs_baseline(mode='run')`, an in-process call of `render_agent_surfaces.render_techdocs_baseline`; the same trio plus `docs/**` read root-level through `wf_techdocs_audit`, which calls `techdocs_audit_lib.run_techdocs_audit` and isolates the raw audit behind a ten-second worker deadline with repository-I/O-free expiry while writing nothing; process-local telemetry focus; `chunker.py` tree-sitter parser stack (lazy-loaded at query time for two-hop symbol extraction in `search_combined`); `lancedb` (embedded vector store, primary semantic search backend); `fastembed`, `numpy` (embedding and numpy fallback) | MCP client responses (stdio); background index refresh requests; memory body rename plus compact-register publication; write-through operational telemetry; marker-owned wave checkpoints at lifecycle/reload/upgrade barriers |
| **Dashboard Surface** | `.wavefoundry/framework/dashboard/` + `.wavefoundry/framework/scripts/dashboard_{lib,server}.py` | Local operational dashboard assets, loopback HTTP serving, shared repository-state snapshot readers | `docs/` tree (read); `.wavefoundry/framework/VERSION` (read); `docs/workflow-config.json` dashboard settings | Browser responses over localhost HTTP; `.wavefoundry/locks/dashboard-server.lock` (host-local lifetime lock + metadata write) |
| **Semantic Index** | `.wavefoundry/index/` | Embedding vectors and chunk metadata for docs and code semantic search; incremental rebuild via file hashes | Repository files (read); `indexer.py` (write) | `server.py` search tools (read) |
| **Operational Telemetry** | `.wavefoundry/logs/context-efficiency.sqlite` | Ignored host-local write-through event/source/evaluation ledger, phase state, replay protection, store identity, and pending checkpoint state; numeric authority for live telemetry | Eligible retrieval/lifecycle calls and typed paired-evaluation attachment | Marker-owned `## Context Efficiency` snapshots in wave records; `wf_current_wave` / `wf_audit` durable-state reads |
| **Self-Hosted Docs** | `docs/` | Wavefoundry project operating surface: plans, waves, architecture, contributing, prompts, agent roles, journals | None | Consumed by framework scripts (lint/gardener); read by MCP server tools |
| **Wave Framework Distribution** | Root zip archives | Packaged distribution for target repositories | `.wavefoundry/framework/` tree | Target repository `.wavefoundry/framework/` after unpack |

## Dependency Direction Rules

1. `.wavefoundry/framework/seeds/` is source of truth for generic framework behavior — no domain modifies it except Wavefoundry maintainers through an explicit wave (requires `seed_edit_allowed` guard).
2. `.wavefoundry/framework/scripts/` does not own whole project docs. It owns only explicit lifecycle records, framework marker-bounded carrier regions, and the missing-only baseline class it materializes exactly once when a destination is absent (the plan-template scaffold, the lifecycle prompt baselines, and the Backstage/TechDocs trio `catalog-info.yaml` / `mkdocs.yml` / `docs/index.md`); a materialized baseline is project-owned from that moment on and is never rewritten, and renderer updates preserve every project-authored byte outside marker regions.
3. `docs/` is tool-independent — it does not import or reference script internals. The MCP server reads `docs/` but `docs/` has no knowledge of the server.
4. Executable-review lifecycle validation may write outside `docs/` only to its bounded ignored host-local coordination state (the `project_state_publication_lock` carrier `.wavefoundry/locks/review-evidence-adoptions.lock`; the adoption-shaped basename is a stable compatibility ABI). Other MCP mutations—such as index state, edit-gate overrides, and platform rendering—remain limited to their explicitly documented tool scopes; this rule does not redefine those separate boundaries.
5. The local dashboard server is loopback-only and read-mostly: it may write host-local endpoint metadata under `.wavefoundry/`, but it must not mutate project docs, wave state, or git-tracked product state.
6. The semantic index (`.wavefoundry/index/`) is a derived artifact — it can always be deleted and rebuilt from source. Nothing outside `server.py` reads it directly.
7. Context-efficiency telemetry writes eligible calls through to SQLite. It can affect the public result only when neither the event nor the durable accounting-gap poison can be persisted; ordinary measurement/projection failures undercount or suppress the headline.
8. `.wavefoundry/logs/context-efficiency.sqlite` is ignored, host-local, and not an index or review authority. It stores opaque identifiers and accounting values, never paths, queries, returned content, prompts, secrets, or conversations. Public reads distinguish absent, healthy, accounting-gap, and failed state. The marker-owned checkpoint is a portable projection, not a numeric recovery source for lost store identity.
9. `review_policy.REVIEW_POLICY_CARRIER_REGISTRY` is the review-policy carrier authority. Its owner labels are permissions: `renderer` may replace only registered marker-owned regions; `lifecycle_reconciler` may replace only an exact registered marker or byte-known baseline section after an all-carrier preflight; `direct_docs` is validation-only and never writes a target repository. A destination may therefore have a `direct_docs` validation row and a separate `renderer` companion row whose only authority is the portable marker-bounded baseline; the validation row does not acquire write authority. No owner may broaden another owner's write boundary, and project-authored surrounding prose remains immutable.

## Interaction Edges

| Edge | Type | Stability | Owner |
|------|------|-----------|-------|
| `build_pack.py` → `.wavefoundry/framework/VERSION` | file write | stable | Engineering (packaging) |
| `lifecycle_id.py` → `docs/workflow-config.json` | file read | stable | Engineering |
| `docs_lint.py` / `docs_gardener.py` → `docs/` | file read/write | stable | Engineering |
| `techdocs_audit_lib.py` → `mkdocs.yml`, `docs/**`, git baseline via `index_state_store` | file read | stable | Engineering |
| `render_platform_surfaces.py` → `.claude/`, `.cursor/`, `.github/hooks/`, `.mcp.json`, and the framework-owned `.codex/config.toml` region | file write | stable | Engineering |
| `render_agent_surfaces.py` → framework-marked regions in registered `docs/agents/`, `docs/prompts/`, `docs/contributing/`, and explicitly enabled native `.claude/agents/` / `.codex/skills/` carriers | bounded file write | stable | Engineering (framework renderer) |
| `techdocs_baseline.py` / `render_agent_surfaces.render_techdocs_baseline` → `catalog-info.yaml`, `mkdocs.yml`, `docs/index.md` | missing-only whole-file write via the explicit `wf techdocs-baseline` command or the `wf_techdocs_baseline` MCP tool (`mode='run'`), both through the one module function (never the render pass, setup, or upgrade); templates read from `.wavefoundry/framework/install/*.template.*` | stable | Engineering (Refresh TechDocs workflow) |
| `wf_review_event` → `docs/waves/<wave>/events.jsonl` + `wave.md` | locked canonical event append plus generated Markdown current-head projection | stable | MCP lifecycle authoring tool |
| `review_evidence.py` → `.wavefoundry/locks/review-evidence-adoptions.lock` | host-local `project_state_publication_lock` coordination write | stable | MCP lifecycle validator |
| `review_policy_reconcile.py` → registered lifecycle carrier sections | all-or-nothing exact-section atomic replacement under lifecycle→publication ownership | stable | Upgrade lifecycle reconciler |
| `indexer.py` → `.wavefoundry/index/` | file write | stable | Engineering (setup/incremental) |
| `server.py` → `.wavefoundry/index/` | file read | stable | MCP server (search tools) |
| `server.py` → `.wavefoundry/logs/context-efficiency.sqlite` | bounded write-through event/source/evaluation transaction on eligible calls | stable | MCP server (context-efficiency telemetry) |
| `server.py` → `.wavefoundry/logs/context-efficiency.gap` | durable fail-closed poison when an accounting transaction cannot commit | stable | MCP server (context-efficiency telemetry) |
| `server.py` → `docs/waves/<wave>/wave.md` `## Context Efficiency` marker | project-global locked, marker-only atomic projection | stable | MCP server (context-efficiency telemetry) |
| `server.py` → `docs/waves/`, `docs/plans/`, `docs/prompts/` | file read/write | stable | MCP server (lifecycle + inspection tools) |
| `server.py` → `docs/agents/session-handoff.md` | file read/write | stable | MCP server (handoff tools) |
| `server.py` → `docs/agents/memory/archive/` + `docs/agents/memory-archive.md` | fenced rename plus atomic compact-register publication; archive bodies are explicit-history-only | stable | MCP server (memory lifecycle tools) |
| `dashboard_server.py` → `docs/waves/`, `docs/plans/`, `docs/prompts/prompt-surface-manifest.json`, `docs/agents/session-handoff.md` | file read | stable | Dashboard server |
| `dashboard_server.py` → `.wavefoundry/locks/dashboard-server.lock` | persistent OS-lock carrier + in-place metadata write | stable | Dashboard server |
| MCP client → `server.py` | stdio (FastMCP protocol) | stable | MCP client (Claude Code, Cursor, etc.) |
| Browser → `dashboard_server.py` | loopback HTTP | stable | Operator browser |
| Zip distribution → target repo `.wavefoundry/framework/` | file unpack | stable | Operator |
