# Implement Wave

Owner: Engineering
Status: active
Last verified: 2026-05-04

Shortcut: **`Implement wave`**

## Purpose

Coordinator-managed implementation and review loop for all admitted changes in a wave. Not a pure coding phase — reviewer lanes participate during execution.

## Pre-condition

**Prepare wave** must have passed cleanly as the immediately preceding lifecycle step. If not, run **Prepare wave** first.

## Execution Model (ReAct Loop)

The coordinator:
1. Records a `Thought:` entry in the Progress Log before each lane invocation.
2. Produces an ordered lane sequence before the first edit.
3. Runs parallel reviewer lanes (those with no shared dependencies) concurrently; synthesizes a merged `Observe:` before the next `Thought:`.
4. Classifies findings: Level 1 (micro, internal fix), Level 2 (reviewer loop, fix and re-run, no re-Prepare), Level 3 (scope/plan invalidation, stop and re-Prepare or re-plan).
5. Records a `Reflect:` entry after blocking findings, identifying the pattern and proactively updating remaining tasks.

When `wave_council_policy.enabled` is true, implementation starts only after `wave-council-readiness` is recorded during **Prepare wave**. The delivery-phase council pass runs during **Review wave** after implementation evidence exists.

## Implementation Guardrails

- Stage gate applies: must be inside a clean Prepare wave pass.
- Follow `docs/repo-profile.json` `code_patterns` when populated; surface significant pattern problems before deviating.
- After changes, verify they actually address the stated problem before declaring done.
- Required review lanes from readiness must participate during execution.

## Framework Script Changes

After any framework script change:
1. `python3 .wavefoundry/framework/scripts/run_tests.py`
2. **Docs gate:** With MCP attached, run **`wave_validate`** (use **`wave_garden`** first if metadata timestamps need refresh). **CLI fallback (no MCP):** `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`

Fix any failures before declaring the implementation complete.
