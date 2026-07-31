# Fragile: memory_backfill.py

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u25a-mem fragile-memory-backfill-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 3641306
Source event: `repeated-repairs:1tz6l:memory_backfill.py`
Validation: promote
Validated by: agent
Action delta: When editing memory_backfill.py, rerun the pfq6 and pfqq external reproduction tests (stale-id repair on the sync path; receipt restage to the trailing graph attempt) before trusting the change
Validation rationale: Both 1tz6l repairs concern recovery-state invariants (legacy-id reconciliation inside sync_inventory's transaction; publication receipt transfer at same generation), each pinned by a named external reproduction executed today. Evidence chain followed in events.jsonl; current file verified in tree.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

memory_backfill.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `memory-id-rename-and-gate-resume-deadlock`
- `graph-maintenance-invalidates-upgrade-staging-receipt`
- `1tz6l`

## Targets

- `memory_backfill.py`
