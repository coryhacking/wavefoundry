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
- Relevant typed memory records (`memory_brief` / `memory_search` when attached; `docs/agents/memory/` directly otherwise) — for active cautions, fragile areas, prior failed attempts, and hard-to-rediscover observations that touch the planned scope. A caution or high-salience memory is a signal that risks, reviewer/persona routing, and acceptance criteria should address that area.

Divergent Pre-Plan (required before drafting):

Before writing the plan, execute a structured diverge → critique → select pass:

- **Diverge:** enumerate 2–3 distinct approaches to the stated problem, each differing in a meaningful assumption, strategy, or scope boundary — not just surface wording.
- **Critique:** for each approach, state its primary weakness or risk in one sentence.
- **Select:** choose one approach and state in one sentence why it is preferred over the alternatives.

Record the selected approach and the rejected alternatives (with their weaknesses) in the change doc's `## Decision Log`. This pass executes within the single planning agent — no additional agents or sub-processes are required.

Code-grounded authoring (required; definition in seed-209, "Code-Grounded Verification"):

- Before a claim about existing code enters `## Requirements`, `## Scope`, an Acceptance Criterion, or a `## Decision Log` rationale, verify it against the actual tree, and execute it where executable: render into the failing shape, call the dispatch path, run the census. Reading code and reasoning about it produces plausible, internally consistent, and false plans; every mechanism defect in the motivating incidents was killed by execution and none by argument.
- Three claim shapes need the strongest evidence: "X already does Y" mechanism claims, "no other caller/site" censuses (run them with `limit=0`, state them exhaustively or narrow the claim to what the census supports), and a rationale that justifies a decision by a benefit (observe the benefit; a plan once kept a mechanism for behavior that never fired).
- A load-bearing claim that cannot be executed is marked `inferred` or `unverified` in the plan, using seed-209's `execution_status` vocabulary, instead of asserted flatly. The reviewer then knows which premises the prepare council must probe first.
- Write each Acceptance Criterion so that an implementation with the fix absent cannot satisfy it, and state the failing condition where it is not obvious. This is the authoring counterpart of the reviewer's known-bad rule in seed-209; an AC satisfiable by a no-op, or by documenting a defect the change itself introduces, is a defect in the plan.

Required planning outputs for non-trivial work:

- wave record (`docs/waves/<wave-id>/wave.md`) — the primary planning artifact; defines the wave objective, admitted changes, review gates, and completion criteria
- change document for each admitted change (single consolidated file in `docs/plans/` while planning; admitted into the wave folder during `Add change to wave`, then validated there during `Prepare wave` — see format below)
- `Agent Execution Graph`
- `Knowledge Transfer Plan`
- `Persona Review Plan`
- `Wave Readiness Plan`
- `Watchpoints` (legacy heading `Journal Watchpoints` on old waves)
- `Salience / Impact` notes only where they change priority, reviewer/persona routing, escalation, handoff, or memory preservation
- factor-review plan when factor-oriented review is relevant for the project and the current wave; source applicable factor docs from `docs/agents/factor-<nn>-<name>.md` and record the dashboard grouping expectations via `Category: factor`
- for framework/prompt-surface maintenance, an explicit file-touch plan naming intended edits, protected surfaces, and read-only vs write-owning lanes before execution starts

Change document format:

- one file per `change-id` at `docs/plans/<change-id>.md` during planning — use the full `<id-prefix>-<kind> <slug>` (preserving the space) so the staging filename matches the wave-folder filename after `Prepare wave` and the `docs-lint` validator (`docs/plans/<change-id>.md` staging check) is satisfied without rename during readiness; the wave record itself does **not** use a staged `docs/plans/<wave-id>.md` path and must be created directly at `docs/waves/<wave-id>/wave.md`
- when the Wavefoundry MCP server is available, create staged change docs with the MCP `wf_new_*` tool for the kind (`wf_new_feature`, `wf_new_bug`, `wf_new_enhancement`, `wf_new_refactor`, `wf_new_change`, `wf_new_documentation`, `wf_new_tech_debt`, `wf_new_task`, `wf_new_maintenance`, `wf_new_operations`) rather than invoking `lifecycle_id.py` directly; these tools generate the ID and scaffold `docs/plans/<change-id>.md` in one call
- when MCP is unavailable, use the CLI fallback `wf lifecycle-id --kind <kind> --slug <slug>` and create the staged change doc from `docs/plans/plan-template.md`
- required sections: `## Rationale`, `## Product Intent`, `## Requirements`, `## Scope`, `## Acceptance Criteria`, `## Tasks`, `## Agent Execution Graph`, `## Serialization Points`, `## Affected architecture docs`, `## Progress Log`, `## Decision Log`, `## Session Handoff`, `## Risks`
- when the change touches any UI surface identified in `docs/repo-profile.json` `design_system.ui_roots` or when the `design_review` trigger fires (see `docs/workflow-config.json` `design_review_triggers`), add a `## Design Intent` section to the change document; the section must include: (1) which design tokens, components, or layout patterns the change uses or introduces; (2) which platform HIG standard applies (per `docs/design-system/design-language.md` **Platform/Framework Conventions**) and whether the change follows or intentionally departs from it; (3) if departing from the HIG or from `docs/design-system/design-language.md`, the explicit rationale for the departure; (4) any new component patterns or color usage that should be promoted to `docs/design-system/design-language.md` after closure; (5) when the project has `docs/design-system/platforms/<surface>/` deltas (seeded by Split C), note which platform surface this change targets and whether any per-surface token overrides or narrative in `docs/design-system/platforms/<surface>/` apply — record "No per-surface delta applies" when `platforms/` is absent or the surface is not affected; omit the section with a note "Design Intent: N/A — no UI surface changes" when the change touches no source paths in `ui_roots`
- `## Rationale` captures the motivation and proposal context — must state a specific motivation, not just describe what will be done; a reviewer reading only the Rationale should understand *why* this change is needed; vague or placeholder Rationale is a blocking gap at `Prepare wave`
- `## Product Intent` captures the intended user/product outcome, boundaries, links to relevant `docs/specs/*.md`, and operator confirmation when non-trivial product work is in scope — distinct from pure implementation rationale (`docs/agents/product-owner.md`)
- `## Requirements` captures numbered behavioral requirements — each requirement must be specific enough that an implementer can act on it unambiguously and a reviewer can verify it without asking for clarification; vague requirements are a blocking gap at `Prepare wave`
- `## Requirements` should capture operational salience only when it changes engineering behavior. Use "Salience / Impact" for trust-risk, repeated rework, operator-signal, urgency, confusion, or confidence-shift that affects planning, not for routine priority labels.
- `## Acceptance Criteria` and `## Tasks` must name concrete verification evidence, not only desired outcomes. Translate "fix the bug" into a reproducer plus passing result when feasible, "add validation" into explicit invalid-input checks, and "refactor" into before/after verification expectations. When a reproducer test is not feasible, record the substitute verification path and why. Each AC must use checkbox syntax with a stable identifier: `- [ ] AC-1: <outcome>`, `- [x] AC-2: <outcome>` (checked when actually complete) — this gives each criterion a stable ID for the AC Priority table, review comments, and test evidence, and enables live progress tracking identical to Tasks. Agents must mark AC and task checkboxes incrementally as work is done, not batch-update at closure. AC completion and every task marker are tracking only; an AC `[~]` remains a reviewable contract change and needs its required inline rationale.

- `## Serialization Points` is the machine-readable review target declaration, and it accepts exactly two forms: a bullet whose content is entirely repo-relative paths, each backtick-quoted, for example `` - `src/app/handler.py`, `docs/specs/` ``; or an explicit `**Review targets (repo-relative paths):**` block whose backtick-quoted entries may contain spaces, which is the only way to declare a path like `docs/waves/<id> <slug>/wave.md`. Prose declares NOTHING in either form: a bullet with one stray English word in it is prose, a wrapped bullet is prose in its entirety, and a fenced example declares nothing. That includes bullets inside the explicit block, so a sentence there that merely quotes a path declares no target. Prepare selects automatic lanes only from declared paths, never from Scope or other narrative. Adoption is decided per DOCUMENT, so declaring targets here never suppresses an un-migrated sibling's prose scoring, and leaving them undeclared keeps that document's whole-document coverage rather than emptying it. Path scoring is a FLOOR, not a ceiling: it catches what a change demonstrably touches, and it cannot see risk that has no file to point at. **Any lane may also be requested by judgment through the wave-level `Requested review lanes` field, and the coordinator is expected to use it.** Architecture review in particular is usually a judgment call — an ownership shift, a protocol or state-machine change, or a new cross-component dependency can land entirely inside files whose paths recruit only the code lane. The same holds for security, performance, release and docs-contract risk. Requesting a lane is cheap and always honored: a requested lane is added ahead of path scoring and recorded in the receipt as `requested by operator/project wave input`, and `wave.md` is not part of the review-policy digest, so naming one costs no receipt churn. Never expect narrative to recruit a lane, and never treat an empty automatic roster as evidence that no review is warranted.

- **Prepare-owned plan content is populated before the prepare council runs, not after it.** The `## AC Priority` table carries one row per AC with its priority and rationale, and `## Tasks` is fully enumerated, at plan time. Both are requirement-bearing and therefore stay part of the review-policy digest, so filling them after readiness has been recorded supersedes the receipt and lapses the readiness approvals it just collected. Template placeholder text that reads "populated at Prepare wave" is stale instruction; treat the `ac_priority_unpopulated` advisory at Prepare as a backstop for an author who skipped the plan-time fill, not as the schedule. This covers ENUMERATION and CONTENT only: checkbox STATE (`[ ]` to `[x]` to `[~]`) necessarily changes during implementation.

### Editing the review-policy canonicalizer is a repository-wide transition

If a change edits `canonical_review_policy_body` or any of its normalizers, say so in the change document and expect a one-time cost that no other edit has. Those functions decide what the review-policy digest SEES, so changing them re-digests every change document in the repository at once, lapsing every readiness approval in every open wave with no document edited. Plan for one re-Prepare per open wave, disclose it, and avoid making the edit while waves are readied but unclosed without saying so.

### Citations in change docs anchor by symbol

When a change document cites code, cite a **resolvable anchor** — a function, class, method, constant, test name, or a distinguishing expression — rather than a bare `file:line`.

The reason is not tidiness, it is resolvability. A symbol anchor can be *resolved*: `code_definition(symbol)` and `code_read` return today's text, so a reviewer reading the plan a week later gets the current version. A line anchor can only be *checked*, and checking is what costs review cycles. Line anchors drift hardest exactly when the target file is under concurrent edit by a sibling wave, which is precisely when reviewers are most likely to be reading it.

**A line number is still correct in these cases**, and using one here is not a defect:

| Case | Why a line is the right anchor |
|---|---|
| A module-level constant block | No containing symbol |
| A data file | No symbol structure at all |
| A specific line in a generated artifact | The generator owns the symbol names, not the author |
| Prose in a hand-authored markdown document | A paragraph has no containing symbol |
| A deliberately historical citation | It records what was verified at a point in time |

**A line citation taken under one of these cases names the case inline**, so a reviewer can tell a deliberate line anchor from a lapsed one. "`docs/architecture/foo.md:477` (prose, no containing symbol)" is a good citation; a bare `foo.md:477` is not.

**Historical rows are exempt and stay exempt.** Line numbers already written into `## Progress Log` and `## Decision Log` rows record what was verified when. Do not rewrite them to symbols — that falsifies the history. The rule applies to live claims, not to the log of how they were reached.

There is no mechanical gate for this. Separating a live claim from a historical row from a legitimately line-anchored site is a judgment call, and a lint rule that fired on correct citations would train authors to ignore it.

### AC and task checkbox states — the `[~]` marker

Three checkbox states are canonical for ACs and tasks:

| State | Meaning | When to use |
|---|---|---|
| `[ ]` | Unmet — in scope, not yet done | Default at admission; flipped to `[x]` when the work completes |
| `[x]` | Done — verification evidence exists | Mark immediately when the AC's verification step lands; never batch-update at close |
| `[~]` | **Intentionally not met** — the original requirement was reconsidered, removed by operator direction during implementation, or genuinely narrowed by scope-discovery within the wave's contract. **Not** the same as "deferred to follow-on" (follow-on work stays `[ ]` with a follow-on-plan reference). | When a requirement falls away mid-wave for a recorded reason |

**Every `[~]` AC at required priority must carry an inline status note** explaining the rationale on the same line — naming when the deferral was decided, who directed or surfaced it, and why the original AC is no longer applicable. Wrap the rationale in markdown italics for readability and to satisfy the docs-lint inline-note check:

```markdown
- [~] AC-13: Mermaid diagram removed entirely per operator direction.
  *Original draft used a five-subgraph composite; operator subsequently directed
  removal in favor of prose description. See Decision Log entry on 2026-06-03.*
```

For `important` and `nice-to-have` priority ACs the inline note is *recommended but not lint-required*. For tasks the inline note is *recommended but not lint-required* regardless of priority, since tasks are implementation hints rather than contract surface.

**Silent `[~]` is a docs-lint error for required-priority ACs.** The mechanical enforcement is the discipline that prevents `[~]` from becoming a silent-deferral pattern. A `[~]` AC that lacks both a markdown italic segment AND sufficient prose (at least 40 characters after the AC label) raises a lint failure at `wf_validate_docs` time.

**Close-wave hard gate.** At `wf_close_wave`, every AC and every task across the wave's admitted changes must be `[x]` (completed) or `[~]` (intentionally deferred). A silent `[ ]` is a blocking close-time finding that surfaces with the change ID, item type, identifier, and inline text. ACs at `not-this-scope` priority are exempt from the close-time gate (the priority already encodes the exclusion). This gate is the discipline that makes the convention *real* rather than optional — at close time, everything is accounted for.

#### Worked example — wave `1p31b` `1p318` AC-13 and AC-19

The `[~]` convention grew from a real artifact: during the public-launch README rewrite (`1p318`), the operator directed full removal of the Mermaid concept-spine diagram mid-implementation. AC-13 (the diagram exists between walkthrough and Core Concepts) and AC-19 (diagram source committed alongside README; render verified) were no longer applicable but neither was satisfied. They were marked `[~]` with inline status notes recording the operator-directed deferral, and the corresponding Decision Log entry on `1p318` named the reasoning. Open `docs/waves/1p31b public-launch-prep/1p318-enh public-launch-surface-doc-rewrite.md` to read the worked example end-to-end.
- `## Tasks` captures the inline implementation checklist
- *Consider **Archetype review** when the change's load-bearing surface is AC formulation, rationale prose, or naming. Default seats: Sun Tzu, Yoda, Spock, Marcus Aurelius, Feynman. Swap Hemingway in for Feynman on prose-heavy rationale. Optional and operator-invoked; does not record `wave-council-readiness`. Seed: `236-archetype-council.prompt.md`.*
- `## Affected architecture docs` lists which canonical architecture children (`docs/ARCHITECTURE.md` hub row updates, `docs/architecture/current-state.md`, `domain-map.md`, `layering-rules.md`, `cross-cutting-concerns.md`, `data-and-control-flow.md`, `testing-architecture.md`, `docs/architecture/decisions/*`) the change is expected to touch during planning, implementation, or closure — use **`N/A`** with rationale when the work stays within one module and does not move boundaries, flows, invariants, or test topology; align listed names with **domain-map** identifiers
- do NOT create a separate `docs/specs/changes/<change-id>/` folder or cross-link to one; all change-tracking content lives in the single document
- `Change ID:` uses `<id-prefix>-<kind> <slug>` from the MCP `wf_new_*` change-creation tool for the selected kind, or from the CLI fallback `wf lifecycle-id --kind <kind> --slug <slug>` when MCP is unavailable (kinds: bug, feat, enh, change, doc, debt, ref, task, maint, ops)

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
- **`Prepare wave`** records **AC priority** on admitted change docs for product-impacting work — required / important / nice-to-have / not this scope, recommended heading **`## AC priority`** — and **`seed-100`** requires **product-owner** delivery scope sign-off before merge plus **`qa-reviewer`** required-row reconciliation at **`Review wave`**; see **`100-project-prompt-surface-bootstrap.prompt.md`** (**prepare-wave** / **review-wave**) and repo **`docs/prompts/prepare-wave.prompt.md`**
- planning should identify high-salience risks, operator signals, repeated rework, trust-risk, and compaction-sensitive knowledge that should affect admission, reviewer/persona routing, or wave watchpoints
- planning should state explicitly when the operator is creating a new wave versus changing the admitted set of an existing wave
- when a request clearly extends work already admitted into the current wave, prefer adjusting that existing change instead of creating a new change; extend the change's ACs and tasks to capture the added scope, and create a new change only when the remaining work is materially different or should be tracked separately
- when **Add change to wave** admits a **feature** or otherwise shifts product semantics, plan **`product-owner`** on the admission delta and a fresh **`product-owner`** pass at the next **`Prepare wave`** for the full admit set (`docs/prompts/add-change-to-wave.prompt.md`, `docs/prompts/prepare-wave.prompt.md`, `docs/contributing/agent-team-workflow.md`)
- planning should define how the wave will actually be orchestrated, not only what work belongs inside it
- planning should define whether any operating-memory signal should be captured as a memory candidate immediately rather than deferred to closure
- when a wave touches shared framework, prompt-surface, entrypoint, or hook files, planning should define the protected surfaces and require a short operator review pause on the file plan before execution starts
- incomplete changes carry forward into the next wave under the same `Change ID`; create a new change-id only when the remaining work is materially different from the original change
- planning should not introduce speculative abstractions, generalization work, or configurability that is not justified by the request, acceptance criteria, or repository evidence

Required planning semantics:

- `change-id` values for tracked changes in scope
- machine-usable `change-id` values in the form `<id-prefix>-<kind> <slug>`, where `<id-prefix>` is the shared lifecycle token emitted by MCP `wf_new_*` tools or, when MCP is unavailable, by `wf lifecycle-id --kind <kind> --slug <slug>`: a 5-character lowercase base36 time-ordered prefix (6 characters after the distant overflow horizon) derived from the provisioned lifecycle policy in `docs/workflow-config.json` (`lifecycle_id_policy`) (kinds: bug, feat, enh, change, doc, debt, ref, task, maint, ops; example: `1a2x8-bug runtime-retry`)
- machine-usable `wave-id` values that sort in time order and can serve as `docs/waves/<wave-id>/` folder names, using `<prefix> <slug>` from the MCP `wf_create_wave` tool (or, when MCP is unavailable, the CLI fallback `wf lifecycle-id --kind wave --slug <slug>`) — there is no `-wave` token in the emitted ID (example: `1a2yy routine-behavior-contract`)
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
- factor-review applicability for the wave and the factor-specific subagents or sub-review lanes that should participate, if any; factor docs should come from `docs/agents/factor-<nn>-<name>.md` and the dashboard should group them under `Category: factor`

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
- which **implementation builder lanes** the admitted change needs — explicitly record in the wave record whether the work is best served by the generic `implementer` or by a senior builder specialist (`software-engineer`, `frontend-developer`, `data-engineer`), and list the domain skills the implementation will require; this gives `Prepare wave` concrete inputs for lane selection instead of requiring reconstruction at readiness time. Select builder lanes from: code areas touched, detected project stack/archetype, acceptance criteria, and whether the change is primarily backend/API, UI/interaction, or data-contract/pipeline work
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
