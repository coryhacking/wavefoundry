# 180 - Implement Feature (Shortcut)

Use this when you want a single command-style request such as:

- `Prepare wave`
- `Implement wave`
- `Execute wave`
- `Implement feature`
- `Implement enhancement`
- `Implement bug`
- `Implement refactor`
- `Implement reliability change`
- `Implement security change`
- `Pause wave`
- `Review wave`

Intent:

- Ready and execute the active wave — evaluate its admitted changes, coordinate agents and reviews, and drive the implementation-review loop until the wave is **closure-ready**. **Do not** perform **terminal closure** (completed `Status`, `Completed at`, closure-only plan/handoff reconciliation) unless the operator **explicitly confirms** closure in the current request (e.g. **`Close wave`**, **`Finalize feature`**, or a clear yes after you ask). See `docs/prompts/implement-wave.prompt.md` and `docs/prompts/close-wave.prompt.md`.

Core execution model:

- the wave is the delivery unit; the coordinator implements all admitted changes together as a cohesive set
- the coordinator is the wave coordinator for the active wave; review and handoff actions do not create a separate execution authority
- the coordinator runs or confirms the wave-readiness evaluation before allocating implementer and reviewer lanes
- the coordinator uses that evaluation to decide which implementer, reviewer, and persona agents must participate for the active wave
- the active wave contains one or more changes; each change may include optional tasks/subtasks when finer tracking is useful
- the coordinator decides which agents work on which admitted changes or tasks and in what order
- blocking review findings send the wave back into implementation until the required lanes are clean
- **`Review wave`** is the operator shortcut for running or reconciling required reviewer lanes **during** this same implementation phase; it shares the coordinator contract with **`Implement wave`** and must not be treated as “only for closure” unless every required lane is already clean or explicitly deferred with recorded rationale
- scoped **work** is done when all admitted changes are implemented and required reviews are clean, or changes are explicitly deferred, moved, or superseded — **formal wave closure** (terminal metadata and closure artifacts) still requires **operator-confirmed** `Close wave` / `Finalize feature` per project prompt docs (for example `docs/prompts/` and `AGENTS.md`)
- the committed result is the wave as a whole — individual changes do not ship outside a wave
- incomplete changes carry forward into the next wave under the same `Change ID`; create a new change only when the remaining work is materially different and that split is made explicit

Implement loop execution model:

The coordinator's implementation loop follows a ReAct-derived model. Each iteration is explicit and auditable:

- **Thought** — before every lane invocation, record a `Thought:` entry in `## Progress Log` stating *why* this action now (not just what). This is a required step, not optional narration.
- **Action** — invoke a single, scoped lane (implementer task, reviewer lane, or persona lane) with defined inputs.
- **Observe** — record the lane's output as an `Observe:` entry before the next Thought. When lanes ran concurrently, record a single merged `Observe:` synthesizing all outputs before the next Thought.
- **Reflect** — after any blocking finding, record a `Reflect:` entry identifying the root cause pattern and any remaining tasks that should be updated proactively to prevent the same class of finding recurring in this wave.

Loop levels — the finding type, not severity alone, determines which level activates:

- **Level 1 (Micro):** edit → test → observe → fix, entirely internal to the implementer sub-agent. No Progress Log entry required. Does not involve the coordinator.
- **Level 2 (Reviewer loop):** implement task(s) → invoke reviewer lane(s) → CRITIC evaluation → fix → re-invoke. Stays within the implementation phase. `Prepare wave` does not re-run. This is the default for findings that do not invalidate an acceptance criterion.
- **Level 3 (Wave lifecycle):** a finding invalidates an acceptance criterion, contradicts the approved plan, crosses an architecture boundary, or reveals scope or requirement ambiguity the coordinator cannot resolve. Coordinator stops, surfaces to operator, routes to `Plan feature` or re-`Prepare wave` before continuing.

Finding escalation — apply this table before deciding which loop level to activate:

| Finding type | Level | Coordinator action |
|---|---|---|
| Code quality, style, formatting | 2 | Fix in place, re-run reviewer lane |
| Missing test coverage | 2 | Add tests, re-run qa-reviewer |
| Logic error, missing behavior | 2 | Fix, re-run affected lanes |
| Scope creep discovered during implementation | 3 | Stop, update change doc, operator resolution, re-Prepare |
| Finding invalidates an acceptance criterion | 3 | Stop, surface to operator, route to Plan feature or re-Prepare |
| Architecture boundary violation | 3 | Stop, route to architecture-reviewer + operator, re-Prepare |
| Requirement ambiguity blocking implementation | 3 | Stop, operator resolution, update change doc, re-Prepare |
| Accepted tradeoff with recorded rationale | Exit loop | Record in change doc, continue |

CRITIC evaluation — after each review cycle, before deciding which loop level to activate:
- For each finding, evaluate: does this invalidate any acceptance criterion in the change doc?
- Early exit on first match — if yes, escalate to Level 3.
- If no finding matches any criterion, route to Level 2.
- "All reviewer lanes clean" alone is not the exit condition for the implement loop; all acceptance criteria met is.

Parallel lane merge — when reviewer or persona lanes with no shared dependencies run concurrently:
- The coordinator invokes them together (one Action per concurrent set).
- The coordinator records a single merged `Observe:` synthesizing all lane outputs before the next `Thought:`.
- The coordinator does not act on partial findings from one lane while others are still running.

Wave plan — extends the operator-approval checkpoint (see Machine-usable execution expectations below):
- Before the first edit, the coordinator produces an ordered lane sequence: which lanes run in which order, with what scoped inputs, for each serialization unit.
- This plan is what the operator approves before implementation begins — not just a list of files, but an ordered execution sequence.
- Deviations from the plan are named `Deviation:` events recorded in Progress Log, not silent reorderings.

Wave orchestration contract:

- **Admission:** the coordinator confirms which changes, feature slices, review lanes, and integration lanes are admitted into the current wave
- **Allocation:** the coordinator assigns ownership, start order, dependency constraints, and parallel lanes for the admitted changes or tasks
- **Synchronization:** participants report outputs, blockers, invalidated assumptions, and review findings often enough for the coordinator to keep the wave coherent
- **Escalation:** the coordinator pauses, replans, adds reviewers, reassigns changes or tasks, splits work, or supersedes the wave when assumptions fail or dependencies shift materially
- **Closure readiness:** the coordinator decides when scoped work and required reviews are satisfied; **terminal closure** (e.g. `Completed at`, `Status: completed`, closure reconciliation) runs only after **explicit operator confirmation** (`Close wave` / `Finalize feature` or confirmed yes), not automatically at the end of `Implement wave`

Coordinator decision rights:

- admit or reject changes into the active wave
- assign or reassign changes, tasks, and workstreams
- control which work may begin in parallel
- require added review or persona participation
- declare the wave not ready and block implementation until prerequisites are satisfied
- activate or skip factor-specific review subagents based on project fit, platform support, and the active wave's scope
- fall back to factor-specific review lanes when the platform does not support the needed subagent model cleanly
- mark changes or tasks as deferred, moved, retried, blocked, or complete
- decide whether incomplete work remains part of the same change or must be split into a new change with explicit rationale
- return to planning when the current wave no longer matches the approved understanding

Machine-usable execution expectations:

- do not edit product implementation source in the repository until a consolidated change plan document exists **and** implementation readiness is satisfied per that project’s `AGENTS.md` (or equivalent entry guard); wave execution must treat a clean `Prepare wave` / `Ready wave` evaluation as the review gate before the first product-code edit unless the operator records an explicit scoped waiver
- after `Prepare wave` passes clean and before the first product-code edit: **stop, present the wave plan to the operator, and wait for explicit approval**; the plan must state which files will be changed and how, which tests will be added and what cases they cover, and any open risks or questions; do not treat the `Implement wave` invocation itself as approval to begin coding immediately
- before the first product-code edit, map intended code changes to the admitted scope, acceptance criteria, and planned verification. For bug fixes, prefer a reproducer test or equivalent failing proof before the fix when feasible; when infeasible, record the substitute evidence and why.
- preserve stable `wave-id` and `Change ID` references when updating wave state
- keep the wave artifact rooted at `docs/waves/<wave-id>/`, where the `wave-id` uses the shared Crockford lifecycle prefix plus the summary slug that best reflects the admitted changes
- before setting `Activated at`, review the admitted changes and rename placeholder wave slugs/titles to a descriptive summary while preserving the shared lifecycle prefix and updating references
- treat admitted change docs as already wave-owned before implementation: `Prepare wave` must physically move every admitted change doc from `docs/plans/<change-id>.md` into `docs/waves/<wave-id>/<change-id>.md`, repair references, and remove duplicate staging copies; `Implement wave` assumes that relocation is complete and only performs defensive repair if drift is detected
- set `Activated at` after the activation-time naming review is complete; do not use activation as the primary relocation stage
- set `Completed at` only when the operator has confirmed **`Close wave`** / **`Finalize feature`** (or equivalent explicit confirmation) and the coordinator has reconciled all scoped changes — not at the end of **`Implement wave`** alone
- generate or confirm the final wave summary title/slug at closure so the archived wave folder remains human-readable from directory listings
- update change status explicitly rather than implying progress only in narrative prose
- record dependency satisfaction or dependency blockage when it materially changes allocation
- record assumption changes explicitly when they affect execution or review
- leave enough structured state that another coordinator or reviewer can resume without reconstructing the wave from chat alone

Participant responsibilities inside an active wave:

- implementers and reviewers should stay within assigned wave changes unless the coordinator expands their scope explicitly
- participants should report blockers, invalidated assumptions, and meaningful new findings rather than silently compensating for them
- implementers should keep changes direct: do not add speculative abstraction, configurability, or unrelated defensive code beyond what the request, acceptance criteria, or checked-in evidence justifies
- personas should participate at declared challenge, review, or acceptance checkpoints and escalate when domain concerns materially change the wave
- personas selected by readiness evaluation are gating participants for that wave's relevant checkpoints
- factor-review participants should evaluate only the factors relevant to the active wave instead of forcing a full factor checklist into every wave
- when factor subagents are active, the factor reviewer should consolidate their findings into one coherent review output for the wave
- all participants should leave enough state in wave artifacts and journals for another agent to continue safely

Required tasks:

1. Load the active execution plan, spec refs, and wave artifacts. Consult `docs/references/project-context-memory.md` and relevant role journals (`docs/agents/journals/`) for active cautions and known pitfalls that apply to the current wave's scope. If memory records a past mistake in this area, treat it as a constraint on implementation — not a suggestion.
2. Determine whether the next `planned` wave is ready to become `active`.
3. If the selected wave still has a provisional holding name, review the admitted changes and rename the wave slug/title to a descriptive summary before activation.
4. Confirm admitted change docs already live under `docs/waves/<wave-id>/` after `Prepare wave`; if any remain under `docs/plans/`, relocate them now and repair references before continuing.
5. Run `Prepare wave` automatically unless a clean readiness evaluation was the immediately preceding successful lifecycle action for the same wave. `Ready wave` remains an accepted alias.
6. Evaluate the admitted change set and decide which implementer lanes, reviewer lanes, and persona lanes must participate. When any admitted change is a **bug** (`change-id` kind `bug`) or other **product defect fix**, include **`qa-reviewer` at minimum** in the reviewer roster (`docs/contributing/agent-team-workflow.md`, `docs/workflow-config.json` `review_policies.require_qa_reviewer_for_bug_fixes`) unless the operator records an explicit scoped waiver in the wave or change doc.
7. Assign admitted changes, tasks, and review lanes to agents and personas.
8. Confirm the wave roster, allocation rules, dependency rules, readiness checkpoints, and review checkpoints.
9. Before the first edit, produce the wave plan: an ordered lane sequence with scoped inputs per serialization unit. This is the plan the operator approves at the checkpoint in task 8. Record it in the wave's Progress Log as the baseline. Deviations are `Deviation:` events, not silent reorderings.
10. Execute the implement loop per the **Implement loop execution model** above (Thought → Action → Observe → Reflect, with CRITIC evaluation and Level 1/2/3 escalation). Defaults apply as specified there; do not restate them inline. After implementation tasks are complete and before invoking inferential reviewer lanes, run `wave_run_sensors()` if the project has computational sensors configured — fix any sensor failures before proceeding to reviewer lanes.
11. Coordinate execution until the wave objective is satisfied or the wave must be reconsidered.
12. Reconcile partial completions, blocked changes, retries, deferred work, or moved work as execution proceeds.
13. Rerun the readiness evaluation during final review before closure is accepted. After confirming required reviewer lanes are clean and required acceptance criteria are met, run an **AC scope gap check**: surface important/nice-to-have items not in admitted scope that would add value, confirm not-this-scope deferrals, and present a short prioritized list so the operator can decide before closure whether to admit follow-on work or carry it to the next wave. Keep this pass bounded — one list, no full discovery exercise.
14. Update wave artifacts, progress state, reviewer status, change state, dependency state, lifecycle timestamps, and journals. Journal entries belong in the relevant role/persona journal when a durable operating-memory signal appears — role/persona identity clarification, operator directive, high-salience risk, bug caught in review, hard-to-find constraint, reversed decision, invalidated assumption, or confidence-shift. Do not wait until closure to record critical or high-salience signals; capture them when they are fresh. Do not journal tasks that completed normally on the first attempt.
15. Use `seed-200` when starting, readying, updating, splitting, or closing a wave.

Guardrails:

- Do not treat the wave as **merge-ready** (ready to merge implementation to the project's main integration branch or to declare the implementation batch integration-complete) until any **product-owner** **delivery scope sign-off** required by **`seed-100`** **prepare-wave** is recorded in the wave **`## Review checkpoints`** when the wave is product-impacting (**product-owner** not **N/A**).
- Do not perform **terminal wave closure** (completed status, `Completed at`, closure-only index/handoff updates) without **explicit operator confirmation** in the current request; pause and ask when implementation is done.
- Do not activate the next wave without a valid handoff or readiness check.
- Do not begin implementation when the readiness evaluation is missing, stale, or failed.
- Do not modify product implementation directories before the consolidated change document and implementation-readiness requirements in the target project’s `AGENTS.md` are met (single-repo guardrail; waive only with explicit operator scope in the active request).
- **Do not write the first line of product code before the operator has approved the presented implementation plan.** Presenting the plan and receiving approval is a required checkpoint, not optional. `Implement wave` is not implicit approval.
- Do not activate a wave under a placeholder slug when the admitted changes already make a better descriptive name obvious.
- Do not silently widen scope; return to planning when wave findings invalidate major assumptions.
- Do not let participants invent their own coordination model for the wave when the plan already defines coordinator-owned orchestration.
- Do not make unrelated cleanup edits during implementation; remove only code, comments, imports, or branches made obsolete by the current change and report pre-existing cleanup separately.
- Do not let implementation drift away from traceable scope; every edit should map back to the admitted change, acceptance criteria, or cleanup directly caused by the change.
- Do not edit any file explicitly listed in an admitted change doc's in-scope list before `Prepare wave` has passed for the active wave — even when the file is under `docs/` or `agent-workflows/` and would otherwise be exempt from the repository code gate. The wave-admitted surfaces gate in `AGENTS.md` governs those files once they are in scope.
- Lanes do not self-escalate to Level 3; only the coordinator classifies findings and decides loop level after the CRITIC step. A reviewer reporting a finding does not itself trigger re-planning — the coordinator evaluates it against acceptance criteria first.
- Use `Salience / Impact` in meaningful `Reflect:` entries when the finding should affect future behavior, retrieval, reviewer routing, or handoff. Do not use salience for routine status.
