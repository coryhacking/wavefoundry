# AC And Task Linked Tracking With Review Verification

Change ID: `12sfj-enh ac-task-linked-tracking`
Change Status: `complete`
Owner: wave-coordinator
Status: complete
Last verified: 2026-05-21
Wave: `12sg7 implementation-governance-upgrades`

## Rationale

Wavefoundry change docs already support:

- explicit Acceptance Criteria with stable `AC-*` IDs,
- task checkboxes,
- AC priority tables,
- dashboard counts for completed tasks and ACs.

But the current model is still too loose in four ways:

1. Tasks are not traceably linked to specific ACs.
2. Agents can defer updating task and AC state until the end instead of keeping the document current during implementation.
3. Review lanes can read the document as if it were ground truth instead of treating code and tests as authoritative evidence.
4. There is no first-class way to say “this AC or task is not complete, and here is why” without burying the reason in prose.

That makes the change doc weaker as a live execution artifact and makes the dashboard less useful as an operational truth surface. A checked box should mean something precise, and an unchecked item should be able to carry a durable reason. More importantly, review should be able to say “implementation claimed this is done, but the evidence does not support it.”

This change upgrades the change-template contract in the simplest workable way: Acceptance Criteria should use the same checkbox tracking style as Tasks, agents should update both sections as they work, and review lanes should verify those marks against code and tests rather than trusting the document blindly. The source of truth remains:

1. code and tests for actual behavior,
2. review evidence for verification,
3. documentation for shared understanding and continuity.

## Requirements

1. `## Acceptance Criteria` must use checkbox tracking syntax instead of plain bullets: `- [ ] AC-1: ...`, `- [x] AC-2: ...`.
2. `## Tasks` must continue to use checkbox tracking syntax and remain the implementation checklist.
3. The template and planning surfaces must instruct agents to update both task and AC checkboxes incrementally during implementation rather than waiting until the end of the wave.
4. The template must preserve AC Priority as a distinct readiness concept. Priority and completion are different things and must not be collapsed into one field.
5. `Implement wave` and `Implement feature` surfaces must instruct implementation lanes to mark tasks and ACs complete when the underlying work is actually done, and to reopen or leave them unchecked when the work is incomplete.
6. `Review wave`, `qa-reviewer`, and `code-reviewer` surfaces must explicitly state that the document is not the truth source. Reviewers must validate checkbox claims against code, tests, and review evidence, and must correct or challenge stale AC/task status when the document overstates completion.
7. The review contract must require that an AC or task marked complete but lacking supporting code/test/review evidence be treated as incomplete or unverified until evidence exists.
8. The framework must support explicit “not done” reasoning when a checked item needs to be reopened or when an unchecked item is intentionally not complete. The reason may live in a nearby note, Progress Log entry, Review Checkpoints, or similar canonical evidence section, but the contract must require that the reason be recorded somewhere durable.
9. The dashboard must reflect the checkbox-based AC and task model clearly, including updated counts as agents mark items during implementation.
10. The dashboard should distinguish implementation claims from review-confirmed truth where possible, at minimum by surfacing review evidence/checkpoint state alongside the checkbox-derived progress rather than treating checkboxes alone as final proof.
11. The dashboard and parser must remain backwards-aware enough to handle older change docs gracefully during migration, but the new template and lint rules must define checkbox ACs as the forward contract.
12. Docs-lint must validate the new forward structure. At minimum it must fail when new or upgraded change docs use plain AC bullets where checkbox ACs are required, or when the AC Priority table falls out of sync with the checkbox AC list.
13. Planning and readiness surfaces must treat checkbox ACs as part of the canonical change doc so agents start with a structure that supports live execution.
14. The framework must define a migration/update path for Wavefoundry-local surfaces and fixtures so docs-lint tests, dashboard tests, and seeded templates stay aligned.

## Scope

**Problem statement:** The current change-doc contract uses checkbox tracking for Tasks but not Acceptance Criteria, which makes live progress uneven and weakens the dashboard and review workflow.

**In scope:**

- Change-template updates so Acceptance Criteria use checkbox tracking like Tasks
- Prompt and role-doc updates so agents maintain status during implementation
- Review-contract updates so review lanes verify against code/tests instead of trusting checkboxes
- Dashboard parser and UI changes to surface AC/task checkbox progress cleanly and in sync
- Docs-lint and test updates to enforce the new structure

**Out of scope:**

- Replacing code/test evidence with documentation-driven completion
- Adding a full external issue-tracker or project-management system
- Retrofitting every historical change doc immediately
- Product-specific semantics beyond the generic framework contract

## Acceptance Criteria

- [x] AC-1: The canonical plan template requires checkbox syntax in `## Acceptance Criteria` so ACs can be tracked the same way as Tasks.
- [x] AC-2: The seeded planning and implementation prompts require agents to update task and AC state incrementally during execution rather than waiting for closure.
- [x] AC-3: The seeded review prompts and review docs explicitly state that code and tests are the truth, review evidence confirms that truth, and documentation is the shared understanding layer rather than the authority layer.
- [x] AC-4: Review lanes are required to challenge or correct any AC/task item marked complete when code/test/review evidence does not support that state.
- [x] AC-5: The dashboard parser and UI surface checkbox-based AC/task status and stay in sync as agents mark items during implementation.
- [x] AC-6: Docs-lint validates the new forward contract and rejects malformed or non-checkbox AC tracking in newly updated surfaces.
- [x] AC-7: Existing forward-facing Wavefoundry-local docs, fixtures, and tests are updated so the template, dashboard, and validators all agree on the same structure.
- [x] AC-8: The change supports explicit “not done with reason” recording for future reference without forcing the operator to infer that context from prose elsewhere in the doc.

## Tasks

- [x] T-1: Update `docs/plans/plan-template.md` so `## Acceptance Criteria` uses checkbox syntax
- [x] T-2: Update planning seeds and prompt surfaces so new change docs scaffold checkbox ACs by default
- [x] T-3: Update implementation prompts and role docs so agents mark ACs and tasks during execution, not only at the end
- [x] T-4: Update review prompts and review docs so reviewers verify completion claims against code/tests and correct stale document state
- [x] T-5: Extend dashboard parsing in `.wavefoundry/framework/scripts/dashboard_lib.py` to treat checkbox ACs as the canonical forward model
- [x] T-6: Update `.wavefoundry/framework/dashboard/dashboard.js` and related UI so AC/task progress and review context are visible together
- [x] T-7: Add or update docs-lint validators so checkbox ACs are required in the forward contract and stay aligned with AC Priority
- [x] T-8: Refresh fixtures and tests covering dashboard snapshot parsing, docs-lint, and any change creation scaffolds
- [x] T-9: Update Wavefoundry-local generated or canonical docs that describe plan/change execution semantics
- [x] T-10: Run framework tests and docs validation

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| template-and-seeds | implementer | Prepare wave | Template, `170`, `100`, `180`, `190`, related docs |
| review-contract | implementer | template-and-seeds | `review-wave`, review docs, role-doc updates |
| parser-and-dashboard | implementer | template-and-seeds | `dashboard_lib.py`, `dashboard.js`, UI/test updates |
| lint-and-fixtures | implementer | template-and-seeds | Validator rules, fixtures, dashboard parsing tests |
| verify | qa-reviewer | all | Framework tests + docs validation + dashboard/test assertions |

## Serialization Points

- The checkbox AC template and seeded prompt contract should be stabilized before parser/dashboard work so the UI does not implement a moving target.
- Validator rules should be reviewed alongside the template contract to avoid shipping a template the linter does not actually enforce.
- Dashboard UI work should follow parser/schema decisions so display logic is driven by canonical data, not ad-hoc text parsing.

## Affected Architecture Docs

N/A — this change affects framework execution docs, dashboard behavior, and validation rules rather than runtime architecture boundaries.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The checkbox AC template contract is the foundation for the rest of the work |
| AC-2 | required | Live execution behavior must change, not just the document shape |
| AC-3 | required | The truth hierarchy is a core policy requirement |
| AC-4 | required | Review must be able to reject incorrect completion claims |
| AC-5 | required | The dashboard is part of the requested deliverable |
| AC-6 | required | Linting is what makes the contract durable |
| AC-7 | important | Repo-local surfaces and fixtures must stay coherent |
| AC-8 | required | Explicit not-done reasoning is a key requested outcome |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-21 | Change doc created after reviewing the current plan template, dashboard parser/UI, dashboard tests, docs-lint AC validation, and review semantics. | Operator request + repo inspection |
| 2026-05-21 | Prepare wave completed; change marked ready for implementation in `12sg7`. | `docs/waves/12sg7 implementation-governance-upgrades/wave.md` |
| 2026-05-21 | Implementation complete. Updated `plan-template.md` to use checkbox AC syntax. Updated `seed-170` to require checkbox ACs with incremental marking and not-done-with-reason recording. Updated `seed-180` with explicit incremental task/AC marking rule. Updated `review-wave.prompt.md` with AC/Task Verification Truth Hierarchy section. Updated `qa-reviewer.md` and `code-reviewer.md` with truth-hierarchy language and new refusal condition. Dashboard parser already handled checkbox ACs; added review evidence badge to AcsDialog in `dashboard.js` and `dashboard.css`. Added `_check_checkbox_ac_syntax` lint validator to `wave_lint_lib/wave_validators.py`. Added 2 new lint tests. Updated all 6 wave change docs to use checkbox AC syntax. 1501 tests pass, docs-lint clean. | `plan-template.md`, `seed-170`, `seed-180`, `review-wave.prompt.md`, `qa-reviewer.md`, `code-reviewer.md`, `dashboard.js`, `dashboard.css`, `wave_validators.py`, `test_docs_lint.py`, all 6 wave change docs |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-21 | Use checkbox ACs in `## Acceptance Criteria` instead of adding a separate AC tracking table | Simpler operational model; matches the existing task pattern and current dashboard parser behavior | Add a second tracking table with duplicate completion state |
| 2026-05-21 | Treat review verification as distinct from implementation-complete | A checked task or AC should not automatically mean validated by evidence | Keep only binary checkbox state |
| 2026-05-21 | Preserve documentation as the coordination layer, not the authority layer | Matches the requested “code and test are the truth” policy | Treat checked docs as sufficient proof |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The contract grows beyond the simple checkbox model the team will actually maintain | Keep completion tracking in the AC/task lists themselves and keep richer reasoning in review/progress sections |
| Dashboard and lint drift from the template | Treat template, parser, dashboard, and validator updates as one contract change with shared tests |
| Agents update checkboxes mechanically without real evidence | Review prompts must explicitly challenge unsupported completion claims |
| Migration friction for older docs | Preserve graceful parser handling for older docs while enforcing the new forward contract on newly touched surfaces |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
