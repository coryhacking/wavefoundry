# 170 - Plan Feature (Shortcut)

Use this when you want a single command-style request such as:

- `Plan feature`
- `Plan enhancement`
- `Plan bug`
- `Plan refactor`
- `Plan reliability change`
- `Plan security change`
- `Create wave`
- `Add change to wave`
- `Add bug to wave`
- `Add feature to wave`
- `Add enhancement to wave`
- `Add task to wave`
- `Add refactor to wave`
- `Add reliability change to wave`
- `Add security change to wave`
- `Remove change from wave`
- `Remove bug from wave`
- `Remove feature from wave`
- `Remove enhancement from wave`
- `Remove task from wave`
- `Remove refactor from wave`
- `Remove reliability change from wave`
- `Remove security change from wave`
- `Implement wave`

Intent:

- Define a wave and its admitted changes, turning scope into implementation-ready planning artifacts. The wave is the delivery unit — changes are what it contains.

Before planning, consult:

- `docs/references/project-context-memory.md` — for known pitfalls, recurring anti-patterns, and durable constraints relevant to the planned scope. If memory records a past mistake in this area, the plan must address it explicitly rather than repeating it.
- Relevant role and persona journals (`docs/agents/journals/`) — for operating identity, salience triggers, active cautions, unresolved watchpoints, promotion queues, and hard-to-rediscover observations that touch the planned scope. A caution or high-salience memory is a signal that risks, reviewer/persona routing, and acceptance criteria should address that area.

Required planning outputs for non-trivial work:

- wave record (`docs/waves/<wave-id>/wave.md`) — the primary planning artifact; defines the wave objective, admitted changes, review gates, and completion criteria
- change document for each admitted change (single consolidated file in `docs/plans/` while planning; moved into the wave folder during `Prepare wave` / readiness — see format below)
- `Agent Execution Graph`
- `Knowledge Transfer Plan`
- `Persona Review Plan`
- `Wave Readiness Plan`
- `Journal Watchpoints`
- `Salience / Impact` notes only where they change priority, reviewer/persona routing, escalation, handoff, or memory preservation
- factor-review plan when factor-oriented review is relevant for the project and the current wave
- for framework/prompt-surface maintenance, an explicit file-touch plan naming intended edits, protected surfaces, and read-only vs write-owning lanes before execution starts

Change document format:

- one file per `change-id` at `docs/plans/<change-id>.md` during planning — use the full `<id-prefix>-<kind> <slug>` (preserving the space) so the staging filename matches the wave-folder filename after `Prepare wave` and the `docs-lint` validator (`docs/plans/<change-id>.md` staging check) is satisfied without rename during readiness; the wave record itself does **not** use a staged `docs/plans/<wave-id>.md` path and must be created directly at `docs/waves/<wave-id>/wave.md`
- when the Wavefoundry MCP server is available, create staged change docs with the MCP `wave_new_*` tool for the kind (`wave_new_feature`, `wave_new_bug`, `wave_new_enhancement`, `wave_new_refactor`, `wave_new_change`, `wave_new_documentation`, `wave_new_tech_debt`, `wave_new_task`, `wave_new_maintenance`, `wave_new_operations`) rather than invoking `lifecycle_id.py` directly; these tools generate the ID and scaffold `docs/plans/<change-id>.md` in one call
- when MCP is unavailable, use the CLI fallback `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>` and create the staged change doc from `docs/plans/plan-template.md`
- required sections: `## Rationale`, `## Product Intent`, `## Requirements`, `## Scope`, `## Acceptance Criteria`, `## Tasks`, `## Agent Execution Graph`, `## Serialization Points`, `## Affected architecture docs`, `## Progress Log`, `## Decision Log`, `## Session Handoff`, `## Risks`
- when the change touches any UI surface identified in `docs/repo-profile.json` `design_system.ui_roots` or when the `design_review` trigger fires (see `docs/workflow-config.json` `design_review_triggers`), add a `## Design Intent` section to the change document; the section must include: (1) which design tokens, components, or layout patterns the change uses or introduces; (2) which platform HIG standard applies (per `docs/design/design-language.md` Platform/Framework Conventions) and whether the change follows or intentionally departs from it; (3) if departing from the HIG or from `docs/design/design-language.md`, the explicit rationale for the departure; (4) any new component patterns or color usage that should be promoted to `docs/design/design-language.md` after closure; omit the section with a note "Design Intent: N/A — no UI surface changes" when the change touches no source paths in `ui_roots`
- `## Rationale` captures the motivation and proposal context — must state a specific motivation, not just describe what will be done; a reviewer reading only the Rationale should understand *why* this change is needed; vague or placeholder Rationale is a blocking gap at `Prepare wave`
- `## Product Intent` captures the intended user/product outcome, boundaries, links to relevant `docs/specs/*.md`, and operator confirmation when non-trivial product work is in scope — distinct from pure implementation rationale (`docs/agents/product-owner.md`)
- `## Requirements` captures numbered behavioral requirements — each requirement must be specific enough that an implementer can act on it unambiguously and a reviewer can verify it without asking for clarification; vague requirements are a blocking gap at `Prepare wave`
- `## Requirements` should capture operational salience only when it changes engineering behavior. Use "Salience / Impact" for trust-risk, repeated rework, operator-signal, urgency, confusion, or confidence-shift that affects planning, not for routine priority labels.
- `## Acceptance Criteria` and `## Tasks` must name concrete verification evidence, not only desired outcomes. Translate "fix the bug" into a reproducer plus passing result when feasible, "add validation" into explicit invalid-input checks, and "refactor" into before/after verification expectations. When a reproducer test is not feasible, record the substitute verification path and why.
- `## Tasks` captures the inline implementation checklist
- `## Affected architecture docs` lists which canonical architecture children (`docs/ARCHITECTURE.md` hub row updates, `docs/architecture/current-state.md`, `domain-map.md`, `layering-rules.md`, `cross-cutting-concerns.md`, `data-and-control-flow.md`, `testing-architecture.md`, `docs/architecture/decisions/*`) the change is expected to touch during planning, implementation, or closure — use **`N/A`** with rationale when the work stays within one module and does not move boundaries, flows, invariants, or test topology; align listed names with **domain-map** identifiers
- do NOT create a separate `docs/specs/changes/<change-id>/` folder or cross-link to one; all change-tracking content lives in the single document
- `Change ID:` uses `<id-prefix>-<kind> <slug>` from the MCP `wave_new_*` change-creation tool for the selected kind, or from the CLI fallback `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>` when MCP is unavailable (kinds: bug, feat, enh, change, doc, debt, ref, task, maint, ops)

Wave planning rules:

- non-trivial waves should include a **`## Product intent`** section on `wave.md` (scoped outcome, spec links) aligned with each admitted change’s **`## Product Intent`**
- apply the `wave.md` dedup guardrail from `seed-110` **Guardrails** when authoring or refreshing the wave record via `Create wave` / `Add change to wave` — the wave record indexes and coordinates admitted changes; do not mirror an admitted change's requirements, acceptance criteria, task list, or risks on `wave.md`, and do not duplicate the same guardrail across scaffolding sections
- the wave is the primary planning unit; changes are the first-class records admitted into it — plan the wave first, then define its changes
- a wave admits one or more changes; each change may include optional tasks/subtasks when finer tracking is useful
- changes do not ship independently; every change must be admitted into a wave before implementation begins
- `Prepare wave` moves admitted change docs from `docs/plans/` into `docs/waves/<wave-id>/` so the wave folder is the canonical working home before implementation; activation records chronology but is not the primary relocation stage
- concurrency happens inside a wave only after shared assumptions and interfaces are stable enough
- planning should define which changes are admitted into this wave and why, not just what work exists
- planning should identify the wave coordinator and decision rights
- planning should define the readiness gate that must pass before implementation begins and again during final review
- **`Prepare wave`** records **AC priority** on admitted change docs for product-impacting work — required / important / nice-to-have / not this scope, recommended heading **`## AC priority`** — and **`seed-100`** requires **product-owner** delivery scope sign-off before merge plus **`qa-reviewer`** required-row reconciliation at **`Review wave`**; see **`100-project-prompt-surface-bootstrap.prompt.md`** (**prepare-wave** / **review-wave**) and repo **`docs/prompts/prepare-wave.md`**
- planning should identify high-salience risks, operator signals, repeated rework, trust-risk, and compaction-sensitive knowledge that should affect admission, reviewer/persona routing, or journal watchpoints
- planning should state explicitly when the operator is creating a new wave versus changing the admitted set of an existing wave
- when **Add change to wave** admits a **feature** or otherwise shifts product semantics, plan **`product-owner`** on the admission delta and a fresh **`product-owner`** pass at the next **`Prepare wave`** for the full admit set (`docs/prompts/add-change-to-wave.md`, `docs/prompts/prepare-wave.md`, `docs/contributing/agent-team-workflow.md`)
- planning should define how the wave will actually be orchestrated, not only what work belongs inside it
- planning should define whether any role/persona operating-memory signal should be journaled immediately rather than deferred to closure
- when a wave touches shared framework, prompt-surface, entrypoint, or hook files, planning should define the protected surfaces and require a short operator review pause on the file plan before execution starts
- incomplete changes carry forward into the next wave under the same `Change ID`; create a new change-id only when the remaining work is materially different from the original change
- planning should not introduce speculative abstractions, generalization work, or configurability that is not justified by the request, acceptance criteria, or repository evidence

Required planning semantics:

- `change-id` values for tracked changes in scope
- machine-usable `change-id` values in the form `<id-prefix>-<kind> <slug>`, where `<id-prefix>` is the shared Crockford lifecycle token emitted by MCP `wave_new_*` tools or, when MCP is unavailable, by `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>`: 4 Crockford Base32 digits for hours since the workflow-configured lifecycle epoch in `docs/workflow-config.json` (`lifecycle_id_policy.epoch_utc`, plus optional `hour_offset`) plus one Crockford minute-bucket character, all lowercase (kinds: bug, feat, enh, change, doc, debt, ref, task, maint, ops; example: `1a2x8-bug runtime-retry`)
- machine-usable `wave-id` values that sort in time order and can serve as `docs/waves/<wave-id>/` folder names, using `<prefix> <slug>` from `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind wave --slug <slug>` — there is no `-wave` token in the emitted ID (example: `1a2yy routine-behavior-contract`)
- wave-0 baseline IDs in the form `00000 wave-zero-plans-and-specs` when init or migration captures pre-wave corpora
- generated `Title` values or summary slugs that describe the admitted change set for each wave
- lifecycle timestamp fields for each wave record: `Activated at` and `Completed at`
- wave objectives
- entry and exit criteria
- wave coordinator and decision rights
- participant roster and roles inside the wave
- admission rules for work entering the wave
- work allocation and dependency rules
- synchronization or reporting expectations during the wave
- escalation triggers and replanning triggers
- participating generic roles
- participating personas
- changes inside each wave, with optional tasks/subtasks inside change documents when needed
- which changes are present inside each wave
- machine-usable `Change ID` identifiers for admitted changes
- explicit status vocabulary for waves and admitted changes
- review checkpoints and their gating effect
- readiness-evaluation checkpoints and their gating effect
- assumption tracking and assumption status where shared assumptions matter
- serialization points
- review checkpoints
- handoff rules
- factor-review applicability for the wave and the factor-specific subagents or sub-review lanes that should participate, if any

Required orchestration outputs for each non-trivial wave:

- who is coordinating the wave
- whether the current planning pass created the wave, admitted a change into it, or removed a change from it
- which changes are admitted into the wave
- who owns each change or workstream
- which changes can run in parallel and which must wait
- what information participants must report during execution
- what conditions block, defer, move, retry, or supersede work
- how the coordinator decides that the wave is complete
- what incomplete changes carry forward into the next wave and what, if anything, should become a new change with explicit justification
- which anchors later agents should be able to read without guessing, including identifiers, owners, statuses, dependencies, and handoff state
- which lifecycle timestamps the wave artifact must preserve so later readers can distinguish activation, completion, and merge chronology
- what final summary title or slug should be produced for the wave folder once the admitted changes are known well enough to name the wave clearly
- whether the initial wave slug is only a provisional holding name and what readiness-time or activation-time review should rename it to before the wave is marked active
- which persona lanes and reviewer lanes the readiness gate is expected to evaluate before implementation starts — when any admitted change has kind **`bug`** (or is a product defect fix), **`qa-reviewer` must be in that roster at minimum** unless a waiver is explicitly recorded (`docs/contributing/agent-team-workflow.md`, `docs/workflow-config.json` `review_policies.require_qa_reviewer_for_bug_fixes`)
- which role/persona salience triggers affected the roster, if any
- whether factor review is active for this wave, whether it uses subagents or review lanes, and which factor-specific participants are relevant
- which protected surfaces require one write owner and which lanes must remain read-only

Guardrails:

- Do not force flat or shallow plans when the work is complex.
- Do not hide wave or persona reasoning only in chat output.
- Do not trim planning tasks, dependencies, risks, or review points to an arbitrary small count; include every item needed to make execution and review reliable.
- Do not leave a placeholder wave slug such as `pending-change-batch` in place once the admitted changes are clear enough to name the wave descriptively.
- Do not leave verification implicit for behavior-changing work; bug fixes should plan a reproducer or record why equivalent evidence is the best available substitute.
- Do not turn salience into generic urgency language. Use it only when it changes a decision, retrieval priority, handoff, or future behavior.
- **Planning-vs-implementation ambiguity:** when an active wave exists whose admitted change has not yet passed `Prepare wave`, and the operator makes a request that could be interpreted as either a planning action (update the change doc scope or wave record) or an implementation action (edit an in-scope file now), the coordinator must surface the ambiguity explicitly before acting. State which interpretation is being applied and confirm with the operator before editing any file listed in the change doc's in-scope list. The **Stage Gate (wave-admitted surfaces)** in `AGENTS.md` blocks in-scope file edits until `Prepare wave` passes; use this rule to catch the ambiguity before reaching that gate.
