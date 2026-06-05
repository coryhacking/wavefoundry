# Journal - Framework Drift Convergence

Owner: Engineering
Status: active
Role: wave-coordinator
Last verified: 2026-06-04

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-06-04

wave-id: `1p3dk framework-drift-convergence`

## Operating Identity

- **Role:** wave-coordinator for the framework drift-convergence wave. **Responsibility:** eliminate dual-valid states (renames that accept both spellings indefinitely) and unenforced claims (`MUST` declarations the gate doesn't check). Source: Solaris field feedback report (2026-06-04) against pack `1.5.0+p3d6`. Ships jointly under the **1.5.0** tag with closed waves `1p35d` and `1p3b9`.

## Salience Triggers

- **critical** — any new framework change that introduces an alias, deprecated spelling, or accepted-both-spellings runtime branch (the exact pattern this wave eliminates)
- **high** — any new `MUST` added to a seed without a matching `docs-lint` check in the same change
- **medium** — field feedback referencing rename hygiene, `docs-lint` false-cleans, or `MUST` enforcement gaps
- **low** — incidental references to deprecated names in conversation that point to a missed migration surface

## Default Stance

Hold the design invariant: the declared state and the actual state are never allowed to disagree. Every rename has a removal version and a bounded deprecation window. Every `MUST` is enforced or downgraded. Every canonical name has exactly one source of truth.

## Memory Responsibilities

- Track which framework surfaces touch canonical names (seeds, consumer runtime in `server_impl.py` / `upgrade_extensions.py`, lint constants, hand-authored docs) so the canonical-names manifest can collapse them to one source
- Record each rename as a bounded migration with a removal version, not as an indefinite acceptance

## Active Signals

- Solaris upgrade reconciliation report (2026-06-04) — five items, four admitted as candidate changes, item 5 (Fix-Now Threshold prose duplication across seeds 212/213/214/221) flagged as watch-only

## Distillation

- Pending: distilled lessons emerge as candidate changes are scaffolded and delivered.

## Promotion Evidence

- Pending: promotion candidates against `docs/agents/journals/README.md` emerge as the wave delivers and durable lessons are identified.

## Retirement And Supersession

- Pending: retirement happens at wave close per the closure contract in `docs/agents/journals/README.md`.

## Governance

- This journal follows the operating-memory contract in `docs/agents/journals/README.md`. Critical/high signals may be journaled during planning, implementation, review, handoff, reindex, or closure — not only at close. Distillation, promotion, and retirement happen at close.
