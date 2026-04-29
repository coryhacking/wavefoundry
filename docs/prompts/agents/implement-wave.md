# Agent Body — Implement Wave

Owner: Engineering
Status: active
Last verified: 2026-04-28

## Context

You are running **Implement wave** on Wavefoundry as the wave-coordinator.

## Pre-conditions

- **Prepare wave** has passed cleanly as the immediately preceding lifecycle step.
- Stage gate satisfied: change docs admitted and relocated.

## Execution

Follow the ReAct loop (Thought → Action → Observe → Reflect on blocking findings). Produce an ordered lane sequence before the first edit.

## Wavefoundry-Specific Implementation Rules

- **Framework script changes:** after any edit to `.wavefoundry/framework/scripts/`, run `python3 .wavefoundry/framework/scripts/run_tests.py` before declaring the implementation task done.
- **Seed edits:** require `seed_edit_allowed` guard approval in `.wavefoundry/guard-overrides.json`; reset after editing.
- **Framework plan gate:** `framework_edit_allowed` approval required for broad `docs/prompts/`, `AGENTS.md`, or hook config edits.
- **Docs gate:** after any `docs/` edit, the post-edit hook runs `./docs-lint`; fix failures before continuing.
- **No `git commit`:** hand off diff + suggested message; operator commits.

## Level 3 Escalation Triggers

Stop and re-Prepare when:
- Scope expands beyond admitted changes
- A new durable decision is required (update ADRs)
- A previously frozen assumption is invalidated
