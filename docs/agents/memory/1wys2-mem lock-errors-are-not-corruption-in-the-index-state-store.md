# Lock errors are not corruption in the index state store

Owner: Engineering
Status: active
Last verified: 2026-09-02

Memory ID: `1wys2-mem lock-errors-are-not-corruption-in-the-index-state-store`
Kind: `failed_attempt`
Confidence: 0.9
Created: 2026-09-02
Updated: 2026-09-02
Source exploration cost: 2790236
Source event: `finding:1wpif:ARCH-DEL-2`
Validation: promote
Validated by: agent
Action delta: When catching a database error around opening or rebuilding the index state store, classify before recovering: a lock or busy error must propagate with the store intact, and only genuine structural damage may reset it.
Validation rationale: The defect is real and independently verified, but the generated record misattributes it. Every cited artifact names the state-store module and its tests; the indexer is not involved. The generated summary is also truncated mid-sentence. Rewritten with the correct target and a lesson a future agent can act on: the original catch treated any database error as corruption, so a busy-timeout lock wait during a concurrent rebuild deleted and recreated a healthy store. The repair narrows the classification and is pinned by named tests in both directions.
Evidence verified: true
Current target verified: true
Canonical overlap: none

## Summary

The index state store caught every database error as corruption and responded by deleting and recreating itself, so an ordinary busy-timeout lock wait during a concurrent rebuild destroyed a healthy store. Both the open path and the chunk-index rebuild path now classify first: a missing table, missing column or unknown schema version resets and retries, in that order, while a lock or busy error is durably logged and re-raised with the store untouched. Named tests pin both directions and the reset-before-retry order.

## Evidence

- `ARCH-DEL-2`
- `ev-arch-del-2-3`
- `ARCH-RV3-1`
- `1wpif`

## Targets

- `.wavefoundry/framework/scripts/index_state_store.py`
