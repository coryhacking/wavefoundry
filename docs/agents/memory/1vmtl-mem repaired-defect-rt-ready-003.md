# Repaired defect RT-READY-003

Owner: Engineering
Status: rejected
Last verified: 2026-08-17

Memory ID: `1vmtl-mem repaired-defect-rt-ready-003`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `finding:1viyu:RT-READY-003`
Validation: reject
Validated by: agent
Action delta: No separate action: the lesson (registered tool description and root README are public carriers that need semantic-anchor tests) is carried by the rewritten record 1vlnj-mem from DOC-READY-002, which cites RT-READY-003 as evidence.
Validation rationale: RT-READY-003 (red-team, implementing session) and DOC-READY-002 (docs-contract) name the same gap from two seats: newly discovered public carriers of the wf_audit_install contract lacked ownership and mutation-sensitive tests. The generated draft ("closes the carrier-test and ownership-map gap with bounded executable checks") restates plan status and would duplicate 1vlnj-mem; the ledger keeps the finding history, so a second memory adds retrieval noise without a distinct future action.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1viyu: The repaired plan closes the carrier-test and ownership-map gap with bounded executable checks.

## Evidence

- `RT-READY-003`
- `ev-rt-ready-003-3`
- `1viyu`

## Targets

- `test_server_tools.py`
