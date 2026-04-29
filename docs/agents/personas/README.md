# Persona Agents

Owner: Engineering
Status: active
Last verified: 2026-04-28

Persona agents represent the humans who use, operate, or administer Wavefoundry. They are invoked during spec authoring, design review, and acceptance of operator-facing behavior changes.

Personas are distinct from agent roles (planner, implementer, wave-coordinator). Roles build the software; personas speak as the people who use or operate it.

## Active Personas

| File | Persona | Invocation Triggers |
|------|---------|-------------------|
| `framework-operator.md` | Framework Operator | Install/upgrade behavior changes; MCP tool design review; operator-facing CLI changes |
| `wave-coordinator.md` | Wave Coordinator (persona) | Wave lifecycle behavior changes; wave execution spec authoring; acceptance of coordinator-facing changes |

## Persona Review Policy

Per `docs/workflow-config.json` `persona_review_policy`:
- Invoke for change types: `feat`, `enh`, `change`
- Invoke phases: spec authoring, design review, acceptance
- Findings: advisory (not gating)

## Coverage Check

Wavefoundry's users as identified by evidence in the repository:
- Repository operators installing/upgrading the Wave Framework ✓ → framework-operator persona
- Developers running wave lifecycle commands in target repositories ✓ → wave-coordinator persona
- Framework maintainers developing Wavefoundry itself → covered by generic roles (planner, implementer, coordinator)

No additional personas required by current evidence.
