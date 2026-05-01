# Specialist Agent Catalog

Owner: Engineering
Status: active
Last verified: 2026-04-30

Specialists extend the generic Wave Framework role set when a repository needs deeper domain coverage than the default planner / implementer / reviewer lanes provide.

## Taxonomy

| Tier | Meaning |
|------|---------|
| universal specialist | broadly reusable across many software projects |
| archetype specialist | enabled from repository shape such as web/full-stack, mobile/desktop, AI/agent, JVM/service, or infrastructure-heavy repos |
| repo-local specialist | project-specific extension that should not be treated as a framework default |

## Seed Candidates

Classification key: **adopt** = author role doc and seed now; **adapt** = adopt with scoping changes noted; **defer** = hold until clear demand; **reject** = out of scope for code-agent framework.

### Universal Specialists

| Role | Classification | Rationale |
|------|----------------|-----------|
| `software-architect` | **adopt** | Applicable across every repo type; clear routing contract around architectural decisions and system design. |
| `security-engineer` | **adopt** | Security concerns (threat modeling, vulnerability review, dependency audit) arise in virtually all software projects. |
| `technical-writer` | **adopt** | Documentation is universally needed; distinct from code authoring with a clear deliverable shape. |
| `codebase-onboarding-engineer` | **adopt** | Guides agents and contributors through unfamiliar codebases; high value on first-session orientation and handoff. |
| `workflow-architect` | **adopt** | Dev workflows, automation pipelines, and process design are distinct from system architecture and recur across repos. |
| `reality-checker` | **adopt** | Adversarial assumption validation with no domain overlap; uniquely reduces blind-spot risk on any project. |
| `mcp-builder` | **defer** | Narrow scope — only relevant for projects building or integrating MCP tools; promote to universal if demand grows across the framework's target repos. |
| `lsp-index-engineer` | **defer** | Highly specialized to editor/LSP tooling; too narrow for the universal tier; reconsider when an LSP-heavy repo is onboarded. |

### Archetype Specialists

#### Web / full-stack

| Role | Classification | Rationale |
|------|----------------|-----------|
| `frontend-developer` | **adopt** | Core web archetype; broad applicability across React, Vue, Angular, and other UI frameworks. |
| `backend-architect` | **adopt** | Service design, API contracts, and data layers recur across web and service repos. |
| `ui-designer` | **reject** | Visual design requires tools and human judgment outside the code-agent scope; not addressable by a text-based agent role. |
| `ux-researcher` | **reject** | User research (interviews, usability studies) is a human-centered discipline outside code-agent scope. |
| `ux-architect` | **adapt** | Narrow to interaction contracts, information architecture, and navigation patterns rather than visual design; adopt as `interaction-architect` once scoped. |
| `devops-automator` | **adopt** | CI/CD, deployment pipelines, and infrastructure-as-code are common in web/service repos with a clear agent-addressable scope. |
| `sre` | **adopt** | Observability, reliability, and alerting patterns are increasingly expected even in smaller projects; bounded and actionable. |
| `accessibility-auditor` | **adopt** | WCAG compliance, ARIA semantics, and keyboard navigation are code-level concerns with a clear, bounded review contract. |
| `api-tester` | **adopt** | Contract testing and API integration testing recur across every web/service repo; scope is distinct from general QA. |
| `database-optimizer` | **adopt** | Schema design, query review, and migration safety are common web/service needs with actionable agent deliverables. |

#### Mobile / desktop

| Role | Classification | Rationale |
|------|----------------|-----------|
| `mobile-app-builder` | **adopt** | Cross-platform mobile work (React Native, Flutter, Expo) is a well-defined archetype with distinct patterns. |
| `apple-platform-engineer` | **adopt** | Native Swift/SwiftUI/Objective-C expertise is sufficiently distinct from generic mobile to warrant its own role; especially relevant given the framework's macOS footprint. |

#### AI / agent systems

| Role | Classification | Rationale |
|------|----------------|-----------|
| `ai-engineer` | **adopt** | ML model integration, prompt engineering, RAG pipelines, and eval harnesses are agent-addressable and recurring in AI repos. |
| `incident-response-commander` | **defer** | Incident response involves production access and on-call coordination that code agents cannot execute; revisit if a runbook-authoring scope is defined. |
| `agentic-identity-and-trust-architect` | **adopt** | Trust boundaries and identity contracts in multi-agent systems are a real, bounded, and growing concern with clear design deliverables. |

#### JVM / service

| Role | Classification | Rationale |
|------|----------------|-----------|
| `java-backend-engineer` | **adopt** | Covers the broad JVM ecosystem (Spring, Gradle/Maven, Micronaut) with a clear routing contract for JVM repos. |
| `spring-boot-engineer` | **defer** | Overlaps significantly with `java-backend-engineer`; adopt as a sub-specialization doc once `java-backend-engineer` is established and Spring-specific patterns need separate depth. |

#### CLI / developer tools

| Role | Classification | Rationale |
|------|----------------|-----------|
| `terminal-integration-specialist` | **adopt** | CLI UX, shell scripting, and terminal integration patterns are a real domain distinct from other archetypes and recurring in developer-tool repos. |

## Inclusion Rules

- Add a specialist to the framework seed set when it is reusable across multiple repositories and has a clear routing contract.
- Keep specialists out of the public prompt table unless the repo actually enables them.
- Preserve repo-local specialists as local extensions instead of forcing them into the canonical framework taxonomy.

## Relationship To Generic Roles

- Specialists complement generic roles; they do not replace the stage gate, wave coordinator, or required reviewer lanes.
- Reviewer-style specialists should still produce explicit evidence, assumptions, and anti-goals in the same sharper structure now expected of canonical role docs.
- Repositories can enable a specialist without enabling every role in the same archetype family.
