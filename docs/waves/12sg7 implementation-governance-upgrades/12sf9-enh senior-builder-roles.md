# Senior Builder Roles For Wave Implementation

Change ID: `12sf9-enh senior-builder-roles`
Change Status: `complete`
Owner: wave-coordinator
Status: complete
Last verified: 2026-05-21
Wave: `12sg7 implementation-governance-upgrades`

## Rationale

Wavefoundry currently defines a generic `implementer` lane and a growing specialist catalog, but it does not define canonical **senior implementation-builder roles** that the framework can select when a wave needs domain-specific engineering depth. That leaves a gap between:

- readiness deciding that implementation should begin, and
- the framework clearly naming **which senior engineer profile** should own the work and what expertise that profile must bring.

For many target repositories, the difference is material. A Java Spring Boot service wave, a UI-heavy interaction wave, and a data-contract or SQL-heavy wave should not all route through the same undifferentiated implementation persona. The framework should define reusable builder roles that:

1. discover the actual project stack from repo evidence before coding,
2. state the required senior-level skills for that stack,
3. follow project and framework best practices explicitly rather than implicitly, and
4. let `Prepare wave` / `Implement wave` select the right implementation lanes before the first code edit.

This change adds those framework-level contracts so the Wave Framework can route implementation with more precision and with fewer silent assumptions.

## Requirements

1. The framework must define three new canonical specialist builder roles:
   - `senior-software-engineer`
   - `senior-ui-ux-engineer`
   - `senior-data-engineer`
2. Each role must be seeded as a reusable framework specialist with a canonical role doc contract: operating identity, responsibilities, default stance, focus areas, output shape, do-not rules, assumption tracking, salience triggers, and memory responsibilities.
3. Each role must explicitly require **project evidence first** before implementation:
   - detect the repo stack and dominant patterns,
   - name the relevant frameworks/languages/tooling in scope,
   - state what is known from code versus inferred from conventions.
4. `senior-software-engineer` must define broad senior implementation expectations for service and backend-heavy repos, including expertise expectations such as:
   - backend development
   - API design and implementation
   - Java / JVM service work when present
   - Spring Boot conventions when present
   - SQL and persistence reasoning when touched
   - testing, observability, concurrency, and failure handling
5. `senior-ui-ux-engineer` must define senior implementation expectations for interface-heavy work, including:
   - component architecture
   - interaction design and information architecture
   - accessibility baseline
   - responsive behavior
   - design-system alignment and stewardship
   - frontend state, loading, empty, and error-state completeness
6. `senior-ui-ux-engineer` must treat an existing project design system as a hard implementation constraint, not a suggestion, and must obey the repository’s design-system governance policy:
   - when a design system is defined in the repository, the role must use it as-is for implementation work unless the project’s own governance allows evolution in the current scope
   - the role must not silently introduce new tokens, components, patterns, or exceptions
   - whether design-system changes require explicit operator approval, reviewer approval, or are allowed within normal implementation scope must be defined by project policy rather than assumed by the generic role
   - the role must read and follow that policy before changing or extending the design system
7. When a project does not yet have a well-defined design system, `senior-ui-ux-engineer` must help define or refine one using the repository’s existing design-system template and governance surfaces rather than inventing an ad hoc local pattern language.
8. The framework should define a project-level setting or documented governance surface that tells agents whether the design system is:
   - read-only unless explicitly approved,
   - evolvable with review inside normal implementation scope,
   - or otherwise governed by project-local rules.
9. When project policy says design-system edits are protected, the framework must support a design-system edit gate through the same MCP/guard model used for seed and framework gates:
   - add a gate such as `design_system_edit_allowed`
   - enforce it only when project policy requires it
   - treat the gate as effectively always open when project policy does not require protection
10. The MCP gate tools should be normalized into a consistent noun-first family aligned with other Wavefoundry MCP surfaces:
   - `wave_gate_open(...)`
   - `wave_gate_close(...)`
   - `wave_gate_status(...)`
   This change should rename the current `wave_open_gate` / `wave_close_gate` family while the surface is still small enough to change safely.
11. The framework must define a read path for gate state through the normalized family. There is no current gate-state MCP tool, so this change should add `wave_gate_status(...)` or an equivalently named structured read surface that tells agents/operators which gates exist, whether they are currently enabled, and whether project policy requires them.
12. `Prepare wave` / readiness tooling must explicitly reconcile protected design-system gates when project policy requires them. At minimum:
   - confirm the expected gate posture before implementation begins
   - close or normalize any stale gate state before handing the wave into implementation
   - ensure closure-time cleanup also leaves required design-system gates in the correct resting state
13. `senior-data-engineer` must define senior implementation expectations for data-heavy work, including:
   - SQL correctness
   - schema and migration safety
   - ETL or pipeline reasoning when present
   - data-contract stability
   - data-quality checks
   - performance and cost awareness for data operations
14. The seed/bootstrap surfaces must explain that these are **builder specialists**: they complement the generic `implementer` role, and `Prepare wave` may assign them as the primary implementation lanes when the admitted change requires their domain depth.
15. `Prepare wave` and `Implement wave` surfaces must require the coordinator to choose implementation lanes from repository evidence and change scope, not habit. Selection criteria must at minimum consider:
   - code areas touched
   - project archetype and detected stack
   - acceptance criteria
   - trust-boundary or data-boundary impact
   - whether the change is primarily backend, UI/interaction, or data-contract/pipeline work
16. The plan/change-authoring surfaces must instruct planners to record the expected builder lanes and the skills the implementation will require, so the readiness pass has explicit inputs instead of reconstructing them later.
17. The framework must codify project-relevant best practices for these builder roles. At minimum the seeded guidance must include:
   - smallest correct change
   - brownfield pattern detection before editing
   - explicit contracts at boundaries
   - no speculative abstraction
   - tests or verification matched to the touched surface
   - explicit error, loading, and empty-state handling where relevant
   - API/schema change safety and migration thinking where relevant
   - accessibility baseline for UI work
   - mandatory adherence to an existing project design system
   - design-system evolution rules enforced from project-local governance, not guessed by the role
   - operator-owned commits and lifecycle gates remain mandatory
18. Repo-local generated specialist catalog and role wrappers must include these new roles only when repository evidence or operator configuration enables them.
19. Wavefoundry’s own self-hosted docs must explain how these roles are used during `Implement wave`, including the difference between generic build lanes and specialist builder lanes.

## Scope

**Problem statement:** The framework lacks canonical senior builder roles and therefore lacks a precise, evidence-driven way to assign implementation expertise during wave execution.

**In scope:**

- New framework specialist seeds for the three senior builder roles
- Specialist-catalog updates and routing guidance
- Plan/prepare/implement prompt updates so readiness chooses builder lanes explicitly
- Seed/bootstrap updates so role docs and wrappers render correctly
- Wavefoundry self-hosted docs updates that explain the new routing model

**Out of scope:**

- Creating every possible stack-specific engineer role (`spring-boot-engineer`, `react-engineer`, `dbt-engineer`, etc.)
- Changing review-lane policy beyond what is necessary to route implementation lanes
- Dashboard feature work beyond any minimal taxonomy/documentation changes needed for the new roles
- Product-code changes outside the framework/prompt/doc surface

## Acceptance Criteria

- [x] AC-1: Three new framework role seeds exist for `senior-software-engineer`, `senior-ui-ux-engineer`, and `senior-data-engineer`, and each is registered in the framework manifest.
- [x] AC-2: Each new role defines required senior skills, evidence-first stack detection, explicit best practices, anti-goals, and output expectations.
- [x] AC-2a: `senior-ui-ux-engineer` explicitly treats an existing repository design system as mandatory and reads mutability/approval rules from project-local governance instead of assuming one universal policy.
- [x] AC-2b: `senior-ui-ux-engineer` explicitly falls back to defining/refining a design system through the repository’s design-system template when no well-defined system exists.
- [x] AC-2c: The change defines a project-level governance setting or equivalent documented control for whether design-system changes are read-only, review-governed, or normally evolvable.
- [x] AC-2d: When project policy requires protection, the framework defines a `design_system_edit_allowed` gate or equivalent gate integrated with the MCP guard model.
- [x] AC-2e: The MCP gate family is normalized to `wave_gate_open`, `wave_gate_close`, and `wave_gate_status` for naming consistency.
- [x] AC-2f: The framework exposes a structured `wave_gate_status` read path so agents/operators can inspect current gate posture; no equivalent read tool exists today.
- [x] AC-2g: Prepare/close lifecycle tooling leaves design-system gates in the correct resting state when project policy requires them.
- [x] AC-3: `seed-050` documents these roles as specialist builder lanes and explains when they should be rendered into repo-local specialist surfaces.
- [x] AC-4: `seed-100` and the generated prompt surfaces state that `Prepare wave` must select the appropriate builder lanes based on repository evidence and admitted scope before implementation starts.
- [x] AC-5: `seed-170` and/or other planning surfaces require change authors to record expected implementation lanes and required skills for the change.
- [x] AC-6: `seed-180` and related implement-wave surfaces describe how the wave coordinator allocates work between the generic `implementer` and the new senior builder specialists during execution.
- [x] AC-7: The generated specialist catalog clearly distinguishes generic roles, reviewer roles, and specialist builder roles so operators can understand why a lane was selected.
- [x] AC-8: The new role guidance includes concrete project-relevant practices for backend/API, UI/accessibility, and SQL/data-contract work rather than generic “write good code” language.
- [x] AC-9: Wavefoundry’s self-hosted docs reflect the new model without contradicting the existing stage gate, council, or operator-owned commit rules.

## Tasks

- [x] Add three new framework specialist seeds for the senior builder roles. Recommended filenames:
  - `.wavefoundry/framework/seeds/222-senior-software-engineer.prompt.md`
  - `.wavefoundry/framework/seeds/223-senior-ui-ux-engineer.prompt.md`
  - `.wavefoundry/framework/seeds/224-senior-data-engineer.prompt.md`
- [x] Define project-level design-system mutability policy and protected-surface behavior in the relevant governance/config surfaces
- [x] Extend the existing gate model with an optional design-system gate (`design_system_edit_allowed`) that is enforced only when project policy requires it
- [x] Rename the MCP gate family to `wave_gate_open`, `wave_gate_close`, and `wave_gate_status`
- [x] Add a structured `wave_gate_status` read surface so agents/operators can inspect current gate posture
- [x] Update prepare/close lifecycle tooling so protected design-system gates are normalized to the correct resting state when policy requires it
- [x] Update `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md` to define builder-specialist rendering and role-doc expectations for these lanes.
- [x] Update `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` so `prepare-wave`, `implement-wave`, and prompt index surfaces explain builder-lane routing.
- [x] Update `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` so change authors record expected builder lanes and required skills during planning.
- [x] Update `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` so the coordinator allocates implementation work across generic and specialist builder lanes explicitly.
- [x] Update any supporting framework overview or routing seeds that describe lane selection — assessed seeds 001, 002, 010, 150, 160; no contradictory language found; no changes required.
- [x] Update `docs/agents/specialists/README.md` to classify the new roles and explain how they differ from narrower archetype specialists like `java-backend-engineer` and `database-optimizer`.
- [x] Update Wavefoundry-local generated or canonical docs as needed so self-hosted surfaces explain how a wave picks and uses the new builder roles.
- [x] Run framework verification and docs validation after implementation.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| role-seeds | implementer | Prepare wave | New seeds 222-224; `seed_edit_allowed` gate required |
| design-system-policy-and-gates | implementer | role-seeds | Project policy, optional `design_system_edit_allowed`, `wave_gate_*` family, lifecycle cleanup |
| seed-routing | implementer | role-seeds, design-system-policy-and-gates | `050`, `100`, `170`, `180` route and describe builder lanes |
| framework-overview-sync | implementer | seed-routing | `001`, `002`, `010`, `150`, `160` alignment pass |
| specialist-catalog | implementer | role-seeds | Clarify taxonomy and enabling rules |
| wf-self-host-docs | implementer | seed-routing, design-system-policy-and-gates | Wavefoundry-local docs and generated surfaces |
| verify | qa-reviewer | all | Framework tests + docs validation |

## Serialization Points

- The three new role seeds should be drafted before routing seeds reference them.
- Design-system policy and gate semantics should be decided before `050` / `100` / `180` are updated so role and lifecycle wording stay consistent.
- `seed-050`, `seed-100`, `seed-170`, and `seed-180` form one contract surface and should be reviewed as a unit before broader overview-sync work.
- Any generated local surfaces should be refreshed only after the seed text is stable.

## Affected Architecture Docs

N/A — this change affects framework prompt/routing contracts and specialist role surfaces, not runtime architecture boundaries.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | Canonical framework roles are the core deliverable |
| AC-2 | required | Skills and best practices must be explicit to be useful |
| AC-2a | required | Design-system compliance must be non-optional, but mutability must come from project policy |
| AC-2b | required | The role needs a disciplined fallback when a project lacks a mature design system |
| AC-2c | required | Projects need an explicit governance switch for rigid versus evolvable design systems |
| AC-2d | required | Protected design systems need the same operational guard discipline as other protected framework surfaces |
| AC-2e | required | The gate family should be named like other noun-first Wavefoundry tool groups |
| AC-2f | required | Agents need a structured way to inspect gate state; today no gate-status read tool exists |
| AC-2g | required | Lifecycle tooling must not leave protected design-system gates in a stale state |
| AC-3 | required | Rendering/routing contract anchors repo-local output |
| AC-4 | required | Readiness must choose lanes before coding starts |
| AC-5 | important | Better plan quality reduces readiness ambiguity |
| AC-6 | required | Implementation flow must actually use the new roles |
| AC-7 | important | Operator clarity prevents taxonomy confusion |
| AC-8 | required | Domain-specific guidance is the whole point of the change |
| AC-9 | required | Self-hosted docs must stay consistent with framework behavior |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-21 | Change doc created to define canonical senior builder roles and wave-routing updates. | Operator request + repo inspection of seeds `050`, `100`, `170`, `180`, specialist catalog, and current implementer surfaces |
| 2026-05-21 | Prepare wave completed; change marked ready for implementation in `12sg7`. | `docs/waves/12sg7 implementation-governance-upgrades/wave.md` |
| 2026-05-21 | Role-seeds workstream complete: wrote `222-senior-software-engineer.prompt.md`, `223-senior-ui-ux-engineer.prompt.md`, `224-senior-data-engineer.prompt.md`. Each seed defines operating identity, evidence-first stack detection, senior domain skills (backend/API/Java/Spring/SQL; component arch/accessibility/design-system governance; SQL/migration/ETL/data-contract), explicit best practices, preflight rubric, salience triggers, do-not rules, and project harness extension placeholder. Framework index auto-discovers new seeds; 1497 tests pass, docs-lint clean. | seed files; `run_tests.py` pass |
| 2026-05-21 | Design-system-policy-and-gates workstream complete: added `design_system_policy` governance section to `docs/workflow-config.json` (governance: evolvable); added `design_system_edit_allowed` to `_VALID_GATES` so it participates in open/close/status/force-close lifecycle; renamed MCP gate family from `wave_open_gate`/`wave_close_gate` to `wave_gate_open`/`wave_gate_close`; added `wave_gate_status` read-only MCP tool; updated all internal strings, `_force_gates_closed` diagnostics, `AGENTS.md` (tool list + gate descriptions + seed guardrail), `CLAUDE.md` (guardrails), `docs/architecture/current-state.md`; updated test class, tool-list test, added 3 new tests (design_system gate, gate_status returns all gates, gate_status reflects open gate). 1497 tests pass. | `server_impl.py`, `test_server_tools.py`, `AGENTS.md`, `CLAUDE.md`, `docs/workflow-config.json`, `docs/architecture/current-state.md` |
| 2026-05-21 | Seed-routing + overview-sync workstream complete: updated `seed-050` with senior builder specialist tier description and rendering rules including design_system_policy pointer for `senior-ui-ux-engineer`; updated `seed-100` prepare-wave rule with evidence-driven builder-lane selection requirement and implement-wave rule with builder-lane allocation mention; updated `seed-170` to require change authors to record expected builder lanes and required skills; updated `seed-180` Allocation bullet with concrete routing criteria for senior builder specialists vs generic implementer. Overview seeds 001, 002, 010, 150, 160 assessed — no lane-selection content to contradict or extend; no changes required. Docs-lint clean, 1497 tests pass. | `seed-050`, `seed-100`, `seed-170`, `seed-180` edits |
| 2026-05-21 | Specialist-catalog + wf-self-host-docs workstream complete: updated `docs/agents/specialists/README.md` with new senior builder specialist tier in taxonomy, seed-candidate table for the three roles, and relationship-to-generic-roles note; updated `docs/agents/implementer.md` with When To Use Senior Builder Specialists section; updated `docs/prompts/implement-wave.prompt.md` with builder-lane allocation guardrail. All workstreams done; final docs-lint clean, 1497 tests pass. | `docs/agents/specialists/README.md`, `docs/agents/implementer.md`, `docs/prompts/implement-wave.prompt.md` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-21 | Model these as specialist builder lanes, not replacements for `implementer` | Preserves the generic role while allowing readiness to route by domain depth | Replace `implementer` entirely — too disruptive and unnecessary |
| 2026-05-21 | Keep Java/Spring Boot, SQL, and API expertise as evidence-driven expectations within `senior-software-engineer` rather than creating a Spring-only canonical role now | Matches the request while keeping the framework reusable across multiple target repos | Add many stack-specific builder seeds immediately — higher complexity and more taxonomy churn |
| 2026-05-21 | Treat `senior-ui-ux-engineer` as a code-agent role focused on interaction implementation and usability quality, not human research or pure visual design | Keeps the role inside code-agent boundaries already used by the framework | Create a pure `ui-designer` role — previously rejected in the specialist catalog |
| 2026-05-21 | Make design-system mutability project-governed rather than universally operator-gated | Different repos have different governance models; enterprise systems are often rigid while smaller systems may evolve in normal implementation | Hard-code all design-system changes to require operator approval |
| 2026-05-21 | Reuse the existing gate model for protected design systems and normalize the tool family to `wave_gate_open` / `wave_gate_close` / `wave_gate_status` | Keeps operator workflow consistent with noun-first Wavefoundry tool groups and removes ambiguity about current state | Introduce an unrelated design-system-only approval mechanism or keep the older verb-first gate names |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| New roles overlap confusingly with existing specialists like `frontend-developer`, `java-backend-engineer`, and `database-optimizer` | Define clear scope in the catalog: senior builder roles are primary implementation lanes; narrower specialists remain advisory or focused deep-expertise lanes |
| Seed text becomes generic and vague instead of actionable | Require concrete skills, anti-goals, and verification expectations in each role seed |
| Readiness routing becomes too complex | Keep lane selection bounded to admitted scope, archetype evidence, and ACs; do not create a combinatorial routing system |
| UI/UX wording drifts into non-code research work | Explicitly constrain the role to interaction architecture, frontend implementation quality, and accessibility/usability evidence from the repo |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
