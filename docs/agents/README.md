# Agent Roles — Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-04-28

Generic Wave Framework agent roles used in Wavefoundry delivery work. Role docs define operating identity, salience triggers, and memory responsibilities.

## Generic Roles

| Role | Doc | Primary Responsibility |
|------|-----|----------------------|
| planner | `docs/agents/planner.md` | Discovery, change doc authoring, wave planning |
| wave-coordinator | `docs/agents/wave-coordinator.md` | Wave admission, execution order, closure |
| implementer | `docs/agents/implementer.md` | Code changes per admitted change doc |
| code-reviewer | `docs/agents/code-reviewer.md` | Implementation correctness and pattern compliance |
| architecture-reviewer | `docs/agents/architecture-reviewer.md` | Boundary and layering impact |
| qa-reviewer | `docs/agents/qa-reviewer.md` | Verification coverage and defect risk |
| security-reviewer | `docs/agents/security-reviewer.md` | Trust and safety boundaries |
| docs-contract-reviewer | `docs/agents/docs-contract-reviewer.md` | Behavioral spec consistency |
| performance-reviewer | `docs/agents/performance-reviewer.md` | Performance and reliability impact |
| release-reviewer | `docs/agents/release-reviewer.md` | Packaging and distribution integrity |

## Persona Agents

See `docs/agents/personas/` for project-specific personas that represent the humans who use, operate, or deploy Wavefoundry.

## Factor-Review Agents

Applicable factor-review agent files are under `.claude/agents/`:
- `.claude/agents/factor-03-config.md` — configuration reading and defaults
- `.claude/agents/factor-05-build-release-run.md` — packaging and VERSION stamping
- `.claude/agents/factor-12-admin-processes.md` — CLI tool contracts
- `.claude/agents/factor-13-api-first.md` — MCP tool surface contracts

## Platform Mapping

See `docs/agents/platform-mapping.md` for how roles and factor agents are mapped to native agent platform files.
