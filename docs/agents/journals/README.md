# Journals

Owner: Engineering
Status: active
Last verified: 2026-04-28

Agent journals capture episodic memory for roles and personas. Journals are advisory — they are not source of truth. Repeated, validated lessons may be promoted to canonical docs or `docs/references/project-context-memory.md`.

## Journal Files

| File | Actor |
|------|-------|
| `wave-coordinator.md` | Wave Coordinator role |
| `planner.md` | Planner role |
| `implementer.md` | Implementer role |
| `framework-operator.md` | Framework Operator persona |
| `wave-coordinator-persona.md` | Wave Coordinator persona |

## Journal Entry Rules

Write a journal entry when: a bug reached review; a review cycle caused rework; a mistake needed correction; a constraint was hard to discover; a tool failure caused significant lost time; an invalidated assumption caused backtracking.

**Do not write entries for routine successful work.** The absence of an entry signals that work completed normally.

## Retention Policy

- **Keep and promote:** lesson is reusable, risk still exists, constraint still applies, mistake is still easy to make.
- **Keep in journal only:** one-time incident, not recurred, not structurally resolved.
- **Retire:** root cause structurally fixed, constraint no longer exists, context superseded.

See `docs/workflow-config.json` `agent_memory` for the full policy.
