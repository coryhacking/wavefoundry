# Implement Wave

Owner: Engineering
Status: active
Last verified: 2026-08-13

Shortcut: **`Implement wave`**

## Purpose

Coordinator-managed implementation and computational verification for all admitted changes in a wave. Required inferential lanes run afterward through **Review wave**.

## Pre-condition

The wave must be **readied** — **Prepare wave** has passed cleanly (council verdict + required lane reviews recorded). If not, run **Prepare wave** first.

`Implement wave` is the **activation** step (wave 1p45l): it opens a readied `planned` wave (or a legacy `active` wave) and is where the **single-OPEN** invariant is enforced. `wf_implement_wave` runs the single-OPEN guard and blocks with `another_wave_active` if another wave is already OPEN (`active`/`implementing`) — pause that wave first. Readying this wave never took the OPEN slot; opening it here does.

## Execution Model (ReAct Loop)

The coordinator:
1. Records a `Thought:` entry in the Progress Log before each scoped action.
2. Produces an ordered implementation sequence before the first edit.
3. Runs independent implementation and computational-verification actions concurrently where safe; synthesizes a merged `Observe:` before the next `Thought:`.
4. Classifies findings: Level 1 (micro, internal fix), Level 2 (exceptional named checkpoint at the affected boundary), Level 3 (scope/plan invalidation, stop and re-Prepare or re-plan).
5. Records a `Reflect:` entry after blocking findings, identifying the pattern and proactively updating remaining tasks.
6. Updates checkbox-tracked ACs and tasks in the admitted change docs as each item actually completes; do not leave completion bookkeeping until the end of the wave.

When `wave_review.enabled` is true, implementation starts only after `wave-council-readiness` is recorded during **Prepare wave**. The policy-selected delivery-phase council pass runs during **Review wave** after implementation evidence exists.

## Readiness Handoff

**Prepare wave** owns the one pre-code critique: failure-first analysis, packet completeness, and the current readiness approval. `wf_implement_wave` consumes that authority directly on declared waves. Do not repeat the critique or mint a second approval before editing.

## Implementation Guardrails

- Stage gate applies: must be inside a clean Prepare wave pass.
- Follow `docs/repo-profile.json` `code_pattern` when populated; surface significant pattern problems before deviating.
- After changes, verify they actually address the stated problem before declaring done.
- Required review lanes from readiness participate during **Review wave** after implementation evidence is complete. During implementation, request a named checkpoint only when a high-risk boundary needs independent judgment before work can safely continue.
- Keep change-doc bookkeeping current: when a task or AC is completed during the run, mark it complete in that same implementation pass. Do not batch-update completion marks at review or closure time.
- **MCP-first code exploration:** Any code investigation at any lifecycle stage (grounding the plan before the first edit, verifying review claims against the tree, and repair/reverification work inside review cycles alike) runs on MCP evidence first: `code_search`, `code_definition`, `code_references`, `code_keyword`, and `code_outline` before `grep`/`rg` or broad file reads. The run contract's Retrieval Rules (`seed-020`) carry this scope for every lane and briefed subagent. Shell search is fallback only when MCP is not attached, the relevant tool is absent, index health is unreliable, or MCP results are genuinely insufficient. Record a `Gapfill:` note in Progress Log when fallback was required. This posture is measured: `wf_implement_wave`'s activation response carries the directive as a `retrieval_posture` field, and a `retrieval_posture_gap` advisory fires at implementation review and close dry-run when implement-stage retrieval telemetry is near zero against a non-trivial code diff — the recorded `Gapfill:` note clears it.
- **Builder-lane allocation:** Allocate implementation lanes from repository evidence and admitted scope. Use the generic `implementer` for cross-cutting or narrow changes. Route to a senior builder specialist when domain depth is needed: `software-engineer` for backend/API/service work; `ui-ux-engineer` for UI/interaction/accessibility surfaces; `senior-data-engineer` for SQL/schema/migration/ETL/data-contract work. Record selected lanes in the wave record or Review checkpoints.

## Framework Script Changes

After any framework script change:
1. `python3 .wavefoundry/framework/scripts/run_tests.py`
2. **Docs gate:** Routine documentation edits already receive automatic incremental changed-set lint. Before declaring implementation complete, with MCP attached run the full **`wf_validate_docs`** (use **`wf_garden_docs`** first if metadata timestamps need refresh). **CLI fallback (no MCP):** `wf docs-gardener && wf docs-lint`

Fix any failures before declaring the implementation complete.

## Agent Memory Briefing

Before the first edit, call `memory_brief(context='pre_implementation', targets=[...])` with the files in scope — active memory records (fragile files, prior failed attempts, operator preferences) surface as capped, cited advisories. Treat a `needs_reverification` fragile-file advisory as a prompt to re-check the concern against current code before editing. `wf_prepare_wave` responses carry the same advisories for the admitted change set. Absence of records is not absence of risk.

<!-- wavefoundry:review-policy:begin -->
## Review-policy implementation

Prepare Wave is the single readiness authority. Implementation consumes the
current shared delivery evaluator and never recreates a separate readiness
review gate.
<!-- wavefoundry:review-policy:end -->
