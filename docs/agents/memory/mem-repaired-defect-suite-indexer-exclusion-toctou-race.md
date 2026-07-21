# Repaired defect suite-indexer-exclusion-toctou-race

Owner: Engineering
Status: superseded
Last verified: 2026-07-20

Memory ID: `mem-repaired-defect-suite-indexer-exclusion-toctou-race`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-20
Updated: 2026-07-20
Source exploration cost: 49128
Source event: `finding:1t72b:suite-indexer-exclusion-toctou-race`
Validation: rewrite
Validated by: agent
Action delta: When coordinating two processes via check-then-act on each other's locks, re-check atomically after acquiring your own lock, and never wait while holding: a deferring holder presents as a phantom running process to every other waiter.
Validation rationale: The drafted candidate is accurate but thin: it targets only run_tests.py (indexer's token in public_path lacks a file suffix) and omits the durable two-part lesson — the TOCTOU itself, and the defer-while-holding first draft that was live-refuted within the hour by a phantom-build 600s test hang.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-toctou-and-phantom-hold-lessons-from-the-suite-indexer-exclu`
## Summary

Real defect fixed in wave 1t72b: The repair was refuted once by live evidence and revised; the revised design is confirmed by behavior, ordering, and full-suite evidence.

## Evidence

- `suite-indexer-exclusion-toctou-race`
- `ev-suite-indexer-exclusion-toctou-race-3`
- `1t72b`

## Targets

- `run_tests.py`
