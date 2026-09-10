# Fragile: test_build_pack.py

Owner: Engineering
Status: candidate
Last verified: 2026-09-09

Memory ID: `1xjza-mem fragile-test-build-pack-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-09-09
Updated: 2026-09-09
Source exploration cost: 3648456
Source event: `repeated-repairs:1tz6l:test_build_pack.py`
Validation: pending

## Summary

test_build_pack.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `bridge-recovery-carriers-violate-agent-shell-multihost-contract`
- `release-main-does-not-enforce-single-public-package`
- `1tz6l`

## Targets

- `test_build_pack.py`
