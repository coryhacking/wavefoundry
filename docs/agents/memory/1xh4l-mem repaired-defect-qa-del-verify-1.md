# Repaired defect QA-DEL-VERIFY-1

Owner: Engineering
Status: superseded
Last verified: 2026-09-08

Memory ID: `1xh4l-mem repaired-defect-qa-del-verify-1`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-08
Updated: 2026-09-08
Source exploration cost: 923641
Source event: `finding:1xfbh:QA-DEL-VERIFY-1`
Validation: rewrite
Validated by: agent
Action delta: When adding or repairing historical changelog tests, select the release owning the announcement and verify that newer-release content cannot satisfy its assertions.
Validation rationale: The linked typed finding and independent repair controls show that Unreleased coupling broke release verification, while selecting 1.22.0 preserved all content checks and tolerated newer headings. Current methods implement that owner-specific boundary. The generated candidate is a truncated repair-status report with a basename-only target; replace it with the actionable lesson and exact file targets. Existing memory 1wvo1 covers mutation discrimination generally, not historical release ownership.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1xgfv-mem pin-historical-changelog-assertions-to-their-owning-release`
## Summary

Real defect fixed in wave 1xfbh: Authorized two-method repair completed; all original content assertions retained. Independent lane replay detected missing/contradictory and wrong-release content, verified valid future releases, and verified current green receipt. Clear o…

## Evidence

- `QA-DEL-VERIFY-1`
- `ev-qa-del-verify-1-4`
- `1xfbh`

## Targets

- `test_docs_lint.py`
