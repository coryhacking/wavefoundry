# Fragile: memory_records.py

Owner: Engineering
Status: superseded
Last verified: 2026-07-22

Memory ID: `1t8ub-mem fragile-memory-records-py`
Kind: `fragile_file`
Confidence: 0.6
Created: 2026-07-22
Updated: 2026-07-22
Source exploration cost: 97730
Source event: `repeated-repairs:1t9w8:memory_records.py`
Validation: rewrite
Validated by: agent
Action delta: Before shipping any multi-pass data migration, make every pass derive its work from current on-disk state rather than in-run bookkeeping, and execute crash-window reproductions (interrupt between passes and mid-step) as part of delivery verification.
Validation rationale: The fragile-file framing is too blunt: both wave 1t9w8 repairs hit the same new migration function, not the module broadly, and the durable lesson is the design rule they share. The operator's live crash probes (rename-only crash leaving unrepaired references; write-before-unlink self-collision; live docs out of scope) all trace to passes driven by in-run mapping state. The rewrite names the real rule and the full target path.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1t7b2-mem multi-pass-migrations-must-be-state-derived-and-crash-probed`
## Summary

memory_records.py required 2 separate repairs during wave 1t9w8; treat it as fragile and re-verify edits with the full suite before relying on them.

## Evidence

- `migration-not-interruption-safe`
- `migration-skips-live-doc-surfaces`
- `1t9w8`

## Targets

- `memory_records.py`
