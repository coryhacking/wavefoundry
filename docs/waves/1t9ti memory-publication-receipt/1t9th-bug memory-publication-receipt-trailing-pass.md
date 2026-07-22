# Memory Publication Receipt Survives Trailing Build Passes

Change ID: `1t9th-bug memory-publication-receipt-trailing-pass`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-07-21
Wave: `1t9ti memory-publication-receipt`

## Rationale

Field-confirmed on the operator's cross-repo 1.14.0 upgrade test (pcx4 → pdsk): a validated historical-memory resume publishes the index but `resume_after_memory` still fails deterministically, forcing a manual `mark_indexed` workaround. Mechanism verified at source, two legs:

1. `reconcile_index_publication` (memory_backfill.py) declares publication successful only when the CURRENT build-state row is `complete` with exactly the receipt's `(attempt_id, generation)`. The build state is a single row that every epoch replaces, and the same publication phase runs a trailing graph-only pass after the content build, so the receipt can never match.
2. Sharper: while the publication env var is set, the trailing pass's own `finalize_build_epoch` (index_state_store.py) also consults the memory gate; the run is by then `publishing_index`, not `ready_for_index`, so `authorize_index_finalize` returns False and the trailing epoch is REFUSED outright, leaving the build state `building`. Any same-window pass (`fts:derived-rebuild`, `optimize`, idle maintenance) behaves identically.

Blast radius: essentially every first-time 1.14 upgrade of a long-lived repo (backfill pauses for validation; the resume always runs content-then-graph). This is a 1.14.0 release blocker; the built `pdsk` pack carries it.

## Requirements

1. **Self-completing publication:** when `finalize_build_epoch` runs with the publication env var set and the run is `ready_for_index`, a successful compare-and-set for the AUTHORIZED attempt immediately marks the run `indexed` (new `memory_backfill.record_publication_success`, matching on run_id + `publishing_index` + the authorized `publication_attempt_id`), inside the same `review_event_write_lock` scope. The publication no longer depends on the mutable global build-state row remaining untouched.
2. **Trailing passes proceed ungated:** with the env var set, `finalize_build_epoch` consults the run's state first (new light `memory_backfill.run_state` read): `ready_for_index` routes through `authorize_index_finalize` exactly as today; `publishing_index` and `indexed` proceed as a normal ungated finalize (no pending memory work can exist in those states); every other state — `awaiting_validation`, `inventory_pending`, or an unknown run — refuses the finalize (fail-closed, preserving the real gate).
3. **Recovery semantics preserved:** `reconcile_index_publication` is unchanged and remains the crash-recovery path for the (now tiny) window between authorize/CAS and the success record: an unmatched receipt still resets the run to `ready_for_index` for a clean re-publication. The census freeze in `authorize_index_finalize` (zero-pending check under BEGIN IMMEDIATE) is unchanged.
4. **Deterministic field reproduction as a test:** inside one `index_publication_scope`, a content pass (`begin`/`finalize` scope `all`) followed by a trailing graph-only pass must: return True from BOTH finalizes, end the run `indexed`, leave the build state `complete` on the trailing attempt, and let `complete_index_publication` succeed. This test must fail on the pre-fix code (second finalize refused).
5. **Gate integrity tests:** with the env var set, a run in `awaiting_validation` still refuses the finalize; an unknown run id still refuses; `record_publication_success` is a no-op when the run's recorded attempt differs from the finalized attempt.
6. **No schema or contract growth:** no new run states, no lock-file or store schema changes, no change to `mark_indexed`, `sync_inventory`, or the upgrade orchestration.

## Scope

**Problem statement:** the memory-publication receipt binds success to the mutable last-build row and simultaneously breaks the trailing pass it will be compared against, so a correct publication reads as failed.

**In scope:**

- `memory_backfill.py`: `run_state` light reader, `record_publication_success`
- `index_state_store.py`: `finalize_build_epoch` gate routing + post-CAS success record
- `tests/test_memory_backfill.py` (and/or `test_index_state_store.py`) additions

**Out of scope:**

- Upgrade orchestration (`upgrade_wavefoundry.py` resume flow is correct once publication self-completes)
- Receipt/reconcile redesign beyond the self-completing record
- Release mechanics (fresh pack follows the wave)

## Acceptance Criteria

- [x] AC-1: the field reproduction (content pass then graph-only pass inside one publication scope) ends `indexed` with both epochs finalized; the same test fails on pre-fix code.
- [x] AC-2: gate integrity holds — `awaiting_validation` and unknown-run finalizes are refused with the env var set; the success record only fires for the authorized attempt.
- [x] AC-3: existing publication/recovery tests pass (crash-window reconcile, history-changed requeue, update-index bypass guard), with one intentional retarget: `test_receipt_does_not_alias_a_later_unrelated_generation` moves to the crash window (success record suppressed) because its old scenario — a successful in-scope CAS not counting as publication — is precisely the behavior this change corrects. The anti-aliasing property itself (a later unrelated generation never reads as publication) is preserved and still asserted.
- [x] AC-4: full framework test suite passes; independent-delivery-verification protocol applied (executed reproduction, not green-units-only) per the standing concurrency/crash-safety feedback.

## Tasks

- [x] Add `run_state` and `record_publication_success` to memory_backfill.
- [x] Route the finalize gate by run state and record success post-CAS in index_state_store.
- [x] Field-reproduction test plus gate-integrity tests; verify the reproduction fails pre-fix.
- [x] Full suite; adversarial pass on the crash windows.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| publication-binding | implementer | — | Two files, one seam each |
| verification | qa-reviewer | publication-binding | Executed reproduction + crash-window adversarial pass |

## Serialization Points

- None; single-writer paths under the existing review-event lock.

## Affected Architecture Docs

N/A: crash-safety bug fix inside the documented memory-publication flow; no boundary, schema, or tool-surface change.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | The deterministic field failure being fixed. |
| AC-2 | required | The gate must not weaken while becoming survivable. |
| AC-3 | required | Recovery semantics are load-bearing for crash windows. |
| AC-4 | required | Standard gate plus the crash-safety verification protocol. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-07-21 | Drafted from the operator's field report; both legs verified at source (reconcile exact-match at memory_backfill.py:759-766 against the single build-state row; trailing-pass refusal via authorize_index_finalize consulted on every in-scope finalize at index_state_store.py:2300-2310). | Field report; code_read of memory_backfill.py:675-817 and index_state_store.py:2251-2380 |
| 2026-07-21 | Implemented. Live-caught design correction on the first test run: the stored run state can lag validation (still `awaiting_validation` after a promote), so the finalize gate must NOT pre-read state to decide whether to authorize — only `publishing_index`/`indexed` short-circuit as trailing passes and unknown runs fail closed; everything else routes through `authorize_index_finalize`, which re-syncs the census exactly as before. Five tests added/retargeted (field reproduction; pending-validation refusal; unknown-run refusal; authorized-attempt-only success record; aliasing test retargeted at the CAS-to-record crash window, plus the setup-retry recovery test retargeted the same way). Known-bad probe reconstructing the pre-fix finalize (always-authorize, no success record) flipped the field reproduction to failure. Modules: memory_backfill 41 OK, index_state_store 36 OK, upgrade 340 OK. | test_publication_survives_trailing_graph_pass_in_same_scope + probe; module runs |
| 2026-07-21 | AC-4 met: full framework suite 6,118/6,118 OK on the final tree; docs lint clean; crash-window adversarial walk recorded in the wave's Delivery Review Evidence. | run_tests.py output; wave.md |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-21 | Record publication success at CAS time instead of re-deriving it later from the build-state row. | The build-state row is mutable global state that the same phase legitimately overwrites; success is known with certainty exactly once, at the CAS. | Receipt-history table (schema growth for one consumer); unsetting the env var between passes (fragile placement in the orchestration, and leaves the exact-match reconcile fragile for every other trailing pass). |
| 2026-07-21 | Retarget the receipt anti-aliasing test at the crash window instead of deleting it. | The property it protects (generation advance by an unrelated build must never read as publication) remains load-bearing wherever reconcile still runs; only its old trigger scenario became a legitimate success. | Keeping it verbatim (impossible: the scenario now correctly succeeds); deleting it (loses the anti-aliasing guarantee). |
| 2026-07-21 | Route the gate by run state; `publishing_index`/`indexed` finalize ungated. | The gate exists to stop publication while memory work is pending; in those states the zero-pending census has already been frozen, so refusing the trailing pass protects nothing and breaks the index epoch. | Refusing all non-ready states (the current behavior — deterministically strands the build state at `building`). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Crash between CAS commit and the success record re-opens the old window. | Window shrinks to two adjacent SQLite commits under one process lock; reconcile still recovers it by resetting to `ready_for_index` for a clean re-publication. |
| Ungated `publishing_index` finalize could mask a failed authorized attempt. | The success record matches on the authorized attempt id only; a stale receipt still reconciles to `ready_for_index` exactly as today. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
