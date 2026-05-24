# Formal Red-Team Role And Council Integration

Change ID: `12sh5-enh formal-red-team-role`
Change Status: `complete`
Owner: wave-coordinator
Status: complete
Last verified: 2026-05-21
Wave: `12sg7 implementation-governance-upgrades`

## Rationale

Wavefoundry currently uses `red-team` in practice inside Wave Council rosters and review notes, but it does not define `red-team` as a formal framework role. That leaves a contract gap:

- `reality-checker` is formally seeded and documented as an evidence/assumption challenger
- `red-team` is treated locally as a distinct seat, but has no canonical role doc, seed, mode set, or routing contract

That gap matters because the intended `red-team` role is broader than "reality check." The operator wants to use red-team in multiple ways:

1. adversarial review, abuse-case analysis, exploit attempts, bypass paths, and failure pressure-testing
2. multi-perspective option exploration before implementation
3. creative challenge of feature definitions, workflows, and implementation paths
4. UI and interaction provocation when a safer or more novel direction should be considered
5. technology, framework, library, and tool inclusion evaluation before a project commits to them
6. feature-definition shaping when the operator wants the team to help decide what a feature should be, not only how to implement it
7. council participation as a distinct voice rather than an implicit alias for `reality-checker`

The framework therefore needs a formal `red-team` specialist that preserves the useful generic agent intuition around red teaming while making Wavefoundry's intended use explicit, reusable, and distinct from `reality-checker`, `security-reviewer`, and other reviewer lanes.

## Requirements

1. The framework must define `red-team` as a formal specialist role with a canonical seed and generated role surface.
2. The seeded role contract must be structured around stable **mission**, **primary question**, and **operating invariants** before it lists modes, so weaker models get a clear anchor and stronger models are not reduced to a checklist.
3. The `red-team` mission must be defined broadly enough to cover adversarial, alternative, strategically competitive, failure-oriented, and opportunity-seeking challenge across plans, features, workflows, technology choices, implementation paths, and delivered artifacts.
4. The seeded role should anchor on a canonical primary question equivalent to: "What is the strongest competing interpretation, alternative, attack, failure, or missed opportunity here?"
5. `red-team` must not be defined as merely another name for `reality-checker`. The contract must explicitly distinguish them:
   - `reality-checker` challenges assumptions, evidence quality, and false confidence
   - `red-team` pressure-tests systems, proposals, and decisions from adversarial, alternative, failure-oriented, and strategically competitive perspectives
6. The `red-team` role must support more than security-oriented attack review. Its role contract must explicitly allow use in:
   - adversarial implementation review
   - failure-mode and bypass-path analysis
   - alternative implementation-path exploration
   - technology, library, and framework evaluation
   - workflow and feature-definition challenge
   - creative UI / interaction provocation when the goal is to surface stronger options or reveal blind spots
7. The seeded role must define explicit operating invariants. At minimum, the invariants should require `red-team` to:
   - challenge from multiple perspectives, not one domain only
   - surface stronger alternatives, not only objections
   - stay grounded in repository evidence, stated goals, and real constraints
   - distinguish evidence, inference, and speculation
   - name tradeoffs, downside risk, and upside opportunity
   - avoid replacing required specialist lanes or pretending to own their signoff
8. The framework must define an explicit mode set for `red-team`. At minimum, the seeded role should include modes equivalent to:
   - `abuse-path-review` or similar
   - `failure-pressure-test`
   - `option-challenge`
   - `technology-evaluation`
   - `workflow-challenge`
   - `feature-definition-challenge`
   - `design-provocation`
   - `council-seat`
   Final naming may vary, but the scope above must be canonical and unambiguous.
9. The mode set must be described as common operating patterns, not an exhaustive ceiling. The role contract should explicitly preserve the ability for stronger models to apply a better grounded challenger lens when one fits the task more precisely than the named modes.
10. The `red-team` role must be framed as a multi-perspective challenger, not just a blocker. Its job is to generate pressure, alternatives, and blind-spot coverage that materially improve decisions.
11. The role contract must define the relationship between `red-team` and `security-reviewer`:
   - `security-reviewer` remains the formal trust-boundary / security-correctness lane
   - `red-team` may explore exploit and bypass scenarios, but it is not a replacement for security review
12. The role contract must define the relationship between `red-team` and `reality-checker`:
   - `reality-checker` asks whether the claim is evidenced
   - `red-team` asks how the design, workflow, or decision can be broken, bypassed, outmaneuvered, or improved by competing alternatives
13. The role contract must define the relationship between `red-team` and `senior-engineering-challenger` so challenge modes do not become redundant or contradictory.
14. The framework must define how coordinators invoke `red-team` during planning, readiness, implementation, review, and council synthesis. At minimum:
   - planners may use it to evaluate candidate technologies, libraries, frameworks, and integration approaches before they are admitted or specified
   - planners may use it to challenge feature definition or workflow choice
   - coordinators may use it to pressure-test implementation paths before first edit
   - review and council phases may use it to stress delivered behavior, residual risk, and bypass/failure paths
15. The framework should make it natural for operators to invoke `red-team` for scoped exploratory asks such as:
   - "Ask the red team how this feature should be defined"
   - "Have the red team compare these libraries before we choose one"
   - "Use the red team to challenge the proposed workflow and suggest stronger alternatives"
   The role guidance should preserve this operator-facing flexibility rather than requiring only narrow review-style entry points.
16. The seeded role should define an output shape that consistently captures:
   - the strongest challenge
   - the best alternative or counterproposal
   - the consequence of keeping the current path
   - the recommendation
   - the evidence basis and confidence level
17. Wave Council policy must support `red-team` as a valid council seat through explicit configuration and seeded documentation. The framework must not rely on local convention alone.
18. The framework must decide whether `red-team` is:
   - part of the default fixed council seat template,
   - an optional configured council seat,
   - or a rotating/advisory challenger seat.
   The answer must be documented consistently across config examples, prompt surfaces, and role docs.
19. Specialist taxonomy docs must classify `red-team` clearly and explain why it is distinct from `reality-checker`.
20. The framework must preserve the useful general-model intuition around "red team" instead of over-constraining it into one narrow checklist. The role should still be able to challenge from multiple angles when the operator or coordinator requests that breadth.
21. Wavefoundry-local docs must explain when to use `red-team` versus `reality-checker`, `security-reviewer`, and `senior-engineering-challenger`.

## Scope

**Problem statement:** Wavefoundry uses `red-team` in practice, but the framework has no formal role contract for it, and the desired behavior is broader than the currently seeded `reality-checker`.

**In scope:**

- New formal role seed and generated role contract for `red-team`
- Taxonomy and routing updates distinguishing `red-team` from related challenger/reviewer roles
- Council policy and prompt-surface updates so `red-team` can be used intentionally in council and non-council workflows
- Wavefoundry-local docs updates clarifying when and how to invoke it

**Out of scope:**

- Replacing `security-reviewer`, `reality-checker`, or `senior-engineering-challenger`
- Turning `red-team` into a mandatory lane for every single change regardless of scope
- Defining human organizational red-team process outside the framework's agent role surface

## Acceptance Criteria

- [x] AC-1: A canonical framework seed exists for `red-team`, and generated repo-local role surfaces can render it.
- [x] AC-2: The `red-team` role doc explicitly distinguishes its purpose from `reality-checker`, `security-reviewer`, and `senior-engineering-challenger`.
- [x] AC-2a: The formal contract leads with mission, primary question, and invariants before listing modes.
- [x] AC-3: The formal `red-team` contract includes non-security challenge modes for option exploration, workflow challenge, feature-definition challenge, and design provocation.
- [x] AC-3a: The formal `red-team` contract includes explicit technology/library/framework evaluation behavior and can be invoked before a project commits to a technical choice.
- [x] AC-3b: The formal `red-team` contract supports feature-definition challenge, not only implementation review, so operators can use it to shape what should be built.
- [x] AC-3c: The role contract explicitly says the named modes are not an exhaustive ceiling when a stronger grounded challenger lens is available.
- [x] AC-4: Council and routing surfaces document how `red-team` can participate in Wave Council and other coordinator-managed challenge flows.
- [x] AC-5: The framework documents whether `red-team` is default, optional, or rotating in council composition, and the documented answer matches workflow-config examples and seeded prompts.
- [x] AC-6: Wavefoundry-local docs explain when to use `red-team` versus adjacent challenger/reviewer roles.
- [x] AC-7: The final role contract preserves broad multi-perspective challenge behavior rather than collapsing `red-team` into a narrow security or reality-check-only lane.
- [x] AC-8: The seeded role includes a consistent output shape that surfaces strongest challenge, best alternative, consequence of staying the course, recommendation, and evidence basis.

## Tasks

- [x] Add a canonical framework role seed for `red-team`. Recommended filename:
  - `.wavefoundry/framework/seeds/225-red-team.prompt.md`
- [x] Decide and document the formal role boundary between `red-team`, `reality-checker`, `security-reviewer`, and `senior-engineering-challenger`
- [x] Define the role around mission, primary question, invariants, and output shape before enumerating modes
- [x] Define the seeded `red-team` mode set for adversarial review, failure pressure, option challenge, technology evaluation, workflow challenge, feature-definition challenge, design provocation, and council participation
- [x] Add an explicit non-exhaustive "freedom clause" so stronger models can apply better grounded challenger lenses without violating the contract
- [x] Update `.wavefoundry/framework/seeds/007-review-system-overview.md` so `red-team` appears in the appropriate review/council routing tables
- [x] Update `.wavefoundry/framework/seeds/050-agent-entry-surface-bootstrap.prompt.md` so repo-local role generation and taxonomy support `red-team`
- [x] Update `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` so review surfaces explain when `red-team` is invoked in council and pre-council challenge
- [x] Update operator-facing routing/docs: `docs/agents/README.md` challenger routing section; `docs/agents/specialists/README.md` challenger tier with routing distinction table
- [x] Overview seeds 010, 150, 160 assessed — no lane-routing content to update; no changes required
- [x] Reconcile `docs/workflow-config.json` — `red-team` already present in `fixed_seats` for both council phases; no change required
- [x] Run framework verification and docs validation after implementation

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| role-contract | implementer | Prepare wave | New seed `225`; define boundaries and modes |
| routing-and-council | implementer | role-contract | `007`, `050`, `100`, config and council wording |
| overview-sync | implementer | routing-and-council | `010`, `150`, `160`, local docs alignment |
| verify | qa-reviewer | all | Framework tests + docs validation |

## Serialization Points

- The `red-team` role boundary should be decided before prompt/routing surfaces are updated.
- Council-seat policy should be decided once and then propagated consistently through config examples, seeds, and local docs.
- Local docs refresh should follow the canonical role contract rather than inventing repo-only behavior.

## Affected Architecture Docs

N/A — this change affects framework role/routing contracts and council policy, not runtime architecture boundaries.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The formal role seed is the primary deliverable |
| AC-2 | required | The distinction from adjacent roles removes the current ambiguity |
| AC-2a | required | Mission/question/invariant-first structure is the best way to stay durable across models |
| AC-3 | required | Broader challenge modes are explicitly requested |
| AC-3a | required | Technology-selection challenge is one of the intended operator uses |
| AC-3b | required | Feature-definition challenge is one of the intended operator uses |
| AC-3c | required | The role must not cap stronger models at a brittle checklist of named modes |
| AC-4 | required | Council/routing behavior must be operational, not implied |
| AC-5 | required | Seat policy drift is the current local/framework mismatch |
| AC-6 | important | Operator clarity prevents misuse and overlap |
| AC-7 | required | Preserving broad red-team behavior is the core intent |
| AC-8 | important | A stable output shape makes the broader role actionable and comparable across runs |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-21 | Change doc created to formalize `red-team` as a distinct multi-mode specialist and council participant. | Operator request + repo inspection of `reality-checker`, Wave Council config, seed routing docs, and recent wave records |
| 2026-05-21 | Expanded the role contract so `red-team` can evaluate technologies/libraries and help shape feature definition, not only pressure-test implementation and delivery. | Operator clarification in this thread |
| 2026-05-21 | Refined the intended implementation shape so `red-team` is defined by mission, primary question, invariants, and a non-exhaustive mode set rather than a narrow checklist. | Red-team exploration in this thread over model variance and advanced-role flexibility |
| 2026-05-21 | Prepare wave rerun completed; change marked ready for implementation in `12sg7`. | `docs/waves/12sg7 implementation-governance-upgrades/wave.md` |
| 2026-05-21 | Implementation complete. Decision: `red-team` as optional/configurable council seat (not in framework default fixed-seat template; Wavefoundry local config already has it in `fixed_seats` for both phases). Wrote `225-red-team.prompt.md` with mission/primary question/invariants-first structure, 8 named modes (non-exhaustive freedom clause), explicit distinctions from `reality-checker`/`security-reviewer`/`senior-engineering-challenger`, output shape with 7 required fields, council participation contract. Updated `seed-007` harness specialist table and question ownership routing table. Updated `seed-050` Wave Council note to include `red-team` config. Updated `seed-100` review-wave rule with council-seat and pre-council invocation guidance. Updated `docs/agents/README.md` (challenger routing section) and `docs/agents/specialists/README.md` (challenger tier table). Docs-lint clean, 1497 tests pass. | `seed-225`, `seed-007`, `seed-050`, `seed-100`, `docs/agents/README.md`, `docs/agents/specialists/README.md` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-21 | Treat `red-team` as distinct from `reality-checker` rather than folding it into assumption-validation work | The requested behavior includes adversarial, creative, and option-generation challenge beyond evidence skepticism alone | Alias `red-team` to `reality-checker` |
| 2026-05-21 | Preserve broad "red team" intuition while still defining explicit modes and boundaries | Agents already have a loose concept of red teaming, but the framework needs a durable contract without narrowing it too far | Constrain `red-team` to only exploit or abuse-path review |
| 2026-05-21 | Keep technology evaluation and feature-definition challenge inside the same `red-team` role instead of splitting them into separate exploratory specialists | The operator wants one reusable multi-perspective team that can challenge choices before implementation, not a set of narrowly siloed challengers | Create separate `technology-evaluator` or `feature-definition-reviewer` roles |
| 2026-05-21 | Define `red-team` by mission/question/invariants first, then modes second | This preserves consistency across weaker models without capping stronger models at a brittle enumerated checklist | Define the role only by a long mode list or only by vague prose |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `red-team` overlaps with `reality-checker` or `senior-engineering-challenger` and creates routing confusion | Define one-sentence primary questions for each role and encode them into routing docs |
| The role becomes too broad to be actionable | Keep explicit modes and output expectations while preserving multi-perspective breadth |
| Overly specific mode language causes weaker models to overfit and stronger models to underuse deeper red-team intuition | Use a non-exhaustive mode set with stable invariants and a freedom clause for better grounded challenger lenses |
| Council wording drifts again between local policy and framework defaults | Decide fixed-vs-optional seat policy once and propagate it through config examples and prompt docs |
| Creative-use wording drifts into ungrounded brainstorming | Require challenge outputs to stay tied to repo evidence, admitted scope, or explicit operator exploration goals |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
