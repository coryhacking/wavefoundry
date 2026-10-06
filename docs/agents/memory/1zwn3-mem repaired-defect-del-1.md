# Repaired defect DEL-1

Owner: Engineering
Status: rejected
Last verified: 2026-10-05

Memory ID: `1zwn3-mem repaired-defect-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-05
Updated: 2026-10-05
Source exploration cost: 177790
Source event: `finding:1zv8c:DEL-1`
Validation: reject
Validated by: agent
Action delta: none
Validation rationale: Summary carries no actionable lesson ("repair verified"); the durable rule (judge lock targets by file identity, not lexical prefix) is recorded in the threat model and the change doc.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Real defect fixed in wave 1zv8c: repair verified

## Evidence

- `DEL-1`
- `ev-del-1-4`
- `1zv8c`

## Targets

- `tests/test_lifecycle_lock_links.py`
