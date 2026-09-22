# Implement Feature

Owner: Engineering
Status: active
Last verified: 2026-09-22

Shortcut: **`Implement feature`**

## Host-neutral orchestration

Follow `.wavefoundry/framework/seeds/180-implement-feature.prompt.md` **Host-neutral orchestration** across the lifecycle. Choose models and reasoning effort per implementation or verification task; accept changes only after coordinator integration checks. Use only available host capabilities; sequential implementation does not satisfy required independent review.

## Purpose

Single-change docs-first implementation path. Use when one admitted change needs implementation without multi-workstream coordination.

## Pre-condition

Repository code stage gate must pass:
1. Consolidated change doc exists and is admitted into a wave
2. Prepare wave has passed cleanly; declared review-enabled waves require the typed `wave-council-readiness` approval on the current receipt. Legacy prose-verdict and review-disabled behavior are preserved.

If any step is missing, stop and route back to **Plan feature**, **Create wave**, **Add change to wave**, or **Prepare wave**.

**Readback before editing:**

Before the first implementation edit of each change, record a concise `Readback:` in its existing Progress Log and surface its substance to the operator: intended behavior, relevant ACs, important scope boundary, and expected affected files. Include one before/after example for nontrivial behavior changes; keep clear tasks brief.

Correct an agent-only misreading directly from the established requirement. Route an actual contract contradiction or missing consequential decision back to planning under existing escalation rules, pausing only dependent work. A readback correction is not automatically Level 3 and adds no second approval. Refresh only materially changed understanding after scope changes or handoff; do not repeat an unchanged readback or create another artifact.

## Steps

1. Read the change doc at `docs/waves/<wave-id>/<change-id>.md` and the AC priority table.
2. Implement per Requirements and Acceptance Criteria.
3. Follow `docs/repo-profile.json` `code_patterns` when populated.
4. Routine documentation edits already receive automatic incremental changed-set lint. After implementation: run framework tests, then prefer the full MCP **`wf_validate_docs`** (and **`wf_garden_docs`** if metadata needs refresh). **CLI fallback:** `wf docs-gardener && wf docs-lint` when MCP is unavailable.
5. Complete required review lanes before closing.
6. Use **Finalize feature** to close the wave.
7. If the operator requests a follow-up that still belongs to the current wave and the scope fits an admitted change, update that existing change's Acceptance Criteria and Tasks instead of opening a new change; create a new change only when the new work is materially different or needs separate tracking.

## Guardrails

- Prefer the smallest correct change; do not refactor adjacent code unless required.
- After changes, verify they actually address the stated problem.
- Stage gate does not scale with perceived scope — always follow the lifecycle.
