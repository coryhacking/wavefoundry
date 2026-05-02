# Journal Upgrade Coverage Gaps

Change ID: `12bc3-enh journal-upgrade-coverage-gaps`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-02
Wave: TBD

## Rationale

The seed-160 journal upgrade step (added in wave `12b9x`) handles the common case — renaming `Recent Captures` → `Active Signals`, deleting activity-log entries, and verifying section order — but post-upgrade review of a target repo revealed three gaps that caused significant cleanup to be missed:

1. **Non-standard activity-log section names**: The upgrade step only looks for `Recent Captures`. Journals in the wild may have other chronological activity-log sections (e.g. `## Recent Entries`) that contain the same anti-pattern under a different heading. The step needs to detect activity-log sections by content behavior, not by name.

2. **Missing `## Distillation` section**: The upgrade step verifies that Distillation appears before Active Signals, but does not instruct the agent to *create* a Distillation section if it is absent. Journals may have accumulated rich incident/lesson entries that were never distilled into bullets.

3. **Stale cross-references to deleted sections**: After an activity-log section is deleted, other sections (e.g. `## Retirement And Supersession`) may still reference the deleted section by name. The step does not include a pass to clean up these dangling references.

## Requirements

1. seed-160 journal upgrade sub-step must broaden activity-log section detection: rename `Recent Captures` → `Active Signals` if present; also identify and delete *any other* section whose entries are solely wave-closed records, change-shipped summaries, or test-pass notes — regardless of the section heading name.
2. seed-160 journal upgrade sub-step must add: if no `## Distillation` section exists, create one by reviewing Incidents and any remaining journal entries for lessons not yet extracted, and promoting qualifying lessons as concise distillation bullets.
3. seed-160 journal upgrade sub-step must add: after deleting any sections, scan remaining sections for references to the deleted section names and remove or replace them.
4. seed-210 (distillation prompt) must mirror requirements 1–3 so the distillation pass catches the same gaps.

## Scope

**Problem statement:** The journal upgrade step misses activity-log sections with non-standard names, leaves journals without Distillation sections, and does not clean up dangling cross-references after deleting sections.

**In scope:**

- seed-160: broaden activity-log section detection, add Distillation creation step, add dangling-reference cleanup pass
- seed-210: mirror the same three improvements for the distillation pass

**Out of scope:**

- Adding a lint rule to enforce Distillation section presence (separate change)
- Changing the journal schema or adding new required sections
- Retroactively updating any in-repo journals (those should be fixed manually in the target repo)

## Acceptance Criteria

- AC-1: seed-160 journal upgrade step instructs the agent to delete any chronological activity-log section, not only those named `Recent Captures`.
- AC-2: seed-160 journal upgrade step instructs the agent to create a `## Distillation` section (with extracted lessons) if none exists.
- AC-3: seed-160 journal upgrade step instructs the agent to clean up references to deleted sections in other sections.
- AC-4: seed-210 distillation prompt mirrors AC-1 through AC-3.

## Tasks

- Open `seed_edit_allowed` gate.
- Edit seed-160 journal upgrade sub-step: broaden activity-log section detection, add Distillation creation instruction, add dangling-reference cleanup instruction.
- Edit seed-210: mirror the same three additions.
- Close `seed_edit_allowed` gate.
- Run `wave_validate`.

## Agent Execution Graph

| Workstream  | Owner       | Depends On | Notes                                     |
| ----------- | ----------- | ---------- | ----------------------------------------- |
| seed-edits  | implementer | —          | seeds 160 and 210 under seed_edit_allowed |
| validation  | implementer | seed-edits | `wave_validate` after edits               |

## Serialization Points

- `seed_edit_allowed` gate must be open for all seed edits; close immediately after both seeds are updated.

## Affected Architecture Docs

N/A — seed content only, no boundary or flow changes.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority      | Rationale |
| ---- | ------------- | --------- |
| AC-1 | required      | Core gap — non-standard section names are the primary failure mode found in review |
| AC-2 | required      | A journal without Distillation is structurally incomplete; upgrade must create it  |
| AC-3 | important     | Dangling references cause confusion but are lower-risk than missing content        |
| AC-4 | required      | Distillation prompt must stay in sync with upgrade step or the gap recurs          |

## Progress Log

| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-05-02 | Created |          |
| 2026-05-02 | Implementation complete | seeds 160 and 210 updated; mcp-builder review findings addressed; docs-lint clean |

## Decision Log

| Date       | Decision                                                               | Reason                                                                                              | Alternatives                                                                       |
| ---------- | ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 2026-05-02 | Detect activity-log sections by entry content, not by section name     | Section names vary across repos; entry behavior is the stable signal                                | Maintain a list of known bad names — misses novel names, requires ongoing updates  |
| 2026-05-02 | Require Distillation creation in the upgrade step, not a separate pass | Most natural to do while the agent already has the journal open during upgrade                      | Separate distillation pass — adds a step the operator must remember to run         |

## Risks

| Risk                                                              | Mitigation                                                                                    |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Agent over-deletes legitimate sections mistaken for activity logs | Guidance must anchor on entry content (wave-closed/change-shipped records), not headings      |
| Distillation quality varies by agent and domain                   | Instruct agent to extract only explicit lessons from existing entries; do not invent new ones |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
