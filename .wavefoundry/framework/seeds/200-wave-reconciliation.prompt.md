# 200 - Wave Reconciliation (Internal Helper)

Intent:

- Start, update, complete, supersede, or hand off waves in a consistent way.

Reconciliation goals:

- normalize the current operational truth of the wave
- confirm or revise coordination truth after execution findings
- record assumption changes and their downstream impact
- decide the explicit disposition of every admitted change and any optional tasks/subtasks
- determine whether unfinished work stays under the same `Change ID` and how it carries forward
- produce next-wave readiness and handoff truth for downstream agents

Use this helper when:

- activating a new wave
- readying a wave before implementation
- updating an active wave as work progresses
- adding a change to a wave
- removing a change from a wave
- pausing a wave
- reconciling wave review state before closure — includes running an AC scope gap check (required ACs met, important/nice-to-have items surfaced, not-this-scope deferrals confirmed) so the operator can decide on follow-on scope before closure; when **`Prepare wave`** recorded **`## AC priority`** on an admitted change doc, reconciliation must include **product-owner** delivery scope sign-off before merge (per **`seed-100`**) and **`qa-reviewer`** required-row verification or deferrals at **`Review wave`** (record in **`wave.md` Review checkpoints**)
- closing a wave
- moving unfinished changes or tasks to a later wave
- recording invalidated assumptions
- creating a next-wave handoff
- splitting a wave into multiple successor waves

Orchestration responsibilities:

- confirm the active coordinator and participant roster
- confirm which changes are represented in the wave
- confirm which changes are admitted into the current wave
- confirm which changes are complete, blocked, deferred, moved, retried, or superseded
- capture any orchestration changes that occurred during execution
- make next-wave prerequisites explicit

Required wave planning-mode handoff semantics (when writing or updating `docs/agents/session-handoff.md` for a wave in `planning` state — i.e., admitted but not yet prepared):

- `Mode: wave_prepare`
- Active wave ID and active change IDs
- **In-scope files** — list every file explicitly named under `## Scope` (`**In scope:**`) in the admitted change doc; add a gate warning: "All listed surfaces are gated by the Stage Gate (wave-admitted surfaces) in `AGENTS.md` — do not edit these files until `Prepare wave` passes."
- Next lifecycle step: `Prepare wave`
- Any open blockers or decisions outstanding before readiness

Example in-scope file list entry:

```
- In-scope files (gated — do not edit before Prepare wave):
  - `.wavefoundry/framework/seeds/180-implement-feature.prompt.md`
  - `AGENTS.md`
  - `docs/prompts/implement-wave.prompt.md`
  - (full list from change doc ## Scope)
```

The generic "next lifecycle step: Prepare wave" line alone is not sufficient — the file list makes the gate visible before any edit is attempted.

Required wave start semantics:

- `wave-id`
- `Status: active`
- admitted change docs physically present in `docs/waves/<wave-id>/`
- objective
- coordinator
- active changes
- participants
- dependency graph or explicit dependency rules
- work allocation and dependency rules
- synchronization or reporting expectations
- frozen assumptions or interfaces
- expected outputs
- review checkpoints and gating rules — for admitted **bug** or product-defect changes, confirm **`qa-reviewer`** is selected at readiness and recorded before closure (`docs/contributing/agent-team-workflow.md`, `docs/workflow-config.json` `review_policies.require_qa_reviewer_for_bug_fixes`) unless waived explicitly
- readiness checkpoints and gating rules, including salience-trigger effects on reviewer/persona routing when relevant
- journal refs when already known, including critical/high operating-memory captures that cannot wait for closure

Required active-wave update semantics:

- explicit state changes for affected changes, tasks, or workstreams
- current status of wave changes, tasks, and workstreams
- blockers, retries, moved changes, and deferred changes
- changed assumptions or new findings
- explicit output deltas: what was produced, invalidated, or still expected
- which implementer lanes and reviewer lanes are active, blocked, complete, or newly required
- which persona lanes are active, blocked, complete, or newly required
- current readiness-evaluation status and whether it remains valid for the next lifecycle action
- review findings or new review requirements
- salience / impact signals when they change routing, escalation, handoff, preservation, or future behavior
- factor-review findings and whether factor-specific subagents or review lanes were active when factor review applied
- coordinator actions taken to rebalance or escalate the wave
- updated handoff or readiness notes when the next action changed materially

Required wave close semantics:

- `Status: completed` or `superseded`
- outputs produced
- final disposition of all scoped wave changes
- explicit carry-forward, defer, retry, move, or split decision for unfinished change work
- assumptions validated
- assumptions invalidated
- missteps and corrections
- review status
- final readiness-evaluation status
- journal updates required
- journal distillation, promotion, retirement, and supersession decisions required
- next-wave handoff
- explicit readiness or non-readiness of the next wave
- explicit statement of whether the wave closed because the objective was satisfied, superseded, or intentionally cut at an operational boundary
- **wave-owned change docs**: confirm every admitted change doc for this wave exists at `docs/waves/<wave-id>/<change-id>.md` (expected after `Prepare wave`); if any stale `docs/plans/` references remain, repair them before closure instead of introducing a second move through `docs/plans/completed/`
- **retrospective prompt**: after closure artifacts are recorded, ask "what was non-obvious in this wave that a future session should know?" — surface zero or more memory candidates; capture architectural decisions (why an approach was chosen), validated approaches that should carry forward (positive confirmations, not only corrections), and workflow discoveries; promote findings to auto-memory or `docs/references/project-context-memory.md`
- **idle handoff**: update `docs/agents/session-handoff.md` to record the closed wave ID and a one-line summary of what shipped, so the next session has recent history without running `wave_list_waves`; include an **Open questions / Deferred decisions** section for any intent not captured in a change doc

Recommended reconciliation outputs:

- normalized change state summary
- change carry-forward summary
- dependency summary
- assumption summary
- review checkpoint summary
- coordinator decision summary

Change carry-forward rules:

- keep the same `Change ID` when unfinished work is still part of the same intended change
- move unfinished changes or tasks into the next wave explicitly when they continue under the same change
- split into a new change only when the remaining work is materially different in purpose, risk, or review treatment
- when a split happens, record why continuing under the old `Change ID` would be misleading

Guardrails:

- Allow wave artifacts to stay compact for simple work.
- Expand hierarchically for large multi-workstream waves.
