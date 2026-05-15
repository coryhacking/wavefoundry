# Implement Feature

Owner: Engineering
Status: active
Last verified: 2026-05-14

Shortcut: **`Implement feature`**

## Purpose

Single-change docs-first implementation path. Use when one admitted change needs implementation without multi-workstream coordination.

## Pre-condition

Repository code stage gate must pass:
1. Consolidated change doc exists and is admitted into a wave
2. **Prepare wave** has passed cleanly as the immediately preceding lifecycle step

If any step is missing, stop and route back to **Plan feature**, **Create wave**, **Add change to wave**, or **Prepare wave**.

## Steps

1. Read the change doc at `docs/waves/<wave-id>/<change-id>.md` and the AC priority table.
2. Implement per Requirements and Acceptance Criteria.
3. Follow `docs/repo-profile.json` `code_patterns` when populated.
4. After implementation: run framework tests, then prefer MCP **`wave_validate`** (and **`wave_garden`** if metadata needs refresh). **CLI fallback:** `.wavefoundry/bin/docs-gardener && .wavefoundry/bin/docs-lint` when MCP is unavailable.
5. Complete required review lanes before closing.
6. Use **Finalize feature** to close the wave.
7. If the operator requests a follow-up that still belongs to the current wave and the scope fits an admitted change, update that existing change's Acceptance Criteria and Tasks instead of opening a new change; create a new change only when the new work is materially different or needs separate tracking.

## Guardrails

- Prefer the smallest correct change; do not refactor adjacent code unless required.
- After changes, verify they actually address the stated problem.
- Stage gate does not scale with perceived scope — always follow the lifecycle.
