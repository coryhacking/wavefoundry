# Decision: Ship the seven sections as a data file and apply them from…

Owner: Engineering
Status: superseded
Last verified: 2026-08-17

Memory ID: `1vlp8-mem decision-ship-the-seven-sections-as-a-data-file-and-apply-th`
Kind: `decision`
Confidence: 0.6
Created: 2026-08-17
Updated: 2026-08-17
Source exploration cost: 3068146
Source event: `decision-log:1vim5-bug workflow-config-required-sections-have-no-install-owner:e8e4202733e96328`
Validation: rewrite
Validated by: agent
Action delta: When a docs-gate requirement must hold on a fresh install, ship it as data under install/ and apply it from setup Step 0 (absent-only), never as seed prose; pin any value that has a code authority (wave_review) to that function by test.
Validation rationale: Decision Log row verified against the tree: install/workflow-config.defaults.json ships, setup_wavefoundry._provision_workflow_defaults_if_absent merges key-wise absent-only via _atomic_write_json, test_workflow_defaults_cover_required_sections_and_review_authority pins wave_review == migrate_wave_review_policy(None). The generated draft targeted server_impl.py, which is wrong; the durable targets are the setup script, the defaults file, and the docs-lint constant it must cover. History: the same requirement lived in seed-010 prose and was lost in the 1p35d install split, so the lesson is the data-not-prose rule, not the specific keys.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1vnka-mem fresh-install-gate-requirements-ship-as-install-data-applied`
## Summary

Decision (wave 1viyu): Ship the seven sections as a data file and apply them from setup Step 0, key-wise absent-only; `wave_review` pinned by test to `migrate_wave_review_policy(None)`.. Rationale: Runs before lint ever reads the file, is idempotent for existing repos, cannot be lost by a seed rewrite the way the seed-010 prose was, and (readiness amendment, red-team RT-10/RT-11) keeps one authority for the fresh `wave_review` value while the file stays inspectable..

## Evidence

- `1vim5-bug workflow-config-required-sections-have-no-install-owner`
- `1viyu`

## Targets

- `server_impl.py`
