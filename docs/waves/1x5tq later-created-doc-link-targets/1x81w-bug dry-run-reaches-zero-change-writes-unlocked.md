# A Dry-Run Build Reaches Zero-Change Writes Without the Lock

Change ID: `1x81w-bug dry-run-reaches-zero-change-writes-unlocked`
Change Status: `complete`
Owner: Engineering
Status: active
Last verified: 2026-09-05
Completed at: 2026-09-05
Wave: 1x5tq later-created-doc-link-targets

## Rationale

Recorded by the architecture lane of wave `1x6ti`'s readiness review
(ARCH-PREP-4) and executed in part by the red-team seat of the same council
(RED-PREP-3). `build_index(dry_run=True)` is documented as a no-write path
(the command line's help says "without writing anything") and it bypasses
the build lock and the store's `ensure_current` on that basis. On the
zero-change branch of `_build_index_locked`, however, the only dry-run return
sits after the whole zero-change block, so a dry run reaches
`reconcile_non_git_drift` (a meta write on a confirmed git to non-git
transition) and, when a reap, a heal, a dirty epoch or an orphan reconcile
is pending, the idle-maintenance epoch (`begin_build_epoch`, the executing
reap and its finalize), all without the lock. Wave `1x6ti` guards its own
new writer with `not dry_run`; this record covers the pre-existing writes on
that branch.

## Requirements

1. A `dry_run` build SHALL return before any store or index mutation on the
   zero-change branch: no drift clear, no idle-maintenance epoch, no
   executing reap, no orphan reconcile.
2. A test SHALL pin that a dry run against a fixture that needs idle
   maintenance leaves the store's generation, the epoch state, the meta table
   and the Lance tables byte-identical, and still reports what a real build
   would do.
3. Verification SHALL cover the distinct pending drift-clear, reap, heal,
   dirty-epoch, and orphan-reconcile branches, plus a genuine no-op control.
   Report those pending conditions through the Python build result and CLI
   diagnostic without claiming a detached MCP tool forwards the result.
   Combined-wave graph-recovery planning SHALL obey the same no-write return.

## Scope

**Problem statement:** the dry run's no-write contract is documented but not
enforced on the zero-change branch.

**In scope:**

- A `dry_run` gate before the drift reconcile and the idle-maintenance epoch
  in `_build_index_locked`, preserving the dry run's reporting.
- Focused no-write/reporting tests for each mutation branch and the genuine no-op.

**Out of scope:**

- The reap policy and the reap-state record (waves `1x54z`, `1x6ti`).

## Acceptance Criteria

- [x] AC-1: A dry run on a fixture with a pending idle-maintenance condition leaves the store's generation, epoch state, meta table and Lance tables unchanged.
- [x] AC-2: The dry run's result still reports the pending condition (what a real build would reap or reconcile).
- [x] AC-3: Deleting the gate fails a named test, recorded as a mutation before review.

## Tasks

- [x] Add the gate; keep the plan-only reporting.
- [x] Pin and record the mutation.
- [x] Update the zero-change dry-run architecture passage and CHANGELOG; run relevant suites and docs validation.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                  |
| ---------- | ----------- | ---------- | -------------------------------------- |
| gate       | implementer | —          | `_build_index_locked` zero-change branch. |
| pin        | implementer | gate       | Store and Lance byte-identity.         |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `docs/architecture/data-and-control-flow.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/data-and-control-flow.md` item 15 (the dry-run sentence
wave `1x6ti` adds).

## AC Priority


| AC   | Priority | Rationale                                         |
| ---- | -------- | ------------------------------------------------- |
| AC-1 | required | The contract itself.                              |
| AC-2 | required | A dry run that reports nothing is not a dry run.  |
| AC-3 | required | A guard that survives its own deletion is not landed. |


## Progress Log

- 2026-09-05 — Operator authorized closure and commit after delivery review. All required ACs and tasks complete; no deferrals. Changelog covers both changes and the interrupted-publication repair.

Thought: implement the admitted repair after current combined Prepare and activation. Root owns `indexer.py` and its tests, landing the dry-run gate first; a separate implementer owns graph persistence/rescan and its differential tests. Root integrates the read-only pending-work plan, documentation and full verification.

Gapfill: MCP keyword lookup excludes framework test files and returned no hits; used scoped shell search for fixture helpers after the MCP outline and targeted reads.


| Date       | Update                                                                                   | Evidence                                              |
| ---------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-09-05 | Filed from wave `1x6ti`'s readiness review (ARCH-PREP-4, read; RED-PREP-3, executed). | Scratch `prep_redteam/probe_b_meta.py` dry-run step.  |
| 2026-09-05 | Operator authorized admission to `1x5tq` alongside `1x8e1`; dry-run guard is ordered first so later graph recovery preserves no-write reporting. Combined readiness must be refreshed before implementation. | Wave admission and dependency order in `wave.md`; `wf_add_change` relocated this document. |


Observe: `DryRunIdleMaintenanceTests` ran 8 tests with zero skips: pre-fix 8 failures; repaired tree 8 passed. Fixtures exercise pending drift-clear, stranded reap, cold chunk heal, dirty epoch, sidecar orphan, missing-Lance dirty recovery, healthy no-op, and real CLI entry. Snapshots compare every SQLite persisted row (including meta and epoch) and byte hashes of Lance and other durable artifacts; SQLite transient WAL/SHM locking files are excluded because read-only SQLite changes their lock bookkeeping. Positive real-build controls clear drift, heal, reap and reconcile.

Mutation: in a scratch in-memory module, delete the entire new idle dry-run gate. `DryRunIdleMaintenanceTests.test_dirty_epoch_dry_run_is_byte_identical_and_reports_recovery` fails on changed persisted state (1 test, 1 failure, no errors/skips). The checked-in source remains repaired. Logs: `/tmp/1x5tq-dryrun-red.log`, `/tmp/1x5tq-dryrun-green.log`, `/tmp/1x5tq-dryrun-mutant.log`.

Thought: now integrate graph pending-work reporting and real locked recovery without moving the established dry-run boundary, then run the combined regression matrix and full suite.

Observe: final frozen-tree `python3 .wavefoundry/framework/scripts/run_tests.py` passed 8,478 tests across 74 files in 185.569 seconds (3 skips). Fresh receipt: `result=ok`, `inputs_hash=4f1428e2657d73f3235f39674788fd5f5c29477e398a70ed96a61766492d78b6`. Full documentation lint and `git diff --check` pass. Framework edit gate closed. Computational implementation is complete; delivery-phase inferential reviews remain the next workflow. Final suite log: `/tmp/1x5tq-framework-tests-final-frozen.log`.

Observe: operator-requested additional smoke pass passed 16 focused tests (zero skips) and 12 independent real CLI invocations across noded and node-less targets. Dry-run persistence, dirty-epoch reporting/recovery, exact edge/doc output, unchanged referring text, stopped repair dispatch and full-build equivalence verified. See [smoke test evidence](smoke-tests.md), including the graph-only cold-index fixture limitation.

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk                                                        | Mitigation                                                 |
| ----------------------------------------------------------- | ---------------------------------------------------------- |
| The gate hides a pending condition the dry run used to surface. | AC-2 keeps the plan-only reporting.                    |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
