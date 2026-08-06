# Fragile: test_review_policy.py

Owner: Engineering
Status: superseded
Last verified: 2026-08-05

Memory ID: `1uh3m-mem fragile-test-review-policy-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-08-05
Updated: 2026-08-05
Source exploration cost: 579028
Source event: `repeated-repairs:1uhcb:test_review_policy.py`
Validation: rewrite
Validated by: agent
Action delta: When testing a section-region scanner, build each fixture so a genuine instance of the target section follows the construct under test, then run the fixture against a mutant that breaks the specific boundary (marker-matched fence toggle, heading level) and confirm it fails; also diff the new pattern's line-ending tolerance against the nearest sibling pattern in the same module.
Validation rationale: The generated candidate's premise does not survive checking. test_review_policy.py is the test file for the change under review, so both repairs landing there is the expected shape of any red-first delivery, not evidence of fragility; the file has no history of unrelated breakage and the drafted target was a bare basename rather than a repo-relative path. The durable signal in the same evidence is the vacuity mechanism the two findings actually exposed: verified in the current tree that test_review_policy.py:1109 and :1136 are the cases added specifically because two mutants survived the five delivered fence tests, and that gardener_metadata.py:12-15 records the CRLF asymmetry against the sibling _GARDENER_DATE_LINE_RE. Rewritten to that reusable control with full repo-relative targets.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1ufqs-mem region-scanner-tests-need-a-real-target-section-after-the-co`
## Summary

test_review_policy.py required 2 separate repairs during wave 1uhcb; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `crlf-change-doc-bypasses-progress-log-exclusion`
- `false-shipped-claims-and-unpinned-boundaries`
- `1uhcb`

## Targets

- `test_review_policy.py`
