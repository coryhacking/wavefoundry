# Journal - Context Efficiency Telemetry

Owner: Engineering
Status: active
Role: wave-coordinator
Last verified: 2026-07-16

Actor: wave-coordinator
Schema version: 1.0
Last distilled: 2026-07-16

wave-id: `1stwj context-efficiency-telemetry`

## Operating Identity

- **Role:** wave-coordinator for wave `1stwj context-efficiency-telemetry`. **Responsibility:** coordinate the wave's admitted changes through prepare → implement → review → close per the lifecycle contract.

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

- **superseded** — the initial buffered, separate-signal readiness contract was withdrawn after operator review; it is retained here only as chronology.
- **high** — the fresh readiness council approved the amended write-through SQLite contract: one closed per-stage ledger, phase/source/version dedup across content and structural tools, lifecycle/reload/upgrade projection barriers, durable accounting-gap poison, v1 audit preservation without v2 reconstruction, and quality-gated paired evidence for saved output/tool loops.

## Distillation

- Pending: distilled lessons emerge as the wave delivers; promote durable findings to `docs/agents/journals/README.md` at close.

## Promotion Evidence

- Pending: promotion candidates against `docs/agents/journals/README.md` emerge as the wave delivers and durable lessons are identified.

## Retirement And Supersession

- Pending: retirement happens at wave close per the closure contract in `docs/agents/journals/README.md`.

## Governance

- This journal follows the operating-memory contract in `docs/agents/journals/README.md`. Critical/high signals may be journaled during planning, implementation, review, handoff, reindex, or closure — not only at close. Distillation, promotion, and retirement happen at close.
