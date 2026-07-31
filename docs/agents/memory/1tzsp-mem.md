# Release packaging tests must pin the single public package

Owner: Engineering
Status: active
Last verified: 2026-07-30

Memory ID: `1tzsp-mem`
Kind: `review_finding`
Confidence: 0.95
Created: 2026-07-30
Updated: 2026-07-30
Supersedes: `1tzj7-mem`

## Summary

Helper-level packaging tests can pass while the release entry point emits the wrong artifact set. Execute build_pack.main and assert that dist contains exactly one public wavefoundry-<version>.zip; bridge composition files must remain internal and be cleaned before publication.

## Evidence

- `wave 1tz6l`
- `change 1txh7`
- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`

## Targets

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
