# Fragile: test_upgrade_wavefoundry.py

Owner: Engineering
Status: candidate
Last verified: 2026-09-09

Memory ID: `1xkmp-mem fragile-test-upgrade-wavefoundry-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-09
Updated: 2026-09-09
Source exploration cost: 818447
Source event: `repeated-repairs:1u2b0:test_upgrade_wavefoundry.py`
Validation: pending

## Summary

test_upgrade_wavefoundry.py required 2 separate repairs during wave 1u2b0; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `preexisting-rules-never-adopted-defeats-motivating-case`
- `permissions-backstop-unreachable-on-default-upgrade-path`
- `1u2b0`

## Targets

- `test_upgrade_wavefoundry.py`
