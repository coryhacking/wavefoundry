# Dashboard: Remove Completed AC/Task Strikethrough

Change ID: `12jng-bug remove-dialog-item-strikethrough`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-12
Wave: `12jnb project-index-stale-use-index-inputs`

## Rationale

Completed acceptance-criteria and task items in the dashboard dialogs currently render with a line-through. That treatment makes the lists harder to scan and is heavier than needed now that completion is already shown by the checkmark and muted text color.

## Requirements

1. Completed AC items must not render with a strike-through.
2. Completed task items must not render with a strike-through.
3. Existing completion affordances such as checkmarks and muted color may remain.
4. Verification must pass.

## Scope

**Problem statement:** the dashboard metric dialogs visually over-emphasize completed AC/task items with line-through styling.

**In scope:**

- `.wavefoundry/framework/dashboard/dashboard.css`
  - Remove strike-through styling from completed metric-dialog list items
- Active wave record updates

**Out of scope:**

- Changing completion status logic
- Changing other dashboard typography

## Acceptance Criteria

- AC-1: Completed AC entries display without strike-through.
- AC-2: Completed task entries display without strike-through.
- AC-3: Checkmark and muted-color completion cues remain intact.
- AC-4: Verification passes.

## Tasks

- Remove line-through declarations from completed dialog item styling
- Record the change in the active wave
- Run docs lint

## Affected Architecture Docs

N/A - CSS presentation only.

## AC Priority

| AC | Priority | Rationale |
|----|----------|-----------|
| AC-1 | required | Primary operator-facing issue |
| AC-2 | required | Same shared dialog pattern applies to tasks |
| AC-3 | important | Preserve readable completion cues |
| AC-4 | required | Verification gate |

## Progress Log

| Date | Update | Evidence |
|------|--------|----------|
| 2026-05-12 | Change doc created for the dialog completed-item typography tweak. | Dashboard operator request |
| 2026-05-12 | Removed the completed-item line-through from the shared metric dialog rule used by both AC and task dialogs, preserving the checkmark and muted color cues. | `.wavefoundry/framework/dashboard/dashboard.css`; `./.wavefoundry/bin/docs-lint` |

## Decision Log

| Date | Decision | Reason | Alternatives |
|------|----------|--------|--------------|
| 2026-05-12 | Keep muted color and checkmark cues but remove only the line-through styling | Minimal change fixes readability without changing completion semantics | Rework the entire completed-item visual treatment (rejected: unnecessary scope) |

## Risks

| Risk | Mitigation |
|------|------------|
| Removing the strike-through could make completed items less distinct | Keep the existing done checkmark and muted text color |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
