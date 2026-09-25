# Independent Delivery Review

Owner: Engineering
Status: active
Last verified: 2026-09-25

## Verdict

Not ready to close: one release-test defect and a stale full-suite receipt. No sensor-routing defect identified in this review.

## QA-DEL-2: changelog pin fails a normal release rollover

`AdvisoryFirstRulePinTests.test_prompt_surfaces_and_contributing_docs_are_reconciled` in `test_docs_lint.py` restricts the new bullet to `changelog.split("\n## [", 2)[1]` (lines 3435–3436). A normal release moves that bullet into a versioned section and leaves Unreleased empty or holding the next release's work. The test then fails even though the changelog correctly preserves the announcement.

QA independently reproduced this without modifying repository files: intercept only the CHANGELOG read and replace its `## [Unreleased]` heading with `## [Unreleased]\n\n## [1.28.0]`, retaining every existing byte of the release content. Running the exact test fails its bullet assertion. The unmodified focused suites pass: 12 tests, zero skips. Nine reviewed-file fingerprints were unchanged.

Repair recommendation: pin the announcement in changelog history rather than requiring it permanently in Unreleased, and retain a release-rollover control. Reverify the test change before restoring affected delivery approvals.

## Receipt currency

QA independently recomputed the current framework hash as `1210d6217a03c3f558383fed654b6528872db6dcf1f2663cda767404b25251c3`. The receipt records 9,672 tests, timestamp `2026-09-25T21:44:52.948516+00:00`, and hash `20cdad4ee367383e34a86164bf639f18238b31c494df4f5b349d861742a59b77`. That green run does not prove the current tree. Run the full suite after the repair and any remaining framework edits.

## Other observations

The registry and validation change matches the admitted design: invalid decision values are rejected before findings/sink branches, both sensors remain advisory, undecided suffix wording remains available, and detection scope is unchanged. The shipped guidance and changelog carry the standing decision and avoid promising a consumer-wide test-health guarantee. The old rationale retains stronger causal language; shipped prose uses observed-change wording.

Change Status still says planned although all implementation ACs/tasks are checked. Reconcile it before closure. Existing DOCS-DEL-1 is terminal; this release-test defect is separate. No source repair, full-suite rerun, operator signoff, closure or commit was performed during this review.
