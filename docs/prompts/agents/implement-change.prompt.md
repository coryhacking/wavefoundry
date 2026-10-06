# Agent Body — Implement Change

Owner: Engineering
Status: active
Last verified: 2026-09-22

## Context

You are running **Implement change** on Wavefoundry (single-change path).

## Guru Orientation

Before writing code, confirm the target exists and identify the dominant pattern:

```
code_definition(symbol) # does this already exist?
code_references(symbol) # who calls it — is this a shared contract?
code_keyword(pattern) # are there similar implementations to follow?
```

This avoids duplicating existing logic and ensures the implementation matches the dominant pattern. If MCP is not available, use `grep -rn "def symbol\|class symbol" .` and `grep -rn "symbol" .` filtered to call sites.

## Pre-conditions

Stage gate satisfied: change doc admitted, **Prepare wave** passed cleanly.

## After Implementation

1. `python3 .wavefoundry/framework/scripts/run_tests.py` (if scripts changed)
2. **Docs gate:** Routine documentation edits already receive automatic incremental changed-set lint. Before declaring implementation complete, prefer full MCP **`wf_validate_docs`** (and **`wf_garden_docs`** if metadata needs refresh). **CLI fallback:** `wf docs-lint` when MCP is unavailable.
3. Complete required review lanes (**Review wave**); then optionally **Close change** for this change, then **Close wave**. Path: Plan change -> Create wave -> Add change to wave -> Prepare wave -> Implement change -> Review wave -> Close change (per change, optional) -> Close wave.

## Rules

- Follow `docs/repo-profile.json` `code_patterns` when populated (currently `insufficient_history`)
- Prefer smallest correct change; no opportunistic cleanup
- Stage gate applies regardless of perceived scope
