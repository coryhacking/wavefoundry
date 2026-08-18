# Retired pack members need an exact absence assertion on a real injected build, not just an allowlist edit

Owner: Engineering
Status: active
Last verified: 2026-08-17

Memory ID: `1vkk1-mem retired-pack-members-need-an-exact-absence-assertion-on-a-re`
Kind: `review_finding`
Confidence: 0.85
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `finding:1viyu:RT-FINAL-007`
Validation: promote
Validated by: agent
Action delta: When retiring a shipped artifact, remove it from every pack allowlist and docstring AND add an exact absence assertion on a real injected build; an allowlist that still permits the retired member lets a phantom reappear silently, and an in-memory self-test of the allowlist helper is not the same guard.
Validation rationale: RT-FINAL-007 (red-team, implementing session): the build-pack test still allowed and documented the phantom zip-root wavefoundry-install-log.md and lacked an exact absence assertion, so a virtual reintroduction passed. Verified now: _ALLOWED_PACK_PREFIXES no longer lists it, test_phantom_root_install_log_fails_the_public_member_contract exists, and the release lane's real-build mutant (reintroducing zf.writestr of the phantom in a scratch copy) was caught by test_install_log_template_ships_in_framework_tree, while the in-memory negative and the un-injected prefix test stayed green (REL-DEL-3), which is exactly the nuance worth remembering. The draft summary was plan status; the rewrite states the rule and the real-build caveat.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1viyu (RT-FINAL-007, REL-DEL-3): the phantom zip-root wavefoundry-install-log.md had been retired from the pack years of releases earlier, but test_build_pack still listed it in the allowlist and docstring, so reintroducing it would have passed. The repair removed it from _ALLOWED_PACK_PREFIXES and added test_phantom_root_install_log_fails_the_public_member_contract; the release lane then showed by a scratch-copy mutant (real zf.writestr reintroduction) that the member-contract self-test and the un-injected prefix test stay green and only test_install_log_template_ships_in_framework_tree (which builds with inject_install_templates=True) catches a real reintroduction. Rule: for every retired shipped artifact, assert its absence on a build that goes through the real injection path; helper self-tests and allowlist edits are necessary but not sufficient.

## Evidence

- `RT-FINAL-007`
- `ev-rt-final-007-3`
- `test_build_pack.InstallTemplateInjectionTests.test_install_log_template_ships_in_framework_tree`
- `test_build_pack.BuildPackTests.test_phantom_root_install_log_fails_the_public_member_contract`
- `scratchpad/release-reviewer/mutation-phantom.log`

## Targets

- `.wavefoundry/framework/scripts/tests/test_build_pack.py`
- `.wavefoundry/framework/scripts/build_pack.py`
