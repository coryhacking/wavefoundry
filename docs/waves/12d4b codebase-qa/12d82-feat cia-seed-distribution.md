# CIA Seed Distribution

Change ID: `12d82-feat cia-seed-distribution`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-05-04
Wave: `12d4b codebase-qa`

## Rationale

The Code Insight Agent prompt (`code-insight-agent.prompt.md`), `performance-reviewer.prompt.md`, and `security-reviewer.prompt.md` were authored in wave 12d4b but exist only in Wavefoundry's own project surface. Target repositories that run **Upgrade wave framework** get the new server tools (`code_ask`, `code_dependencies`, `code-summary`, `doc-summary`) but receive no prompt bodies or `docs/prompts/index.md` entry for the CIA. The reviewer prompt bodies are referenced by name in `seed-010` and `seed-050` but have no backing content in the distribution.

## Requirements

1. `code-insight-agent.prompt.md` must be shipped as a seed so target repos receive it under `docs/prompts/agents/` during install and upgrade.
2. `performance-reviewer.prompt.md` and `security-reviewer.prompt.md` must be shipped as seeds, backing the role names already referenced in `seed-010` and `seed-050`.
3. `seed-010` output list must include all three new prompt files.
4. `seed-160` backfill list must include all three new prompt files so existing repos receive them on next upgrade.
5. `seed-100` must add a rule to include `Ask codebase` / `code_ask` in the `docs/prompts/index.md` it generates.

## Scope

**In scope:**
- Three new seed files: `211-code-insight-agent.prompt.md`, `212-performance-reviewer.prompt.md`, `213-security-reviewer.prompt.md`
- `seed-010` and `seed-160` output/backfill lists updated
- `seed-100` `docs/prompts/index.md` generation rule updated

**Out of scope:**
- Changing the content of the CIA or reviewer prompts (finalized in 12d4b)
- Updating any target repository (job of **Upgrade wave framework** in the consuming repo)

## Affected Architecture Docs

N/A — no boundary, flow, or module-level change. Seeds are distribution artifacts.

## Acceptance Criteria

| AC | Description |
|----|-------------|
| AC-1 | `seed-211-code-insight-agent.prompt.md` exists in `.wavefoundry/framework/seeds/` with content matching `docs/prompts/agents/code-insight-agent.prompt.md` |
| AC-2 | `seed-212-performance-reviewer.prompt.md` exists with content matching `docs/prompts/agents/performance-reviewer.prompt.md` |
| AC-3 | `seed-213-security-reviewer.prompt.md` exists with content matching `docs/prompts/agents/security-reviewer.prompt.md` |
| AC-4 | `seed-010` output list under `docs/prompts/agents/` includes all three files |
| AC-5 | `seed-160` backfill list includes all three files |
| AC-6 | `seed-100` includes a rule to add `Ask codebase` / `code_ask` to `docs/prompts/index.md` |
| AC-7 | All pre-existing framework tests pass |

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | CIA unreachable in target repos without this |
| AC-2 | required | Reviewer body missing despite role name in seeds |
| AC-3 | required | Reviewer body missing despite role name in seeds |
| AC-4 | required | Install flow incomplete without output list entry |
| AC-5 | required | Upgrade flow incomplete without backfill entry |
| AC-6 | required | Target repo index missing code_ask shortcut |
| AC-7 | required | Non-regression |

## Tasks

1. Open `seed_edit_allowed` gate
2. Create `seeds/211-code-insight-agent.prompt.md` — content from `docs/prompts/agents/code-insight-agent.prompt.md`
3. Create `seeds/212-performance-reviewer.prompt.md` — content from `docs/prompts/agents/performance-reviewer.prompt.md`
4. Create `seeds/213-security-reviewer.prompt.md` — content from `docs/prompts/agents/security-reviewer.prompt.md`
5. Update `seed-010` output list to include the three files under `docs/prompts/agents/`
6. Update `seed-160` backfill list to include the three files
7. Update `seed-100` to include `Ask codebase` / `code_ask` row in `docs/prompts/index.md` generation rules
8. Close `seed_edit_allowed` gate
9. Run framework tests

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
|------------|-------|------------|-------|
| seed-files | implementer | — | Create seeds 211–213 |
| seed-010-update | implementer | seed-files | Add output list entries |
| seed-160-update | implementer | seed-files | Add backfill list entries |
| seed-100-update | implementer | seed-files | Add index.md rule |
| tests | implementer | all above | Run framework tests |

## Serialization Points

- All seed file edits must be within the `seed_edit_allowed` gate window.

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-04 | Seed numbers 211–213 | 210 is the last used seed; these are the next available slots | N/A |
| 2026-05-04 | Seeds are copies of project-local prompt bodies | Seeds are standalone shipped artifacts; project-local files remain canonical for self-hosting | References would require target repos to reach back into framework source |
| 2026-05-04 | seed-100 only adds index row, not the prompt body | Prompt body emission is seed-211's job; seed-100 handles index.md generation | Could collapse both into one seed |
