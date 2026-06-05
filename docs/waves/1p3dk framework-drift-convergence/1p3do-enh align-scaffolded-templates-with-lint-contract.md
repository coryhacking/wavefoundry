# Align Scaffolded Templates With Lint Contract

Change ID: `1p3do-enh align-scaffolded-templates-with-lint-contract`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-04
Wave: `1p3dk framework-drift-convergence`

## Rationale

`wave_create_wave` and the implicit journal-scaffolding workflow produce documents that **fail `docs-lint` immediately on creation**. The operator (or coordinating agent) must structurally repair the scaffolded file before they can fill in real content. This is a small instance of the wave's broader theme: the declared template structure disagrees with the lint contract that gates wave admission.

Concrete failures observed when opening wave `1p3dk` from a fresh `wave_create_wave` call:

1. **Wave skeleton missing `## Objective` heading.** Lint errors: ``wave doc must declare `## Objective` section (displayed in the dashboard wave card)``.
2. **Wave skeleton has no `Change ID` declaration.** Lint errors: ``missing stable `Change ID` declaration``. This is structural chicken-and-egg: a freshly-created wave has no admitted changes yet, but lint requires at least one `Change ID:` line in `## Changes`.
3. **No journal is auto-created.** Lint errors: ``active wave `<id>` must be referenced by at least one journal artifact``. The operator must hand-author a journal that mirrors the structure of an existing journal — 9 required sections (`Operating Identity`, `Salience Triggers`, `Default Stance`, `Memory Responsibilities`, `Active Signals`, `Distillation`, `Promotion Evidence`, `Retirement And Supersession`, `Governance`), each with strict content requirements (keyword matches, at-least-one-bullet, stable-artifact backtick references in `Promotion Evidence`).

The change-doc template (`docs/plans/plan-template.md` consumed by `wave_new_*`) already produces lint-clean output on creation — verified for `1p3dm` and this doc (`1p3do`). The defect is scoped to the wave + journal layer.

The fix has the same shape as the wave's other items: collapse declared/actual disagreement at the source.

## Requirements

1. `create_wave` skeleton emits `## Objective` between `Title:` and `## Changes` with a one-line placeholder the operator replaces.
2. `create_wave` either includes a placeholder `Change ID:` line that lint tolerates **or** lint defers the Change ID requirement when wave `Status: planned` AND `## Changes` is empty. The deferral path is preferred (no fake IDs in valid docs).
3. `create_wave` co-creates a journal stub at `docs/agents/journals/<wave-id>.md` with every lint-required section pre-populated with valid placeholder content (matching the keyword/structure requirements lint enforces). Operator populates real content as the wave progresses.
4. Journal stub references the wave-id on a dedicated `wave-id: \`<wave-id>\`` line so the wave's journal-reference lint check passes immediately.
5. Existing waves and journals are not touched by this change. The fix applies to newly-created waves only.
6. `wave_create_wave` MCP response surface: no breaking changes. The response dict keeps current shape (`wave_id`, `path`, `mode`, `created`, `exists`); journal co-creation is reported via an optional `journal_path` field.

## Scope

**Problem statement:** Newly-created waves emit non-lint-clean wave docs and have no journal at all. The first time an operator runs `wave_validate` against a freshly-opened wave they get 3-7 errors that are entirely structural — not content gaps the operator should know about.

**In scope:**

- `create_wave` (server_impl.py around line 4247) — extend the wave.md skeleton with `## Objective` and adjust the Changes-section friction
- `create_wave` — extend to also write a journal stub at `docs/agents/journals/<wave-id>.md`
- `docs-lint` Change-ID requirement — defer when wave `Status: planned` AND `## Changes` is empty (preferred over placeholder Change-ID approach)
- Tests in `test_server_tools.py` confirming `wave_create_wave_response` produces lint-clean wave.md + journal.md
- Tests in `test_docs_lint.py` confirming the Change-ID deferral fires only when both conditions match (not when one is present without the other)

**Out of scope:**

- `_default_template()` / `docs/plans/plan-template.md` — already lints clean
- Modifying existing waves or journals
- Adding a separate `wave_new_journal` MCP tool (co-creation in `wave_create_wave` is sufficient)
- Per-platform launcher regeneration
- Any other wave or change tool surface

## Acceptance Criteria

- [x] AC-1: `wave_create_wave(slug='<x>', mode='apply')` produces a wave.md that lints clean (zero errors, zero warnings) before any `wave_add_change` call.
- [x] AC-2: The wave.md skeleton includes a `## Objective` section between the `Title:` line and `## Changes` with a single-line placeholder the operator replaces with the wave objective.
- [x] AC-3: `docs-lint` defers the `missing stable Change ID declaration` error when wave `Status: planned` AND the `## Changes` section contains zero `Change ID:` lines. After the first `wave_add_change` apply call, the deferral no longer applies and lint enforces normally.
- [x] AC-4: `wave_create_wave(slug='<x>', mode='apply')` co-creates a journal at `docs/agents/journals/<wave-id-slug>.md` containing every lint-required section (`Operating Identity`, `Salience Triggers`, `Default Stance`, `Memory Responsibilities`, `Active Signals`, `Distillation`, `Promotion Evidence`, `Retirement And Supersession`, `Governance`) with at least one valid placeholder bullet each.
- [x] AC-5: The journal stub satisfies the Salience Triggers keyword requirement (mentions critical/high/medium/low or trigger keywords), the Operating Identity role/responsibility requirement, and the Promotion Evidence stable-artifact backtick requirement.
- [x] AC-6: The journal stub includes the literal line `wave-id: \`<wave-id>\`` on its own line (matching the wave-doc's journal-reference lint check exactly).
- [x] AC-7: `wave_create_wave` response dict gains a `journal_path` key reporting the relative path of the created journal. Backwards-compatible — existing fields unchanged.
- [x] AC-8: When `wave_create_wave` runs in `dry_run` mode, the `journal_path` is reported (`created: False`) without writing the file.
- [x] AC-9: Re-running `wave_create_wave` on an existing wave does not overwrite the existing journal (idempotent — same `created: False, exists: True` shape for both wave.md and journal).
- [x] AC-10: New tests in `test_server_tools.py`: `test_wave_create_wave_apply_produces_lint_clean_skeleton`, `test_wave_create_wave_co_creates_journal`, `test_wave_create_wave_dry_run_reports_journal_path_without_writing`, `test_wave_create_wave_idempotent_does_not_overwrite_journal`.
- [x] AC-11: New tests in `test_docs_lint.py`: `test_change_id_deferral_fires_for_planned_wave_with_empty_changes`, `test_change_id_required_after_first_change_admitted`, `test_change_id_required_for_non_planned_status`.
- [x] AC-12: Full framework test suite passes (additional ~7 tests).
- [x] AC-13: docs-lint clean.

## Tasks

- [x] Open `framework_edit_allowed` gate
- [x] Extend `create_wave` in `server_impl.py` to write `## Objective` placeholder in the skeleton
- [x] Extend `create_wave` to co-create journal stub at `docs/agents/journals/<slug>.md` with lint-clean placeholder content
- [x] Add `journal_path` to `wave_create_wave` response dict (both dry_run and apply branches)
- [x] Add Change-ID deferral logic to `docs-lint` validator (`wave_lint_lib/`)
- [x] Add the eight new tests (4 server tool tests + 3 lint tests + 1 end-to-end assertion that `wave_create_wave_apply → docs-lint passes`)
- [x] Verify by running `wave_create_wave` against a throwaway slug then `docs-lint` and confirming zero errors
- [x] Run framework test suite
- [x] Run docs-lint
- [x] Update CHANGELOG under `## [1.5.0]`
- [x] Close `framework_edit_allowed` gate

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| skeleton | implementer | — | Extend `create_wave` skeleton with `## Objective` and journal co-creation |
| lint-deferral | implementer | — | Add Change-ID deferral logic in `wave_lint_lib/` |
| tests | qa-reviewer | skeleton, lint-deferral | Eight new tests covering all ACs |

## Serialization Points

- Both workstreams modify `wave_create_wave_response` / `create_wave` and `wave_lint_lib/` independently — no file-level collision. Sequence: skeleton + lint-deferral land in parallel, tests follow.

## Affected Architecture Docs

`N/A` — extending existing surfaces (`create_wave`, `docs-lint`); no boundary or data-flow change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core invariant — newly-created waves must lint clean. |
| AC-2 | required | `## Objective` is what lint actually demands. |
| AC-3 | required | The chicken-and-egg resolution. |
| AC-4 | required | Closes the journal hand-authoring friction. |
| AC-5 | required | Lint enforces these keyword/content rules — stub must comply. |
| AC-6 | required | Without this, the wave's journal-reference lint check fails. |
| AC-7 | important | Response surface needs to report the co-created artifact. |
| AC-8 | important | dry_run consistency. |
| AC-9 | required | Idempotency contract is part of `wave_create_wave`'s existing behavior; must not regress. |
| AC-10 | required | Coverage for the new behaviors. |
| AC-11 | required | Coverage for the lint deferral. |
| AC-12 | required | Suite must pass. |
| AC-13 | required | docs-lint must pass. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-04 | Change scaffolded and admitted to wave `1p3dk` | This doc |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-04 | Co-create journal in `wave_create_wave` rather than a separate `wave_new_journal` tool | Single call covers the user's mental model ("I just want a new wave"); avoids two-step ceremony. The wave never makes sense without its journal. | Separate `wave_new_journal` tool — rejected; adds a step the operator must remember. |
| 2026-06-04 | Defer the Change-ID lint requirement via lint logic rather than emit a placeholder `Change ID: <pending>` in the skeleton | Placeholders in valid docs are exactly the dual-valid-state pattern this wave is closing. Lint deferral is cleaner. | Placeholder Change-ID line — rejected; introduces a token that exists only to satisfy lint, which lint would then have to special-case anyway. |
| 2026-06-04 | Change-doc template (`_default_template()` / `plan-template.md`) is out of scope | Verified to lint clean on creation for both `1p3dm` and `1p3do` — no defect exists there. | Audit and reformat the change template anyway — rejected; YAGNI for this wave. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The journal stub's placeholder content could be mistaken for real content by future readers | Use explicit `Pending: ...` prefixes so the placeholder nature is unambiguous, mirroring the convention I used for `1p3dk`'s journal. |
| The Change-ID deferral could mask a legitimate missing-Change-ID case (e.g., a wave manually moved out of `planned` without admission) | Deferral fires only when BOTH `Status: planned` AND `## Changes` is empty. The moment status moves to `active`/`closed` OR a Change ID appears, the deferral disables and full enforcement resumes. |
| Auto-created journal might conflict with operator who prefers a custom journal layout | Idempotency rule (AC-9): re-running `wave_create_wave` never overwrites an existing journal. Operators can replace the stub freely after creation. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
