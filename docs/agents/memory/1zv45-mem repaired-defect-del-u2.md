# Repaired defect DEL-U2

Owner: Engineering
Status: superseded
Last verified: 2026-10-04

Memory ID: `1zv45-mem repaired-defect-del-u2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-04
Updated: 2026-10-04
Source exploration cost: 282431
Source event: `finding:1zrak:DEL-U2`
Validation: rewrite
Validated by: agent
Action delta: New tests that name record roots must derive them from the layout roots (self.roots.waves_rel), never write docs/waves literals, or the profile literal census fails the full suite.
Validation rationale: DEL-U2: the new fail-closed discovery tests hard-coded docs/waves and passed focused runs but failed test_profile_literal_census in the full suite. Fixed by deriving from self.roots.waves_rel.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zuc1-mem record-root-literals-in-new-tests-trip-the-profile-census`

## Summary

Real defect fixed in wave 1zrak: resolved

## Evidence

- `DEL-U2`
- `ev-del-u2-3`
- `1zrak`

## Targets

- `tests/test_record_discovery_fail_closed.py`
