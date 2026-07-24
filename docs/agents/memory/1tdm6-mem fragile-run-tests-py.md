# Fragile: run_tests.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-23

Memory ID: `1tdm6-mem fragile-run-tests-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-23
Updated: 2026-07-23
Source exploration cost: 85585
Source event: `repeated-repairs:1tg55:run_tests.py`
Validation: rewrite
Validated by: agent
Action delta: When adding a parameter or supersession-linked behavior to _memory_add_response_locked, forward it at the lock-acquisition self-re-entry and handle the memory_validate rewrite path explicitly (it passes no supersedes; supersession is applied to the old record afterwards).
Validation rationale: The drafted candidate misattributed the fragile target to run_tests.py (the verification command) for the fourth consecutive wave. Both 1tg55 repairs landed at the memory minting seam: the self-re-entry silently dropped the new _source_exploration_cost parameter, and the rewrite path never passes supersedes so lineage-keyed behavior cannot see it. Both were live-caught by the inheritance test matrix before landing.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements
Superseded by: `1tf7m-mem fragile-memory-minting-seam-hidden-indirection`
## Summary

run_tests.py required 2 separate repairs during wave 1tg55; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `zero-cost-key-omission-breaks-draft-consumers`
- `rewrite-inheritance-not-visible-at-mint-seam`
- `1tg55`

## Targets

- `run_tests.py`
