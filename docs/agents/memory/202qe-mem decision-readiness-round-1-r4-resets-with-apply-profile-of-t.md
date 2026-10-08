# Decision: Readiness round 1: R4 resets with `apply_profile` of the sh…

Owner: Engineering
Status: rejected
Last verified: 2026-10-08

Memory ID: `202qe-mem decision-readiness-round-1-r4-resets-with-apply-profile-of-t`
Kind: `decision`
Confidence: 0.6
Created: 2026-10-08
Updated: 2026-10-08
Source exploration cost: 1072877
Source event: `decision-log:200ex-maint distribution-safe-framework-tests:ea54efa0785d4546`
Validation: reject
Validated by: agent
Action delta: Use the canonical shipped-declaration reset helper before applying a profile.
Validation rationale: Verified 200ex Decision Log:164 and current test_profile_support.py:_shipped_declaration already encode the reset with apply_profile/SHIPPED_DECLARATION; this historical readiness narrative adds no separate action.
Evidence verified: true
Current target verified: true
Canonical overlap: duplicates

## Summary

Decision (wave 200ey): Readiness round 1: R4 resets with `apply_profile` of the shipped defaults and `SHIPPED_DECLARATION` (the `tests/test_profile_support.py` idiom, extended to the declaration module because `shipped_default_profile()` omits it), then applies the asset.. Rationale: `apply_profile` requires exactly one assignment per constant; appending `base_declaration_source` creates two and raises..

## Evidence

- `200ex-maint distribution-safe-framework-tests`
- `200ey`

## Targets

- `tests/test_profile_support.py`
