# A Dry-Run Build Reaches Zero-Change Writes Without the Lock

Change ID: `1x81w-bug dry-run-reaches-zero-change-writes-unlocked`
Change Status: `planned`
Owner: Engineering
Status: planned
Last verified: 2026-09-05
Wave: TBD

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

## Scope

**Problem statement:** the dry run's no-write contract is documented but not
enforced on the zero-change branch.

**In scope:**

- A `dry_run` gate before the drift reconcile and the idle-maintenance epoch
  in `_build_index_locked`, preserving the dry run's reporting.
- One pin.

**Out of scope:**

- The reap policy and the reap-state record (waves `1x54z`, `1x6ti`).

## Acceptance Criteria

- [ ] AC-1: A dry run on a fixture with a pending idle-maintenance condition leaves the store's generation, epoch state, meta table and Lance tables unchanged.
- [ ] AC-2: The dry run's result still reports the pending condition (what a real build would reap or reconcile).
- [ ] AC-3: Deleting the gate fails a named test, recorded as a mutation before review.

## Tasks

- [ ] Add the gate; keep the plan-only reporting.
- [ ] Pin and record the mutation.

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                  |
| ---------- | ----------- | ---------- | -------------------------------------- |
| gate       | implementer | —          | `_build_index_locked` zero-change branch. |
| pin        | implementer | gate       | Store and Lance byte-identity.         |


## Serialization Points

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/tests/test_indexer.py`

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


| Date       | Update                                                                                   | Evidence                                              |
| ---------- | ---------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 2026-09-05 | Filed from wave `1x6ti`'s readiness review (ARCH-PREP-4, read; RED-PREP-3, executed). | Scratch `prep_redteam/probe_b_meta.py` dry-run step.  |


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
