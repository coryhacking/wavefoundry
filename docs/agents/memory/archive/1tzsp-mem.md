# Release packaging tests must pin the single public package

Owner: Engineering
Status: archived
Last verified: 2026-07-30

Memory ID: `1tzsp-mem`
Superseded by: `1y7ig-mem verify-package-contents-through-the-real-release-and-injecti`
Kind: `review_finding`
Confidence: 0.95
Created: 2026-07-30
Updated: 2026-09-17
Supersedes: `1tzj7-mem`

Archived: 2026-09-17
Archive reason: consolidated into 1y7ig-mem verify-package-contents-through-the-real-release-and-injecti
Archive path: `docs/agents/memory/archive/1tzsp-mem.md`
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
