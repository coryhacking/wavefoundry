# Verify package contents through the real release and injection paths

Owner: Engineering
Status: active
Last verified: 2026-11-25

Memory ID: `1y7ig-mem verify-package-contents-through-the-real-release-and-injecti`
Kind: `review_finding`
Confidence: 0.6
Created: 2026-09-17
Updated: 2026-11-25
Supersedes: `1tzsp-mem`
Checked at: 2026-11-25T16:09:22Z
Check note: Checked build_pack.py and tests/test_build_pack.py: the root install-log absence is asserted (:58, :1954), but no test builds with inject_install_templates=True, so the injected-member control is still needed; the summary already states its situation.
Check flags: none

## Summary

When changing packaging, execute build_pack.main and assert exactly one public wavefoundry-<version>.zip; internal bridge/composition artifacts must not leak into distribution. Also inspect a real build with install-template injection and explicitly reject each retired member (including root wavefoundry-install-log.md). Helper allowlist tests alone cannot detect a member reintroduced by the actual writer. Keep both entrypoint/cardinality and injected-member negative controls.

## Evidence

- `consolidated from 1tzsp-mem`
- `consolidated from 1vkk1-mem retired-pack-members-need-an-exact-absence-assertion-on-a-re`

## Targets

- `.wavefoundry/framework/scripts/build_pack.py`
- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
