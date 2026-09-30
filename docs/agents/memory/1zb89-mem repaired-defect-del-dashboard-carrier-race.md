# Repaired defect DEL-DASHBOARD-CARRIER-RACE

Owner: Engineering
Status: rejected
Last verified: 2026-09-29

Memory ID: `1zb89-mem repaired-defect-del-dashboard-carrier-race`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 526079
Source event: `finding:1zc7n:DEL-DASHBOARD-CARRIER-RACE`
Validation: reject
Validated by: agent
Action delta: No durable action from this draft: it targets a scratch reviewer script outside the tree; the lesson is recorded as a separate memory.
Validation rationale: Generated candidate names rev-1zc7n/repro.py (a scratch path from the reverification command) as a target and has a disposition-only summary, so it cannot be rewritten in place.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Real defect fixed in wave 1zc7n: Repair resolves the finding: carrier ownership invariant holds with one shared lock protocol

## Evidence

- `DEL-DASHBOARD-CARRIER-RACE`
- `ev-del-dashboard-carrier-race-4`
- `1zc7n`

## Targets

- `wf_server/dashboard_handlers.py`
- `tests/test_process_info_callers.py`
- `rev-1zc7n/repro.py`
