# Repaired defect DEL-1

Owner: Engineering
Status: rejected
Last verified: 2026-10-08

Memory ID: `202yn-mem repaired-defect-del-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 620258
Source event: `finding:203pu:DEL-1`
Validation: reject
Validated by: agent
Action delta: No durable action from this draft: its only target is a scratch probe file; the lesson is recorded as a separate fragile_file record on graph_indexer.py.
Validation rationale: The drafted target tmp/probes/probe.py is a reviewer scratch file outside the repository, so the record cannot anchor to the current tree.
Evidence verified: true
Current target verified: false
Canonical overlap: none

## Summary

Real defect fixed in wave 203pu: repaired

## Evidence

- `DEL-1`
- `ev-del-1-3`
- `203pu`

## Targets

- `tmp/probes/probe.py`
