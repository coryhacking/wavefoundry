# Repaired defect reload-source-guard-omission

Owner: Engineering
Status: rejected
Last verified: 2026-09-20

Memory ID: `1yi7z-mem repaired-defect-reload-source-guard-omission`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-20
Updated: 2026-09-20
Source exploration cost: 828844
Source event: `finding:1yj14:reload-source-guard-omission`
Validation: reject
Validated by: agent
Action delta: Use the durable testing lesson recorded in docs/references/project-context-memory.md and the wave summary; reject this malformed generated record.
Validation rationale: Focused curator verified the linked repair evidence and actual canonical source/tests, but the generated target is an incorrectly relativized temporary probe path absent from the repository. memory_validate rewrite refuses that original target before accepting corrected targets. Reject malformed candidate rather than falsely attest it is current; preserve lesson in canonical project memory.
Evidence verified: true
Current target verified: false
Canonical overlap: supplements
## Summary

Real defect fixed in wave 1yj14: Independent focused replay verifies bounded repair; complete finding after required lane clearance.

## Evidence

- `reload-source-guard-omission`
- `ev-reload-source-guard-omission-3`
- `1yj14`

## Targets

- `private/tmp/wf-1yj14-reload-mutant.py`
