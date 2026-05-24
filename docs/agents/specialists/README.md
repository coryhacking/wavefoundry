# Specialist Agent Catalog

Owner: Engineering
Status: active
Last verified: 2026-05-23

Specialists extend the generic Wave Framework role set when a repository needs deeper domain coverage than the default planner / implementer / reviewer lanes provide. Specialist docs carry `Category: specialist` so the dashboard can group them consistently.

## Taxonomy

| Tier | Meaning |
|------|---------|
| senior builder specialist | primary implementation lane with senior domain expertise; routed by the wave coordinator based on admitted scope and repo evidence |
| universal specialist | broadly reusable across many software projects; primarily advisory or review-focused |
| archetype specialist | enabled from repository shape such as web/full-stack, mobile/desktop, AI/agent, JVM/service, or infrastructure-heavy repos |
| repo-local specialist | project-specific extension that should not be treated as a framework default |

**Senior builder specialists** differ from other specialist tiers: they are primary implementation lanes, not advisory reviewers. The wave coordinator allocates them in place of (or alongside) the generic `implementer` when the admitted change needs domain depth. Each builder specialist requires evidence-first stack detection before the first edit.

## Seed Candidates

Classification key: **adopt** = author role doc and seed now; **adapt** = adopt with scoping changes noted; **defer** = hold until clear demand; **reject** = out of scope for code-agent framework.

### Senior Builder Specialists

| Role | Seed | Classification | Routing Trigger |
|------|------|----------------|-----------------|
| `software-engineer` | `222-software-engineer.prompt.md` | **adopt** | Backend/API/service work; Java/JVM/Spring when present; SQL/persistence touched; testing, observability, or concurrency scope. |
| `frontend-developer` | `223-frontend-developer.prompt.md` | **adopt** | UI component or interaction surfaces; accessibility scope; design-system alignment required; frontend state or async behavior in scope. |
| `data-engineer` | `224-data-engineer.prompt.md` | **adopt** | SQL-heavy schema/migration/ETL work; data-contract stability; pipeline correctness or data-quality scope. |

### Challenger Specialists

| Role | Seed | Classification | Routing Trigger |
|------|------|----------------|-----------------|
| `red-team` | `225-red-team.prompt.md` | **adopt** | Adversarial review, bypass-path analysis, alternative-path challenge, technology/library evaluation before commitment, workflow and feature-definition challenge, design provocation, council participation. |
| `reality-checker` | `216-reality-checker.prompt.md` | **adopt** (universal) | Evidence skepticism, false-confidence detection, assumption validation across plan and delivery phases; fixed council seat in the default framework template. |

**Challenger specialists** differ from other specialist tiers: they improve decision quality by challenging proposals and delivered artifacts from adversarial, alternative-path, or evidence-skepticism perspectives. They do not own required specialist lane signoffs.

**Routing distinction:**
- `red-team` asks: "How can this be broken, bypassed, or improved by a stronger alternative?"
- `reality-checker` asks: "Is this claim actually evidenced?"
- `senior-engineering-challenger` (harness specialist) asks: "Is this plan or delivered result internally consistent and pressure-tested?"

### Universal Specialists

| Role | Seed | Classification | Rationale |
|------|------|----------------|-----------|
| `software-architect` | `227-software-architect.prompt.md` | **adopt** | Applicable across every repo type; clear routing contract around architectural decisions and system design. |
| `security-engineer` | `229-security-engineer.prompt.md` | **adopt** | Security concerns (threat modeling, vulnerability review, dependency audit) arise in virtually all software projects. |
| `technical-writer` | `233-technical-writer.prompt.md` | **adopt** | Documentation is universally needed; distinct from code authoring with a clear deliverable shape. |
| `codebase-onboarding-engineer` | — | **adopt** | Guides agents and contributors through unfamiliar codebases; high value on first-session orientation and handoff. |
| `devops-automator` | — | **adopt** | CI/CD pipelines, deployment automation, and developer workflow tooling; distinct from BPM and system architecture. |
| `reality-checker` | `216-reality-checker.prompt.md` | **adopt** | Adversarial assumption validation with no domain overlap; uniquely reduces blind-spot risk on any project. |
| `mcp-builder` | — | **defer** | Narrow scope — only relevant for projects building or integrating MCP tools; promote to universal if demand grows across the framework's target repos. |
| `lsp-index-engineer` | — | **defer** | Highly specialized to editor/LSP tooling; too narrow for the universal tier; reconsider when an LSP-heavy repo is onboarded. |

### Archetype Specialists

#### Web / full-stack

| Role | Seed | Classification | Rationale |
|------|------|----------------|-----------|
| `frontend-developer` | `223-frontend-developer.prompt.md` | **adopt** | Core web archetype; broad applicability across React, Vue, Angular, and other UI frameworks. |
| `backend-architect` | `226-backend-architect.prompt.md` | **adopt** | Service design, API contracts, and data layers recur across web and service repos. |
| `api-tester` | `232-api-tester.prompt.md` | **adopt** | Contract testing and API integration testing recur across every web/service repo; scope is distinct from general QA. |
| `database-optimizer` | `228-database-optimizer.prompt.md` | **adopt** | Schema design, query review, and migration safety are common web/service needs with actionable agent deliverables. |
| `devops-automator` | — | **adopt** | CI/CD, deployment pipelines, and infrastructure-as-code are common in web/service repos with a clear agent-addressable scope. |
| `sre` | — | **adopt** | Observability, reliability, and alerting patterns are increasingly expected even in smaller projects; bounded and actionable. |
| `accessibility-auditor` | — | **adopt** | WCAG compliance, ARIA semantics, and keyboard navigation are code-level concerns with a clear, bounded review contract. |
| `ui-designer` | — | **reject** | Visual design requires tools and human judgment outside the code-agent scope; not addressable by a text-based agent role. |
| `ux-researcher` | — | **reject** | User research (interviews, usability studies) is a human-centered discipline outside code-agent scope. |
| `ux-architect` | — | **adapt** | Narrow to interaction contracts, information architecture, and navigation patterns rather than visual design; adopt as `interaction-architect` once scoped. |

#### Mobile / desktop

| Role | Classification | Rationale |
|------|----------------|-----------|
| `mobile-app-builder` | **adopt** | Cross-platform mobile work (React Native, Flutter, Expo) is a well-defined archetype with distinct patterns. |
| `apple-platform-engineer` | **adopt** | Native Swift/SwiftUI/Objective-C expertise is sufficiently distinct from generic mobile to warrant its own role; especially relevant given the framework's macOS footprint. |

#### AI / agent systems

| Role | Seed | Classification | Rationale |
|------|------|----------------|-----------|
| `ai-engineer` | `231-ai-engineer.prompt.md` | **adopt** | ML model integration, prompt engineering, RAG pipelines, and eval harnesses are agent-addressable and recurring in AI repos. |
| `agentic-identity-and-trust-architect` | — | **adopt** | Trust boundaries and identity contracts in multi-agent systems are a real, bounded, and growing concern with clear design deliverables. |
| `incident-response-commander` | — | **defer** | Incident response involves production access and on-call coordination that code agents cannot execute; revisit if a runbook-authoring scope is defined. |

#### JVM / service

| Role | Classification | Rationale |
|------|----------------|-----------|
| `java-backend-engineer` | **adopt** | Covers the broad JVM ecosystem (Spring, Gradle/Maven, Micronaut) with a clear routing contract for JVM repos. |
| `spring-boot-engineer` | **defer** | Overlaps significantly with `java-backend-engineer`; adopt as a sub-specialization doc once `java-backend-engineer` is established and Spring-specific patterns need separate depth. |

#### Enterprise / integration

| Role | Seed | Classification | Rationale |
|------|------|----------------|-----------|
| `workflow-engineer` | `234-workflow-engineer.prompt.md` | **adopt** | BPM process architecture and engine implementation (Camunda, Temporal, Flowable, jBPM); approval chains, BPMN modeling, failure recovery, audit trails in high-governance environments. |
| `enterprise-integration-engineer` | `235-enterprise-integration-engineer.prompt.md` | **adopt** | Messaging middleware and event streaming integration (Kafka, RabbitMQ, Azure Service Bus, IBM MQ); delivery guarantees, schema compatibility, dead-letter handling. |

#### CLI / developer tools

| Role | Classification | Rationale |
|------|----------------|-----------|
| `terminal-integration-specialist` | **adopt** | CLI UX, shell scripting, and terminal integration patterns are a real domain distinct from other archetypes and recurring in developer-tool repos. |

## Inclusion Rules

- Add a specialist to the framework seed set when it is reusable across multiple repositories and has a clear routing contract.
- Keep specialists out of the public prompt table unless the repo actually enables them.
- Preserve repo-local specialists as local extensions instead of forcing them into the canonical framework taxonomy.

## Relationship To Generic Roles

- **Senior builder specialists** are primary implementation lanes that the wave coordinator routes to instead of (or alongside) the generic `implementer` when domain depth is needed. They are not advisory; they own the implementation of the admitted change.
- Other specialists complement generic roles without replacing them; they do not replace the stage gate, wave coordinator, or required reviewer lanes.
- Reviewer-style specialists should still produce explicit evidence, assumptions, and anti-goals in the same sharper structure now expected of canonical role docs.
- Repositories can enable a specialist without enabling every role in the same archetype family.
- Do not route all implementation through the generic `implementer` by habit when a senior builder specialist is the better fit for the admitted scope.
