# Fragile: reconcile_scan.py

Owner: Engineering
Status: active
Last verified: 2026-07-31

Memory ID: `1u0yp-mem fragile-reconcile-scan-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-31
Updated: 2026-07-31
Source exploration cost: 3641306
Source event: `repeated-repairs:1tz6l:reconcile_scan.py`
Validation: promote
Validated by: agent
Action delta: When editing reconcile_scan.py exclusions or channels, keep the near-miss controls non-vacuous: the exact excluded shape must not flag while sibling-named files and wrong-root directories still do, and host-permission files must partition to their own channel
Validation rationale: Both 1tz6l repairs concern scan-scope boundaries (rollback-prefix exclusion; host-permission channel separation), each guarded by set-equality near-miss tests executed today. Evidence chain followed in events.jsonl; current file verified in tree.
Evidence verified: true
Current target verified: true
Canonical overlap: none
## Summary

reconcile_scan.py required 2 separate repairs during wave 1tz6l; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `rollback-bridge-backup-leaks-into-live-reconciliation-scan`
- `upgrade-reconciliation-misses-live-guidance-and-misroutes-host-rules`
- `1tz6l`

## Targets

- `reconcile_scan.py`
