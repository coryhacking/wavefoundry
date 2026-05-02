# Journals

Owner: Engineering
Status: active
Last verified: 2026-05-02

Agent journals capture episodic memory for roles and personas. Journals are advisory — they are not source of truth. Repeated, validated lessons may be promoted to canonical docs or `docs/references/project-context-memory.md`.

## Journal Files

| File | Actor |
|------|-------|
| `wave-coordinator.md` | Wave Coordinator role |
| `planner.md` | Planner role |
| `implementer.md` | Implementer role |
| `framework-operator.md` | Framework Operator persona |
| `wave-coordinator-persona.md` | Wave Coordinator persona |

## Journal Section Order

Journals must lead with identity, not activity:

1. Operating Identity
2. Salience Triggers
3. Distillation ← durable, authoritative operating memory
4. Active Signals ← pending entries awaiting distillation
5. Promotion Evidence
6. Retirement And Supersession
7. Governance / Active Watchpoints

## Journal Entry Rules

Write a journal entry when: a bug reached review; a review cycle caused rework; a mistake needed correction; a constraint was hard to discover; a tool failure caused significant lost time; an invalidated assumption caused backtracking.

**Filter gate:** Before writing any entry ask: *"Would this still matter to a new agent inheriting this role with no access to git history?"* If no — skip it. Wave IDs, change IDs, "wave X closed", and test-pass counts are activity logs — they belong in git and wave docs, not here.

**Do not write entries for routine successful work.** The absence of an entry signals that work completed normally.

## Retention Policy

- **Keep and promote:** lesson is reusable, risk still exists, constraint still applies, mistake is still easy to make.
- **Keep in journal only:** one-time incident, not recurred, not structurally resolved.
- **Retire:** root cause structurally fixed, constraint no longer exists, context superseded.

See `docs/workflow-config.json` `agent_memory` for the full policy.
