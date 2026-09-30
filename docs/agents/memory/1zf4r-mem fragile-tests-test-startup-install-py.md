# Fragile: tests/test_startup_install.py

Owner: Engineering
Status: rejected
Last verified: 2026-09-29

Memory ID: `1zf4r-mem fragile-tests-test-startup-install-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-29
Updated: 2026-09-29
Source exploration cost: 413440
Source event: `repeated-repairs:1zfd9:tests/test_startup_install.py`
Validation: reject
Validated by: agent
Action delta: None; no action follows from this candidate.
Validation rationale: The two cited findings were repaired in server.py and upgrade_wavefoundry.py; the test file only gained coverage. Not fragile.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

tests/test_startup_install.py required 2 separate repairs during wave 1zfd9; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `DEL-STARTUP-ENTRY-UNTESTED`
- `DEL-SETUP-COMMAND-QUOTING`
- `1zfd9`

## Targets

- `tests/test_startup_install.py`
