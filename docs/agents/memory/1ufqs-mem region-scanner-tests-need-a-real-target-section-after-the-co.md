# Region-scanner tests need a real target section after the construct under test

Owner: Engineering
Status: active
Last verified: 2026-08-05

Memory ID: `1ufqs-mem region-scanner-tests-need-a-real-target-section-after-the-co`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-08-05
Updated: 2026-08-05
Source exploration cost: 579028
Source event: `repeated-repairs:1uhcb:test_review_policy.py`
Validation: promote
Validated by: agent
Action delta: When testing a section-region scanner, build each fixture so a genuine instance of the target section follows the construct under test, then run the fixture against a mutant that breaks the specific boundary (marker-matched fence toggle, heading level) and confirm it fails; also diff the new pattern's line-ending tolerance against the nearest sibling pattern in the same module.
Validation rationale: The generated candidate's premise does not survive checking. test_review_policy.py is the test file for the change under review, so both repairs landing there is the expected shape of any red-first delivery, not evidence of fragility; the file has no history of unrelated breakage and the drafted target was a bare basename rather than a repo-relative path. The durable signal in the same evidence is the vacuity mechanism the two findings actually exposed: verified in the current tree that test_review_policy.py:1109 and :1136 are the cases added specifically because two mutants survived the five delivered fence tests, and that gardener_metadata.py:12-15 records the CRLF asymmetry against the sibling _GARDENER_DATE_LINE_RE. Rewritten to that reusable control with full repo-relative targets.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

When testing a scanner that locates a document section and excludes it up to the next boundary, a fixture that omits a REAL instance of the target section after the construct under test proves only that some guard exists, not that the guard is correct. Wave 1uhcb delivered five fence tests for the Progress Log exclusion and two mutants survived all of them: a fence toggle that closes on any marker rather than the matching one, and a region that ends at any heading level rather than at `## `. Neither fixture placed a genuine `## Progress Log` after the fenced or heading construct, so both passed on a broken scanner. Each mutant is killed only by a case that does place one. The sibling boundary lesson from the same wave: a heading regex ending `[ \t]*$` cannot match a CRLF checkout's trailing `\r`, and the adjacent gardener-date pattern already used `\s*$` — check line-ending tolerance against the nearest sibling pattern before assuming parity.

## Evidence

- `crlf-change-doc-bypasses-progress-log-exclusion`
- `false-shipped-claims-and-unpinned-boundaries`
- `1uhcb`
- `test_review_policy.py:1109`
- `test_review_policy.py:1136`
- `gardener_metadata.py:12-15`

## Targets

- `.wavefoundry/framework/scripts/tests/test_review_policy.py`
- `.wavefoundry/framework/scripts/gardener_metadata.py`
