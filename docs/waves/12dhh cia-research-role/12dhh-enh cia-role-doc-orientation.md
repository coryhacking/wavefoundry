# CIA Orientation in Role Docs

Change ID: `12dhh-enh cia-role-doc-orientation`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-05
Wave: `12dhh cia-research-role`

## Rationale

Wave 12dhh expanded the CIA from a pure retrieval tool to a research-and-document role, and seed-050 ensures new projects get CIA orientation sections in their role docs at install time. But the existing Wavefoundry role docs (`plan-feature`, `prepare-wave`, `implement-feature`, `implement-wave`, `review-wave`) do not yet reference the CIA — agents running those prompts have no guidance on when or how to use it.

Without this, the CIA is available but not in the flow. A planner writing a change doc, an implementer about to modify a module, or a reviewer checking call sites all benefit from a quick CIA orientation pass, but nothing in their current prompts tells them that.

## Requirements

1. Each affected role doc must include a `## CIA Orientation` section tailored to that role's workflow.
2. Each section must name the specific tools recommended for that role and describe when to use them.
3. Each section must include a pointer to the fallback path for when MCP is not available.
4. Sections must be concise — the role doc's primary content is the workflow; CIA orientation is a pre-step, not the main event.
5. All existing behavior in each role doc is preserved unchanged.

## Scope

**In scope:**
- Add `## CIA Orientation` to `docs/prompts/agents/plan-feature.prompt.md`
- Add `## CIA Orientation` to `docs/prompts/agents/prepare-wave.prompt.md`
- Add `## CIA Orientation` to `docs/prompts/agents/implement-feature.prompt.md`
- Add `## CIA Orientation` to `docs/prompts/agents/implement-wave.prompt.md`
- Add `## CIA Orientation` to `docs/prompts/agents/review-wave.prompt.md`

**Out of scope:**
- `close-wave.prompt.md` — closure is record-keeping, not research
- `init-wave-context.prompt.md` — context loading, not research
- `finalize-feature.prompt.md` — finalization is handoff, not research
- `upgrade-wave-context.prompt.md` — context upgrade, not research
- Corresponding seeds for these role docs (no seeds exist for them; they are project-specific runtime docs, not distributed seeds)

## Affected Architecture Docs

N/A — prompt surface changes only.

## Acceptance Criteria

| AC | Description |
|----|-------------|
| AC-1 | `plan-feature.prompt.md` has a `## CIA Orientation` section with planner-relevant tools and when-to-use guidance |
| AC-2 | `prepare-wave.prompt.md` has a `## CIA Orientation` section with scope-assessment-relevant tools |
| AC-3 | `implement-feature.prompt.md` has a `## CIA Orientation` section with implementer-relevant tools |
| AC-4 | `implement-wave.prompt.md` has a `## CIA Orientation` section with implementer-relevant tools |
| AC-5 | `review-wave.prompt.md` has a `## CIA Orientation` section or CIA tool guidance integrated into the reviewer lane table |
| AC-6 | All existing content in each role doc is preserved unchanged |
| AC-7 | Each `## CIA Orientation` section includes a pointer to the MCP fallback path |

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | planner is the highest-leverage integration point |
| AC-2 | required | prepare-wave scope assessment benefits directly from index orientation |
| AC-3 | required | implementer pre-condition checks are exactly what CIA tools support |
| AC-4 | required | wave implementer has same need as feature implementer |
| AC-5 | required | reviewer lanes already reference CIA tools in seed-050; role doc should match |
| AC-6 | required | no regressions in existing role behavior |
| AC-7 | required | fallback pointer ensures the guidance holds when MCP is not active |

## Tasks

1. Open `framework_edit_allowed` gate
2. Add `## CIA Orientation` to `plan-feature.prompt.md`
3. Add `## CIA Orientation` to `prepare-wave.prompt.md`
4. Add `## CIA Orientation` to `implement-feature.prompt.md`
5. Add `## CIA Orientation` to `implement-wave.prompt.md`
6. Add `## CIA Orientation` to `review-wave.prompt.md`
7. Close `framework_edit_allowed` gate
8. Run docs-lint / wave_validate

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-05 | Section named `## CIA Orientation` not `## MCP Tools` | The CIA is the agent, not the transport; naming it after the agent makes the relationship clear | Could use `## Codebase Research` — less specific, doesn't connect to the CIA prompt |
| 2026-05-05 | Orientation sections are role-specific, not copy-paste of seed-050 guidance | Each role has a different research need at a different point in the workflow | Could add one generic section to a shared file — reduces precision, harder to maintain |
| 2026-05-05 | `review-wave.prompt.md` integrates CIA guidance into the existing reviewer table rather than a standalone section | The reviewer table is the organizing structure; CIA tools fit naturally as a column or note there | Could add a standalone section — would duplicate the table's scope |
