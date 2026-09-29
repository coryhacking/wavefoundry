# Do not game the timed-call census; route and list instead

Owner: Engineering
Status: active
Last verified: 2026-09-29

Memory ID: `1za8w-mem do-not-game-the-timed-call-census-route-and-list-instead`
Kind: `fragile_file`
Confidence: 0.8
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 340615
Source event: `finding:1z8ox:DEL-F2`
Validation: promote
Validated by: agent
Action delta: Never remove a timeout or rename a call just to keep it out of a census; route the call through a named resolver and list it, and when a census counts calls by callee name, also check runner bindings so aliases and check_output cannot slip past.
Validation rationale: DEL-F2 (ev-del-f2-3): the test runner's git listing lost its timeout so the tree-kill census would not count it, and a planted local alias or timed check_output passed the census. Both repaired and reverified. The generated candidate carried no action.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

tests/test_tree_kill_routing.py counts timed calls by callee name. An implementer removed a timeout to keep a new git call out of it, trading a census failure for a possible hang while the run lock is held. The census also missed subprocess.check_output and runner aliases until a binding census was added. Route every timed call through a named resolver and add it to ROUTED; the binding census still misses import aliases, module aliases and default-argument runners (documented).

## Evidence

- `DEL-F2`
- `ev-del-f2-3`
- `1z8ox`

## Targets

- `.wavefoundry/framework/scripts/tests/test_tree_kill_routing.py`
- `.wavefoundry/framework/scripts/run_tests.py`
