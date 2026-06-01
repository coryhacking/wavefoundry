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
- if the operator requests a follow-up that still belongs to the current wave and the scope fits an admitted change, update that existing change's ACs and tasks instead of opening a new change; create a new change only when the new work is materially different or needs separate tracking
- update checkbox-tracked ACs and tasks as the underlying work actually completes; do not defer the bookkeeping to the end of the wave or wait for closure to mark finished items

Implement loop execution model:

The coordinator's implementation loop follows a ReAct-derived model. Each iteration is explicit and auditable:

- **Thought** — before every lane invocation, record a `Thought:` entry in `## Progress Log` stating *why* this action now (not just what). This is a required step, not optional narration.
- **Action** — invoke a single, scoped lane (implementer task, reviewer lane, or persona lane) with defined inputs.
- **Observe** — record the lane's output as an `Observe:` entry before the next Thought. When lanes ran concurrently, record a single merged `Observe:` synthesizing all outputs before the next Thought.
- **Reflect** — after any blocking finding, record a `Reflect:` entry identifying the root cause pattern and any remaining tasks that should be updated proactively to prevent the same class of finding recurring in this wave.
- **Gapfill** — after all lanes in a phase complete, if any evidence referenced in the briefing packet (per `209-agent-harness-core.prompt.md`) was absent or incomplete, record a `Gapfill:` entry in Progress Log noting what was missing and where it should be added before the next wave. This is a forward-looking record, not a blocking finding.

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
- When multiple lanes produce overlapping findings, the coordinator deduplicates by `finding_id` (per `209-agent-harness-core.prompt.md`) before recording the merged Observe.

Wave plan — extends the operator-approval checkpoint (see Machine-usable execution expectations below):
- Before the first edit, the coordinator assembles a briefing packet per `209-agent-harness-core.prompt.md` required fields (`wave_id`, `phase`, `change_ids`, `trust_boundaries_touched`, `files_in_scope`) as part of the wave plan.
- The coordinator then produces an ordered lane sequence: which lanes run in which order, with what scoped inputs, for each serialization unit.
- This plan is what the operator reviews before implementation begins — not just a list of files, but an ordered execution sequence. An explicit implementation instruction in the current request such as `Implement wave` or `Implement feature` counts as approval to proceed once the plan is surfaced, unless repo-local docs, the active handoff, or a material review-driven packet change creates an explicit hold.
- Deviations from the plan are named `Deviation:` events recorded in Progress Log, not silent reorderings.

Pre-implementation review gate:

This gate is the **mandatory first phase of `Implement wave`** — it runs after the wave plan is assembled and before the first code edit. Its purpose is not to re-do readiness; it is to challenge the wave from the perspective of likely failure and confirm the implementation packet contains enough information to proceed without avoidable churn.

**Step 1 — Pre-mortem:** Assume the implementation was completed and produced avoidable rework, missed a key assumption, or required a re-Prepare. Name the 3–5 most likely causes before writing any code. Use these categories to structure the challenge:
- Misunderstood or ambiguous scope in the change doc
- Missing codebase knowledge (what a symbol does, who calls it, what the dominant pattern is)
- Unknown dependency or ordering between admitted changes
- Missing test or verification strategy
- Hidden trust, data, or interface assumption not surfaced in requirements
- Missing or wrong builder lanes or review lanes for the work

**Step 2 — Packet completeness check:** Before the first edit, verify the following are all present and current:
- Every admitted change doc is complete and contains both Requirements and Acceptance Criteria
- AC priority has been recorded (required / important / nice-to-have / not this scope)
- Required review and builder lanes are selected and recorded in the wave record
- Relevant architecture docs, specs, or context docs are identified
- Key unknowns and risk areas named in Step 1 are either resolved or explicitly accepted as known risks
- The ordered lane sequence (from the wave plan) is grounded in MCP evidence, not shell-discovered assumptions

**Step 3 — Verdict:** Record the outcome in the wave record under `## Review Checkpoints` using this format:
```
- pre-implementation-review: passed (<date>) — pre-mortem completed, packet complete, [brief note on highest risk and how it was addressed]
```
Or, if the gate finds a blocking gap:
```
- pre-implementation-review: blocked (<date>) — [specific missing evidence or unresolved risk that must be resolved before coding starts]
```
A `blocked` verdict halts implementation until the gap is resolved and the gate is re-run with a `passed` verdict.

When `wave_council_policy.enabled` is true: the existing `wave-council-readiness` verdict proves the wave was admissible; the pre-implementation verdict is the coordinator's own packet-completeness and failure-mode challenge. Both must be present before the first edit. The council does not need to run a second session for this gate unless the coordinator's pre-mortem reveals a risk large enough to require council-level synthesis.

MCP-first code exploration:

When MCP is attached, exploration before any code edit follows this order. Agents must not default to shell search or broad file reads for questions these tools are designed to answer:

1. `code_ask` — cross-cutting "what does this currently do?" questions
2. `code_search` — conceptual or module-level discovery
3. `code_definition` — declarations and symbol ownership
4. `code_references` — call sites and impact radius (all reference kinds: call sites, imports, mentions)
5. `code_callhierarchy` — direct callers and callees with exact line numbers and snippets; prefer over `code_references` when the question is purely structural ("what calls X?" / "what does X call?"). For languages whose cross-file resolution is less mature (Swift, Java, Kotlin, C/C++/C#, ObjC, Ruby, PHP, Scala), if a `code_callhierarchy` result is empty for a symbol you can independently verify exists, fall back to `code_references` — it uses text-based search and finds the call sites regardless of graph-extractor coverage. The `code_callhierarchy.external_outgoing_count` / `external_incoming_count` fields surface how many external (non-project) entries were suppressed; pass `include_external=true` to inline them.
6. `code_impact` — transitive upstream callers up to N hops; run before modifying a shared symbol to size the full blast radius across the codebase before the first edit. The `path=` heuristic mode only parses imports in Python/JS/TS/Go/Rust; for other languages it returns `unsupported_language: true`. Use `symbol=` (graph mode) for impact analysis on Swift/Java/Kotlin/C/C++/C#/etc.
7. `code_keyword` — exact token or string matches
8. `code_outline` — before a broad `code_read` on a large file
9. `code_callgraph` — call tree beyond 1 hop (depth > 1) when broader call structure is needed
10. `rg` / `grep` / broad file reads — fallback only

Shell search and broad file reads are fallback when: (a) MCP is not attached; (b) the relevant tool is unavailable in the host session; (c) index health or freshness makes results unreliable; or (d) MCP results are genuinely insufficient after a reasonable pass.

The wave plan produced in task 9 must be grounded in MCP evidence for each intended edit: which file owns the behavior, whether the target symbol already exists, which call sites will be affected, and what neighboring patterns the repo already uses. Do not substitute shell exploration for this step when MCP is available. This exploration obligation does not replace the existing requirement to validate with targeted reads before synthesis or code changes — both apply.

When fallback to shell tools was necessary, record a `Gapfill:` entry in Progress Log with what was missing and why — this surfaces repeated tool friction for maintainers without blocking implementation.

Wave orchestration contract:

- **Admission:** the coordinator confirms which changes, feature slices, review lanes, and integration lanes are admitted into the current wave
- **Allocation:** the coordinator assigns ownership, start order, dependency constraints, and parallel lanes for the admitted changes or tasks. Implementation lanes are allocated from repository evidence and admitted scope — not by habit. When the admitted change primarily involves backend/API/service code, allocate `software-engineer`; for UI/interaction/accessibility surfaces, allocate `frontend-developer`; for SQL/schema/migration/ETL/data-contract work, allocate `data-engineer`. Use the generic `implementer` when the change is cross-cutting, narrow in scope, or when domain depth is not required. Record the selected lanes in the wave record or Review checkpoints so readiness and review passes have explicit inputs.
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
- after `Prepare wave` passes clean and before the first product-code edit: present the wave plan to the operator; the plan must state which files will be changed and how, which tests will be added and what cases they cover, and any open risks or questions. A separate second approval is required only when repo-local docs or the active handoff explicitly impose that hold, or when review materially changed the execution packet after the operator’s earlier implementation instruction.
- before the first product-code edit, map intended code changes to the admitted scope, acceptance criteria, and planned verification. For bug fixes, prefer a reproducer test or equivalent failing proof before the fix when feasible; when infeasible, record the substitute evidence and why.
- preserve stable `wave-id` and `Change ID` references when updating wave state
- keep the wave artifact rooted at `docs/waves/<wave-id>/`, where the `wave-id` uses the shared Crockford lifecycle prefix plus the summary slug that best reflects the admitted changes
- before setting `Activated at`, review the admitted changes and rename placeholder wave slugs/titles to a descriptive summary while preserving the shared lifecycle prefix and updating references
- treat admitted change docs as already wave-owned before implementation: `Add change to wave` is the canonical relocation step that moves admitted change docs from `docs/plans/<change-id>.md` into `docs/waves/<wave-id>/<change-id>.md`; `Prepare wave` validates placement, repairs drift, and removes duplicate staging copies when needed; `Implement wave` assumes that relocation is complete and only performs defensive repair if drift is detected
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
- implementers must mark task and AC checkboxes as each item is actually completed — do not batch-update them at the end of the wave. Mark `[x]` only when the underlying work is done and verifiable. When an AC or task is intentionally left unchecked or must be reopened, record the reason in the Progress Log or a Review Checkpoints note so the rationale is durable.
- the coordinator should verify that change-doc checkbox state stays current as part of normal progress reconciliation; if a completed work item is still unchecked, fix the bookkeeping in the same pass rather than leaving it for a later cleanup step
- personas should participate at declared challenge, review, or acceptance checkpoints and escalate when domain concerns materially change the wave
- personas selected by readiness evaluation are gating participants for that wave's relevant checkpoints
- factor-review participants should evaluate only the factors relevant to the active wave instead of forcing a full factor checklist into every wave; source those factors from `docs/agents/factor-<nn>-<name>.md` and keep the dashboard grouping aligned with `Category: factor`
- when factor subagents are active, the factor reviewer should consolidate their findings into one coherent review output for the wave
- all participants should leave enough state in wave artifacts and journals for another agent to continue safely

Required tasks:

1. Load the active execution plan, spec refs, and wave artifacts. Consult `docs/references/project-context-memory.md` and relevant role journals (`docs/agents/journals/`) for active cautions and known pitfalls that apply to the current wave's scope. If memory records a past mistake in this area, treat it as a constraint on implementation — not a suggestion.

   **MCP resource orientation** — before reaching for tool calls to load stable reference content, prefer attaching it directly as context via MCP resources. Stable resources available without parameters: `wavefoundry://overview` (project orientation), `wavefoundry://wave/current` (active wave record), `wavefoundry://agents` (AGENTS.md operating guide), `wavefoundry://graph/status` (graph index health), `wavefoundry://graph/communities` (catalog of code-graph communities for blast-radius and refactor planning). Use `wavefoundry://change/{change_id}`, `wavefoundry://seed/{slug}`, and `wavefoundry://architecture/{slug}` for parameterized reads. Resources return raw markdown with no tool-call overhead; fall back to tools (`wave_get_change`, `seed_get`, etc.) when you need structured envelopes with `diagnostics` and `next_tools`.
2. Determine whether the next `planned` wave is ready to become `active`.
3. If the selected wave still has a provisional holding name, review the admitted changes and rename the wave slug/title to a descriptive summary before activation.
4. Confirm admitted change docs already live under `docs/waves/<wave-id>/` after `Add change to wave`; if any remain under `docs/plans/`, repair placement before continuing.
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
- **Do not write the first line of product code before the implementation plan has been surfaced and the current request authorizes implementation.** `Implement wave` / `Implement feature` in the current request is sufficient approval once the plan is presented, unless repo-local docs, the active handoff, or a material review-driven packet change explicitly requires a second stop.
- Do not activate a wave under a placeholder slug when the admitted changes already make a better descriptive name obvious.
- Do not silently widen scope; return to planning when wave findings invalidate major assumptions.
- Do not let participants invent their own coordination model for the wave when the plan already defines coordinator-owned orchestration.
- Do not make unrelated cleanup edits during implementation; remove only code, comments, imports, or branches made obsolete by the current change and report pre-existing cleanup separately.
- Do not let implementation drift away from traceable scope; every edit should map back to the admitted change, acceptance criteria, or cleanup directly caused by the change.
- Do not edit any file explicitly listed in an admitted change doc's in-scope list before `Prepare wave` has passed for the active wave — even when the file is under `docs/` or `agent-workflows/` and would otherwise be exempt from the repository code gate. The wave-admitted surfaces gate in `AGENTS.md` governs those files once they are in scope.
- Lanes do not self-escalate to Level 3; only the coordinator classifies findings and decides loop level after the CRITIC step. A reviewer reporting a finding does not itself trigger re-planning — the coordinator evaluates it against acceptance criteria first.
- Use `Salience / Impact` in meaningful `Reflect:` entries when the finding should affect future behavior, retrieval, reviewer routing, or handoff. Do not use salience for routine status.
