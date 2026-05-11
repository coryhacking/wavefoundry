# Agent Roles — Wavefoundry

Owner: Engineering
Status: active
Last verified: 2026-05-08

Generic Wave Framework agent roles used in Wavefoundry delivery work. Role docs define operating identity, salience triggers, and memory responsibilities.

## Generic Roles

| Role | Doc | Primary Responsibility |
|------|-----|----------------------|
| planner | `docs/agents/planner.md` | Discovery, change doc authoring, wave planning |
| wave-coordinator | `docs/agents/wave-coordinator.md` | Wave admission, execution order, closure |
| council-moderator | `docs/agents/council-moderator.md` | Wave Council synthesis and verdict ownership |
| implementer | `docs/agents/implementer.md` | Code changes per admitted change doc |
| code-reviewer | `docs/agents/code-reviewer.md` | Implementation correctness and pattern compliance |
| architecture-reviewer | `docs/agents/architecture-reviewer.md` | Boundary and layering impact |
| qa-reviewer | `docs/agents/qa-reviewer.md` | Verification coverage and defect risk |
| security-reviewer | `docs/agents/security-reviewer.md` | Trust and safety boundaries |
| docs-contract-reviewer | `docs/agents/docs-contract-reviewer.md` | Behavioral spec consistency |
| performance-reviewer | `docs/agents/performance-reviewer.md` | Performance and reliability impact |
| release-reviewer | `docs/agents/release-reviewer.md` | Packaging and distribution integrity |

## Universal Specialists

Currently supported universal specialists. These are the cross-project roles that now have canonical role docs and are valid framework seed candidates when repo evidence or operator intent enables them.

| Role | Primary Responsibility |
|------|------------------------|
| software-architect | Cross-cutting system design and major topology decisions |
| security-engineer | Threat modeling, trust-boundary review, and security hardening |
| technical-writer | Operator-facing docs authoring and durable guidance polish |
| codebase-onboarding-engineer | Read-only repo discovery, architecture walkthroughs, onboarding maps |
| workflow-architect | Happy-path, failure-path, and handoff design before implementation |
| reality-checker | Evidence-first release skepticism and claim validation; fixed seat in the default Wave Council template |

## Archetype Specialists

Currently supported archetype specialists. Enable these from repository shape rather than seeding them everywhere by default.

### Web / Full-Stack

- `frontend-developer`
- `backend-architect`
- `devops-automator`
- `sre`
- `accessibility-auditor`
- `api-tester`
- `database-optimizer`

### Mobile / Desktop

- `mobile-app-builder`
- `apple-platform-engineer`

### AI / Agent Systems

- `ai-engineer`
- `agentic-identity-and-trust-architect`

### JVM / Service Platforms

- `java-backend-engineer`

### CLI / Developer Tools

- `terminal-integration-specialist`

## Repo-Local Specialists

Repo-local specialists capture project-specific workflows or domain surfaces that should not be generalized into the framework seed set. Keep them clearly separated from universal and archetype specialists so upgrades can preserve local additions without confusing them for framework defaults.

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

## Specialist Catalog

See `docs/agents/specialists/README.md` for the full specialist catalog, including adopted roles, deferred candidates, rejected roles, and adaptations that are not yet part of the supported framework surface.
