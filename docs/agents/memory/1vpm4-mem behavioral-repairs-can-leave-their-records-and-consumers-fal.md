# Behavioral repairs can leave their records and consumers false

Owner: Engineering
Status: active
Last verified: 2026-08-19

Memory ID: `1vpm4-mem behavioral-repairs-can-leave-their-records-and-consumers-fal`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-19
Updated: 2026-08-19
Source exploration cost: 3090767
Source event: `finding:1vqqi:DEL-10`
Validation: promote
Validated by: agent
Action delta: After repairing delivery findings, re-check every changed record and documented consumer against executed output; a correct implementation is not enough when handoff, specs, prompts, or bounding prose still describe the pre-repair behavior.
Validation rationale: DEL-10 is durable as a failed-attempt pattern, but the candidate is truncated and incorrectly narrows the target to techdocs_audit.py. The verified defect family was repair-induced drift across records and consumers, including the handoff, change doc, spec, domain map and seed 178.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

A repair can pass its implementation tests while leaving wave records, handoff state, public prompts, specs, or bounded-response consumer prose inconsistent with shipped behavior. After each repair batch, execute the public behavior and re-check every touched record and consumer surface; do not validate repair prose against itself.

## Evidence

- `DEL-10`
- `ev-del-10-3`
- `delivery-1vqqi-rv5-docs`

## Targets

- `docs/waves/1vqqi techdocs-audit-and-review-branch/1vmt2-enh techdocs-audit-tool-and-review-only-branch.md`
- `docs/agents/session-handoff.md`
- `docs/specs/mcp-tool-surface.md`
- `.wavefoundry/framework/seeds/178-refresh-techdocs.prompt.md`
- `.wavefoundry/framework/scripts/techdocs_audit.py`
