# Agent Body — Implement Wave

Owner: Engineering
Status: active
Last verified: 2026-05-08

## Context

You are running **Implement wave** on Wavefoundry as the wave-coordinator.

## CIA Orientation

Before the first edit, run an orientation pass per change:

```
code_search(topic, kind="code-summary", limit=5)   # which modules are in scope?
code_definition(symbol)                             # does the target already exist?
code_references(symbol)                             # who are the callers?
```

Use `code_ask` for open-ended questions ("how does X currently work?") when the answer requires synthesizing multiple files. When `partition_applied` is true, use `final_rank` rather than `score` to read the ordered citations, and treat `demoted: true` as an intentional policy reorder rather than a ranking bug. Ground the ordered lane sequence in indexed evidence before assigning implementation tasks. If MCP is not available, use `grep -rn "symbol" .` and `grep -n "^import\|^from" <path>`.

## Pre-conditions

- **Prepare wave** has passed cleanly as the immediately preceding lifecycle step.
- Stage gate satisfied: change docs admitted and wave-owned; fix placement drift before editing code if any staged copy remains.
- When `wave_council_policy.enabled` is true, `wave-council-readiness` must already be recorded before the first edit.

## Execution

Follow the ReAct loop (Thought → Action → Observe → Reflect on blocking findings). Produce an ordered lane sequence before the first edit.

## Wavefoundry-Specific Implementation Rules

- **Framework script changes:** after any edit to `.wavefoundry/framework/scripts/`, run `python3 .wavefoundry/framework/scripts/run_tests.py` before declaring the implementation task done.
- **Seed edits:** require `seed_edit_allowed` guard approval in `.wavefoundry/guard-overrides.json`; reset after editing.
- **Framework plan gate:** `framework_edit_allowed` approval required for broad `docs/prompts/`, `AGENTS.md`, or hook config edits.
- **Docs gate:** after any `docs/` edit, prefer MCP **`wave_validate`** (and **`wave_garden`** when metadata needs refresh); the post-edit hook still runs **`.wavefoundry/bin/docs-lint`** — fix hook failures too. **CLI-only fallback:** `.wavefoundry/bin/docs-lint` when MCP is not attached.
- **No `git commit`:** hand off diff + suggested message; operator commits.

## Level 3 Escalation Triggers

Stop and re-Prepare when:
- Scope expands beyond admitted changes
- A new durable decision is required (update ADRs)
- A previously frozen assumption is invalidated
