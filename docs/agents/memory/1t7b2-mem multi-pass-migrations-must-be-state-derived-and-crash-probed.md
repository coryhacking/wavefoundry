# Multi-pass migrations must be state-derived and crash-probed

Owner: Engineering
Status: active
Last verified: 2026-07-22

Memory ID: `1t7b2-mem multi-pass-migrations-must-be-state-derived-and-crash-probed`
Kind: `failed_attempt`
Confidence: 0.8
Created: 2026-07-22
Updated: 2026-07-22
Source event: `repeated-repairs:1t9w8:memory_records.py`
Validation: promote
Validated by: agent
Action delta: Before shipping any multi-pass data migration, make every pass derive its work from current on-disk state rather than in-run bookkeeping, and execute crash-window reproductions (interrupt between passes and mid-step) as part of delivery verification.
Validation rationale: The fragile-file framing is too blunt: both wave 1t9w8 repairs hit the same new migration function, not the module broadly, and the durable lesson is the design rule they share. The operator's live crash probes (rename-only crash leaving unrepaired references; write-before-unlink self-collision; live docs out of scope) all trace to passes driven by in-run mapping state. The rewrite names the real rule and the full target path.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

Wave 1t9w8's memory-naming migration shipped with every pass driven by in-run bookkeeping (rename list, mapping dict), and the operator's live crash probes refuted its interruption-safety claim twice: a crash after the rename pass left stale references a rerun could not repair (empty mapping), and a crash between new-file write and old-file unlink made the rerun raise its own collision guard; reference scope also never left the memory directory. The repair pattern: each pass discovers its work from current on-disk state (same-internal-id residue completes; stale tokens found by scanning and resolved by slug lookup), destructive steps order write-then-unlink with residue recovery, and unresolvable references report loudly instead of vanishing. Verify such migrations with executed crash-window reproductions, not idempotence-after-success tests alone.

## Evidence

- `migration-not-interruption-safe` — operator finding with executed crash probes, wave 1t9w8 ledger
- `migration-skips-live-doc-surfaces` — operator finding with the docs/live.md probe, wave 1t9w8 ledger
- `1t9w8 memory-lifecycle-naming` — the wave whose repair landed the state-derived pattern

## Targets

- `.wavefoundry/framework/scripts/memory_records.py`
