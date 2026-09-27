# Pin historical changelog assertions to their owning release

Owner: Engineering
Status: archived
Last verified: 2026-09-08

Memory ID: `1xgfv-mem pin-historical-changelog-assertions-to-their-owning-release`
Kind: `failed_attempt`
Confidence: 0.95
Created: 2026-09-08
Updated: 2026-09-26
Source exploration cost: 923641
Source event: `finding:1xfbh:QA-DEL-VERIFY-1`
Validation: promote
Validated by: agent
Action delta: When adding or repairing historical changelog tests, select the release owning the announcement and verify that newer-release content cannot satisfy its assertions.
Validation rationale: The linked typed finding and independent repair controls show that Unreleased coupling broke release verification, while selecting 1.22.0 preserved all content checks and tolerated newer headings. Current methods implement that owner-specific boundary. The generated candidate is a truncated repair-status report with a basename-only target; replace it with the actionable lesson and exact file targets. Existing memory 1wvo1 covers mutation discrimination generally, not historical release ownership.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Archived: 2026-09-26
Archive reason: Operator directed removal of historical announcement assertions on 2026-09-26. Preserve the earlier release-rollover incident as history, not active guidance to recreate those tests.
Archive path: `docs/agents/memory/archive/1xgfv-mem pin-historical-changelog-assertions-to-their-owning-release.md`

## Summary

Historical announcement tests must select the release that owns the content, rather than Unreleased or the latest section. In wave 1xfbh, renaming Unreleased to 1.22.0 caused two IndexErrors before any content assertion ran. Pinning those historical tests to 1.22.0 retained all presence and omission checks. When adding or repairing such tests, exercise missing required content, forbidden content, and a newer unrelated release; content copied only into the newer release must not satisfy the historical assertion.

## Evidence

- `docs/waves/1xfbh upgrade-retry-pruning/wave.md`
- `QA-DEL-VERIFY-1`
- `ev-qa-del-verify-1-4`
- `EvaluatorEditBaselinePolicyPinTests.test_the_1_22_0_changelog_states_one_policy`
- `SerializationPointsTokenGrammarPinTests.test_the_1_22_0_changelog_announces_the_wave`

## Targets

- `.wavefoundry/framework/scripts/tests/test_docs_lint.py`
- `CHANGELOG.md`
