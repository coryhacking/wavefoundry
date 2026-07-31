# Fragile: test_build_pack.py

Owner: Engineering
Status: rejected
Last verified: 2026-07-31

Memory ID: `1u1k6-mem fragile-test-build-pack-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 2939264
Source event: `repeated-repairs:1tz6l:test_build_pack.py`
Validation: reject
Validated by: agent
Action delta: No new action: active memory 1tzsp-mem already requires executing build_pack.main and asserting the one-public-package invariant at the implementation/release boundary.
Validation rationale: The candidate targets only the test carrier and repeats a lesson already captured against build_pack.py with the precise production-entry-point action. Keeping both would dilute retrieval without adding a distinct decision rule.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates
## Summary

test_build_pack.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `bridge-recovery-carriers-violate-agent-shell-multihost-contract`
- `release-main-does-not-enforce-single-public-package`
- `1tz6l`

## Targets

- `test_build_pack.py`
