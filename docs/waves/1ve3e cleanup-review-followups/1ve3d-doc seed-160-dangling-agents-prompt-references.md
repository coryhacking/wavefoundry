# Seed 160 references agents-prompt bodies that do not exist

Change ID: `1ve3d-doc seed-160-dangling-agents-prompt-references`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-08-15
Wave: 1ve3e cleanup-review-followups

## Rationale

The 2026-08-15 codebase cleanup review's reference census (F3) found seed `160-upgrade-wavefoundry.prompt.md` naming `docs/prompts/agents/` members that do not exist in this repository:

- The specialist-bodies list names `docs/prompts/agents/architecture-reviewer.prompt.md` (seed-214) as a backfill target ("backfill missing specialist agent bodies introduced in `seed-212` through `seed-214` when not present"), yet only the performance-reviewer and security-reviewer bodies exist here and upgrades have never backfilled the third; the sibling code-reviewer entry already carries softer when-present phrasing.
- The upgrade-contract reconciliation line names `docs/prompts/agents/upgrade-wavefoundry.md`, a file that exists nowhere; the only upgrade-related member of that directory is the legacy pre-rename `upgrade-wave-context.prompt.md`.

Seed 160 instructs the upgrade flow in every target repository, so dangling expectations there cause wasted searches at every upgrade. The `docs/prompts/agents/` directory's own README declares its members optional non-public helpers, which is the semantics the seed should reflect: reconcile-when-present, never backfill-mandatory.

## Requirements

1. **Align the specialist-bodies instruction with reality.** Rephrase the seed-212-through-214 backfill sentence and the architecture-reviewer bullet to the same reconcile-when-present semantics the code-reviewer bullet already uses, so absence of an optional body is a valid state rather than an upgrade gap.
2. **Drop the ghost upgrade body reference.** Remove `docs/prompts/agents/upgrade-wavefoundry.md` from the upgrade-contract reconciliation line, keeping `docs/prompts/upgrade-wavefoundry.prompt.md`.
3. **Mirror in the rendered doc when present.** If `docs/prompts/upgrade-wavefoundry.prompt.md` carries the same dangling text, apply the equivalent correction there; otherwise record that no mirror was needed.
4. **Seed gate.** Both seed edits under one `seed_edit_allowed` open/close cycle.

## Scope

**Problem statement:** The canonical upgrade seed names optional helper files as expected-present, including one that exists nowhere, misdirecting upgrade agents in every target repo.

**In scope:** the two seed-160 passages above + the rendered upgrade prompt mirror check.

**Out of scope:**

- Pruning or renaming `docs/prompts/agents/` members (the cleanup review's F2, referred to Framework config review).
- Creating the missing architecture-reviewer body (the when-present semantics make its absence valid).
- Any other seed-160 content.

## Acceptance Criteria

- [x] AC-1: seed 160 no longer names any `docs/prompts/agents/` member as expected-present that this repository lacks; the specialist-bodies list is uniformly when-present; the ghost `agents/upgrade-wavefoundry.md` reference is gone (grep-verified zero dangling `prompts/agents/` references from seeds to nonexistent files).
- [x] AC-2: the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` carries no equivalent dangling reference (corrected or verified absent).
- [x] AC-3: seed edits under `seed_edit_allowed`; docs-lint clean; full suite green (seed content is fixture-checked by shipped-reference tests).

## Tasks

- [x] Rephrase the specialist-bodies instruction + architecture-reviewer bullet; remove the ghost upgrade-body reference (one `seed_edit_allowed` cycle).
- [x] Mirror check on the rendered upgrade prompt.
- [x] Verify: dangling-reference grep sweep, docs-lint, full suite.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| seed       | implementer | —          | Goal: both passages corrected in one gate cycle; sweep clean |


## Serialization Points

- `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`
- `docs/prompts/upgrade-wavefoundry.prompt.md`

## Affected Architecture Docs

`N/A`: seed prose accuracy; no boundary, flow, or verification change.

## AC Priority

(Populate one row per AC at plan time, before the prepare council runs. Filling this table after readiness is recorded supersedes the review-policy receipt and lapses the approvals it just collected. The `ac_priority_unpopulated` advisory at Prepare is the backstop, not the schedule.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The dangling expectations are the defect. |
| AC-2 | important | The rendered doc is what target-repo agents actually read day to day. |
| AC-3 | required  | Gate discipline + no regression. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-08-15 | Planned from cleanup review F3. Census: `docs/prompts/agents/` holds 12 members; seed 160 names two nonexistent ones as expected-present (`architecture-reviewer.prompt.md` in the backfill list, `upgrade-wavefoundry.md` in the upgrade-contract line) while the directory README declares members optional non-public helpers. | Reference census greps 2026-08-15; `docs/prompts/agents/README.md` |
| 2026-08-15 | Implemented under one `seed_edit_allowed` cycle: the specialist-bodies preamble now states the optional when-present semantics ("absence is a valid state, never a backfill obligation") governing all four bullets, so the architecture-reviewer entry stays as a reconcile-when-present member; the ghost `docs/prompts/agents/upgrade-wavefoundry.md` reference removed from the upgrade-contract line. Mirror check: the rendered `docs/prompts/upgrade-wavefoundry.prompt.md` never carried either dangling reference (grep 0), so no mirror edit was needed. Sweep: no seed names a `prompts/agents/` member as expected-present that this repo lacks. `test_shipped_reference_docs` 12/12 OK. | Seed 160 lines 179 and 231; grep sweeps 2026-08-15; scratchpad `t1ve3e.log` |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-08-15 | Correct the seed to when-present semantics rather than backfilling the missing body. | The directory's own README defines members as optional helpers; practice matches (upgrades never backfilled the third body); creating new optional surfaces to satisfy stale prose inverts the fix. | Backfill `architecture-reviewer.prompt.md` from seed 214 (rejected: grows an optional surface to match wrong prose); delete the bullets entirely (rejected: the when-present reconcile instruction is still useful where the bodies exist). |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Softening to when-present hides a body that genuinely should exist somewhere. | The role docs under `docs/agents/` remain the mandatory carriers with their own registry and tests; this touches only the optional prompt-body supplements. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
