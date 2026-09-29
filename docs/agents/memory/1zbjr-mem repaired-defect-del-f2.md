# Repaired defect DEL-F2

Owner: Engineering
Status: superseded
Last verified: 2026-09-29

Memory ID: `1zbjr-mem repaired-defect-del-f2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 340615
Source event: `finding:1z8ox:DEL-F2`
Validation: rewrite
Validated by: agent
Action delta: Never remove a timeout or rename a call just to keep it out of a census; route the call through a named resolver and list it, and when a census counts calls by callee name, also check runner bindings so aliases and check_output cannot slip past.
Validation rationale: DEL-F2 (ev-del-f2-3): the test runner's git listing lost its timeout so the tree-kill census would not count it, and a planted local alias or timed check_output passed the census. Both repaired and reverified. The generated candidate carried no action.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1za8w-mem do-not-game-the-timed-call-census-route-and-list-instead`

## Summary

Real defect fixed in wave 1z8ox: Resolved.

## Evidence

- `DEL-F2`
- `ev-del-f2-3`
- `1z8ox`

## Targets

- `tests/test_tree_kill_routing.py`
