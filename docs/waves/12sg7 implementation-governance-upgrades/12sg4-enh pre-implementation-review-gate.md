# Formal Pre-Implementation Review Gate

Change ID: `12sg4-enh pre-implementation-review-gate`
Change Status: `complete`
Owner: wave-coordinator
Status: complete
Last verified: 2026-05-21
Wave: `12sg7 implementation-governance-upgrades`

## Rationale

Wavefoundry already has a strong readiness model:

- `Prepare wave` is the stage gate before implementation.
- readiness selects lanes and records AC priority.
- when enabled, Wave Council already runs a readiness pass before implementation.

But there is still a practical gap between “readiness passed” and “the first code edit begins.” Right now the framework does not define a distinct, formal **pre-implementation review** whose job is to answer:

1. do we actually have enough information to implement successfully,
2. what is most likely to fail once implementation starts,
3. what missing evidence, ambiguity, or dependency would cause churn or rework if we proceed now.

That gap matters because readiness often proves the wave is admissible, while implementation success depends on a tighter question: is the implementation packet complete enough that the team can start coding without avoidable rediscovery, silent assumptions, or immediate re-planning.

This change adds a formal pre-implementation review gate, including a structured **pre-mortem** step and a council-backed synthesis, so implementation begins only after the wave has been challenged from the perspective of likely failure.

## Requirements

1. The framework must define a formal **pre-implementation review** checkpoint that occurs after `Prepare wave` and before the first implementation edit.
2. The framework must decide and document whether this is:
   - a new first-class lifecycle shortcut, or
   - the mandatory first phase inside `Implement wave`.
   The contract must be unambiguous either way.
3. The pre-implementation review must include a structured **pre-mortem** step: assume the implementation failed or produced avoidable churn, then identify the most likely causes before coding starts.
4. The pre-implementation review must confirm that the implementation packet is complete enough to begin. At minimum it must verify:
   - admitted change docs are complete and current
   - required lanes are selected
   - AC priority is recorded
   - relevant architecture/spec/context docs are identified
   - key unknowns, dependencies, and risk areas are named
   - implementation scope and serialization points are clear
   - the evidence needed for likely risky areas is actually present
5. The pre-implementation review must produce a recorded verdict in the wave record distinct from ordinary `Prepare wave` completion, so later reviewers can tell whether the wave was only prepared or also passed the pre-implementation gate.
6. When `wave_council_policy.enabled` is true, the framework must define how council participates in this gate. At minimum one of the following must be made canonical:
   - the existing readiness council expands to include pre-mortem obligations and a separate recorded pre-implementation verdict, or
   - a second pre-implementation council synthesis occurs after `Prepare wave` and before coding.
7. The pre-implementation gate must explicitly test for implementation readiness from a failure-first perspective, including:
   - likely misunderstanding of scope
   - missing codebase understanding
   - missing dependency or ordering knowledge
   - missing test strategy
   - hidden trust, data, or interface assumptions
   - missing review lanes or specialist builder lanes
8. `Implement wave` and `Implement feature` surfaces must block the first edit until this pre-implementation review has passed or has been explicitly folded into the first implementation step and completed there.
9. The pre-implementation review must be tied to the implementation plan itself. Before the first edit, the coordinator must confirm that:
   - the ordered lane sequence is grounded in evidence,
   - the likely failure points have been challenged,
   - the packet includes enough context for the assigned implementers/reviewers.
10. The framework must preserve the distinction between:
   - planning,
   - readiness,
   - pre-implementation review,
   - implementation,
   - delivery review.
   These phases may be adjacent, but must not be collapsed conceptually.
11. Review and closure surfaces must recognize the new checkpoint and reconcile it later if implementation revealed that the pre-implementation review missed important risks or information gaps.
12. Wavefoundry-local docs must explain this gate in a way that makes it operational rather than ceremonial: the purpose is to reduce failed starts, rework, and assumption-driven coding.

## Scope

**Problem statement:** The framework has a readiness gate, but no formal last review focused specifically on whether implementation is about to fail due to missing information or unchallenged assumptions.

**In scope:**

- Prompt/seed changes that define a formal pre-implementation review gate
- Council/readiness contract changes needed to accommodate the new gate
- Role-doc and coordinator-contract updates
- Wavefoundry-local docs updates that explain when and how this gate runs

**Out of scope:**

- Replacing `Prepare wave`
- Replacing delivery review or closure review
- Adding runtime automation beyond documentation and workflow surfaces
- Product-specific failure-mode logic outside the generic framework contract

## Acceptance Criteria

- [x] AC-1: The framework defines a formal pre-implementation review checkpoint that runs after `Prepare wave` and before coding begins.
- [x] AC-2: The checkpoint includes a required pre-mortem step focused on likely implementation failure modes, churn, and missing evidence.
- [x] AC-3: `Implement wave` / `Implement feature` surfaces block the first edit until the pre-implementation review is complete.
- [x] AC-4: The coordinator contract records a distinct pre-implementation verdict in the wave record or an equally explicit canonical artifact.
- [x] AC-5: The council/readiness contract is updated so the new gate has a clear relationship to `wave-council-readiness` when council policy is enabled.
- [x] AC-6: The framework explicitly requires this gate to confirm that the implementation packet contains enough information to succeed, not just enough to admit the wave.
- [x] AC-7: Wavefoundry-local docs and prompts explain the new gate clearly enough that later agents can distinguish it from ordinary readiness and ordinary delivery review.

## Tasks

- [x] Update `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` so the first implementation phase is a formal pre-implementation review gate or routes to a separate gate before first edit
- [x] Update `.wavefoundry/framework/seeds/100-project-prompt-surface-bootstrap.prompt.md` so generated `prepare-wave`, `implement-wave`, and related prompts describe the new checkpoint clearly
- [x] Update `.wavefoundry/framework/seeds/001-feature-wave-framework-overview.md` so the lifecycle model reflects the added gate — assessed seed-002; no contradictory language; no change required.
- [x] Update council/readiness surfaces as needed — updated `215-council-moderator.prompt.md` with Relationship To Pre-Implementation Review Gate section; updated `seed-100` `implement-feature + implement-wave` with lifecycle sequence.
- [x] Update Wavefoundry-local docs and prompt surfaces: `docs/prompts/prepare-wave.prompt.md` (readiness verdict clarification + lifecycle sequence), `docs/prompts/implement-wave.prompt.md` (Pre-Implementation Review Gate section), `docs/prompts/review-wave.prompt.md` (pre-implementation gate reconciliation at review).
- [x] Update review/closure docs so the new checkpoint is later reconciled when implementation exposed missed risks — covered by review-wave.prompt.md Pre-Implementation Gate Reconciliation section.
- [x] Run framework verification and docs validation

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| implementation-gate-contract | implementer | Prepare wave | `180`, `100`, lifecycle wording |
| council-and-readiness | implementer | implementation-gate-contract | `215`, readiness/council relationship |
| wf-self-host-surfaces | implementer | implementation-gate-contract | Local prompts + contributing docs |
| verify | qa-reviewer | all | Framework tests + docs validation |

## Serialization Points

- The `180` / `100` implementation-contract wording should stabilize before council or self-hosted docs are updated.
- The relationship between `Prepare wave`, council readiness, and the new gate must be decided once and propagated consistently.

## Affected Architecture Docs

N/A — this is a lifecycle and execution-contract change, not a runtime architecture change.

## AC Priority

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The formal gate is the core deliverable |
| AC-2 | required | The pre-mortem is the main new behavior |
| AC-3 | required | The checkpoint must actually block the first edit |
| AC-4 | required | The verdict must be durable and reviewable later |
| AC-5 | required | Council interaction must be explicit, not implied |
| AC-6 | required | The information-sufficiency test is the point of the change |
| AC-7 | important | Repo-local clarity prevents the gate becoming ceremonial |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-21 | Change doc created after reviewing the current `Prepare wave`, `Implement wave`, council-readiness, and review/closure surfaces. | Operator request + repo inspection |
| 2026-05-21 | Prepare wave completed; change marked ready for implementation in `12sg7`. | `docs/waves/12sg7 implementation-governance-upgrades/wave.md` |
| 2026-05-21 | Implementation complete. Decision: implement as mandatory first phase of `Implement wave` (not a separate lifecycle command) to avoid ceremony without signal. Added "Pre-implementation review gate" section to `seed-180` with 3-step protocol (pre-mortem, packet completeness check, verdict format). Updated `seed-100` implement-feature+implement-wave and implement-wave rules with lifecycle sequence and gate requirement. Updated `seed-001` lifecycle step 3 description and implementation rule. Added "Relationship To Pre-Implementation Review Gate" section to `seed-215`. Updated local prompt surfaces: `prepare-wave.prompt.md` (readiness verdict clarification), `implement-wave.prompt.md` (Pre-Implementation Review Gate section), `review-wave.prompt.md` (Pre-Implementation Gate Reconciliation section). Docs-lint clean, 1497 tests pass. | `seed-180`, `seed-100`, `seed-001`, `seed-215`, `docs/prompts/` edits |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-21 | Treat this as a distinct checkpoint between readiness and coding, even if implemented as the first phase of `Implement wave` | The missing behavior is a last review before first edit, not more planning or more delivery review | Expand `Prepare wave` only, with no distinct boundary |
| 2026-05-21 | Require a pre-mortem rather than a generic “double-check” | Failure-first review is the actual signal needed before implementation starts | Add a softer checklist with no adversarial framing |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The new gate duplicates `Prepare wave` and becomes ceremonial | Define the distinction clearly: readiness admits the wave; pre-implementation review challenges whether implementation is about to fail |
| Council/readiness wording becomes inconsistent across prompts | Decide the contract centrally in `180` / `100` / `215` and propagate from there |
| The extra gate slows down trivial work disproportionately | Keep the gate bounded to implementation-readiness evidence and likely failure modes rather than reopening full planning |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
