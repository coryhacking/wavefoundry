# Challenge apparent tradeoffs in plan review

Spec ID: `24c3q-enh challenge-false-tradeoffs-in-plan-review`
Spec Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-11-25
Wave: 24c3o review-comprehension-isolation-and-contract-drift

## Rationale

Plan spec already compares alternatives. A review can still accept a false choice when every alternative shares the same unnecessary assumption.

## Product Intent

A planner learns whether two valuable outcomes can coexist and what a combined option would cost. When a proposed readiness repair would undo an earlier repair, the operator sees the competing outcomes and the evidence needed to choose.

## Requirements

1. During the existing optional Review plan, when a real conflict affects the decision, name both outcomes and the assumption that puts them in conflict.
2. Try one concrete way to remove the assumption. Compare its cost, risk and residual limits with the original options. Record the reason when the constraint still binds or evidence is missing.
3. Use the existing decision log or review response. Route consequential architectural choices through Evaluate decision when appropriate. Skip this question for straightforward plans.

4. At the existing readiness escalation after focused verification, compare the proposed repair with the applied repair. If it would undo the earlier outcome, identify both requested outcomes, cite the finding or repair evidence for each, and state the decision the operator needs to make before further work.

## Scope

Use the existing optional plan review and the bounded readiness handoff. The operator retains authority over another repair round.

## Acceptance Criteria

- [x] AC-1: For a fixture requiring human-visible summaries and one machine sentinel, the review identifies the audiences and evaluates separate human output and terminal output, including a compatibility cost.
- [x] AC-2: A fixture with a genuinely binding constraint records why it binds. A straightforward fixture finishes without inventing a tradeoff or requiring a brainstorming round.
- [x] AC-3: Given an applied repair that preserves a primary-only scan warning and a later proposal that removes that warning to suppress a duplicate summary, the readiness handoff identifies the lost warning, cites the evidence for both requests and asks which behavior the next repair must preserve. It waits for operator direction. In a control that removes only the duplicate and retains the warning, the handoff raises no reversal.

## Tasks

- [x] Add the conditional question to the canonical Review plan seed and self-hosted prompt.
- [x] Reuse the upgrade-summary example for one short walkthrough. Vary the constraint in the same example to check when to offer an alternative and when to move on.
- [x] Update the council-chair readiness guidance and both Prepare wave prompts. Use the same walkthrough to compare a repair that drops the warning with one that preserves it. Record the handoff once and identify which edit triggers it.

## Agent Execution Graph

1. Implementer updates the named guidance or qualification procedure.
2. The assigned reviewer checks the observations against the acceptance criteria during normal delivery review.

## Serialization Points

- `.wavefoundry/framework/seeds/175-review-plan.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/review-plan.prompt.md`
- `docs/prompts/review-plan.prompt.md`
- `.wavefoundry/framework/seeds/215-council-chair.prompt.md`
- `.wavefoundry/framework/install/lifecycle-prompts/prepare-wave.prompt.md`
- `docs/prompts/prepare-wave.prompt.md`

## Affected Architecture Docs

N/A. This change extends an existing workflow within its current authority.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the stated outcome or its scope boundary. |
| AC-2 | required | Establishes the stated outcome or its scope boundary. |
| AC-3 | required | The operator needs evidence of what a reversal would undo before authorizing more work. |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-11-25 | Planned for wave admission. | Requirements and acceptance criteria above. |
| 2026-11-25 | Operator included repair reversals in this wave. | Requirement 4 and AC-3. |

An independent reader followed the delivered Review plan and Prepare prompts on one synthetic upgrade. A parser that counts sentinels permits ordinary primary and cleanup messages and one final footer. A parser that accepts only a single fixed record on its sole channel requires a compatibility decision. A spelling correction needed no decision. In the readiness handoff the reader cited the earlier repair P (restore the primary warning) and proposal F (suppress the entire primary output), named the warning that would disappear and asked what the next repair must preserve. Removing only the duplicate footer, F2, preserved P and went through the ordinary handoff.

The docs-contract reviewer verified the ADR referral on the seed, install and self-hosted prompts. Each offered the existing decision workflow and waited for operator choice. All three rejected the immediate-launch, missing-choice and ordinary-log-only controls.

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-11-25 | Extend optional plan review. | Plan spec already compares alternatives. A review can still accept a false choice when every alternative shares the same unnecessary assumption. | Repeating the divergent pre-plan adds work. A dedicated brainstorm skill fragments the existing entry points. |

## Risks

A combined option can hide cost. Require the reviewer to identify who bears it.

## Session Handoff

See the wave record for coordination.
