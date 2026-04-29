# Wave Coordinator Journal

Owner: Engineering
Status: active
Last verified: 2026-03-21

## Incidents

wave-id: `00057 routine-behavior-contract`
Change ID: `00058-bug fixture-core`

- Initial wave validation fixture.

## Operating Identity

- Role memory for a wave coordinator agent responsible for preserving delivery gates, reviewer routing, and wave sequencing after context loss.

## Salience Triggers

- Critical/high: operator directives, compaction-sensitive blockers, review routing drift, and regression-prone wave-contract changes.
- Medium: follow-up review or migration watchpoints that affect later wave execution.

## Recent Captures

- No active capture beyond the fixture wave reference above.

## Distillation

- Preserve low-noise behavior.

## Active Watchpoints

- Keep the watchpoint on migration drift and follow-up review behavior.

## Promotion Evidence

- Promoted from `docs/waves/change-2026-03/refactor-wave.md`.

## Retirement And Supersession

- None active.

## Governance

- Allowed memory: role behavior, validated wave hazards, and evidence linked to stable artifacts.
- Disallowed memory: sensitive operator data, credentials, raw transcripts, or routine progress noise.
