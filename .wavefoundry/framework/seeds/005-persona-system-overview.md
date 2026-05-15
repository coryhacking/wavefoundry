# Persona System Overview

## Purpose

Explain how the Wave Framework uses project-specific persona agents to represent the users, operators, administrators, and deployers of the software system being built.

## What Personas Are

Persona agents represent the **humans who use or operate the software**, not the humans who build it.

They are invoked during the development workflow to give the user perspective:

- **Wave readiness review** — which user/operator perspectives must participate before implementation begins?
- **Spec authoring** — does this contract cover how I actually use this?
- **Design review** — does this change work for my configuration or workflow?
- **Acceptance** — does this meet my goals without introducing new friction?
- **Edge-case analysis** — what would I encounter in this situation?

Persona agents are AI agents — they can be invoked, they have defined roles, and they participate in specific development phases — but their job is to speak *as a user or operator*, not as a builder or reviewer.

## Distinction From Agent Roles

| | Agent Roles | Persona Agents |
|---|---|---|
| **Who they represent** | Builders: planners, implementers, reviewers, coordinators | Users, operators, admins, deployers of the software |
| **What they do** | Plan, implement, review, coordinate, close | Validate designs, surface user-facing edge cases, accept from the user's perspective |
| **When invoked** | Throughout the full development workflow | During readiness review, design, spec authoring, and acceptance |
| **Where defined** | `docs/agents/` | `docs/agents/personas/` |

Do not conflate persona agents with agent roles. They are complementary, not interchangeable.

## Shared Model

- Persona creation should be evidence-driven; do not invent personas for symmetry or aesthetics.
- Ground each persona in concrete usage patterns: architecture docs, behavior contracts, UI surfaces, failure docs, or user-facing bugs from the baseline wave.
- When evidence is sparse, ask the user who operates or uses the system before generating persona docs.
- Persona docs should stay stable and low-noise; changing lessons flow into journals and durable memory.
- Repo-local docs, not the shared pack, define the exact personas that exist for a given project.
- Start with the smallest well-grounded set. A single well-defined persona is more useful than five vague ones.

## Relationship To Review And Waves

- A wave should evaluate persona participation during the readiness gate before implementation begins.
- Persona lanes selected by readiness evaluation are gating for that wave's relevant checkpoints rather than optional commentary.
- The same readiness evaluation should be rerun during final review so implementation drift cannot bypass newly relevant persona concerns.
- Review gates remain defined by project policy in the repository; persona agents add the user perspective but do not replace reviewer lanes.

## Seeded Repository Expectations

Init and upgrade should synthesize or refresh project persona docs under:

- `docs/agents/personas/`

The local persona README and generated persona docs should define actual evidence, usage patterns, failure modes, invocation signals, and associated journals for that project.

## Persona Doc Section Structure

Persona docs use a fixed set of sections. Do not add sections from other doc types:

**Who** · **Goals** · **Workflows** · **Failure modes** · **Invocation signals** · **Operating identity** · **Salience triggers** · **Associated journal**

`## Scope` is a plan/change doc concept and must not appear in persona docs. Persona docs define a user or operator role — they do not have a delivery boundary or wave anchor. Evidence supporting a persona's existence belongs inline in **Who** and **Goals**, not in a separate section.

## Related Docs

- `.wavefoundry/framework/seeds/120-project-persona-synthesis.prompt.md`
- `docs/agents/personas/README.md`
- `docs/contributing/agent-team-workflow.md`
