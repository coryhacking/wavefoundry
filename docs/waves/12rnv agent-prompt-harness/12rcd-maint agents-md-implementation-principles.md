# AGENTS.md Implementation Principles

Change ID: `12rcd-maint agents-md-implementation-principles`
Change Status: `planned`
Owner: wave-coordinator
Status: planned
Last verified: 2026-05-19
Wave: `12rnv agent-prompt-harness`

## Rationale

AGENTS.md has a `## Core Principles` section that documents project-level design values. It does not currently document the behavioral principles that govern how agents implement changes — specifically around clarifying intent before acting, solution minimalism, scope containment, and explicit uncertainty. These principles prevent common failure modes (silent assumptions, over-engineering, scope creep, false confidence) and belong in the agent entry file where every session reads them.

## Requirements

1. The following four principles must appear in `AGENTS.md` under a dedicated `## Implementation Principles` section:
   - **Ask, don't assume.** If something is unclear, ask before writing a single line. Never make silent assumptions about intent, architecture, or requirements.
   - **Simplest solution first.** Always implement the simplest thing that could work. Do not add abstractions or flexibility that weren't explicitly requested.
   - **Don't touch unrelated code.** If a file or function is not directly part of the current task, do not modify it, even if you think it could be improved.
   - **Flag uncertainty explicitly.** If you are not confident about an approach or technical detail, say so before proceeding. Confidence without certainty causes more damage than admitting a gap.
2. The section must be placed after `## Core Principles` and before `## Stage Gate` so it is read at the start of every session.
3. Seed `050-agent-entry-surface-bootstrap.prompt.md` must reference the four principles so they are installed in target repository `AGENTS.md` files on upgrade.

## Scope

**Problem statement:** Agents can read the project-level design principles but have no explicit behavioral contract for how to handle ambiguity, scope, or uncertainty during implementation. The failure modes these principles prevent (silent assumptions, scope drift, over-engineering, overconfident answers) are recurring across waves.

**In scope:**

- Add `## Implementation Principles` section to `AGENTS.md` with the four principles
- Update seed `050-agent-entry-surface-bootstrap.prompt.md` to reference the four principles for target-repo AGENTS.md generation

**Out of scope:**

- Changes to any other AGENTS.md guidance sections
- Changes to seed prompts other than `050-`
- Target repository AGENTS.md files — those are updated via framework upgrade

## Acceptance Criteria

- AC-1: `AGENTS.md` contains an `## Implementation Principles` section with all four principles.
- AC-2: The section is placed after `## Core Principles` and before `## Stage Gate`.
- AC-3: Seed `050-agent-entry-surface-bootstrap.prompt.md` references the four principles so target-repo AGENTS.md files receive them on upgrade.
- AC-4: Docs-lint passes.

## Tasks

- Edit `AGENTS.md`: add `## Implementation Principles` section after `## Core Principles`
- Open `seed_edit_allowed` gate; edit `050-agent-entry-surface-bootstrap.prompt.md` to reference the four principles; close gate
- Run docs-lint

## Agent Execution Graph

| Workstream      | Owner            | Depends On | Notes |
| --------------- | ---------------- | ---------- | ----- |
| AGENTS.md edit  | wave-coordinator | —          | No gate required |
| seed-050 edit   | wave-coordinator | —          | seed_edit_allowed gate required |

## Serialization Points

- None — AGENTS.md and seed-050 are independent edits.

## Affected Architecture Docs

N/A — confined to agent guidance and seed. No impact on framework boundaries, data flow, or verification architecture.

## AC Priority

| AC   | Priority     | Rationale |
| ---- | ------------ | --------- |
| AC-1 | required     | Core deliverable |
| AC-2 | required     | Placement determines whether principles are read at session start |
| AC-3 | important    | Ensures target repos receive the principles on next upgrade |
| AC-4 | required     | Standard gate |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | Change doc created. | operator request |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-19 | New `## Implementation Principles` section rather than appending to `## Core Principles` | Core Principles documents project design values; Implementation Principles documents agent behavioral rules — distinct audiences and purpose | Append to Core Principles (rejected: mixes project design values with agent behavioral rules) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Principles may conflict with existing guidance in narrow edge cases | Principles are intentionally high-level; existing section-specific guidance takes precedence in its domain |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
