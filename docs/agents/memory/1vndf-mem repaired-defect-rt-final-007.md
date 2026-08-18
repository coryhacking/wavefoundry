# Repaired defect RT-FINAL-007

Owner: Engineering
Status: superseded
Last verified: 2026-08-17

Memory ID: `1vndf-mem repaired-defect-rt-final-007`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `finding:1viyu:RT-FINAL-007`
Validation: rewrite
Validated by: agent
Action delta: When retiring a shipped artifact, remove it from every pack allowlist and docstring AND add an exact absence assertion on a real injected build; an allowlist that still permits the retired member lets a phantom reappear silently, and an in-memory self-test of the allowlist helper is not the same guard.
Validation rationale: RT-FINAL-007 (red-team, implementing session): the build-pack test still allowed and documented the phantom zip-root wavefoundry-install-log.md and lacked an exact absence assertion, so a virtual reintroduction passed. Verified now: _ALLOWED_PACK_PREFIXES no longer lists it, test_phantom_root_install_log_fails_the_public_member_contract exists, and the release lane's real-build mutant (reintroducing zf.writestr of the phantom in a scratch copy) was caught by test_install_log_template_ships_in_framework_tree, while the in-memory negative and the un-injected prefix test stayed green (REL-DEL-3), which is exactly the nuance worth remembering. The draft summary was plan status; the rewrite states the rule and the real-build caveat.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1vkk1-mem retired-pack-members-need-an-exact-absence-assertion-on-a-re`
## Summary

Real defect fixed in wave 1viyu: The exact negative pack contract closes the release-carrier gap.

## Evidence

- `RT-FINAL-007`
- `ev-rt-final-007-3`
- `1viyu`

## Targets

- `test_build_pack.py`
