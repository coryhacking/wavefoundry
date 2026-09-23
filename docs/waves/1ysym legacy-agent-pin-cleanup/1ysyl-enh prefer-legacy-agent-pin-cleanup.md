# Prefer Legacy Agent Pin Cleanup During Upgrade

Change ID: `1ysyl-enh prefer-legacy-agent-pin-cleanup`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-09-22
Wave: 1ysym legacy-agent-pin-cleanup

## Rationale

An upgraded target retained model: sonnet in its Guru wrapper because rendering correctly preserves existing frontmatter. The operator wants removing inherited framework model defaults to be the preferred upgrade cleanup. Make this an explicit agent editing-pass recommendation, preserving deliberately selected operator pins and existing renderer ownership. This improves adoption of task-fit model selection without silently overwriting user choices.

## Requirements

1. During upgrade, inventory model and effort pins in existing Wavefoundry-managed Claude agent wrappers, including Guru. Recommend removing obsolete framework-provided defaults so host/task-level selection can apply.
2. Remove pins whose framework-default origin is established by prior templates/history or operator confirmation. A value such as sonnet alone does not prove provenance. Preserve intentional operator choices; if provenance is unclear, present the recommendation and ask before changing that pin.
3. Limit cleanup to selected model/effort fields. Preserve tools, other frontmatter, wrapper body and project-owned custom agents. Keep the renderer's existing preservation and malformed-header behavior unchanged.
4. Reconcile canonical seed-160 upgrade editing guidance and its project-local prompt carrier; report removed, retained and unresolved pins in the upgrade summary. Repeated upgrades must not restore removed defaults.

## Scope

In scope: preferred authored upgrade cleanup in seed-160 and local upgrade prompt; focused guidance/renderer verification and changelog entry. Derive wrapper inventory from existing Wavefoundry-rendered wrappers rather than all project agents.

Out of scope: blanket removal of model preferences, a new automatic renderer migration, changing host model selection semantics, editing the external tester repository, rebuilding indexes, publishing or rebuilding the existing test package.

Protected surfaces: renderer code, permissions/tools allowlists, unrelated frontmatter and custom agent bodies. Write owner: implementer after readiness; docs-contract and QA reviewers read only.

## Acceptance Criteria

- [x] AC-1: Canonical and local upgrade guidance explicitly prefer clearing inherited model/effort defaults, including Guru, and distinguish verified defaults, intentional pins and unknown provenance. Independent text review covers all three cases.
- [x] AC-2: The guidance limits edits to selected fields and records retained/unresolved decisions; focused existing-renderer evidence shows a cleaned header remains unpinned on rerender while an intentional pin survives.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Defines preferred cleanup and ownership boundaries |
| AC-2 | required | Preserves user configuration and rerender stability |

## Tasks

- [x] Admit and prepare this change before editing framework seeds or tests.
- [x] Update seed-160 and its authored local carrier, preserving renderer-owned regions; add an Unreleased changelog note.
- [x] Verify the guidance against default, intentional and unknown-provenance scenarios and current renderer behavior; obtain independent docs/QA review and required checks.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Guidance | implementer | readiness | Canonical seed and local carrier |
| Verification | docs-contract-reviewer and qa-reviewer | guidance | Independent review; no implementation writes |

## Serialization Points

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`

## Affected architecture docs

N/A: no runtime, ownership or module boundary changes. Existing frontmatter preservation remains the contract.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-22 | Prefer guided removal of verified inherited defaults | Implements operator preference while retaining deliberate user configuration | Automatically strip every pin: loses user choices. Leave cleanup merely optional: repeats the field-test outcome. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-22 | Planned from operator request following 1.26 field upgrade; selected guided cleanup over automatic stripping or optional-only advice | User request; 1ycrj preservation contract |
| 2026-09-22 | Readback: prefer clearing verified inherited model/effort pins; deliberate current intent wins, unknown provenance requires asking. Edit only seed-160/local carrier and changelog. Before: optional deletion advice; after: preferred cleanup with protected fields and summary dispositions. | AC-1/AC-2; independent primer |
| 2026-09-22 | External review: add verified historical pin inventory to both guidance rows; repair status/table formatting and re-Prepare before seed correction. Operator signoff remains pending. | pre-1ycrj template and seed-050; external review F1–F3 |

## Session Handoff

Implemented and independently reviewed in wave 1ysym. All ACs/tasks complete; fresh QA/docs delivery approvals recorded. Full suite 9,550 tests passes; docs lint clean. Seed gate closed. Wave remains open pending operator closure; no commit or package rebuild requested. Existing 1.26.0+prtm archive does not include this change.
