# Mid-file unittest.main hides later tests

Owner: Engineering
Status: archived
Last verified: 2026-07-18

Memory ID: `1sxln-mem mid-file-unittest-main-hides-later-tests`
Superseded by: `1t018-mem place-unittest-main-at-eof-in-per-file-test-modules`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-07-18
Updated: 2026-11-22
Source event: `finding:1slep:qa-build-pack-direct-run`
Validation: promote
Validated by: agent
Action delta: Before trusting direct execution of a unittest file, keep unittest.main() at EOF and compare its test count with the canonical per-file runner.
Validation rationale: The executed 1slep repair proved that a mid-file unittest.main() terminated discovery before later classes while still exiting green; the current file keeps the entrypoint at EOF.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Archived: 2026-11-22
Archive reason: Retired by the active-record audit on 2026-11-22: superseded by 1t018, which states the same unittest.main-at-EOF rule for every test module run by the canonical runner; the original 1slep test_build_pack.py incident is kept for history.
Archive path: `docs/agents/memory/archive/1sxln-mem mid-file-unittest-main-hides-later-tests.md`

## Summary

A mid-file unittest.main() can exit before later test classes are defined while reporting green; keep the entrypoint at EOF and compare direct-execution counts with the canonical runner.

## Evidence

- `1slep`
- `qa-build-pack-direct-run`
- `ev-qa-build-pack-direct-run-3`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`

## Targets

- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
