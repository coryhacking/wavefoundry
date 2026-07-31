# Fragile: test_upgrade_protocol.py

Owner: Engineering
Status: rejected
Last verified: 2026-07-31

Memory ID: `1u1rc-mem fragile-test-upgrade-protocol-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 2939264
Source event: `repeated-repairs:1tz6l:test_upgrade_protocol.py`
Validation: reject
Validated by: agent
Action delta: No new action: the durable cross-platform bundle/recovery matrix is already captured by active memory 1tz9e-mem against upgrade_bundle.py and its tests.
Validation rationale: The candidate infers fragility from two test-file touches and targets only a test filename. The actionable lesson is already recorded with the implementation boundary and exact recovery matrix, so retaining this would duplicate and weaken retrieval.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

test_upgrade_protocol.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `bridge-recovery-carriers-violate-agent-shell-multihost-contract`
- `release-main-does-not-enforce-single-public-package`
- `1tz6l`

## Targets

- `test_upgrade_protocol.py`
