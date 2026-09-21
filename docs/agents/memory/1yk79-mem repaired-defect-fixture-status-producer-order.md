# Repaired defect fixture-status-producer-order

Owner: Engineering
Status: rejected
Last verified: 2026-09-21

Memory ID: `1yk79-mem repaired-defect-fixture-status-producer-order`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-21
Updated: 2026-09-21
Source exploration cost: 403004
Source event: `finding:1yd24:fixture-status-producer-order`
Validation: reject
Validated by: agent
Action delta: No additional durable action: follow seed-209 fixture fidelity and the helper's explicit post-producer status contract, already pinned by regression tests.
Validation rationale: Read candidate and complete fixture-status-producer-order evidence chain through ev-fixture-status-producer-order-4; current helper applies status last and rejects ready, and tests kill both regressions. Candidate summary is administrative lane clearance rather than actionable knowledge, its extracted target fixture-fidelity/status-order-mutation-probe.py does not exist, and canonical seed209 already requires canonical producer prerequisites plus independent path-reachability verification. No separate memory is needed for this repaired implementation detail; preserve evidence in wave report. Related existing memories 1vn0v and 1u8q2 already cover producer-built fresh-tree fixtures and mutating-seam/polarity checks.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Real defect fixed in wave 1yd24: Unchanged contract now satisfied; focused repair independently verified; clear acting QA lane.

## Evidence

- `fixture-status-producer-order`
- `ev-fixture-status-producer-order-4`
- `1yd24`

## Targets

- `fixture-fidelity/status-order-mutation-probe.py`
