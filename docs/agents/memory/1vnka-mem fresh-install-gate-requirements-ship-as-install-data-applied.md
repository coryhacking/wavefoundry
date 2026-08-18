# Fresh-install gate requirements ship as install data applied at setup Step 0, not as seed prose

Owner: Engineering
Status: active
Last verified: 2026-08-17

Memory ID: `1vnka-mem fresh-install-gate-requirements-ship-as-install-data-applied`
Kind: `decision`
Confidence: 0.9
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `decision-log:1vim5-bug workflow-config-required-sections-have-no-install-owner:e8e4202733e96328`
Validation: promote
Validated by: agent
Action delta: When a docs-gate requirement must hold on a fresh install, ship it as data under install/ and apply it from setup Step 0 (absent-only), never as seed prose; pin any value that has a code authority (wave_review) to that function by test.
Validation rationale: Decision Log row verified against the tree: install/workflow-config.defaults.json ships, setup_wavefoundry._provision_workflow_defaults_if_absent merges key-wise absent-only via _atomic_write_json, test_workflow_defaults_cover_required_sections_and_review_authority pins wave_review == migrate_wave_review_policy(None). The generated draft targeted server_impl.py, which is wrong; the durable targets are the setup script, the defaults file, and the docs-lint constant it must cover. History: the same requirement lived in seed-010 prose and was lost in the 1p35d install split, so the lesson is the data-not-prose rule, not the specific keys.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

The seven WORKFLOW_REQUIRED_KEYS sections were required by seed-010 prose until the 1p35d install split dropped the step; every fresh install then failed check_workflow_config. Wave 1viyu ships install/workflow-config.defaults.json and applies it key-wise absent-only from setup Step 0 (setup_wavefoundry._provision_workflow_defaults_if_absent, atomic ensure_ascii=False writer); a constant-derived test covers WORKFLOW_REQUIRED_KEYS and pins wave_review to migrate_wave_review_policy(None). Rule: a requirement the docs gate enforces on a fresh install must be produced by code from shipped data before lint runs; prose steps get lost in seed rewrites, and a hand-authored copy of a code-owned value drifts.

## Evidence

- `1vim5-bug workflow-config-required-sections-have-no-install-owner`
- `test_setup_wavefoundry.LifecyclePolicyStepZeroTests.test_workflow_defaults_cover_required_sections_and_review_authority`
- `git show 11b3af4e^ seed-010 line 142`

## Targets

- `.wavefoundry/framework/scripts/setup_wavefoundry.py`
- `.wavefoundry/framework/install/workflow-config.defaults.json`
- `.wavefoundry/framework/scripts/wave_lint_lib/constants.py`
