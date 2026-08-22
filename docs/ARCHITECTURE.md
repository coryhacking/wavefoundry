# Architecture

Owner: Engineering
Status: active
Last verified: 2026-08-21

Hub index for Wavefoundry architecture documentation. Child docs provide detail; this file provides scope, update triggers, and cross-links.

## How the system is put together

Wavefoundry is a framework-and-tooling repository, not a product application: it ships the Wave Framework seed prompts, Python CLI scripts, a local MCP server, and an optional loopback dashboard, and no networked service (Scope below; [Project overview](references/project-overview.md), What Wavefoundry Is). The repository is two trees with different owners: `.wavefoundry/framework/` is the canonical framework product (seeds, scripts, install templates, dashboard assets, `VERSION`) that is packaged and installed into every target repository, while `docs/` is this repository's own self-hosted operating surface, which the scripts read but which never imports script internals ([Domain map](architecture/domain-map.md), Domains and Dependency Direction Rules items 1 and 3). Seeds are the source of truth for generic framework behavior and change only through an explicit wave under the `seed_edit_allowed` gate, a flag in the gitignored `.wavefoundry/guard-overrides.json` ([Domain map](architecture/domain-map.md), Dependency Direction Rules item 1; `render_platform_surfaces.GUARD_OVERRIDES_REL`, line 16).

At runtime a reader meets four pieces: `wf setup` bootstraps the shared tool venv and builds the single semantic index at `.wavefoundry/index/` (`setup_wavefoundry.main`, lines 281-453; `indexer.INDEX_DIR_NAME`, line 46); `server.py` builds a FastMCP app and serves it over stdio to the agent host through rendered configs such as `.mcp.json` (`server.build_server`, `server.py` lines 486-563; `server.main`, lines 582-624; `render_platform_surfaces.render_mcp_json`, lines 1489-1522); `dashboard_server.py` serves a loopback-only, read-only viewer that writes only host-local state under `.wavefoundry/`: its lifetime lock and endpoint-metadata carrier under `.wavefoundry/locks/` and a diagnostic log at `.wavefoundry/logs/dashboard.log` (`dashboard_lib.dashboard_metadata_path`, lines 217-225; [Data and control flow](architecture/data-and-control-flow.md), Paths 7 and 8); and `build_pack.py` with `upgrade_wavefoundry.py` package a source-only zip to `~/.wavefoundry/dist/` and install it into targets by extracting only `.wavefoundry/` members plus one transient root bootstrap file (`build_pack._DEFAULT_DIST_DIR`, line 68; `upgrade_wavefoundry._extract_feature_members`, lines 914-928).

The framework's write footprint in a target is documented and code-scoped: `.wavefoundry/framework/` on install and upgrade, rendered host surfaces, marker-bounded regions and explicit lifecycle records under `docs/`, and ignored host-local state under `.wavefoundry/`; it never writes `.github/workflows/` or `.git/hooks/`, project-authored bytes outside marker regions, or any path outside the repository root (`render_platform_surfaces._PLATFORM_WRITE_ROOTS`, lines 130-137; `_preflight_platform_render_paths`, lines 140-176; `server_impl.resolve_path_under_root`, lines 3283-3309; [Layering rules](architecture/layering-rules.md), Boundary Invariants).

The documented principle (repository `AGENTS.md`) is that no network call is required at runtime for install, upgrade, validation, indexing, or packaging; the two network touchpoints to know are these: setup may download Python dependencies and embedding models before verifying the cache offline, and the dashboard's browser assets load from unpkg on first load (`setup_index._offline_env`, lines 597-607; [Data and control flow](architecture/data-and-control-flow.md), Path 5 steps 2-3 and Path 7 step 5). Everything runs with the operator's own authority: the MCP server speaks stdio to its host process and opens no listener, the dashboard binds loopback by default and warns on any other host, and neither carries authentication; the [threat model](architecture/threat-model.md) names the promotion triggers that would re-scope that (Trust Boundaries, Promotion Triggers).

The review-authority tables (Boundary Invariants and Allowed Dependencies in the layering rules, Interaction Edges and Dependency Direction Rules in the domain map, State Ownership in data-and-control-flow) are the structural authority; this hub summarizes and links to them and does not restate their rows.

## Scope

Wavefoundry is a framework and tooling repository: canonical Wave Framework seed prompts, Python CLI scripts, a local MCP server, and an optional local loopback dashboard surface. No networked product application is shipped from this repository.

## Child Docs

| Doc | Purpose | Status |
|-----|---------|--------|
| `docs/architecture/current-state.md` | Runtime topology, major flows, current risks | active |
| `docs/architecture/domain-map.md` | Named domains, responsibilities, interaction edges | active |
| `docs/architecture/layering-rules.md` | Allowed/forbidden dependencies; boundary invariants | active |
| `docs/architecture/cross-cutting-concerns.md` | Config, logging, observability, shared utilities | active |
| `docs/architecture/data-and-control-flow.md` | Control paths, state ownership, mutations | active |
| `docs/architecture/testing-architecture.md` | Test tiers, target ownership, CI hooks | active |
| `docs/architecture/threat-model.md` | Trust boundaries, security posture | active |
| `docs/architecture/performance-budget.md` | Performance expectations and hotspots | active |
| `docs/architecture/design-system.md` | Design-system extraction philosophy, regeneration semantics, semantic index relationship | active |
| `docs/architecture/search-architecture.md` | Semantic index layers, retrieval, reranking, and `code_ask` behavior | active |
| `docs/architecture/graph-index-system.md` | Graph schema, generation pipeline, query layer, clustering, and MCP tool integration | active |
| `docs/architecture/chunking-and-indexing-pipeline.md` | End-to-end file discovery, chunking, embedding, and index storage | active |
| `docs/architecture/decisions/` | Architecture Decision Records (ADRs) | active |

## Update Triggers

Update this hub and relevant child docs when:
- MCP server is scaffolded (updates current-state, domain-map, data-and-control-flow)
- Transport decision is made (updates current-state, threat-model)
- New framework tool is added (updates domain-map, data-and-control-flow)
- Local dashboard server or browser asset contract changes (updates current-state, domain-map, threat-model, design-system)
- Integration contract changes (updates layering-rules boundary invariants)
- New test tier or CI gate is added (updates testing-architecture)

## Cross-Links

- `docs/repo-index.md` — inventory and architecture handoff
- `docs/specs/mcp-tool-surface.md`: behavioral contract for the MCP tool surface, the governing contract for follow-on MCP work (repository path outside the published TechDocs site; named in `docs/architecture/current-state.md`, Current Risk Areas)
- `docs/architecture/decisions/README.md` — ADR index
- `docs/architecture/decisions/1tsbu-adr review-policy-and-upgrade-protocol.md` — review-policy authority, shared evaluator, lock order, reconciliation, and protocol-2 bridge
