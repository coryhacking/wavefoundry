# Fragile: test_upgrade_protocol.py

Owner: Engineering
Status: candidate
Last verified: 2026-09-09

Memory ID: `1xk6g-mem fragile-test-upgrade-protocol-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-09
Updated: 2026-09-09
Source exploration cost: 3648456
Source event: `repeated-repairs:1tz6l:test_upgrade_protocol.py`
Validation: pending

## Summary

test_upgrade_protocol.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `bridge-recovery-carriers-violate-agent-shell-multihost-contract`
- `release-main-does-not-enforce-single-public-package`
- `1tz6l`

## Targets

- `test_upgrade_protocol.py`
