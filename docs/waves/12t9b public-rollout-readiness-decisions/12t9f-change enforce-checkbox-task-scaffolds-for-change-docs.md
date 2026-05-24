# Enforce Checkbox Task Scaffolds For Change Docs

Change ID: `12t9f-change enforce-checkbox-task-scaffolds-for-change-docs`
Change Status: `implemented`
Owner: planner
Status: implemented
Last verified: 2026-05-22
Wave: `12t9b public-rollout-readiness-decisions`

## Rationale

Wavefoundry change documents are intended to serve as live planning and execution records. In practice, a newly created change doc in this repository still scaffolded `## Tasks` as plain bullet items, even though the framework MCP default template already uses checkbox tasks and the local `Plan feature` prompt describes tasks as checkboxes. The immediate problem is a stale repo-local template; the systemic problem is that the framework lint contract currently enforces checkbox syntax for Acceptance Criteria but not for Tasks, so this drift is not caught automatically.

## Requirements

1. Make newly scaffolded change docs generate checkbox tasks consistently across repo-local templates and framework default templates.
2. Align local prompt/docs language with the actual change-doc contract for Tasks.
3. Add framework-level validation or equivalent enforcement so task syntax drift is detected automatically.
4. Document whether task checkboxes are a Wavefoundry-only convention or a framework-wide contract for downstream repositories.
5. Preserve backward compatibility expectations for existing change docs or define the migration path if lint enforcement becomes stricter.

## Scope

**Problem statement:** New change docs in this repository can still produce plain-bullet Tasks because the repo-local template has drifted, and the framework does not currently enforce task checkbox syntax.

**In scope:**

- Fix the local Wavefoundry planning template so `## Tasks` uses checkbox syntax.
- Audit prompt/template/scaffolder sources for task-syntax inconsistencies.
- Decide and document whether checkbox tasks are part of the framework contract.
- Add framework enforcement if the contract is meant to be universal.
- Identify test and upgrade-surface changes needed to keep local and downstream scaffolds aligned.

**Out of scope:**

- Broad redesign of change-doc structure beyond task checkbox behavior.
- Changing Acceptance Criteria syntax, which is already enforced separately.
- Rewriting unrelated planning or review workflow rules that are unaffected by task syntax.

## Acceptance Criteria

- [x] AC-1: The change doc identifies the immediate root cause of the plain-bullet task scaffold in Wavefoundry and the relevant local files.
- [x] AC-2: The plan distinguishes local-repo drift from framework-level gaps and states which surfaces belong to each.
- [x] AC-3: The plan defines the target contract for `## Tasks` syntax in newly scaffolded change docs.
- [x] AC-4: The plan names the implementation surfaces needed for template updates, prompt updates, enforcement, and tests.
- [x] AC-5: The plan states how existing docs will be treated if task checkbox enforcement becomes stricter.

## Tasks

- [x] Audit `docs/plans/plan-template.md`, `docs/prompts/plan-feature.prompt.md`, framework seeds, and the MCP default template for task-syntax expectations.
- [x] Decide whether checkbox tasks are a framework-wide contract or a Wavefoundry-local convention.
- [x] Define the required local template and prompt updates.
- [x] Define the required framework lint/enforcement and test updates.
- [x] Record migration expectations for existing staged or wave-owned change docs if enforcement changes.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| contract-audit | planner | — | Compare local template, local prompt, framework seed, MCP default template, and lint behavior |
| contract-definition | planner | contract-audit | Decide whether checkbox tasks are local or framework-wide |
| implementation-scope | planner | contract-definition | Name required template, prompt, lint, and test changes |

## Serialization Points

- Local Wavefoundry prompt/template updates should not diverge from the framework contract once the task syntax decision is made.
- If lint enforcement changes, scaffolds and tests must be updated in the same implementation pass to avoid self-hosting drift.

## Affected Architecture Docs

`docs/architecture/current-state.md`, `docs/architecture/data-and-control-flow.md`, and possibly `docs/architecture/testing-architecture.md` if task-checkbox enforcement becomes part of the framework contract. ADR update likely `N/A` unless the change becomes a broader planning-contract decision.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | The root cause must be precise before implementation |
| AC-2 | required | The fix spans both local and framework surfaces and must not stop at one layer |
| AC-3 | required | The target contract must be explicit before enforcement is tightened |
| AC-4 | required | Self-hosting requires synchronized template, prompt, lint, and test updates |
| AC-5 | important | Enforcement changes need a migration stance for existing docs to avoid noisy failures |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-22 | Change scaffolded after reviewing the missing task checkbox behavior in new change docs. | Comparison of `docs/plans/plan-template.md`, `docs/prompts/plan-feature.prompt.md`, `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`, `.wavefoundry/framework/scripts/server_impl.py`, and docs-lint tests. |
| 2026-05-22 | Implemented the checkbox-task contract across the local template, local prompt, framework upgrade guidance, and framework docs-lint enforcement. | `docs/plans/plan-template.md`, `docs/prompts/plan-feature.prompt.md`, `.wavefoundry/framework/scripts/wave_lint_lib/wave_validators.py`, `.wavefoundry/framework/scripts/tests/test_docs_lint.py`, and `.wavefoundry/framework/seeds/160-upgrade-wavefoundry.prompt.md`; verification: `python3 -B -m unittest discover -s .wavefoundry/framework/scripts/tests -p 'test_docs_lint.py'`, `python3 .wavefoundry/framework/scripts/docs_lint.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-22 | Track task checkbox drift as its own rollout-readiness change rather than folding it into a larger planning cleanup. | The issue combines a local template bug with a framework enforcement gap and needs explicit scope. | Fix only the local template; ignore framework enforcement. |
| 2026-05-22 | Treat checkbox tasks as a framework-wide forward contract for wave-owned change docs. | The framework MCP scaffold already used checkbox tasks, and self-hosting drift persisted only because repo-local scaffolds and lint had diverged. | Keep checkbox tasks as a Wavefoundry-only convention; fix the local template without framework enforcement. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The local repo is fixed but downstream repos can still drift because framework lint does not enforce task checkbox syntax. | Treat framework enforcement as part of the implementation scope if checkbox tasks are the intended contract. |
| Tightening lint without a migration story may create noisy failures on existing change docs. | Define backward-compatibility and migration expectations before adding enforcement. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
