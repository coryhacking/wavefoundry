# Repaired defect ARCH-DEL-2

Owner: Engineering
Status: superseded
Last verified: 2026-09-02

Memory ID: `1wxp4-mem repaired-defect-arch-del-2`
Kind: `failed_attempt`
Confidence: 0.6
Created: 2026-09-02
Updated: 2026-09-02
Source exploration cost: 2790236
Source event: `finding:1wpif:ARCH-DEL-2`
Validation: rewrite
Validated by: agent
Action delta: When catching a database error around opening or rebuilding the index state store, classify before recovering: a lock or busy error must propagate with the store intact, and only genuine structural damage may reset it.
Validation rationale: The defect is real and independently verified, but the generated record misattributes it. Every cited artifact names the state-store module and its tests; the indexer is not involved. The generated summary is also truncated mid-sentence. Rewritten with the correct target and a lesson a future agent can act on: the original catch treated any database error as corruption, so a busy-timeout lock wait during a concurrent rebuild deleted and recreated a healthy store. The repair narrows the classification and is pinned by named tests in both directions.
Evidence verified: true
Current target verified: true
Canonical overlap: none
Superseded by: `1wys2-mem lock-errors-are-not-corruption-in-the-index-state-store`
## Summary

Real defect fixed in wave 1wpif: Repair completed and independently verified for the named instance under four mutants. The two residual same-class instances found in the same file are recorded as their own findings, ARCH-RV1-1 and ARCH-RV1-2, not as a reopening of this o…

## Evidence

- `ARCH-DEL-2`
- `ev-arch-del-2-3`
- `1wpif`

## Targets

- `indexer.py`
