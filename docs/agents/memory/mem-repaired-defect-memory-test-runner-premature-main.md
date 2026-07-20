# Repaired defect memory-test-runner-premature-main

Owner: Engineering
Status: superseded
Last verified: 2026-07-19

Memory ID: `mem-repaired-defect-memory-test-runner-premature-main`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-07-19
Updated: 2026-07-19
Source exploration cost: 1764640
Source event: `finding:1sxj7:memory-test-runner-premature-main`
Validation: rewrite
Validated by: agent
Action delta: Keep unittest.main() at the physical end of each directly executed test module so the canonical per-file runner registers every test class.
Validation rationale: Direct execution previously stopped at line 281 and ran only 16 tests; after moving the block to EOF the same file runs 141 tests. The current target and direct execution were independently verified.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `mem-place-unittest-main-at-eof-in-per-file-test-modules`
## Summary

Real defect fixed in wave 1sxj7: Independent QA verified the repaired behavior with executable evidence.

## Evidence

- `memory-test-runner-premature-main`
- `ev-memory-test-runner-premature-main-3`
- `1sxj7`

## Targets

- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
