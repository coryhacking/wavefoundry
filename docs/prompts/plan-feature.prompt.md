# Plan Feature

Owner: Engineering
Status: active
Last verified: 2026-05-26

Shortcut: **`Plan feature`**

## Purpose

Author a consolidated change document at `docs/plans/<change-id>.md`. Wave admission and **Prepare wave** are required before implementation begins.

## Steps

1. Clarify scope through discovery; classify by risk and blast radius.
2. **Divergent Pre-Plan (required):** Before drafting the plan, execute a diverge → critique → select pass:
   - **Diverge:** enumerate 2–3 distinct approaches differing in a meaningful assumption, strategy, or scope boundary — not just surface wording.
   - **Critique:** for each approach, state its primary weakness or risk in one sentence.
   - **Select:** choose one approach and state in one sentence why it is preferred.
   - Record the selected approach and the rejected alternatives (with weaknesses) in `## Decision Log`.
3. Create the staged change doc through MCP when available:
   - `feat` → `wave_new_feature`
   - `bug` → `wave_new_bug`
   - `enh` → `wave_new_enhancement`
   - `ref` → `wave_new_refactor`
   - `change` → `wave_new_change`
   - `doc` → `wave_new_documentation`
   - `debt` → `wave_new_tech_debt`
   - `task` → `wave_new_task`
   - `maint` → `wave_new_maintenance`
   - `ops` → `wave_new_operations`
4. If MCP is unavailable, use the CLI fallback: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>`, then create `docs/plans/<change-id>.md` from `docs/plans/plan-template.md`.
5. Author or refine the change doc. Include:
   - `## Rationale` — specific motivation a reviewer can understand
   - `## Requirements` — numbered behavioral requirements
   - `## Scope` — in-scope / out-of-scope
   - `## Acceptance Criteria` — testable outcomes written with stable checkbox identifiers: `- [ ] AC-1: <outcome>`, `- [ ] AC-2: <outcome>`, etc.
   - `## Tasks` — implementation checklist items written as checkboxes: `- [ ] <step>`
   - `## Affected architecture docs` — which architecture docs need updating, or N/A with rationale (required when the change crosses module boundaries, integration contracts, primary data/control paths, or test/release seams)
   - if the operator's request clearly extends work already admitted into the current wave, prefer updating that existing change rather than creating a fresh one; extend that change's Acceptance Criteria and Tasks to capture the added scope, and create a new change only when the remaining work is materially different or should be tracked separately
6. Surface assumptions explicitly; prefer one clarifying question over a wrong assumption.
7. Note: **Interrogate this plan** is available as an optional stress-test before admission.

## Stage Gate

Repository code must not be edited until:
1. This change doc exists
2. The change is admitted via **Create wave** / **Add change to wave**
3. **Prepare wave** has passed cleanly

## Framework / Prompt-Surface Maintenance Plans

When the change touches `docs/prompts/`, `AGENTS.md`, seed prompts, or hook configs, the plan must name intended file edits, protected surfaces, and read-only vs write-owning lanes before execution.
