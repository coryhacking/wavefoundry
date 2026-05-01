# Agent Body — Close Wave

Owner: Engineering
Status: active
Last verified: 2026-04-30

## Context

You are running **Close wave** on Wavefoundry.

## Wavefoundry Closure Checks

Before marking `Status: completed`:

1. Framework tests pass: `python3 .wavefoundry/framework/scripts/run_tests.py`
2. Docs gate passes: **`wave_validate`** over MCP (or **`.wavefoundry/bin/docs-lint`** if MCP is unavailable)
3. Guard-overrides reset: `.wavefoundry/guard-overrides.json` has `seed_edit_allowed: false` and `framework_edit_allowed: false` (or file doesn't exist)
4. All required review lanes reconciled in `## Review checkpoints`
5. Docs-contract review disposition recorded
6. Journals distilled (no entry if work was routine)
7. Durable memory promoted to `docs/references/project-context-memory.md` if applicable
8. `docs/agents/session-handoff.md` cleared

## What Goes in Wave Summary

- What was delivered (specific files changed and why)
- What was deferred with rationale
- Key decisions made
- Lessons promoted (if any)

## Git Commits

Operator-owned. Hand off a complete diff and suggested commit message. Do not run `git commit`.