# Delegation-layer MCP-first rule — route code subagents through role-typed agents or carry the directive

Change ID: `1p7bi-enh delegation-mcp-first-rule`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Wave: `1p79y factor-surface-integrity`
Last verified: 2026-06-22

## Rationale

The framework already mandates MCP-first code navigation for the **role** agents: `seed-050` generates `implementer.md` with *"`rg`, `grep`, and broad file reads are fallback tools only — not first-choice exploration … record a `Gapfill:` note when fallback was required"*; `seed-180`/`seed-211` carry the full MCP-first exploration order + recipes; and the closed wave `12sfb` made these defaults explicit for `implementer`/`planner`/`wave-coordinator`.

But that guidance only binds an agent that has **adopted a role**. When an orchestrator spawns a bare **`general-purpose` / Task subagent** for code investigation or implementation, the role-doc contract never applies — the subagent inherits the parent's MCP tools (confirmed: Task-spawned subagents inherit MCP tools by default) yet, absent the role guidance or a prompt directive, defaults to `grep`/Bash. Observed first-hand this session: general-purpose implementation subagents used shell despite the wavefoundry `code_*` tools being available, purely because the spawn prompts told them to and carried no MCP-first directive.

So the gap is at the **delegation layer**, not the role docs. Restating the tool list anywhere would be noise (it already exists 5×). The one genuinely-missing rule: an orchestrator delegating code work must route it through a role-typed agent **or** carry the MCP-first directive into the subagent prompt.

## Requirements

1. **Delegation-layer rule.** Add to the implementation/coordination orchestration guidance (`seed-180` implement-feature and/or `seed-100` implement-wave, and the `wave-coordinator` role-doc generation in `seed-050`): when an orchestrator (the coordinator, or any agent) spawns a subagent for **code investigation or implementation**, it must EITHER use a role-typed agent that carries the MCP-first contract (`implementer`, `guru`, or a builder specialist) **or** include the MCP-first code-navigation directive in the subagent's prompt. A bare `general-purpose`/Task subagent spawned for code work without that directive is the same shell-by-habit defect as in the main thread.
2. **State that subagents inherit MCP tools.** Note explicitly that Task-spawned subagents inherit the parent session's MCP tools by default, so "the subagent didn't have the MCP" is not a valid reason to fall back to shell.
3. **`AGENTS.md`.** Add the delegation rule to `AGENTS.md` (near the auto-Guru / retrieval-intent-backstop section) so the orchestrator reads it during a normal session; ship the same downstream via the seed that generates target `AGENTS.md` agent-routing guidance.
4. **Extend the `Gapfill:` expectation to spawned subagents.** `seed-050`'s implementer rule already requires a `Gapfill:` note when shell fallback was used; make the orchestrator responsible for requiring/surfacing the same from subagents it spawns for code work.
5. **No tool-list restatement.** Reference the existing MCP-first exploration order (`seed-180`/`seed-211`) rather than duplicating it.

## Scope

**Problem statement:** The framework's MCP-first navigation guidance binds role agents but not bare `general-purpose`/Task subagents spawned for code work, so orchestrators silently delegate code investigation/implementation to shell-by-habit subagents.

**In scope:** the delegation-layer rule in `seed-180`/`seed-100` + the `wave-coordinator` role-doc generation (`seed-050`); the `AGENTS.md` note (+ its generating seed); the `Gapfill:`-for-subagents extension.

**Out of scope:** restating the tool list / exploration order (already covered); changing the role-doc MCP-first guidance (it's correct); any code/validator change.

**Depends on:** none. Pairs with `1p79x`/`1p7ac` as 1.8.0 pre-release dogfooding fixes discovered while validating downstream.

## Acceptance Criteria

- [x] AC-1: `seed-180` (and/or `seed-100`) states the delegation-layer rule — code-work subagents must run through a role-typed agent or carry the MCP-first directive; a bare general-purpose subagent without it is the shell-by-habit defect.
- [x] AC-2: the guidance states explicitly that Task-spawned subagents inherit the parent's MCP tools by default.
- [x] AC-3: `AGENTS.md` (+ the generating seed) carries the delegation rule so the orchestrator reads it in a normal session.
- [x] AC-4: the rule references the existing MCP-first exploration order rather than restating the tool list (no duplication).
- [x] AC-5: the `Gapfill:` expectation is extended to subagents the orchestrator spawns for code work.
- [x] AC-6: `docs-lint` / `wave_validate` clean; no external-project names introduced; no VERSION bump; seed edits performed under `seed_edit_allowed`.

## Tasks

- [x] Open `seed_edit_allowed`; edit `seed-180`/`seed-100` (delegation rule + inherit-MCP note + Gapfill-for-subagents) and the `wave-coordinator` generation in `seed-050`; close the gate.
- [x] Add the delegation rule to `AGENTS.md` (auto-Guru / retrieval-backstop area) and its generating seed.
- [x] `wave_validate` clean; grep external-names = 0; confirm no VERSION change.

## Agent Execution Graph


| Workstream     | Owner       | Depends On | Notes                                                       |
| -------------- | ----------- | ---------- | ----------------------------------------------------------- |
| seed-rule      | implementer | —          | `seed-180`/`seed-100` + `seed-050` wave-coordinator gen     |
| agents-md      | implementer | seed-rule  | `AGENTS.md` note + generating seed                          |
| review         | reviewer    | all above  | docs-contract lane; re-run delivery council                 |


## Serialization Points

- Joins `1p79y` after both councils — the `wave-council-delivery` signoff must be re-run to cover `1p7bi` before close.

## Affected Architecture Docs

- **N/A** — prompt/guidance edits only; no module boundary, data flow, or code change.

## AC Priority


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The delegation-layer rule is the deliverable — the one genuinely-missing piece. |
| AC-2 | required  | Removes the "subagent lacks MCP" excuse, which is factually wrong. |
| AC-3 | required  | The orchestrator must encounter the rule during a normal session (`AGENTS.md`). |
| AC-4 | important | Avoid noise — reference, don't duplicate, the existing tool order. |
| AC-5 | important | `Gapfill:` visibility is how repeated subagent shell-by-habit becomes correctable. |
| AC-6 | required  | Gated prompt edits, clean validation, vendor-neutrality + no-release-yet preserved. |


## Progress Log


| Date       | Update                                                                 | Evidence                          |
| ---------- | --------------------------------------------------------------------- | --------------------------------- |
| 2026-06-22 | Plan created. Investigation (`code_keyword`/`docs_search`) showed the framework already mandates MCP-first for role agents (`seed-050:540`, `seed-180`, `seed-211`, closed wave `12sfb`); the gap is the delegation layer — bare `general-purpose`/Task subagents spawned for code work bypass the role-doc contract (observed first-hand this session). Operator directed adding it to the current wave. | `seed-050` implementer rule; `seed-180`/`seed-211`; wave `12sfb`; claude-code-guide confirmation that subagents inherit parent MCP tools |
| 2026-06-22 | Implemented (inline, not delegated — fitting for a delegation-discipline change). Added the delegation rule to `seed-180` (after the MCP-first exploration order), `seed-100` (implement-wave carry), `seed-050` (wave-coordinator generation + the retrieval-intent backstop), and `AGENTS.md` — referencing the existing exploration order, not restating it; states subagents inherit the parent's MCP tools; extends the `Gapfill:` expectation to spawned subagents. Verified: suite 3394 green bytecode-free (unchanged — seed prose), docs-lint clean, external-project names = 0 in changed files, no VERSION bump, `seed_edit_allowed` opened+closed. All 6 ACs `[x]`. | `seed-180`/`seed-100`/`seed-050` + `AGENTS.md`; `run_tests.py` (3394 OK); `wave_validate` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-22 | **Add a delegation-layer rule, do NOT restate the tool list** | The MCP-first exploration order already exists in 5+ surfaces; the only missing piece is the rule binding orchestrators when they spawn non-role subagents. Reference the existing order. | Re-state "use code_* tools" in more places — rejected: pure noise, the guidance already exists and was not the gap. |
| 2026-06-22 | Target the orchestration seeds + `AGENTS.md`, not the role docs | The role docs already carry MCP-first; the defect is upstream (the delegation decision). Fixing the orchestration layer makes role-typed delegation the default and carries the directive when a generic subagent is used anyway. | Edit each role doc — rejected: they're already correct; the spawn decision is the lever. |


## Risks


| Risk                                                                 | Mitigation                                                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Redundant guidance accretes (more "use the tools" prose) | Reference the existing exploration order; add only the delegation rule + inherit-MCP fact. |
| Joins `1p79y` after both councils | Re-run the `wave-council-delivery` to cover `1p7bi` before close. |
| Rule is prose an agent may still ignore | Pair the rule with the `Gapfill:` visibility extension so repeated subagent shell-by-habit surfaces as a recorded, correctable signal. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
