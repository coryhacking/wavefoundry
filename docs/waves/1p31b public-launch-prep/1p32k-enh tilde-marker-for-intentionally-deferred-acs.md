# Tilde Marker For Intentionally-Deferred ACs

Change ID: `1p32k-enh tilde-marker-for-intentionally-deferred-acs`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-06-03
Wave: `1p31b public-launch-prep` (late-admitted post-delivery-council; the same wave whose `1p318` AC-13/AC-19 are the canonical worked example for the convention this change codifies)

## Rationale

Acceptance criteria checkboxes today support two states: `[ ]` (unmet) and `[x]` (met). There is no canonical marker for **intentionally deferred** ACs — those where the original requirement was reconsidered, removed by operator direction during implementation, or genuinely narrowed by scope-discovery within the wave's contract.

The wave `1p31b public-launch-prep` surfaced two such ACs during the `1p318` README rewrite: AC-13 (Mermaid concept-spine diagram) and AC-19 (diagram render verified on GitHub branch preview). The operator directed full removal of the Mermaid diagram mid-implementation; both ACs are no longer applicable, but neither is satisfied either. They were marked `[~]` ad hoc, with an inline status note recording the operator-directed deferral. That convention worked in this wave but is not codified anywhere — a future agent or reviewer encountering `[~]` would have no framework-level reference for what it means or what evidence of legitimate deferral should look like.

The Delivery-phase Wave Council for `1p31b` raised this as advisory finding **QA-D-1**:

> *"Consider adding a framework-level convention for `[~]` ACs — they should ALL be referenced in the wave-close handoff so future-readers see them surface as 'intentionally deferred, see status note.'"*

Operator confirmed: codify the convention. This change does so.

The risk of NOT codifying: `[~]` accumulates as a partially-understood marker that future waves use inconsistently — some with inline rationale, some without; some surfaced at close, some buried. That is the silent-technical-debt pattern this framework is explicitly designed to prevent.

## Requirements

1. **Canonical `[~]` marker** for "intentionally not met" added as a documented AC checkbox state alongside `[ ]` and `[x]` in the canonical AC formulation guidance (`seed 170-plan-feature`).
2. **Each `[~]` AC must carry an inline status note** explaining the deferral rationale immediately after the AC text — same shape as the existing inline `[x]` evidence notes on this self-host. The note must name (a) when the deferral was decided, (b) who directed or surfaced it, (c) why the original AC is no longer applicable. *"Operator-directed removal during implementation, see Decision Log entry on <date>"* is a valid form.
3. **docs-lint validator accepts `[~]` as a valid checkbox state** — neither raising a lint error nor counting it as unmet for the "all required ACs satisfied" check. Required ACs marked `[~]` require an additional explicit attestation from `qa-reviewer` that the deferral is legitimate (not a silent gap).
4. **Review-wave guidance** updated so `qa-reviewer`'s AC reconciliation pass explicitly verifies every `[~]` AC has a recorded rationale. A silent `[~]` (no status note) is a finding, not a deferral.
5. **Close-wave guidance** updated so the close-readiness handoff surfaces all `[~]` ACs across the wave's admitted changes — either inline in the close summary or as a separate "intentionally deferred" section. Future-readers must see them as a single discoverable list.
6. **`AGENTS.md` change-doc-tracking section** updated to mention `[~]` alongside `[ ]` / `[x]` so agents reading `AGENTS.md` for the AC-tracking contract learn the full set.
7. **Seed cross-references** — the canonical convention (defined in seed 170) is referenced from `175-interrogate-plan.prompt.md`, prepare-wave / review-wave / close-wave seeds and the corresponding `docs/prompts/*.md` public prompt bodies. Single source of truth in seed 170; references elsewhere.
8. **Worked example** preserving the `1p31b` `1p318` AC-13/AC-19 case as the canonical precedent in the seed. The example must include the inline status notes that landed in that change doc, plus a pointer to the Decision Log entry that surfaced the deferral.
9. **Dashboard surfacing** — the local dashboard parses ACs from change docs and renders per-change and per-wave progress. The dashboard must treat `[~]` as a third state distinct from `[ ]` and `[x]`:
   - **Backend parsing** (`dashboard_lib.py`) recognizes `[~]` and exposes it in the per-change AC aggregate alongside met/unmet counts.
   - **Frontend rendering** (`dashboard.js`) displays `[~]` ACs with a visually distinct marker (different color, icon, or label) so an operator scanning the dashboard sees them as a category, not as just-uncomplete.
   - **Progress accounting** — `[~]` ACs do *not* count toward the unmet pool (which would make the progress bar misleadingly low) and do *not* count toward the met pool either (which would inflate completion). The cleanest accounting: progress bars are over `[x] / (total - [~])`; `[~]` is surfaced as a separate count with its own visual treatment.
   - **Tests** in `test_dashboard_server.py` cover the parsing and aggregation behavior.
10. **No retrofit** of `[~]` markers onto prior closed waves. The convention applies from this change forward.
11. **No backwards-incompatible behavior change** for existing `[ ]` / `[x]` ACs in either the validator or the dashboard.
12. **The `[~]` marker also applies to `## Tasks` checkboxes** with looser enforcement than ACs: the inline status note is *recommended but not lint-required* for task `[~]`. Rationale: tasks are implementation hints rather than contract surface, so over-enforcement creates friction without proportional benefit. The shape is otherwise identical — `[~]` means "intentionally not done in this change," and the dashboard renders task `[~]` with the same distinct treatment as AC `[~]`. The `1p312` change in this same wave demonstrates the use case: the "Bench the reaper on 5,000-row fixture" task was streamlined out with rationale recorded in AC-3's status note; under this convention, the task should have been marked `[~]` with an inline note pointing at the AC-3 rationale rather than silently removed from the Tasks list.
13. **Hard close-time gate** — at `wave_close` (specifically the wave-close validator path), every AC and every task across the wave's admitted changes must be marked either `[x]` (completed) or `[~]` (intentionally deferred). A silent `[ ]` (unchecked) is a **blocking close-time finding** that surfaces with the change ID, AC or task identifier, and the inline text. This is the discipline that makes `[~]` a real convention rather than a marker some operators use ad hoc — *everything is accounted for at close*. The gate applies to all AC priorities (required, important, nice-to-have); `not-this-scope` ACs are exempt by definition. The gate also applies regardless of whether the change status is `implemented` — a change marked `implemented` with silent `[ ]` items reveals a tracking-discipline failure that the gate surfaces.

## Scope

**Problem statement:** The `[~]` marker is being used ad hoc to record "intentionally not met" ACs without a framework-level convention. Without codification, it will be applied inconsistently across waves, producing silent technical debt — exactly the failure mode the framework's AC tracking is designed to prevent.

**In scope:**

- Framework seed updates: `170-plan-feature.prompt.md` (canonical definition), `175-interrogate-plan.prompt.md` (acknowledge marker during interrogation), prepare-wave and review-wave and close-wave seeds (lifecycle integration).
- Public prompt body updates: `docs/prompts/plan-feature.prompt.md`, `docs/prompts/interrogate-plan.prompt.md`, `docs/prompts/prepare-wave.prompt.md`, `docs/prompts/review-wave.prompt.md`, `docs/prompts/close-wave.prompt.md` — cross-reference the seed definition; do not duplicate it.
- `AGENTS.md` change-doc-tracking section — add `[~]` to the documented marker set.
- docs-lint validator (`wave_lint_lib/core_validators.py` or the AC-priority validator) — accept `[~]` as a valid checkbox state.
- Tests for the validator change.
- **Dashboard backend** (`dashboard_lib.py`) — parse `[~]` as a third AC state; expose it in the per-change aggregate.
- **Dashboard frontend** (`dashboard.js` + `dashboard.css` if a new color/icon is needed) — render `[~]` ACs with a visually distinct marker; account for `[~]` correctly in the per-change and per-wave progress bars.
- **Dashboard tests** (`test_dashboard_server.py`) — cover parsing, aggregation, and progress accounting.
- Worked example anchored on `1p31b` `1p318` AC-13/AC-19.

**Out of scope:**

- Retrofitting `[~]` markers on prior closed waves.
- Adding new AC checkbox states beyond `[~]` (e.g., `[?]` for "uncertain", `[!]` for "blocked").
- A historical / cross-wave dashboard view of all `[~]` ACs ever recorded across closed waves — the per-change and per-wave surfacing in v1 is sufficient; a cross-wave aggregate is a forward-compat possibility.
- A `wave_close` response field counting `[~]` ACs across the wave's admitted changes — the close-wave seed guidance handles the surfacing for v1; a structured response field is a forward-compat possibility.

## Acceptance Criteria

- [x] AC-1: `seed 170-plan-feature.prompt.md` documents `[~]` as the canonical AC checkbox state for "intentionally not met", alongside `[ ]` (unmet) and `[x]` (met). *Added under the "AC and task checkbox states — the `[~]` marker" subsection with a three-state table.*
- [x] AC-2: The seed mandates that each `[~]` AC must carry an inline status note naming when, who, and why — and that a silent `[~]` (no status note) is a docs-lint or review-pass finding, not a legitimate deferral.
- [x] AC-3: docs-lint validator accepts `[~]` as a valid checkbox state — no false-positive lint error on a well-formed `[~]` AC. *Verified by `test_tilde_ac_with_inline_italic_note_passes` and `test_tilde_ac_with_long_inline_prose_passes`.*
- [x] AC-4: docs-lint validator requires the inline status note when `[~]` is used on a required-priority AC — surfaces a lint error if the note is missing. *Verified by `test_silent_tilde_required_ac_fails`. Heuristic: 40+ chars of prose or a markdown italic segment.*
- [x] AC-5: Review-wave guidance (seed + public prompt body) updated so `qa-reviewer`'s AC reconciliation explicitly verifies every `[~]` AC has a recorded rationale. *Added to `docs/prompts/review-wave.prompt.md` step 5.*
- [x] AC-6: Close-wave guidance (seed + public prompt body) updated to surface all `[~]` ACs in the close-readiness handoff. *Added as Closure Requirement #10 in `docs/prompts/close-wave.prompt.md` plus a `## Wave Summary` handoff-surfacing requirement.*
- [x] AC-7: `AGENTS.md` change-doc-tracking section names `[~]` alongside `[ ]` / `[x]` with a one-line description. *Added second paragraph to `## Change Doc Tracking (Real-Time)` covering all three states plus the close-time gate.*
- [x] AC-8: Cross-references from `175-interrogate-plan`, prepare-wave, review-wave, close-wave seeds to the canonical definition in seed 170 — no duplicated convention text in the dependent seeds.
- [x] AC-9: Worked example in seed 170 cites `1p31b` `1p318` AC-13/AC-19 with the original inline status notes and the operator-direction Decision Log pointer.
- [x] AC-10: New tests in `wave_lint_lib` test suite cover: well-formed `[~]` AC (no error), silent `[~]` AC on a required priority (error), `[~]` on an important / nice-to-have priority (no error; status note recommended but not required). *Added 5 tests; full framework suite 2285 tests pass.*
- [x] AC-11: Dashboard backend (`dashboard_lib.py`) parses `[~]` as a third state; per-change AC aggregate exposes `deferred_count` (or equivalent) alongside met / unmet counts. *Implemented `_deferred_ac_counts` + `ac_deferred_counts` field on `ChangeRecord`; tasks aggregate gains `deferred` count.*
- [x] AC-12: Dashboard frontend renders `[~]` ACs with a visually distinct marker (color, icon, or label) so an operator scanning the dashboard distinguishes them from both met and unmet ACs. *Glyph `~` (muted blue), italic text, `--deferred` BEM modifier, separate "· N deferred" suffix on progress fractions.*
- [x] AC-13: Progress bar accounting — `[~]` ACs are excluded from the denominator: a change with 10 ACs (8 `[x]`, 2 `[~]`) shows 100% complete (8/8), not 80% complete (8/10). The deferred count surfaces as a separate badge or label. *Verified by `test_deferred_acs_excluded_from_progress_denominator`.*
- [x] AC-14: New tests in `test_dashboard_server.py` cover parsing (`[~]` recognized), aggregation (`deferred_count` correctly computed), and progress accounting (a fully-met change with `[~]` ACs reports 100% complete). *3 new tests added.*
- [x] AC-15: `docs-lint` passes on this change doc after additions. *Verified throughout via `wave_validate`.*
- [x] AC-16: Full framework test suite passes after additions. *2285 tests across 24 files — 13 new tests added on top of the prior 2272 baseline.*
- [x] AC-17: No regression on existing AC tracking: existing `[ ]` and `[x]` markers behave unchanged in both the validator and the dashboard. Verified by running prior dashboard fixtures. *No prior fixtures regressed.*
- [x] AC-18: docs-lint validator accepts `[~]` on `## Tasks` checkboxes; inline status note is **not** lint-required for tasks (asymmetric with the AC rule per Decision Log). *Verified by `test_tilde_task_without_inline_note_passes`.*
- [x] AC-19: Dashboard renders task `[~]` with the same visually distinct treatment as AC `[~]`. *Task dialog rendering updated to share the same `--deferred` class and glyph as ACs; `sortPendingFirst` updated to treat deferred items as "not pending" so they sort with done items.*
- [x] AC-20: New tests cover task `[~]` validator behavior — accept without inline note, no false-positive lint error. *Covered by `test_tilde_task_without_inline_note_passes`.*
- [x] AC-21: `wave_close` validator path enforces the close-time hard gate: every AC and every task across the wave's admitted changes must be `[x]` or `[~]`. Silent `[ ]` items produce a blocking error listing the change ID, item type (AC vs task), item identifier, and inline text. *Implemented as `_collect_silent_unchecked_items_for_close` + `silent_unchecked_items_at_close` diagnostic in `wave_close_response`.*
- [x] AC-22: `wave_close` close-time gate exempts `not-this-scope` priority ACs (the priority itself encodes the exclusion). *Verified by `test_close_gate_exempts_not_this_scope_priority_ac`.*
- [x] AC-23: `wave_close` tests cover: (a) wave with all `[x]` items closes cleanly; (b) wave with mix of `[x]` and `[~]` items closes cleanly; (c) wave with one silent `[ ]` required-priority AC fails close with a structured error naming the item; (d) wave with one silent `[ ]` task fails close; (e) wave with one silent `[ ]` `not-this-scope` AC closes cleanly (exempt). *5 tests added covering all scenarios.*
- [x] AC-24: Close-wave seed updated to document the hard gate explicitly so operators see the requirement before invoking `wave_close`. *Added as Closure Requirement #10 in `docs/prompts/close-wave.prompt.md`.*

## Tasks

- [x] Open `seed_edit_allowed` gate (framework seed addition + cross-seed weaving)
- [x] Open `framework_edit_allowed` gate (docs-lint validator change + tests)
- [x] Author canonical `[~]` definition in `seed 170-plan-feature.prompt.md`
- [x] Update `seed 175-interrogate-plan.prompt.md` with cross-reference
- [x] Update prepare-wave seed (or `100-project-prompt-surface-bootstrap.prompt.md` if that's where prepare-wave lifecycle guidance lives) with cross-reference + AC priority guidance update
- [x] Update review-wave seed with `qa-reviewer` `[~]` verification step
- [x] Update close-wave seed with handoff surfacing requirement
- [x] Update public prompt bodies (`docs/prompts/plan-feature`, `interrogate-plan`, `prepare-wave`, `review-wave`, `close-wave`) with cross-references
- [x] Update `AGENTS.md` `## Change Doc Tracking (Real-Time)` section
- [x] Implement docs-lint validator change in `wave_lint_lib` — handle both AC `[~]` (mandatory inline note for required-priority) and task `[~]` (no mandatory note)
- [x] Add tests for the validator change covering AC-10 + AC-20 cases (5 tests)
- [x] Update dashboard backend (`dashboard_lib.py`) to parse `[~]` and expose `deferred_count`
- [x] Update dashboard frontend (`dashboard.js` + `dashboard.css`) to render `[~]` distinctly and exclude from progress denominator
- [x] Verify dashboard task-list rendering scope; if tasks are rendered, apply the same `[~]` treatment (AC-19); if not, record the no-regression + future-rendering note. *Tasks ARE rendered in the tasks dialog; same treatment applied.*
- [x] Add dashboard tests in `test_dashboard_server.py` covering AC-14 cases (3 tests)
- [x] **Implement the `wave_close` close-time hard gate** in `server_impl.py` — walk admitted changes; for each AC and task, fail close if any are silent `[ ]` (except `not-this-scope` ACs); structured error names change-id + item-id + inline text
- [x] Add `wave_close` tests covering AC-23 scenarios (a–e) (5 tests)
- [x] Update close-wave seed + public prompt body to document the hard gate (AC-24)
- [x] Author worked example in seed 170 citing `1p31b` `1p318` AC-13/AC-19. *The `1p312` task example (bench task) is referenced in the Decision Log on this change doc rather than the seed, per the no-retrofit principle (Req-9) — retrofitting `1p312` to use `[~]` for the bench task is not in scope.*
- [x] Run framework tests (`python3 .wavefoundry/framework/scripts/run_tests.py`) — 2285 tests pass
- [x] Run `wave_validate` to confirm docs-lint passes
- [~] Manually verify the dashboard rendering by opening it against a wave containing `[~]` ACs. *Operator-action: dashboard auto-refreshes when running; the implementation passes all 143 dashboard tests and follows existing dashboard rendering conventions. Manual verification deferred to post-merge operator inspection rather than gating the change-doc close, since dashboard rendering is verified by automated tests and the implementation reuses existing styling primitives.*
- [x] Close gates; mark change `implemented`

## Affected Architecture Docs

`N/A` — this change extends an existing documentation / tracking convention; no architectural boundary, data flow, or testing-architecture impact. The docs-lint validator change is a localized rule addition in an existing validator family.

## AC Priority

| AC | Priority | Rationale |
|---|---|---|
| AC-1 (canonical `[~]` definition in seed 170) | required | Source of truth for the convention. Without it, the marker has no codified meaning. |
| AC-2 (inline status note mandatory) | required | Anchors the non-silent-gap discipline. Without the inline note requirement, `[~]` becomes the silent-deferral pattern the convention is designed to prevent. |
| AC-3 (docs-lint accepts `[~]`) | required | Without this, every `[~]` AC raises a lint error and operators revert to ad hoc workarounds. |
| AC-4 (lint error on silent `[~]` for required ACs) | required | Mechanical enforcement of the discipline in AC-2. Soft prose guidance alone has a track record of silent drift. |
| AC-5 (review-wave `qa-reviewer` step) | required | Lifecycle integration on the review side. Without this, `qa-reviewer` won't know to check the marker. |
| AC-6 (close-wave handoff surfacing) | required | Lifecycle integration on the close side. Without this, `[~]` ACs disappear from the post-close audit trail — the exact failure mode QA-D-1 named. |
| AC-7 (`AGENTS.md` mention) | required | Agent-facing discoverability. Agents read `AGENTS.md` as the change-doc-tracking contract; the marker must be named there. |
| AC-8 (cross-references, no duplication) | important | Single-source-of-truth discipline. Important rather than required because duplication is recoverable in a follow-on. |
| AC-9 (worked example) | required | Anchors the convention in the real precedent it grew from. A future reviewer can read `1p318` AC-13/AC-19 and the seed together to verify the convention describes what actually happened. |
| AC-10 (validator tests) | required | Regression discipline. The validator behavior must be testable and tested. |
| AC-11 (dashboard backend parses `[~]` + exposes deferred count) | required | Operator-facing discoverability. The dashboard is the primary visual surface for AC progress; the marker must be parseable there or it silently breaks the discoverability promise QA-D-1 named. |
| AC-12 (dashboard frontend renders `[~]` distinctly) | required | Visual distinctness is the affordance. Without it, `[~]` ACs blend into either the met or unmet pool — the same silent-debt failure mode the convention is designed to prevent, just rendered visually instead of textually. |
| AC-13 (progress bar excludes `[~]` from denominator) | required | Without this, a fully-met change with `[~]` ACs reports as incomplete in the dashboard — visually misleading. The denominator-exclusion accounting matches the AC priority semantics (`[~]` is "not in this scope" rather than "in scope but not done"). |
| AC-14 (dashboard tests) | required | Regression discipline. Dashboard parsing and aggregation must be testable and tested. |
| AC-15 (docs-lint passes on this change doc) | required | Standard hygiene gate. |
| AC-16 (framework test suite passes) | required | No regression on existing tests. |
| AC-17 (no regression on existing `[ ]` / `[x]`) | required | Hard gate on the backwards-compatibility promise (Req-11) — applies to both the validator and the dashboard. |
| AC-18 (validator accepts task `[~]` without mandatory note) | required | The asymmetric enforcement is the design (per Req-12 / Decision Log). Without the explicit lint-accepts behavior, the convention extension to tasks is incomplete. |
| AC-19 (dashboard renders task `[~]` distinctly) | important | Visual consistency with AC `[~]` treatment. Important rather than required because the dashboard may not currently render task lists, in which case AC-19 reduces to "no regression" with a future-rendering note. |
| AC-20 (task validator tests) | required | Regression discipline for the task-specific validator branch. |
| AC-21 (`wave_close` hard gate on silent `[ ]`) | required | Per Req-13. This is the discipline that converts `[~]` from "a marker some operators use" to "a real convention." Without it, silent `[ ]` items continue accumulating as before. |
| AC-22 (`wave_close` exempts `not-this-scope`) | required | Logical correctness — `not-this-scope` priority already encodes the exclusion; enforcing checkbox marking on it would be redundant and confusing. |
| AC-23 (close-wave gate tests) | required | Regression discipline for the close-wave gate. Five scenarios (a–e) cover the success cases and the blocking case explicitly. |
| AC-24 (close-wave seed documents the gate) | required | Operator-discoverability. Without seed-level documentation, operators only encounter the gate via lint error at close-time, which is too late for graceful planning. |

All required ACs are load-bearing on either the convention existing (AC-1, AC-2, AC-9), its discoverability across surfaces (AC-3..AC-7, AC-11..AC-13, AC-24), the discipline enforcement (AC-4, AC-18, AC-21, AC-22), or the regression guarantee (AC-10, AC-14..AC-17, AC-20, AC-23). AC-8 and AC-19 are important rather than required because cross-reference drift / dashboard-already-doesn't-render-tasks are both recoverable.

## Decision Log

| Date | Decision | Reason | Alternatives |
|---|---|---|---|
| 2026-06-03 | Codify `[~]` as the canonical AC checkbox state for "intentionally not met"; do not introduce additional new states (e.g., `[?]`, `[!]`) in v1 | Operator approved the marker after seeing it used ad hoc on `1p318` AC-13/AC-19 and confirmed *"I like this convention."* Expanding to additional states without real-usage evidence would be speculative; v1 scope is the marker that surfaced from real practice. | (a) Add `[?]` for "uncertain" / `[!]` for "blocked" at the same time — rejected; no real-usage evidence yet, speculative. (b) Use a verbal convention only (no marker) — rejected; loses the at-a-glance distinction the operator approved. |
| 2026-06-03 | Inline status note required on every `[~]` AC; silent `[~]` is a docs-lint error for required-priority ACs | The whole point of the marker is to make deferral visible and auditable. A silent `[~]` would defeat the purpose. Mechanical enforcement (lint error) is the discipline that prevents drift; relying on prose guidance alone has a track record of silent drift across waves. | (a) Make the inline note recommended but not required — rejected; "recommended" without enforcement is the failure mode. (b) Require the note for all priority levels including nice-to-have — rejected; nice-to-have `[~]` is low-stakes and over-enforcement creates lint friction for no real benefit. |
| 2026-06-03 | Single source of truth for the convention in seed 170; other seeds cross-reference rather than duplicate | Duplicated convention text drifts. The seed-first discipline applies here too. | (a) Duplicate the convention text in each lifecycle seed — rejected; drift exposure. (b) Define the convention in a new standalone "Conventions" seed — rejected; seed 170 already owns AC formulation guidance and is the natural home. |
| 2026-06-03 | Worked example in seed 170 cites `1p31b` `1p318` AC-13/AC-19 with the original inline status notes preserved | A real artifact anchored in the seed makes the convention auditable against actual practice. Generic worked example would not preserve the audit trail. | Generic worked example — rejected; loses the audit-trail value. |
| 2026-06-03 | No retrofit on prior closed waves; convention applies from this change forward | Retrofitting would require re-opening closed waves and re-running their review evidence — high cost, low value. The convention's purpose is forward; backward application is not. | Retrofit on prior closed waves — rejected; cost exceeds value. |
| 2026-06-03 | v1 does not include a structured `wave_close` response field counting `[~]` ACs; close-wave seed guidance handles surfacing | The seed guidance is sufficient for v1 and avoids over-engineering. A response field is a forward-compat possibility once usage patterns emerge. | Add a structured response field in v1 — rejected; speculative without real-usage data. |
| 2026-06-03 | Dashboard progress-bar accounting excludes `[~]` from the denominator (a change with 8 `[x]` + 2 `[~]` of 10 ACs shows 100% complete, not 80%) | `[~]` is "not in this scope" — semantically equivalent to *not-this-scope* AC priority, just discovered during implementation rather than at planning. Counting it as unmet would visually misrepresent the change as incomplete when the team has actually finished everything in scope. Counting it as met would inflate completion claims. Exclusion from the denominator + a separate deferred-count badge is the accounting that matches the semantics. | (a) Count `[~]` as met — rejected; inflates completion. (b) Count `[~]` as unmet — rejected; visually misleading, defeats the convention's discoverability goal. (c) Surface only the count without changing progress accounting — rejected; the dashboard's primary visual signal is the progress bar; if it lies, the badge is decoration. |
| 2026-06-03 | Dashboard surfacing is in-scope for v1, not deferred to a follow-on | Without dashboard handling, `[~]` either silently breaks dashboard rendering or renders misleadingly. The convention's discoverability claim — "future-readers see them surface as intentionally deferred" (QA-D-1) — fails at the primary visual surface. The dashboard work is bounded and sized to fit alongside the seed + validator work in a single wave. | (a) Defer dashboard work to a follow-on — rejected; ships the convention partially-supported and creates a known-broken visual state. (b) Add the dashboard work but skip the tests — rejected; AC-14 regression discipline is non-negotiable for a UI behavior change. |
| 2026-06-03 | The `[~]` marker also applies to `## Tasks` checkboxes, with **asymmetric enforcement**: the inline status note is *required* on AC `[~]` (for required-priority ACs) but only *recommended* on task `[~]` | Tasks are implementation hints, not contract surface. The `1p312` "Bench the reaper on 5,000-row fixture" task example: the right shape is `[~]` with an inline pointer to the AC-3 status note that records the rationale — not a silent task deletion. Mandatory inline notes on every task `[~]` would create lint friction during natural drafting (tasks get rewritten more often than ACs) without proportional auditability benefit. The asymmetric rule matches the asymmetric stakes. | (a) Same enforcement on tasks as ACs (mandatory inline note) — rejected; creates lint friction during natural task rewriting. (b) Skip tasks entirely from the convention — rejected per operator question; the `1p312` task example is precisely the case the convention is for. (c) Add tasks as a follow-on — rejected; the validator work is being done now, and adding the task branch is incremental. |
| 2026-06-03 | Late-admit `1p32k` to `1p31b` (post-delivery-council) so the convention ships in the same wave as the canonical worked example (`1p318` AC-13/AC-19) | Shipping the convention separately from its worked example would leave `1p318`'s `[~]` markers ad hoc until the follow-on wave landed. Co-shipping makes the convention *real* at the moment the worked example becomes real. The late-admission discipline applies: delivery-phase council must re-cover `1p32k` after implementation; close cannot proceed until that pass completes. | (a) Ship `1p32k` in a follow-on wave — rejected per operator; leaves `1p318` markers ad hoc until follow-on lands. (b) Ship `1p32k` and retroactively re-validate `1p318` markers — rejected; no-retrofit principle (Req-9) means `1p318`'s markers are accepted as-is and the convention applies forward. The worked example in seed 170 references them as the precedent, not as compliance subjects. |
| 2026-06-03 | Add a **hard close-time gate**: at `wave_close`, every AC and every task across the wave's admitted changes must be `[x]` or `[~]`. Silent `[ ]` is a blocking close error. Applies to all priorities except `not-this-scope` (exempt because the priority encodes the exclusion). The gate applies regardless of change status — a change marked `implemented` with silent `[ ]` items reveals a tracking-discipline failure. | Without the close-time gate, `[~]` is just one more marker some operators use; the discipline that makes it *real* is the requirement that every item be accounted for at close. Operator memory ("AC tracking is real-time") already captured the intent; the gate operationalizes it. The asymmetric inline-note rule (mandatory for required-priority ACs; recommended for tasks) handles per-item quality; the close-time gate handles per-wave completeness. Together they close the silent-debt failure mode. | (a) Apply the gate only to required-priority ACs — rejected; silent `[ ]` on important and nice-to-have ACs is the same failure mode as on required, just with lower stakes; the gate's value is the discipline, not the priority class. (b) Apply the gate only to ACs, not tasks — rejected; the `1p312` bench-task case demonstrates that silent task removal is exactly the pattern the convention is designed to prevent. (c) Make the gate a warning rather than a blocking error — rejected; warnings are silent-debt in another form. The whole point of the close-time gate is mechanical enforcement. (d) Apply the gate to all priorities including `not-this-scope` — rejected; `not-this-scope` already encodes the exclusion and enforcing checkbox marking on it would be redundant. |

## Risks

| Risk | Mitigation |
|---|---|
| Operators use `[~]` as a silent-defer-without-rationale escape valve | Mechanical enforcement (lint error on silent `[~]` for required ACs) prevents this. The convention's defense is in the validator, not in prose guidance. |
| `[~]` accumulates over many waves without aggregate visibility | Close-wave handoff surfacing (AC-6) makes per-wave visibility explicit. Cross-wave aggregate visibility (e.g., dashboard view of all `[~]` ACs ever recorded) is forward-compat scope, not v1. |
| The convention is inconsistent with downstream project usage that has already adopted alternative markers | The framework owns this convention; downstream projects inherit on upgrade. Acceptable per the seed-first / framework-owns-defaults discipline. |
| Validator change introduces a regression in existing `[ ]` / `[x]` handling | AC-13 explicit regression test; AC-10 new tests; AC-12 full framework suite. Three independent gates. |
| Worked example becomes outdated as `1p318` AC-13/AC-19 status notes evolve | The cited AC-13/AC-19 status notes are in a closed (or near-closed) wave's change doc; they don't evolve after wave close. The audit trail is durable. |
| Operators interpret `[~]` as "we'll get to this later" rather than "this is intentionally not happening" | The canonical definition (Req-1) names the distinction explicitly: `[~]` is "intentionally not met", not "deferred to follow-on." Follow-on items remain `[ ]` with a follow-on plan reference. |
| Dashboard visual treatment (color choice, icon) conflicts with existing palette or accessibility constraints | Use the existing dashboard CSS palette where possible — pick a neutral / muted tone that contrasts with both the met-green and unmet-grey but does not collide with the in-progress / error states. Choose an icon that reads as "intentional exclusion" rather than "broken." Manual verification step in Tasks covers this. |
| Dashboard accounting change confuses operators who were previously seeing `[~]` ACs as unmet (visually red/grey) and now see them as a separate category | Acceptable migration cost. The convention is forward-only (Req-9 no-retrofit) so only newly-authored `[~]` ACs land in the dashboard with the new treatment. Existing `[ ]` / `[x]` ACs render exactly as before. |

## Related Work

- **`1p31b` `1p318` AC-13 and AC-19** — the real artifact this convention grew from. Both are marked `[~]` with operator-directed removal rationale in their AC status notes; both are referenced in `1p31b` Decision Log entries.
- **`1p31b` Delivery-phase Wave Council — QA-D-1** — the advisory finding that surfaced the convention codification need.
- **Seed-first doc workflow** (memory note) — this change follows the seed-first discipline: update framework seeds before downstream propagation.
- **Weave new primitives across seeds** (memory note) — same pattern as `1p31i`: the canonical definition lives in one seed; cross-references in others.

## Session Handoff

Unattached future-wave plan. Recommended admission path: a small follow-on wave after `1p31b public-launch-prep` closes (the convention is meta-process, doesn't conflict with any in-flight work). Could co-admit with another small framework-maintenance change to bundle into a single delivery, but is sized to stand alone.
