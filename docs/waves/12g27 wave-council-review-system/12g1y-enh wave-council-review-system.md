# Wave Council Meta-Review System

Change ID: `12g1y-enh wave-council-review-system`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-08
Wave: `12g27 wave-council-review-system`

## Rationale

Wavefoundry already has most of the mechanics needed for a council-style review model: readiness selects review lanes, reviewer lanes can run concurrently, and the wave-coordinator already merges lane outputs into a single next-step decision. What is missing is a first-class deliberation contract that produces one explicit, synthesized recommendation before implementation begins and again before a wave closes.

External pattern guidance points in the same direction, with an important constraint. DeepLearning.AI's April 17, 2024 note on multi-agent collaboration argues that role-specialized agents improve focus and decomposition, but also warns that multi-agent output quality is harder to predict when interaction becomes too free-form. Google's December 16, 2025 ADK guide recommends parallel fan-out/gather with a final synthesizer for review-style tasks. Together, those sources support a Wave Council design built around independent seat reviews plus centralized synthesis, rather than open-ended cross-agent debate.

This change should add a universally required meta-review for all waves while preserving the current specialist review model. The council should improve decision quality and operator clarity, but it must not become a mechanism that suppresses or waives mandatory specialist findings from architecture, security, QA, docs-contract, release, performance, persona, or factor-review lanes.

## Requirements

1. The framework must define **Wave Council** as a universally required meta-review for all waves, with a readiness pass before implementation and a delivery pass after implementation.
2. The readiness pass must review the admitted change set, wave plan, selected lanes, protected surfaces, and major risks before implementation starts.
3. The delivery pass must review the implemented result, verification evidence, specialist-lane findings, and unresolved tradeoffs before closure.
4. Wave Council must not replace, bypass, or downgrade existing required review lanes, persona lanes, or factor-review lanes. Blocking specialist findings remain binding unless the underlying framework policy for that lane changes explicitly.
5. The council model must use isolated seat reviews plus a synthesis pass. Version 1 must not depend on free-form debate among council members.
6. The default council composition must be five seats: `architecture-reviewer`, `security-reviewer`, `qa-reviewer`, `reality-checker` as the pragmatist seat, and one rotating domain seat selected from roles such as `performance-reviewer`, `docs-contract-reviewer`, `release-reviewer`, or an applicable persona. The fixed four seats apply to both phases; the rotating fifth seat may differ between the readiness pass and the delivery pass based on phase-specific evidence.
7. The framework must define how the rotating fifth seat is chosen from wave evidence and review triggers, and must fall back safely when no special domain seat is warranted. The selection criteria must be defined separately for the readiness phase and the delivery phase.
8. The framework must define a dedicated **council-moderator** role for synthesis. The `wave-coordinator` remains responsible for lifecycle routing and gate enforcement, but the council-moderator owns the council briefing packet, synthesis pass, conflict handling, and final council verdict.
9. Version 1 of Wave Council must use a structured protocol: isolated first-pass seat reviews, a synthesis pass by the council-moderator, and at most one targeted challenge round when seats materially disagree. It must not require free-form multi-round debate among all seats.
10. The workflow contract must record council outputs in existing wave artifacts rather than inventing a parallel report system.
11. The framework must add a project-visible policy surface, likely in `docs/workflow-config.json`, that makes council behavior explicit: enabled status, phases, seat templates, rotating-seat selection policy, evidence format, targeted-challenge policy, and whether any repo-local customizations are allowed.
12. MCP lifecycle tooling and prompt surfaces must align on council requirements so `Prepare wave`, `Review wave`, and `Close wave` cannot drift into contradictory expectations.
13. The canonical seed prompts must be updated so Wave Council can be installed and upgraded consistently across target repositories rather than existing only as Wavefoundry-local guidance.

## Scope

**Problem statement:** Wavefoundry has parallel reviewer lanes and coordinator synthesis, but no explicit, universal deliberation layer that pressure-tests a wave before implementation and again after implementation. Review outputs remain fragmented across lanes, which makes tradeoff resolution and operator decision-making less explicit than they should be.

**In scope:**

- Naming and contract definition for **Wave Council** as a framework-level concept
- Council lifecycle design: readiness pass and delivery pass
- Council operating protocol: briefing packet, isolated seat pass, synthesis pass, optional targeted challenge round
- Seat model: four fixed seats plus one rotating domain seat
- Council-moderator role and the split between lifecycle coordination and council synthesis
- Phase-specific council templates for wave planning, wave delivery, and broader project-decision reviews
- Structured synthesis output and verdict semantics for both phases
- Evidence recording format in wave artifacts
- `docs/workflow-config.json` schema and policy additions for council behavior
- MCP lifecycle enforcement and diagnostics where council becomes a required framework checkpoint
- Canonical seed updates and Wavefoundry local surface updates for prepare/review/close guidance
- Seeding the `reality-checker` role — it exists as a local specialist doc (`docs/agents/specialists/reality-checker.md`) but is not in `.wavefoundry/framework/seeds/`; the council depends on it as a fixed seat, so it must be seeded in this wave
- Seeding the `council-moderator` role — this role does not yet exist anywhere; it must be created and seeded canonically so target repositories receive it through framework install/upgrade
- Tests covering council policy parsing, evidence recognition, and gating behavior
- Transition policy for waves already in flight when council ships — must define explicitly whether council applies retroactively, from next Prepare, or only to new waves

**Out of scope:**

- Replacing existing specialist, persona, factor-review, or operator signoff lanes
- Free-form peer debate among councilors in v1
- Automatic invocation of council agents by the MCP server
- Cross-repository customization of generic framework behavior without an explicit policy surface
- A full redesign of the review taxonomy beyond the council addition

## Acceptance Criteria

- AC-1: The framework defines Wave Council as a universal two-phase meta-review: one readiness pass before implementation and one delivery pass before closure.
- AC-2: Council guidance explicitly states that existing required lanes remain authoritative and cannot be waived by synthesis output alone.
- AC-3: The council operating protocol is documented: isolated first-pass seat reviews, council-moderator synthesis, and at most one targeted challenge round on material disagreement.
- AC-4: The framework defines a dedicated council-moderator role and explicitly separates that role from the wave-coordinator. The `council-moderator` role is present in the canonical seed set so target repositories receive it through framework install/upgrade.
- AC-5: The default council seat model is documented, including the `reality-checker` pragmatist seat, rotating fifth-seat rules, and phase-specific templates. The `reality-checker` role is present in the canonical seed set.
- AC-5a: The rotating fifth-seat trigger criteria are explicitly documented — what wave evidence or review trigger selects each candidate domain seat, and what the safe fallback is when no special domain seat is warranted.
- AC-6: `Prepare wave`, `Review wave`, and `Close wave`/`Finalize feature` surfaces consistently describe when council runs, what it reads, and where its output is recorded.
- AC-7: `docs/workflow-config.json` gains an explicit council policy surface, and server-side lifecycle logic reads it consistently.
- AC-8: MCP lifecycle responses and/or docs validation can detect missing required council evidence for the phases where council is mandatory.
- AC-9: Tests cover the no-drift path: council required and recorded, council required and missing, specialist lane missing even when council exists, and repo without custom council overrides.
- AC-10: The implementation does not introduce a parallel closure artifact; council output is recorded in existing wave sections and remains auditable. The specific section name and location within `wave.md` is documented and consistent across both phases.
- AC-10a: The transition policy is documented: which waves are subject to council requirements and from which lifecycle event the requirement applies.
- AC-11: The canonical seed set and generated local prompt surfaces both expose Wave Council so target repositories receive the feature through framework install/upgrade.

## Tasks

- [ ] Finalize the council contract: name, phases, authority boundaries, verdict shape, and rotating-seat policy
- [ ] Define rotating fifth-seat trigger criteria explicitly: map each candidate domain seat to the wave evidence or review signal that selects it, and specify the safe fallback when no signal is present
- [ ] Decide the specific evidence recording location within `wave.md` (e.g., a `## Council` section) for both readiness-phase and delivery-phase outputs — this must be locked before server diagnostics and prompt wording proceed
- [ ] Define the transition policy: state explicitly whether council applies to waves already in flight, from next Prepare only, or only to newly created waves after the council wave ships
- [ ] Define the council operating protocol: briefing packet contents, isolated seat pass, synthesis pass, targeted challenge round criteria, and output schema
- [ ] Define the dedicated council-moderator role and its boundary with `wave-coordinator`
- [ ] Define phase-specific council templates for wave planning, delivery review, and broader project-decision review
- [ ] Add council policy schema to `docs/workflow-config.json` and server readers
- [ ] Seed the `reality-checker` role canonically (`.wavefoundry/framework/seeds/`) — it is a fixed council seat and must be available in target repositories via framework install/upgrade
- [ ] Update canonical lifecycle and review seeds to describe council as universal meta-review without replacing existing lanes
- [ ] Add or update canonical role/prompt surfaces for Wave Council synthesis behavior, including a seeded council-moderator prompt
- [ ] Update Wavefoundry local docs and prompts generated from those seeds
- [ ] Extend MCP lifecycle logic and diagnostics for required council evidence
- [ ] Add regression tests for council policy parsing, evidence parsing, and gating interactions with existing required lanes
- [ ] Stress-test the plan with `Interrogate this plan` before wave admission

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| contract design | planner | - | Define council semantics before changing prompts or server logic |
| moderator design | planner | contract design | Define council-moderator scope, briefing-packet schema, and synthesis rules |
| seed and prompt updates | implementer | contract design | Protected surfaces: `.wavefoundry/framework/seeds/`, `docs/prompts/`, `AGENTS.md` |
| server and tests | implementer | contract design | Keep MCP enforcement aligned with documented behavior |
| local surface refresh | implementer | seed and prompt updates | Regenerated or reconciled Wavefoundry-local docs and workflow config |
| review hardening | wave-coordinator | server and tests | Confirm specialist lanes remain authoritative and council does not overreach |

## Serialization Points

- `docs/workflow-config.json` council schema must be settled before server enforcement and prompt wording proceed in parallel.
- `.wavefoundry/framework/seeds/` is a protected surface and requires `seed_edit_allowed` guard approval before implementation.
- `docs/prompts/` and `AGENTS.md` are protected framework-maintenance surfaces and require `framework_edit_allowed` guard approval before implementation.
- **Council evidence recording location** (specific section name and placement in `wave.md`) must be decided before server diagnostics, lifecycle prompt wording, or docs examples are written — any parallelism before this is locked will cause immediate drift.
- Council evidence format must be fixed before lifecycle tool parsing and docs examples are updated, or drift will be introduced immediately.
- **Rotating fifth-seat trigger criteria** must be defined before the council-moderator briefing-packet schema is written.
- The council-moderator role contract must be fixed before any seed/prompt text refers to moderator vs coordinator responsibilities.
- **`reality-checker` and `council-moderator` seeds** must both land before any council seat-composition or synthesis reference in prompt surfaces or tests points to them.
- `server.py` lifecycle diagnostics and `.wavefoundry/framework/scripts/tests/test_server_tools.py` must land together to avoid contract skew.

## Affected Architecture Docs

- `docs/architecture/current-state.md` — if MCP lifecycle tooling gains explicit council enforcement or new lifecycle checkpoints
- `docs/architecture/data-and-control-flow.md` — if council evidence becomes part of readiness/review/closure control flow
- `docs/architecture/testing-architecture.md` — if new test responsibilities or lifecycle verification tiers are added

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Universal two-phase council behavior is the core contract change that the rest of the wave depends on. |
| AC-2 | required | Non-waiver boundaries preserve existing review authority and prevent the council from creating unsafe shortcuts. |
| AC-3 | required | The isolated-review plus synthesis protocol is the main quality-control mechanism that differentiates the council from generic discussion. |
| AC-4 | required | A dedicated seeded `council-moderator` is central to the accepted design and affects both framework role taxonomy and prompt behavior. |
| AC-5 | required | Default seats and phase-specific templates determine whether the council is usable across planning, delivery, and broader project decisions. |
| AC-5a | important | Rotating-seat trigger criteria are essential for consistent operator use but refine, rather than establish, the core council contract. |
| AC-6 | required | Prepare/review/close prompt-surface consistency is necessary so target repositories can actually operate the council correctly. |
| AC-7 | required | Explicit workflow-config and server-reader support is needed for the council to be auditable and enforceable rather than prose-only guidance. |
| AC-8 | important | Lifecycle diagnostics for missing council evidence strengthen adoption, but the council contract and surfaces can be implemented before every diagnostic path is complete. |
| AC-9 | important | Regression coverage is necessary because this change spans seeds, server logic, and generated local docs. |
| AC-10 | important | Reusing existing wave artifacts preserves auditability and avoids adding a parallel artifact class to the framework. |
| AC-10a | important | Transition policy matters for safe rollout, but it is downstream of the council contract and evidence shape. |
| AC-11 | required | Canonical seed coverage is what makes this a framework feature rather than a Wavefoundry-only local adaptation. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-08 | Created the initial change plan for a universal Wave Council meta-review system. | Internal review of Wavefoundry review/lifecycle surfaces plus external pattern review: DeepLearning.AI (2024-04-17), Google Developers Blog ADK guide (2025-12-16), InfoQ Google pattern summary (2026-01-05), and the 2024 LLM multi-agent systems survey. |
| 2026-05-08 | Added four open design gaps as tasks, ACs, serialization points, and risks: (1) rotating fifth-seat trigger criteria under-specified; (2) evidence recording location not decided; (3) no transition policy for in-flight waves; (4) `reality-checker` role exists locally but is not seeded — confirmed missing from `.wavefoundry/framework/seeds/`. | Plan review session. |
| 2026-05-08 | Prepare wave pass completed: change doc confirmed wave-owned and complete; required review lanes selected; AC priority table populated; wave advanced to ready state pending implementation. | `docs/waves/12g27 wave-council-review-system/wave.md` readiness verdict and participants roster. |
| 2026-05-08 | Implemented Wave Council across canonical seeds, local prompt/role surfaces, and MCP lifecycle enforcement. Added `council-moderator` local role surface, explicit `wave_council_policy` configuration, council signoff gating in prepare/review/close flows, and regression coverage for council enforcement. | `python3 .wavefoundry/framework/scripts/run_tests.py` (1008 tests, pass); `.wavefoundry/bin/docs-gardener`; `.wavefoundry/bin/docs-lint`. |
| 2026-05-08 | Review wave found two contract blockers in the first pass and resolved them in the same wave: missing canonical seed files for `council-moderator` / `reality-checker`, and missing `transition_policy` enforcement for closure-time council requirements. | Added seeds `215-council-moderator.prompt.md` and `216-reality-checker.prompt.md`; updated `007-review-system-overview.md`; updated `server.py`; reran `python3 .wavefoundry/framework/scripts/run_tests.py` (1010 tests, pass) and `.wavefoundry/bin/docs-lint`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-08 | Use **Wave Council** as the feature name | Fits existing framework vocabulary and gives a clean operator-facing command surface | Council of Five, Review Council, Deliberation Council |
| 2026-05-08 | Make the council a universal meta-review, not a replacement for specialist lanes | Preserves existing authority boundaries while adding synthesis and tradeoff clarity | Replace current lane model with a fixed council |
| 2026-05-08 | Prefer isolated seat reviews plus centralized synthesis in v1 | External guidance supports parallel fan-out/gather for review tasks and cautions against overly free-form multi-agent interaction | Open debate among councilors before synthesis |
| 2026-05-08 | Use `reality-checker` as the pragmatist seat before inventing a new generic reviewer | The repository already has a role that challenges assumptions, reversibility, and risk posture | Create a new `pragmatist-reviewer` role immediately |
| 2026-05-08 | Split council synthesis from lifecycle coordination via a dedicated council-moderator role | Keeps wave governance and deliberative judgment separate, reducing bias toward momentum and matching structured evaluator patterns better | Reuse `wave-coordinator` as the synthesizer |
| 2026-05-08 | Use phase-specific council templates | Pre-implementation plan review and post-implementation delivery review need different evidence and sometimes different seats | One static five-seat roster for all phases and project decisions |
| 2026-05-08 | Cap v1 council at 5 seats (four fixed + one rotating) | Synthesis quality degrades faster than review quality improves beyond 5 seats; the rotating seat handles domain variation without growing the roster | 3 seats (too thin — loses either domain coverage or fixed-seat balance); 7 seats (synthesis cost outweighs marginal review gain) |
| 2026-05-08 | Include split-phase seating in v1; defer promoted rotating seat | Split-phase seating (readiness and delivery passes may use a different rotating fifth seat based on phase-specific evidence) is low-complexity and makes the two-phase model meaningfully more useful — the risk profile at plan time often differs from delivery time. Promoted rotating seat (moderator requests a second rotating seat for cross-cutting waves, capped at 6) is only warranted in genuinely complex multi-domain waves; deferring avoids over-engineering the v1 seat model and can be added cleanly in a follow-up wave or defined as an opt-in for very complex scenarios. | Bring both into v1 (unnecessary complexity for common cases); defer both (misses an easy win with split-phase) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The council becomes a cosmetic summary layer that duplicates existing reviews without improving decisions | Require phase-specific inputs, verdict shape, and explicit tradeoff synthesis tied to wave artifacts |
| The council is mistaken for permission to waive blocking specialist findings | State non-waiver rules in config, prompts, and lifecycle diagnostics; add regression tests |
| A fixed five-seat council forces irrelevant reviewers into low-risk waves | Use one rotating domain seat rather than five fixed specialist seats |
| Free-form inter-agent debate increases token cost and unpredictability without improving outcomes | Keep v1 on independent reviews plus synthesis only |
| Tooling and prompt surfaces drift, causing inconsistent council enforcement | Land seed, local-doc, server, and test changes as one coordinated change set |
| Lifecycle and council responsibilities blur, making ownership ambiguous | Seed a dedicated council-moderator role and keep wave-coordinator focused on routing, gating, and artifact state |
| `reality-checker` role is unavailable in target repositories because it is not seeded | Seed `reality-checker` canonically in this wave — it is a fixed council seat and cannot be assumed present |
| Rotating fifth-seat selection is under-specified, leading to inconsistent seat choices across operators | Define trigger criteria explicitly in the council contract before writing any prompt or template that references the rotating seat |
| Evidence recording location is ambiguous, causing wave.md structure to vary across waves | Lock the section name and placement before any lifecycle tooling or prompt wording references it |
| Waves already in progress at ship time have no clear council obligation, creating ambiguity at Review/Close | Define and document the transition policy explicitly — recommended: council applies from next Prepare forward only |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
