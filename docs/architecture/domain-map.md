# Domain Map

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Domains

| Domain | Path | Owned Responsibilities | Inbound Deps | Outbound Deps |
|--------|------|----------------------|-------------|---------------|
| **Framework Seeds** | `.wavefoundry/framework/seeds/` | Canonical prompt source; numbered seed prompts; overview docs; reference appendices | None — canonical source | Consumed by target repositories via install/upgrade |
| **Framework Scripts** | `.wavefoundry/framework/scripts/` | Lifecycle ID generation; docs linting; docs gardening; platform surface rendering; packaging; test running | `docs/workflow-config.json` (config read); `docs/` tree (lint/gardener read/write) | `.wavefoundry/framework/VERSION` (write); zip archives (write); .claude/, .cursor/, .github/hooks/ (render writes) |
| **Self-Hosted Docs** | `docs/` | Wavefoundry project operating surface: plans, waves, architecture, contributing, prompts, agent roles, journals | None | Consumed by framework scripts (lint/gardener) |
| **Wave Framework Distribution** | Root zip archives | Packaged distribution for target repositories | `.wavefoundry/framework/` tree | Target repository `.wavefoundry/framework/` after unpack |
| **Future MCP Server** | `src/wavefoundry/` (planned) | Read-only tool surface: wave inspection, validation, code search, seed resolution | Target repository roots (read) | MCP client responses |
| **Future Code Index** | `.wavefoundry/index.sqlite` (planned) | Local exact-search index over target repository files | Target repository files (read) | code.search tool |

## Dependency Direction Rules

1. `.wavefoundry/framework/seeds/` is source of truth for generic framework behavior — no domain modifies it except Wavefoundry maintainers through an explicit wave.
2. `.wavefoundry/framework/scripts/` reads `docs/` but does not own it; the docs tree is owned by the Wave Framework seeding process.
3. `docs/` never imports or references `src/wavefoundry/` (planned MCP implementation) — docs are tool-independent.
4. The future MCP server reads target repository paths; it must not write outside configured allowed roots without an explicit mutation tool.

## Interaction Edges

| Edge | Type | Stability | Owner |
|------|------|-----------|-------|
| `build_pack.py` → `.wavefoundry/framework/VERSION` | file write | stable | Engineering (packaging) |
| `lifecycle_id.py` → `docs/workflow-config.json` | file read | stable | Engineering |
| `docs_lint.py` / `docs_gardener.py` → `docs/` | file read/write | stable | Engineering |
| `render_platform_surfaces.py` → `.claude/`, `.cursor/`, `.github/hooks/` | file write | evolving | Engineering |
| Zip distribution → target repo `.wavefoundry/framework/` | file unpack | stable | Operator |

## Open Questions

- MCP server integration edges (tool call protocol, allowed-roots format): **TBD**
- Code index file format and location: **TBD**
