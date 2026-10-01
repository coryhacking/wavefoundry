# Fragile: tests/test_profile_support.py

Owner: Engineering
Status: superseded
Last verified: 2026-10-01

Memory ID: `1zgxs-mem fragile-tests-test-profile-support-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-10-01
Updated: 2026-10-01
Source exploration cost: 134809
Source event: `repeated-repairs:1zim5:tests/test_profile_support.py`
Validation: rewrite
Validated by: agent
Action delta: A test-support helper that rewrites source modules must be tested against a copied tree it can never escape, and any frozen snapshot that gates skips needs a value-level guard.
Validation rationale: The three repairs were about the profile infrastructure's safety (temp-repo cleanup, a refusal test that could write the real tree, a snapshot that could silently disable marked tests), not file fragility.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1zic3-mem source-rewriting-test-helpers-need-escape-proof-tests-and-va`

## Summary

tests/test_profile_support.py required 3 separate repairs during wave 1zim5; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `DEL-1ZIM5-PROFILE-RUN-CLEANUP`
- `DEL-1ZIM5-CANONICAL-TREE-TEST`
- `DEL-1ZIM5-SNAPSHOT-GUARD`
- `1zim5`

## Targets

- `tests/test_profile_support.py`
