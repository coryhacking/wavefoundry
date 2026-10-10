# Repaired defect QA-2071N-01

Owner: Engineering
Status: superseded
Last verified: 2026-10-09

Memory ID: `2069j-mem repaired-defect-qa-2071n-01`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-09
Updated: 2026-10-09
Source exploration cost: 1492431
Source event: `finding:2071n:QA-2071N-01`
Validation: rewrite
Validated by: agent
Action delta: When simulating a loaded vocabulary in tests, restore derived regexes alongside their base labels and run the real corpus assertion in an actual renamed-profile copy; deleting the derived restoration must fail without skips.
Validation rationale: QA-2071N-01 was a real introduced test-fixture defect: restoring MEMBER_ID_LABEL alone left the imported second-profile MEMBER_ID_LABEL_RE matching Wave ID, so the real corpus had zero matches. The current test restores the derived pattern and independently executes1105 IDs; independent deletion controls reproduce the retained >100 assertion failure with no errors/skips. Full default/second/declared qualification is now green. Correct the generated basename-only anchor and obsolete pending-qualification summary; this supplements existing source-rewrite/value-guard memory with derived-state consistency.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `205d1-mem mocked-profile-labels-need-consistent-derived-patterns`

## Summary

Real defect fixed in wave 2071n: Completed bounded repair independently verified by the acting lane. Whole-delivery approval awaits final full qualification.

## Evidence

- `QA-2071N-01`
- `ev-qa-2071n-01-5`
- `2071n`

## Targets

- `test_profile_support.py`
