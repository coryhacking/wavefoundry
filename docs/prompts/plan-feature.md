# Plan Feature

Owner: Engineering
Status: active
Last verified: 2026-04-28

Shortcut: **`Plan feature`**

## Purpose

Author a consolidated change document at `docs/plans/<change-id>.md`. Wave admission and **Prepare wave** are required before implementation begins.

## Steps

1. Clarify scope through discovery; classify by risk and blast radius.
2. Generate a change ID: `python3 .wavefoundry/framework/scripts/lifecycle_id.py --kind <kind> --slug <slug>`
3. Author the change doc using `docs/plans/plan-template.md`. Include:
   - `## Rationale` — specific motivation a reviewer can understand
   - `## Requirements` — numbered behavioral requirements
   - `## Scope` — in-scope / out-of-scope
   - `## Acceptance Criteria` — testable outcomes
   - `## Affected architecture docs` — which architecture docs need updating, or N/A with rationale (required when the change crosses module boundaries, integration contracts, primary data/control paths, or test/release seams)
4. Surface assumptions explicitly; prefer one clarifying question over a wrong assumption.
5. Note: **Interrogate this plan** is available as an optional stress-test before admission.

## Stage Gate

Repository code must not be edited until:
1. This change doc exists
2. The change is admitted via **Create wave** / **Add change to wave**
3. **Prepare wave** has passed cleanly

## Framework / Prompt-Surface Maintenance Plans

When the change touches `docs/prompts/`, `AGENTS.md`, seed prompts, or hook configs, the plan must name intended file edits, protected surfaces, and read-only vs write-owning lanes before execution.
