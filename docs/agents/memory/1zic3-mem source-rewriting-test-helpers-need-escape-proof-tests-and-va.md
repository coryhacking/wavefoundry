# Source-rewriting test helpers need escape-proof tests and value guards

Owner: Engineering
Status: active
Last verified: 2026-10-01

Memory ID: `1zic3-mem source-rewriting-test-helpers-need-escape-proof-tests-and-va`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 134809
Source event: `repeated-repairs:1zim5:tests/test_profile_support.py`
Validation: promote
Validated by: agent
Action delta: A test-support helper that rewrites source modules must be tested against a copied tree it can never escape, and any frozen snapshot that gates skips needs a value-level guard.
Validation rationale: The three repairs were about the profile infrastructure's safety (temp-repo cleanup, a refusal test that could write the real tree, a snapshot that could silently disable marked tests), not file fragility.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1zim5: apply_profile edits vocabulary_profile.py and record_paths.py in a copied tree; its refusal test ran against the real tree, so a regression would have rewritten the developer's modules (now patched to a temp copy). The default_profile_only marker compares against a frozen SHIPPED_DEFAULTS; without a value-level guard a changed shipped default silently skips every marked test. The profile run's temp git repo also needed read-only-aware removal and a SIGTERM handler.

## Evidence

- `DEL-1ZIM5-PROFILE-RUN-CLEANUP`
- `DEL-1ZIM5-CANONICAL-TREE-TEST`
- `DEL-1ZIM5-SNAPSHOT-GUARD`
- `1zim5`

## Targets

- `.wavefoundry/framework/scripts/tests/record_layout_support.py`
- `.wavefoundry/framework/scripts/tests/test_profile_support.py`
- `.wavefoundry/framework/scripts/run_tests.py`
