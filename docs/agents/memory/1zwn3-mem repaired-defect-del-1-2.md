# Repaired defect DEL-1

Owner: Engineering
Status: active
Last verified: 2026-10-06

Memory ID: `1zwn3-mem repaired-defect-del-1-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-06
Updated: 2026-10-06
Source exploration cost: 190020
Source event: `finding:1zyc3:DEL-1`
Validation: promote
Validated by: agent
Action delta: In framework Python outside vocabulary_profile.py, including docstrings, do not write record-vocabulary markers such as ``wave.md``; say 'the wave record' instead, or test_vocabulary_census fails with an unrouted site.
Validation rationale: Wave 1zyc3's wf_review_event docstring named ``wave.md`` and failed test_census_has_no_unrouted_sites only in the full suite.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

Real defect fixed in wave 1zyc3: resolved

## Evidence

- `DEL-1`
- `ev-del-1-3`
- `1zyc3`

## Targets

- `test_vocabulary_census.py`
