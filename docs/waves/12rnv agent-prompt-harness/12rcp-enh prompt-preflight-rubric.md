# Prompt Preflight Rubric and Ambiguity Routing

Change ID: `12rcp-enh prompt-preflight-rubric`
Change Status: `implemented`
Owner: wave-coordinator
Status: implemented
Last verified: 2026-05-19
Wave: `12rnv agent-prompt-harness`

## Rationale

The best parts of the reviewed prompt guidance are short, reusable operating questions that prevent agents from guessing too early: what is the state, what is owned, what breaks, how wide is the blast radius, what order matters, and what still remains uncertain. Wavefoundry already has scattered versions of this guidance in `020-run-contract`, role docs, and review lanes, but the language is not yet consolidated enough to reliably improve every individual agent prompt.

This change adds a compact **prompt preflight rubric** to the shared run contract and threads it through the role docs that most benefit from it. The goal is not to add more process gates. The goal is to make the existing framework easier for agents to use correctly under ambiguity.

The proposed language is intentionally operational rather than aspirational. It should help an agent do four things quickly:

1. establish what evidence exists and what is still inference
2. identify the owned boundary and the likely failure modes
3. choose the smallest correct next action instead of over-expanding
4. state confidence and verification needs before claiming success

That makes the rubric useful in planning, implementation, review, and council synthesis without introducing a new lifecycle concept.

## Proposed Shape

The final wording should be short enough to be reused verbatim across seeds and role docs. A good fit would look like this:

- **Evidence first:** use repository evidence as the source of truth; separate facts, inferences, and unknowns.
- **Own the boundary:** say which file, module, prompt surface, or lifecycle step owns the change.
- **What breaks:** name the failure mode, blast radius, or regression if the change is wrong or removed.
- **Order matters:** identify ordering, dependency, or readiness constraints before acting.
- **State uncertainty:** surface assumptions explicitly and say what remains unverified.
- **Verify before declaring done:** describe what would count as proof the change actually solved the problem.

The role-specific follow-up language should be similarly compact:

- planner: prefer one precise clarifying question when a core assumption is not grounded in evidence
- implementer: restate current behavior, why the change is needed, the smallest correct change, and the post-change verification
- reviewer / council: ask what breaks, what is evidenced, what is still uncertain, and whether the proposed change is the smallest correct one for the stated problem

This belongs in the existing framework because it reinforces rules Wavefoundry already uses:

- `020-run-contract.prompt.md` already requires scoped-work triage, explicit assumptions, smallest correct change, and post-change verification
- the role docs already separate planning, implementation, and review responsibilities
- the public prompt surface already routes operators through lifecycle-aware commands rather than ad hoc behavior

The feature simply turns those scattered expectations into a shared preflight habit.

## Requirements

1. Add a short prompt preflight rubric to `.wavefoundry/framework/seeds/020-run-contract.prompt.md` covering:
   - evidence available and source of truth
   - state ownership and boundary responsibility
   - blast radius and what breaks if the change is wrong or removed
   - ordering / timing dependencies
   - assumptions, unknowns, and confidence level
   - verification expectation before declaring success
2. Add explicit ambiguity routing language to the role docs that most often decide or execute work:
   - `docs/agents/planner.md` must prefer one precise clarifying question when a core assumption is not grounded in evidence.
   - `docs/agents/implementer.md` must restate current behavior, why the change is needed, the smallest correct change, and post-change verification.
   - `docs/agents/code-reviewer.md`, `docs/agents/qa-reviewer.md`, and `docs/agents/council-moderator.md` must use the same rubric to ask what breaks, what is evidenced, and what remains uncertain before signoff or synthesis.
3. If needed for generated surfaces, update `050-agent-entry-surface-bootstrap.prompt.md` or `docs/prompts/index.md` with a concise cross-reference so the public prompt surface reflects the rubric without duplicating the whole contract.
4. Keep the language generic and lifecycle-aware. Do not introduce product-specific examples, new gates, or new review roles.
5. Preserve the existing wave methodology: document → admit → Prepare wave for any repository-code or framework-seed edits. This feature only changes the prompt guidance that drives those edits.

## Scope

**Problem statement:** Core prompt guidance for individual agents is good but fragmented. The framework already values evidence, smallest correct change, and explicit uncertainty, but those concepts are not yet packaged as a single preflight habit that every role can reuse.

**In scope:**

- `.wavefoundry/framework/seeds/020-run-contract.prompt.md`
- `docs/agents/planner.md`
- `docs/agents/implementer.md`
- `docs/agents/code-reviewer.md`
- `docs/agents/qa-reviewer.md`
- `docs/agents/council-moderator.md`
- `050-agent-entry-surface-bootstrap.prompt.md` and/or `docs/prompts/index.md` if required for prompt-surface propagation
- Optional follow-through in generated surfaces if the bootstrap seed needs a one-line reference to the rubric

**Out of scope:**

- New lifecycle gates or new wave roles
- Product-runtime code changes
- Product-specific prompt examples
- Rewriting unrelated prompt surfaces that do not benefit from the rubric

## Acceptance Criteria

- AC-1: `020-run-contract.prompt.md` contains a compact preflight rubric that a downstream agent can apply before acting.
- AC-2: `planner.md` and `implementer.md` contain explicit ambiguity-handling language aligned with the rubric.
- AC-3: `code-reviewer.md`, `qa-reviewer.md`, and `council-moderator.md` use the same rubric to ground review and synthesis in evidence, blast radius, and unresolved assumptions.
- AC-4: The public prompt surface (`docs/prompts/index.md` and any required bootstrap seed) reflects the rubric or cross-references it clearly.
- AC-5: `docs-lint` passes on all edited `docs/` and seed files.
- AC-6: The change remains generic, compact, and consistent with the current Wavefoundry lifecycle vocabulary; it does not introduce a new process gate or duplicate the full run contract in every role doc.
- AC-7: The change document is detailed enough that a reviewer can approve the eventual implementation without reopening the original gist discussion.

## Tasks

- [x] Update `020-run-contract.prompt.md` with the preflight rubric
- [x] Update `planner.md`, `implementer.md`, and the relevant reviewer docs with role-specific phrasing
- [x] Update prompt-surface index/bootstrap guidance if needed for propagation
- [x] Run docs validation
- [x] Keep the wording short and reusable; avoid bespoke examples unless a role doc truly needs one
- [x] Verify the final wording does not conflict with the existing stage gate, brownfield pattern detection, or explicit-assumption rules

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| run-contract-rubric | implementer | Prepare wave | seed edit required |
| role-guidance-refresh | implementer | run-contract-rubric | planner / implementer / reviewer docs |
| surface-propagation | implementer | role-guidance-refresh | only if `050` or `docs/prompts/index.md` need a touch |
| verify | qa-reviewer | all | docs-lint |

## Serialization Points

- `020` should land before the role docs that reference it.
- If public prompt-surface text changes, update the generated surface guidance in the same change set.

## Affected Architecture Docs

N/A — this is prompt-surface and role-guidance work only. No runtime architecture boundary changes are expected.

## AC Priority

| AC | Priority | Rationale |
| --- | -------- | --------- |
| AC-1 | required | Shared run-contract anchor |
| AC-2 | required | Role-specific ambiguity routing |
| AC-3 | required | Reviewer and synthesis alignment |
| AC-4 | important | Keeps public prompt surface in sync |
| AC-5 | required | Standard docs gate |
| AC-6 | required | Change must not introduce new process gates or duplicate contract language |
| AC-7 | important | Change doc completeness for reviewer sign-off without rework |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-19 | Change doc created from prompt guidance review. | user request |
| 2026-05-20 | Implemented: seed-020 preflight rubric section added; `planner.md`, `implementer.md`, `code-reviewer.md`, `qa-reviewer.md`, `council-moderator.md` updated with role-specific rubric language. | implementer |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-19 | Keep the feature inside the existing `12rnv` prompt-harness wave | The request fits the same framework area and reuses the same seed/role surfaces | Open a separate wave (rejected: would duplicate the same prompt-harness workstream) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| The rubric becomes redundant with nearby guidance | Keep it short and use it as a cross-cutting preflight habit, not a new process layer |
| Role docs drift from the shared run contract | Anchor the wording in `020` first, then propagate the same phrasing to the roles |
| The rubric gets too long to reuse | Limit it to a compact checklist and keep role-specific text to one or two sentences each |
| The public surface ends up duplicating the full contract | Keep `docs/prompts/index.md` to a cross-reference only unless a stronger pointer is necessary |

## Session Handoff

Implemented. See `docs/agents/session-handoff.md` for current wave state and closure tracking.
