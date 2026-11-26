# Fragile: memory_backfill.py

Owner: Engineering
Status: archived
Last verified: 2026-11-10

Memory ID: `1u25a-mem fragile-memory-backfill-py`
Superseded by: `24b9i-mem memory-backfill-py-fragile-seams`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-11-25
Source exploration cost: 3641306
Source event: `repeated-repairs:1tz6l:memory_backfill.py`
Validation: promote
Validated by: agent
Action delta: When editing memory_backfill.py, rerun the pfq6 and pfqq external reproduction tests (stale-id repair on the sync path; receipt restage to the trailing graph attempt) before trusting the change
Validation rationale: Both 1tz6l repairs concern recovery-state invariants (legacy-id reconciliation inside sync_inventory's transaction; publication receipt transfer at same generation), each pinned by a named external reproduction executed today. Evidence chain followed in events.jsonl; current file verified in tree.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Archived: 2026-11-25
Archive reason: Superseded by 24b9i-mem in the 244cm item 7 review (rewritten to state when it applies, full-path targets).
Archive path: `docs/agents/memory/archive/1u25a-mem fragile-memory-backfill-py.md`

## Summary

memory_backfill.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `memory-id-rename-and-gate-resume-deadlock`
- `graph-maintenance-invalidates-upgrade-staging-receipt`
- `1tz6l`

## Targets

- `memory_backfill.py`
