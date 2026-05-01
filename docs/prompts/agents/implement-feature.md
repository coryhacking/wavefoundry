# Agent Body — Implement Feature

Owner: Engineering
Status: active
Last verified: 2026-04-30

## Context

You are running **Implement feature** on Wavefoundry (single-change path).

## Pre-conditions

Stage gate satisfied: change doc admitted, **Prepare wave** passed cleanly.

## After Implementation

1. `python3 .wavefoundry/framework/scripts/run_tests.py` (if scripts changed)
2. **Docs gate:** Prefer MCP **`wave_validate`** (and **`wave_garden`** if metadata needs refresh). **CLI fallback:** `.wavefoundry/bin/docs-lint` when MCP is unavailable.
3. Complete required review lanes before calling **Finalize feature**

## Rules

- Follow `docs/repo-profile.json` `code_patterns` when populated (currently `insufficient_history`)
- Prefer smallest correct change; no opportunistic cleanup
- Stage gate applies regardless of perceived scope
