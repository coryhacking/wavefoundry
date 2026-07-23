# Repaired defect pending-archive-docs-gate-has-no-recovery

Owner: Engineering
Status: superseded
Last verified: 2026-07-22

Memory ID: `1tb6q-mem repaired-defect-pending-archive-docs-gate-has-no-recovery`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-22
Updated: 2026-07-22
Source exploration cost: 408549
Source event: `finding:1t8la:pending-archive-docs-gate-has-no-recovery`
Validation: rewrite
Validated by: agent
Action delta: When a fenced multi-step lifecycle can be interrupted, give its intermediate on-disk state a lint/gate diagnostic that names the exact retry command instead of a bare schema error.
Validation rationale: The generated summary only echoed the lane-clearance prose; the durable lesson is the recovery-route principle. Verified against the repaired check_memory_docs branch: the pending-archive state (retired-status body under memory/archive after the rename window) now yields a diagnostic naming the memory_reconcile retry, pinned by regression, while completed-archive validation stays strict.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1td27-mem interrupted-lifecycle-states-need-a-named-recovery-route`
## Summary

Real defect fixed in wave 1t8la: Code lane independently reassessed and cleared after repair; chain terminal.

## Evidence

- `pending-archive-docs-gate-has-no-recovery`
- `ev-pending-archive-docs-gate-has-no-recovery-6`
- `1t8la`

## Targets

- `wave_validators.py`
