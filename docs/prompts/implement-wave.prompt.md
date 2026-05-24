# Implement Wave

Owner: Engineering
Status: active
Last verified: 2026-05-23

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

## Pre-Implementation Review Gate

Mandatory first phase before any code edit. Purpose: challenge the wave from a failure-first perspective and confirm the implementation packet is complete enough to begin without avoidable rework.

**Step 1 — Pre-mortem:** Assume the implementation produces avoidable churn. Name the 3–5 most likely causes before writing any code: scope ambiguity, missing codebase knowledge, unknown dependencies, missing test strategy, hidden assumptions, wrong lanes.

**Step 2 — Packet completeness:** Verify all of the following before the first edit:
- All admitted change docs are complete with Requirements and ACs
- AC priority recorded (required / important / nice-to-have / not this scope)
- Required review and builder lanes selected and in the wave record
- Relevant architecture, spec, or context docs identified
- Key unknowns named and either resolved or accepted as explicit known risks
- Ordered lane sequence grounded in MCP evidence

**Step 3 — Verdict:** Record in `## Review Checkpoints`:
```
- pre-implementation-review: passed (YYYY-MM-DD) — [brief note on highest risk and how it was addressed]
```
A `blocked` verdict halts implementation until the gap is resolved. When `wave_council_policy.enabled`, the `wave-council-readiness` verdict covers admissibility; this gate is the coordinator's packet-completeness and failure-mode check.

## Implementation Guardrails

- Stage gate applies: must be inside a clean Prepare wave pass.
- Follow `docs/repo-profile.json` `code_patterns` when populated; surface significant pattern problems before deviating.
- After changes, verify they actually address the stated problem before declaring done.
- Required review lanes from readiness must participate during execution.
- **MCP-first code exploration:** Before the first edit, ground the implementation plan in MCP evidence — `code_search`, `code_definition`, `code_references`, `code_keyword`, and `code_outline` before `grep`/`rg` or broad file reads. Shell search is fallback only when MCP is not attached, the relevant tool is absent, index health is unreliable, or MCP results are genuinely insufficient. Record a `Gapfill:` note in Progress Log when fallback was required.
- **Builder-lane allocation:** Allocate implementation lanes from repository evidence and admitted scope. Use the generic `implementer` for cross-cutting or narrow changes. Route to a senior builder specialist when domain depth is needed: `software-engineer` for backend/API/service work; `ui-ux-engineer` for UI/interaction/accessibility surfaces; `senior-data-engineer` for SQL/schema/migration/ETL/data-contract work. Record selected lanes in the wave record or Review checkpoints.

## Framework Script Changes

After any framework script change:
1. `python3 .wavefoundry/framework/scripts/run_tests.py`
2. **Docs gate:** With MCP attached, run **`wave_validate`** (use **`wave_garden`** first if metadata timestamps need refresh). **CLI fallback (no MCP):** `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint`

Fix any failures before declaring the implementation complete.
