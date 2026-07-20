# Journal - Mcp Tool Hygiene

Owner: Engineering
Status: active
Role: wave-coordinator
Last verified: 2026-07-20

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-07-20

wave-id: `1t3gt mcp-tool-hygiene`

## Operating Identity

- **Role:** wave-coordinator for wave `1t3gt mcp-tool-hygiene`. **Responsibility:** coordinate the wave's admitted changes through prepare → implement → review → close per the lifecycle contract.

## Salience Triggers

- **critical** — operator directives that change wave scope, admitted changes, or close authorization
- **high** — review-time findings that block close, dependency changes between admitted changes
- **medium** — implementation-time observations about scope drift or unexpected blockers
- **low** — routine coordination notes, status updates, lint pass/fail signals

## Default Stance

Maintain the wave's load-bearing invariants throughout implementation. Preserve the change-doc contracts admitted at prepare time; surface drift from operator immediately rather than silently absorbing scope.

## Memory Responsibilities

- Track per-change implementation state (gate-open/close pairs, AC completion, follow-up findings)
- Record decisions made during implementation that affected scope, AC formulation, or test strategy

## Active Signals

- Wave closed 2026-07-20; all four changes complete. No open signals.

## Distillation

- Bulk mechanical renames are the legitimate domain of scripted longest-first substring replacement, but the safety of that approach lives entirely in the pre-pass collision census: two tool names (`wave_review`, `wave_implement`) doubled as workflow-config schema keys, and blind replacement would have broken config compatibility. Census name collisions across every namespace (config keys, module names, prose) before any bulk rename.
- The rename table in a change doc is a snapshot; the live registration set is the authority. Re-deriving the live list before editing caught nothing this time only because prepare-time reconciliation had already caught the phantom tool; keep the re-derivation step.
- Deterministic-transformation delivery verification wants an exact-set oracle, not spot checks: diffing the full fresh-process `tools/list` against an independently authored expected set is cheap and categorical.
- A scaffold change can surface latent contracts elsewhere: baking the review-status projection into the wave scaffold exposed the 1t3dm freshness contract's implication that direct wave.md edits changing derived signoff keys must re-render the projection. When a fix collides with a recently shipped contract, prefer conforming to the contract over quietly weakening it; the prototyped empty-ledger tolerance was reverted for exactly that reason.
- Running the framework test suite concurrently with a live server/index probe can fail `test_indexer` through interference; verify suspected flakes in isolation and re-run the suite uncontended before treating them as regressions.

## Promotion Evidence

- Promoted to agent memory (typed record, via memory_propose/memory_validate rewrite): "Reload-survivor MCP tool changes are a process-restart boundary" (`mem-reload-survivor-mcp-tool-changes-are-a-process-restart-bound`).
- Promoted to operator auto-memory during the wave: "templates must generate lint-valid docs" (the 1t3gu operating principle).
- Follow-up work drafted rather than journaled: `1t22z` and `1t230` in `docs/plans/` carry the retrieval-posture and checkpoint-flush lessons as actionable changes.

## Retirement And Supersession

- Wave closed 2026-07-20; this journal is final. No entries superseded.

## Governance

- This journal follows the operating-memory contract in `docs/agents/journals/README.md`. Critical/high signals may be journaled during planning, implementation, review, handoff, reindex, or closure — not only at close. Distillation, promotion, and retirement happen at close.
