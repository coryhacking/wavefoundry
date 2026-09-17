# Verify package contents through the real release and injection paths

Owner: Engineering
Status: active
Last verified: 2026-09-17

Memory ID: `1y7ig-mem verify-package-contents-through-the-real-release-and-injecti`
Kind: `review_finding`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-09-17
Supersedes: `1tzsp-mem`

## Summary

When changing packaging, execute build_pack.main and assert exactly one public wavefoundry-<version>.zip; internal bridge/composition artifacts must not leak into distribution. Also inspect a real build with install-template injection and explicitly reject each retired member (including root wavefoundry-install-log.md). Helper allowlist tests alone cannot detect a member reintroduced by the actual writer. Keep both entrypoint/cardinality and injected-member negative controls.

## Evidence

- `consolidated from 1tzsp-mem`
- `consolidated from 1vkk1-mem retired-pack-members-need-an-exact-absence-assertion-on-a-re`

## Targets

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
