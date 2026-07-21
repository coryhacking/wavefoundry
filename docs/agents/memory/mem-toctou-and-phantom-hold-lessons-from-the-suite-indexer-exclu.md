# TOCTOU and phantom-hold lessons from the suite/indexer exclusion

Owner: Engineering
Status: active
Last verified: 2026-07-20

Memory ID: `mem-toctou-and-phantom-hold-lessons-from-the-suite-indexer-exclu`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-20
Updated: 2026-07-20
Source event: `finding:1t72b:suite-indexer-exclusion-toctou-race`
Validation: promote
Validated by: agent
Action delta: When coordinating two processes via check-then-act on each other's locks, re-check atomically after acquiring your own lock, and never wait while holding: a deferring holder presents as a phantom running process to every other waiter.
Validation rationale: The drafted candidate is accurate but thin: it targets only run_tests.py (indexer's token in public_path lacks a file suffix) and omits the durable two-part lesson — the TOCTOU itself, and the defer-while-holding first draft that was live-refuted within the hour by a phantom-build 600s test hang.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1t72b (1t727): the suite/indexer mutual exclusion was twice wrong before it was right. First, check-then-act — each side probed the other's lock BEFORE acquiring its own — let simultaneous starts race (operator-caught TOCTOU). Second, the repair draft deferred while HOLDING the build lock, and a hook-spawned build deferring to a running suite presented as a phantom running build, hanging unit tests for their full 600s budget. Final design: check the other's lock only AFTER acquiring your own (atomic with ownership), and never wait while holding — release, wait unlocked, retry with bounded cycles and safe endgames (suite fails loudly; build proceeds).

## Evidence

- `suite-indexer-exclusion-toctou-race`
- `ev-suite-indexer-exclusion-toctou-race-3`
- `test_build_defers_unlocked_until_test_lock_releases`
- `1t72b`

## Targets

- `.wavefoundry/framework/scripts/run_tests.py`
- `.wavefoundry/framework/scripts/indexer.py`
