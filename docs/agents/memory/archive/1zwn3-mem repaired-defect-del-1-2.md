# Repaired defect DEL-1

Owner: Engineering
Status: archived
Last verified: 2026-10-06

Memory ID: `1zwn3-mem repaired-defect-del-1-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-10-06
Updated: 2026-11-25
Source exploration cost: 190020
Source event: `finding:1zyc3:DEL-1`
Validation: promote
Validated by: agent
Action delta: In framework Python outside vocabulary_profile.py, including docstrings, do not write record-vocabulary markers such as ``wave.md``; say 'the wave record' instead, or test_vocabulary_census fails with an unrouted site.
Validation rationale: Wave 1zyc3's wf_review_event docstring named ``wave.md`` and failed test_census_has_no_unrouted_sites only in the full suite.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Checked at: 2026-11-25T16:09:23Z
Check note: Item 7 review: encoded elsewhere. The whole lesson (no record-vocabulary marker such as wave.md in framework Python outside vocabulary_profile.py, docstrings included) is enforced by tests/test_vocabulary_census.py:161 VocabularyCensusTests::test_census_has_no_unrouted_sites, whose failure message names the remedy; the record's own summary is empty. Assertion: tests/test_vocabulary_census.py::Voc.
Check flags: target_not_canonical
Archived: 2026-11-25
Archive reason: Retired in the 244cm item 7 review, encoded in The whole lesson (no record-vocabulary marker such as wave.md in framework Python outside vocabulary_profile.py, docstrings included) is enforced by tests/test_vocabulary_census.py:161 VocabularyCensusTests::test_census_has_no_unrouted_sites, whose fai.
Archive path: `docs/agents/memory/archive/1zwn3-mem repaired-defect-del-1-2.md`

## Summary

Real defect fixed in wave 1zyc3: resolved

## Evidence

- `DEL-1`
- `ev-del-1-3`
- `1zyc3`

## Targets

- `test_vocabulary_census.py`
