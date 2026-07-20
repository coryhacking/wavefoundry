# Decision: Mirror `dashboard_lib.py`'s `os.name` `fcntl`/`msvcrt` spli…

Owner: Engineering
Status: rejected
Last verified: 2026-07-18

Memory ID: `mem-decision-mirror-dashboard-lib-py-s-os-name-fcntl-msvcrt-spli`
Kind: `decision`
Confidence: 0.6
Created: 2026-07-18
Updated: 2026-07-18
Source exploration cost: 0
Source event: `decision-log:1p9iy-bug dev-test-infra-windows-hardening:b3eeeb617bdee79c`
Validation: reject
Validated by: agent
Action delta: None; inspect the current shared locking and subprocess utilities before choosing a portability abstraction.
Validation rationale: The historical no-abstraction choice was local to the old test runner and is not durable architecture guidance.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

Decision (wave 1p9j0): Mirror `dashboard_lib.py`'s `os.name` `fcntl`/`msvcrt` split in `run_tests.py` rather than adding a shared lock abstraction.. Rationale: Proven in-tree pattern; keeps the fix minimal and consistent with `dashboard_lib.py`/`indexer.py`..

## Evidence

- `1p9iy-bug dev-test-infra-windows-hardening`
- `1p9j0`

## Targets

- `dashboard_lib.py`
- `run_tests.py`
- `indexer.py`
