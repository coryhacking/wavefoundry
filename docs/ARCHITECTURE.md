# Architecture

Owner: Engineering
Status: active
Last verified: 2026-04-28

Hub index for Wavefoundry architecture documentation. Child docs provide detail; this file provides scope, update triggers, and cross-links.

## Scope

Wavefoundry is a framework and tooling repository: canonical Wave Framework seed prompts, Python CLI scripts, planned local MCP server. No shipped user-facing application.

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
| `docs/architecture/decisions/` | Architecture Decision Records (ADRs) | active |

## Update Triggers

Update this hub and relevant child docs when:
- MCP server is scaffolded (updates current-state, domain-map, data-and-control-flow)
- Transport decision is made (updates current-state, threat-model)
- New framework tool is added (updates domain-map, data-and-control-flow)
- Integration contract changes (updates layering-rules boundary invariants)
- New test tier or CI gate is added (updates testing-architecture)

## Cross-Links

- `docs/repo-index.md` — inventory and architecture handoff
- `docs/specs/` — behavioral contracts (does not exist yet; see `docs/missing-docs.md`)
- `docs/architecture/decisions/README.md` — ADR index
