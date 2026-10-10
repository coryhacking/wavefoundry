# Mocked profile labels need consistent derived patterns

Owner: Engineering
Status: active
Last verified: 2026-10-09

Memory ID: `205d1-mem mocked-profile-labels-need-consistent-derived-patterns`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-10-09
Updated: 2026-10-09
Source exploration cost: 1492431
Source event: `finding:2071n:QA-2071N-01`
Validation: promote
Validated by: agent
Action delta: When simulating a loaded vocabulary in tests, restore derived regexes alongside their base labels and run the real corpus assertion in an actual renamed-profile copy; deleting the derived restoration must fail without skips.
Validation rationale: QA-2071N-01 was a real introduced test-fixture defect: restoring MEMBER_ID_LABEL alone left the imported second-profile MEMBER_ID_LABEL_RE matching Wave ID, so the real corpus had zero matches. The current test restores the derived pattern and independently executes1105 IDs; independent deletion controls reproduce the retained >100 assertion failure with no errors/skips. Full default/second/declared qualification is now green. Correct the generated basename-only anchor and obsolete pending-qualification summary; this supplements existing source-rewrite/value-guard memory with derived-state consistency.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Wave2071n's initial corpus meta-test restored stock vocabulary constants but left MEMBER_ID_LABEL_RE imported from the renamed profile. The actual admitted-ID assertion matched zero IDs. Restore the derived label regex with its base label, retain real >100 and zero-rejected corpus assertions, and execute an actual renamed-profile copy. Independent deletion controls detected the stale-regex defect without skips; final full default/second/declared suites and exact skip audit pass.

## Evidence

- `QA-2071N-01`
- `ev-qa-2071n-01-5`
- `docs/waves/2071n profile-skip-qualification/evidence/delivery/wf-2071n-final-qa-reality.json`
- `docs/waves/2071n profile-skip-qualification/qualification-evidence.md`

## Targets

- `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/scripts/tests/test_change_id_path_guard.py`
