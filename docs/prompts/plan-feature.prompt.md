# Plan Feature

Owner: Engineering
Status: active
Last verified: 2026-09-08

Shortcut: **`Plan feature`**

## Purpose

Author a consolidated change document at `docs/plans/<change-id>.md`. Wave admission and **Prepare wave** are required before implementation begins.

**Brief before drafting:**

Reuse the request, prior answers, and relevant project context before the Divergent Pre-Plan. Establish the relevant goal, consumer/audience, angle or approach, constraints, deliverable/format, exclusions, and observable success. Put the brief in the existing Rationale and summarize it to the operator before dependent drafting. For clear tasks, one concise sentence can suffice; do not require a field-filling interview or confirmation.

Ask only questions whose answers materially change the result: at most three for small tasks and five for complex tasks per briefing pass, ceilings rather than quotas. Do not repeat known questions or restart a pass to evade the budget. State assumptions only for reversible implementation choices within established scope. Keep unresolved goal, scope, acceptance, or authorization decisions open until answered; pause dependent work and continue independent work while waiting. Silence is neither an answer nor approval. Reuse established durable preferences without creating another brief file.

## Steps

1. Clarify scope through discovery; classify by risk and blast radius.
2. **Divergent Pre-Plan (required):** Before drafting the plan, execute a diverge → critique → select pass:
   - **Diverge:** enumerate 2–3 distinct approaches differing in a meaningful assumption, strategy, or scope boundary — not just surface wording.
   - **Critique:** for each approach, state its primary weakness or risk in one sentence.
   - **Select:** choose one approach and state in one sentence why it is preferred.
   - Record the selected approach and the rejected alternatives (with weaknesses) in `## Decision Log`.
3. Create the staged change doc through MCP when available:
   - `feat` → `wf_new_feature`
   - `bug` → `wf_new_bug`
   - `enh` → `wf_new_enhancement`
   - `ref` → `wf_new_refactor`
   - `change` → `wf_new_change`
   - `doc` → `wf_new_documentation`
   - `debt` → `wf_new_tech_debt`
   - `task` → `wf_new_task`
   - `maint` → `wf_new_maintenance`
   - `ops` → `wf_new_operations`
4. If MCP is unavailable, use the CLI fallback: `wf lifecycle-id --kind <kind> --slug <slug>`, then create `docs/plans/<change-id>.md` from `docs/plans/plan-template.md`.
5. Author or refine the change doc. Include:
   - `## Rationale` — specific motivation a reviewer can understand
   - `## Requirements` — numbered behavioral requirements
   - `## Scope` — in-scope / out-of-scope
   - `## Acceptance Criteria` — testable outcomes written with stable checkbox identifiers: `- [ ] AC-1: <outcome>`, `- [ ] AC-2: <outcome>`, etc. Three checkbox states are canonical: `[ ]` (unmet, in scope), `[x]` (done), `[~]` (intentionally not met — operator-directed removal or scope-narrowing during implementation, with mandatory inline status note for required-priority ACs). See `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` *"AC and task checkbox states — the `[~]` marker"* for the canonical convention. An acceptance criterion asserts an outcome **this change controls** and that a reviewer can verify from **this change's own evidence**; repository-wide or environment state (the whole test suite being green, machine load, another wave's artifacts, the state of files this change never touches) is a gate concern and must not be written as an AC. `docs-lint` runs an advisory sensor on change documents in a readied, active, or implementing wave, or in any wave whose record carries an explicit `Activated at:` line (a paused wave that was once activated stays in scope): its findings are `WARNING:` lines that never fail validation, a flip to blocking is a later recorded change made on field data (the release checklist lists every sensor still advisory so the flip is decided, not forgotten), and new docs-lint sensors ship advisory the same way; it recognises a finite list of repository-scope words, so an unlisted repository-wide adjective passes silently to review while a compliant change-local criterion is never blocked. The diagnostic supplies the replacement sentence: write "the change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change" instead. See `.wavefoundry/framework/seeds/170-plan-feature.prompt.md` *"Acceptance criteria assert what the change controls"*.
   - `## Tasks` — implementation checklist items written as checkboxes: `- [ ] <step>`. The `[~]` marker applies here too, with looser enforcement (no mandatory inline note).
   - `## Affected architecture docs` — which architecture docs need updating, or N/A with rationale (required when the change crosses module boundaries, integration contracts, primary data/control paths, or test/release seams)
   - if the operator's request clearly extends work already admitted into the current wave, prefer updating that existing change rather than creating a fresh one; extend that change's Acceptance Criteria and Tasks to capture the added scope, and create a new change only when the remaining work is materially different or should be tracked separately
6. Surface assumptions explicitly; prefer one clarifying question over a wrong assumption.
7. Note: **Review plan** is available as an optional stress-test of this change doc, or of the current wave when no change is named, before or after admission and before implementation. **Interrogate this plan** and **Stress-test this plan** remain natural-language aliases. It records no typed signoff and satisfies no gate; **Review wave** is the distinct delivery-review lifecycle command.

## Stage Gate

Repository code must not be edited until:
1. This change doc exists
2. The change is admitted via **Create wave** / **Add change to wave**
3. **Prepare wave** has passed cleanly

## Framework / Prompt-Surface Maintenance Plans

When the change touches `docs/prompts/`, `AGENTS.md`, seed prompts, or hook configs, the plan must name intended file edits, protected surfaces, and read-only vs write-owning lanes before execution.
