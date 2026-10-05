# Record-root literals in new tests trip the profile census

Owner: Engineering
Status: active
Last verified: 2026-10-04

Memory ID: `1zuc1-mem record-root-literals-in-new-tests-trip-the-profile-census`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 282431
Source event: `finding:1zrak:DEL-U2`
Validation: promote
Validated by: agent
Action delta: New tests that name record roots must derive them from the layout roots (self.roots.waves_rel), never write docs/waves literals, or the profile literal census fails the full suite.
Validation rationale: DEL-U2: the new fail-closed discovery tests hard-coded docs/waves and passed focused runs but failed test_profile_literal_census in the full suite. Fixed by deriving from self.roots.waves_rel.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Tests that create wave or plan folders must take the paths from the layout roots (self.roots.waves_rel and similar), not docs/waves literals. A literal passes focused runs but fails test_profile_literal_census in the full suite. Run the census module in focused runs when adding such tests.

## Evidence

- `DEL-U2`
- `ev-del-u2-3`
- `1zrak`

## Targets

- `.wavefoundry/framework/scripts/tests/test_record_discovery_fail_closed.py`
