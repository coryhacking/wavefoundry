# Repaired defect DEL-10

Owner: Engineering
Status: superseded
Last verified: 2026-08-19

Memory ID: `1vq8r-mem repaired-defect-del-10`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-19
Updated: 2026-08-19
Source exploration cost: 3090767
Source event: `finding:1vqqi:DEL-10`
Validation: rewrite
Validated by: agent
Action delta: After repairing delivery findings, re-check every changed record and documented consumer against executed output; a correct implementation is not enough when handoff, specs, prompts, or bounding prose still describe the pre-repair behavior.
Validation rationale: DEL-10 is durable as a failed-attempt pattern, but the candidate is truncated and incorrectly narrows the target to techdocs_audit.py. The verified defect family was repair-induced drift across records and consumers, including the handoff, change doc, spec, domain map and seed 178.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1vpm4-mem behavioral-repairs-can-leave-their-records-and-consumers-fal`
## Summary

Real defect fixed in wave 1vqqi: All seven fresh defects the previous repair introduced are gone, and the two consumer-facing items are verified against executed behaviour rather than against the wording alone. Three residual stale numbers inside the change document's own…

## Evidence

- `DEL-10`
- `ev-del-10-3`
- `1vqqi`

## Targets

- `techdocs_audit.py`
