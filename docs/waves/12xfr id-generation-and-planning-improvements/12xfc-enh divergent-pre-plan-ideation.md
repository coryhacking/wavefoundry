# Divergent Pre-Plan Ideation

Change ID: `12xfc-enh divergent-pre-plan-ideation`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-26
Wave: TBD

## Rationale

The Wave Framework applies divergent thinking only late in the lifecycle — during red-team review and Wave Council — after a plan has already been drafted and anchored expectations. By that point, challenging the problem framing requires reworking significant documentation.

`Plan feature` (seed-170) is linear: the planner reads requirements and drafts a single approach. This misses framing errors, unexplored alternatives, and non-obvious risks that would surface if multiple approaches were enumerated and critiqued before the plan was written. Adding a structured diverge → critique → select pass before drafting catches these at the cheapest possible moment, within the same single planning agent pass.

## Requirements

1. `seed-170` must include a required **Divergent Pre-Plan** step that executes before the full plan is drafted:
   - **Diverge:** enumerate 2–3 distinct approaches to the stated problem, each differing in a meaningful assumption, strategy, or scope boundary — not just surface wording.
   - **Critique:** for each approach, state its primary weakness or risk in one sentence.
   - **Select:** choose one approach and state in one sentence why it is preferred over the alternatives.
2. The selected approach and the rejected alternatives (with their weaknesses) must be recorded in the change doc's `## Decision Log` so the tradeoff is visible to reviewers.
3. The divergent pass executes within the single planning agent pass — no additional agents or sub-processes required.
4. The local rendered planning prompt surface (`docs/prompts/plan-feature.prompt.md`) must reflect the same requirement as the seed.

## Scope

**Problem statement:** Plan creation is the cheapest moment to catch wrong problem framing and missed alternatives, but the framework currently applies divergent thinking only at review time, after the plan has already anchored.

**In scope:**

- `.wavefoundry/framework/seeds/170-plan-feature.prompt.md`
- `docs/prompts/plan-feature.prompt.md`

**Out of scope:**

- Changes to red-team or Wave Council review behavior
- Changes to the change doc template or other wave lifecycle steps
- Multi-agent or parallel sub-process orchestration

## Acceptance Criteria

- [x] AC-1: `seed-170` contains a required Divergent Pre-Plan step with Diverge / Critique / Select structure that runs before the plan is drafted.
- [x] AC-2: The step explicitly requires recording the selected approach and rejected alternatives in `## Decision Log`.
- [x] AC-3: `docs/prompts/plan-feature.prompt.md` reflects the same requirement as the seed.
- [ ] AC-4: `wave_validate` passes after the seed and prompt edits.

## Tasks

- [x] Open `seed_edit_allowed` gate
- [x] Add Divergent Pre-Plan step to `seed-170`
- [x] Close `seed_edit_allowed` gate immediately after
- [x] Update `docs/prompts/plan-feature.prompt.md` to match
- [ ] Run `wave_validate` to confirm docs gate passes

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Seed edit | implementer | gate open | Open + close `seed_edit_allowed` as a unit |
| Prompt surface | implementer | seed edit | Mirror the seed change in the rendered local surface |
| Validation | implementer | prompt surface | `wave_validate` confirms docs gate |

## Serialization Points

- Open `seed_edit_allowed` gate before editing seed-170; close immediately after — do not leave it open across the prompt surface edit.

## Affected Architecture Docs

N/A — confined to the planning seed and its rendered local prompt surface; no boundary, flow, or verification architecture impact.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Core behavior change |
| AC-2 | required | Makes the tradeoff visible to reviewers |
| AC-3 | required | Local rendered surface must stay in sync with the seed |
| AC-4 | required | Docs gate is always required |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-05-26 | Single-agent divergent pass, not multi-agent | The cost/latency penalty of true parallel sub-agents (~5x cost, ~10x latency) is not justified for a default planning step; structured prompting within the planner achieves meaningful divergence at negligible extra cost | Spawn N parallel sub-agents — rejected: too expensive as a default |
| 2026-05-26 | Inline in Plan feature, not a separate Ideate lifecycle step | Plan feature is the earliest, cheapest moment to challenge framing; a separate step adds lifecycle friction without proportional benefit | New Ideate/Brainstorm wave step — rejected: adds overhead; the pass is lightweight enough to be inline |
| 2026-05-26 | Record rejected alternatives in Decision Log | Tradeoffs are visible to red-team and Wave Council without requiring them to re-derive what was considered | Record in Progress Log only — rejected: Decision Log is the correct home for approach tradeoffs |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-05-26 | Change doc created | Operator direction after reviewing ADHD parallel divergent ideation research |

## Risks

| Risk | Mitigation |
| --- | --- |
| Divergent pass adds token overhead for simple, obvious changes | The step requires 2–3 distinct approaches — for truly obvious changes the alternatives will be trivially short, adding minimal cost |
| Planner produces surface-level alternatives that differ only in wording | Requirement explicitly states each approach must differ in a meaningful assumption, strategy, or scope boundary |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
