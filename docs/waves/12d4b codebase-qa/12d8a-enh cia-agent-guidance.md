# CIA Agent Guidance — Cross-Role Usage

Change ID: `12d8a-enh cia-agent-guidance`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-04
Wave: `12d4b codebase-qa`

## Rationale

The CIA prompt (`code-insight-agent.prompt.md` / `seed-211`) documents how the five reviewer lanes use the MCP search tools. But the agents that do the most file-reading work — planner, implementer, wave coordinator, and project personas — have no guidance on using CIA tools for orientation before diving into code. This creates a gap where those agents either make speculative assumptions or burn context on full file reads when a focused `code_ask` or `code_search` pass would answer the same question faster.

## Requirements

1. The CIA prompt must document usage by planning, implementation, and coordination roles — not only reviewer lanes.
2. The `seed-050` role-doc generation rules must instruct that seeded role docs (planner, implementer, wave-coordinator) include an **MCP tools** section pointing to CIA as the first-stop orientation tool before reading files or writing plans.
3. Coverage must include persona agents — they should ground answers in indexed evidence, not memory recall.

## Scope

**In scope:**
- Extend `## Usage by Specialist Agents` (or add a new `## Usage by Planning and Implementation Agents` section) in `docs/prompts/agents/code-insight-agent.prompt.md` and `seed-211`
- Update `seed-050` to instruct that generated planner, implementer, and wave-coordinator role docs include an MCP tools / CIA orientation section
- Cover persona agents in the CIA prompt guidance

**Out of scope:**
- Editing the actual seeded role docs for planner/implementer/wave-coordinator in target repositories (those get refreshed by **Upgrade wave framework**)
- Changes to `seed-170` / `seed-180` (plan-feature / implement-feature prompts) — CIA guidance in those prompts is a follow-on candidate

## Affected Architecture Docs

N/A — seed distribution artifacts only, no module boundary or data flow change.

## Acceptance Criteria

| AC | Description |
|----|-------------|
| AC-1 | `code-insight-agent.prompt.md` includes guidance for planner, implementer, wave-coordinator, and persona agent roles with recommended tools and use cases |
| AC-2 | `seed-211` matches the updated `code-insight-agent.prompt.md` content |
| AC-3 | `seed-050` instructs that generated planner, implementer, and wave-coordinator role docs include a CIA / MCP tools orientation section |
| AC-4 | All pre-existing framework tests pass |

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Source of truth for CIA usage must cover all production roles |
| AC-2 | required | Seed must match source or target repos receive stale guidance |
| AC-3 | required | Role docs seeded without CIA guidance leave the gap unaddressed |
| AC-4 | required | Non-regression |

## Tasks

1. Open `seed_edit_allowed` gate
2. Extend `docs/prompts/agents/code-insight-agent.prompt.md` — add planning/implementation/coordination/persona agent rows and guidance
3. Update `seeds/211-code-insight-agent.prompt.md` to match
4. Update `seed-050` role-doc generation rules to add CIA / MCP tools section requirement for planner, implementer, wave-coordinator
5. Close `seed_edit_allowed` gate
6. Run framework tests

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-04 | Extend CIA prompt rather than seed-050 alone | CIA prompt is the canonical reference; seed-050 just points at it | Could add to seed-170/180 implement loop — deferred to follow-on |
| 2026-05-04 | Include persona agents | Personas answer user questions; grounding in indexed evidence vs memory recall is a concrete behavioral improvement | Could defer to persona seed update |
