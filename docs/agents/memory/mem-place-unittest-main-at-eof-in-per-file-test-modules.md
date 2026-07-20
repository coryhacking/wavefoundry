# Place unittest.main at EOF in per-file test modules

Owner: Engineering
Status: active
Last verified: 2026-07-19

Memory ID: `mem-place-unittest-main-at-eof-in-per-file-test-modules`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-07-19
Updated: 2026-07-19
Source event: `finding:1sxj7:memory-test-runner-premature-main`
Validation: promote
Validated by: agent
Action delta: Keep unittest.main() at the physical end of each directly executed test module so the canonical per-file runner registers every test class.
Validation rationale: Direct execution previously stopped at line 281 and ran only 16 tests; after moving the block to EOF the same file runs 141 tests. The current target and direct execution were independently verified.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

In test modules executed directly by the canonical runner, place the single unittest.main() block at the physical end of the file. A mid-file block starts and exits before later test classes are defined, silently shrinking coverage while still returning a green result.

## Evidence

- `1sxj7`
- `memory-test-runner-premature-main`
- `ev-memory-test-runner-premature-main-3`
- `python3 -B .wavefoundry/framework/scripts/tests/test_memory_records.py`

## Targets

- `.wavefoundry/framework/scripts/tests/test_memory_records.py`
- `.wavefoundry/framework/scripts/run_tests.py`
