# Parent-owned index recovery must preserve current memory authorization

Owner: Engineering
Status: active
Last verified: 2026-09-09

Memory ID: `1xk4o-mem parent-owned-index-recovery-must-preserve-current-memory-aut`
Kind: `fragile_file`
Confidence: 0.95
Created: 2026-09-09
Updated: 2026-09-09
Source exploration cost: 2492314
Source event: `finding:1xjmm:ARCH-DEL-1`
Validation: promote
Validated by: agent
Action delta: For parent-owned index publication, recheck current memory-run authorization before consuming a retained staging receipt, require observed child outcomes, and run fresh storage verification only after parent CAS; test preflight retirement and post-CAS interruption through ordinary resume.
Validation rationale: Followed ARCH-DEL-1 initial, failed first repair and successful native reverification plus actual final package recovery. The generated candidate incorrectly targeted only sqlite_storage_migration.py; the ordering and authorization seam is upgrade_wavefoundry.py. Existing memory README explains publishing_index generally; this adds the concrete retained-stage/interruption action and demonstrated mutants.
Evidence verified: true
Current target verified: true
Canonical overlap: supplements

## Summary

When changing parent-owned upgrade indexing, a retained child staging receipt is usable only while the current memory run still authorizes publishing_index and both child exits were observed successful. Standard preflight can retire that authorization; rerun ordinary children then. Finalize the parent epoch before fresh storage verification, and reverify already-indexed retries after an interrupted verifier. Exercise real memory reconciliation, native CAS and fresh-process verification; successful child stubs alone miss these ordering failures.

## Evidence

- `ARCH-DEL-1`
- `ev-arch-del-1-4`
- `1xjmm`

## Targets

- `.wavefoundry/framework/scripts/upgrade_wavefoundry.py`
