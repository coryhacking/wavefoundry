# Decide whether one-sentence changes get a lighter lifecycle lane

Change ID: `2136q-change small-change-lane`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-10-18
Wave: TBD

## Rationale

The Claude Code best-practices guide says planning "adds overhead", and "If you could describe the diff in one sentence, skip the plan."

The framework does the opposite on purpose. Seed 020:17 says "The lifecycle gate does not scale with perceived scope." Every code edit needs a change doc, wave admission, and readiness with `council-readiness`. Then come delivery review, operator signoff and close. Mechanical enforcement sits at activation (`council_signoff_gate`, `lifecycle_gates.py:980`, and `wf_implement_wave_response`). The edit hook does not enforce the stage gate.

Recent waves show the cost:
- **210e9:** four test files changed. It took a full readiness council with four lanes, delivery lanes, signoff and close.
- **210eb:** a two-line filter. Same cycle.
- **2136j:** an alias deletion. It has been through readiness and delivery review and is awaiting signoff and close.

The operator has reported that wave 1yxyw took about three hours, with the lesson "size plans to the change". That is an operator report; it has no checked-in record.

Lighter paths that already exist:
- the operator-approved waiver for a named scope (`AGENTS.md` Stage Gate; seed 050:122);
- review-depth scaling: targeted delivery Council, the red-team `lightweight` tier, and focused re-review.

No path reduces the readiness council or the lane count for a trivially small change.

This change records the decision. **It is a framework policy change for every target, and it is the operator's call.** Run it through **Evaluate decision** before any implementation is planned.

## Requirements

1. Record a decision with **Evaluate decision**, comparing options A and C as its two specific options (seed 176:22). Option B is carried under Alternatives Considered as a "not yet" path (seed 176:106). Outcome: adopt A or keep C; B stays open as a later step.
2. If an option is adopted, write the implementation as a separate change doc, with its own wave and readiness, before any code. This change carries no code.

**Options:**

- **A. A small-change lane, chosen by the operator.** At admission the operator marks a change `small`, and it must also pass mechanical eligibility:
  - a diff declared in one sentence;
  - at most a few files, all in declared paths;
  - no seed, hook, security, release or public-contract path.

  Readiness becomes one code-review lane with no council. Delivery is one code-review lane plus operator signoff. Close, the test receipt and the operator-owned close rule are unchanged.
- **B. Scale the readiness roster only.** The full lifecycle stays, but a change whose declared paths recruit one lane gets that lane alone at readiness, with no multi-lane council. Smaller saving; no new state.
- **C. Status quo.** Use the existing waiver for trivial edits, recorded in the change doc or handoff.

## Scope

**Problem statement:** small changes pay the full readiness and delivery cost.

**In scope:**

- The decision record.
- If adopted, a follow-up change doc.

**Out of scope:**

- Any code or seed edit under this change.

## Acceptance Criteria

- [ ] AC-1: A decision record exists under `docs/architecture/decisions/`, comparing options A and C with costs and risks, and recording B as an alternative. The operator chose the outcome, and the record quotes their words.
- [ ] AC-2: If A is chosen, a follow-up change doc exists with requirements and ACs for it. If C is chosen, the Decision Log says so and no follow-up exists.

## Tasks

- [ ] Run **Evaluate decision** with the operator.
- [ ] Write the decision record.
- [ ] Plan the follow-up change, or record the status quo.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| decision | operator, architect | none | Requirement 1 |

## Serialization Points

- `docs/architecture/decisions/`

## Affected Architecture Docs

`docs/architecture/decisions/` gains the decision record. If option A is adopted later, `docs/architecture/data-and-control-flow.md` (lifecycle flow) changes under the follow-up.

## AC Priority

| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The decision is the deliverable. |
| AC-2 | required | The outcome must be acted on or closed off. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-18 | Planned from the best-practices review. Existing light paths and enforcement points were identified. | Guru investigation |
| 2026-10-18 | Plan review: the claims were verified. Revised to the A-versus-C shape that seed 176 expects, with B as an alternative. The waiver citation was corrected, and the 1yxyw figure is labelled an operator report. | Fable plan review |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | -------- |
| 2026-10-18 | Plan as a decision, not as code. | It reverses a stated framework principle (020:17) for every target. | Implement option A directly; skips the decision the operator owns. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Agents route real work into a light lane. | Option A requires the operator's mark plus mechanical eligibility. The agent cannot choose it alone. |
| Fewer reviews let defects through. | Under A, the test receipt, the close gate and one code-review lane remain, and the eligibility rules exclude seed, hook, security, release and public-contract paths. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
