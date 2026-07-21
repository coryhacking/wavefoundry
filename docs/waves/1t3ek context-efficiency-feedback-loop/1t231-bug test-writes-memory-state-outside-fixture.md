# Test Writes memory-state.sqlite Outside Its Fixture

Change ID: `1t231-bug test-writes-memory-state-outside-fixture`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-07-20
Wave: TBD

## Rationale

During wave 1t3gt's full-suite runs (2026-07-20), a stray
`.wavefoundry/framework/scripts/.wavefoundry/index/memory-state.sqlite` appeared in the
working tree, containing exactly one `memory_backfill_runs` row with
`entry_path='setup'` and `state='inventory_pending'` timestamped mid-run. Some test
reaches the historical-memory state store with a cwd-relative root instead of its tmp
fixture when the suite runs with the scripts directory as cwd. The same stray-artifact
class was just fixed for the CLI entry points in change `1t1b3` (wave 1t3gt); this is
the test-suite instance of it. A quick grep for setup-entry callers without an explicit
fixture root found no obvious offender, so the reproduction step below is part of the
work.

## Requirements

1. Identify the test (or test-reached production path) that writes
   `memory-state.sqlite` relative to the process cwd during a suite run, by
   reproducing with a marker directory watch or by auditing every
   `ensure_run`/`memory_backfill`/setup-gate call path reachable from tests.
2. Fix it so every test writes only inside its own fixture root. If the root cause is a
   production code path defaulting to cwd (the `1t1b3` class), fix it with the shared
   `repo_root.py` discovery instead of masking it in the test.
3. Add a suite-level guard: after the affected test module (or in the runner), assert no
   `.wavefoundry` directory was created under `framework/scripts/` — turning any
   recurrence of this artifact class into a test failure instead of a working-tree
   surprise.

## Requirements

1. [Numbered behavioral requirement — specific enough for an implementer to act on unambiguously]
2. …

## Scope

**Problem statement:** A test writes durable historical-memory state relative to cwd,
littering the working tree with an untracked sqlite artifact whenever the suite runs
from the scripts directory.

**In scope:**

- Locating and fixing the offending write path
- A recurrence guard for this artifact class in the test suite
- Deleting any stray artifact the reproduction creates

**Out of scope:**

- The CLI entry-point cwd defaults (already fixed in `1t1b3`)
- Broader cwd-anchored `_discover_root` unification in `indexer.py`/`lifecycle_id.py`/
  `render_platform_surfaces.py`/`docs_gardener.py` (known, separately tracked class)

## Acceptance Criteria

- [x] AC-1: The offending write path is identified and recorded in the Decision Log with
      the reproduction evidence.
- [x] AC-2: A full suite run from a clean tree creates no `.wavefoundry` directory under
      `framework/scripts/` (or anywhere outside fixture roots), verified by the new guard.
- [x] AC-3: The guard fails when the artifact class recurs (demonstrated once against the
      unfixed behavior or a seeded reproduction).
- [x] AC-4: Full framework test suite passes
      (`python3 .wavefoundry/framework/scripts/run_tests.py`).

## Tasks

- [x] Reproduce with a directory watch during a full suite run; identify the writer
- [x] Fix the write path (fixture root or `repo_root.py` discovery, per root cause)
- [x] Add the recurrence guard
- [x] Run full framework test suite from a clean tree and verify no stray artifacts

## Agent Execution Graph


| Workstream   | Owner       | Depends On | Notes |
| ------------ | ----------- | ---------- | ----- |
| test-hygiene | Engineering | —          | Small; tests plus possibly one production write path |


## Serialization Points

- None expected; independent of the other changes in this wave unless the root cause
  lands in `server_impl.py`, in which case sequence with them.

## Affected Architecture Docs

N/A — test hygiene plus at most one contained write-path fix; no boundary or flow
change. `docs/architecture/testing-architecture.md` only if the recurrence guard becomes
a runner-level convention worth documenting; decide at implementation.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | Fixing without identifying the writer risks masking a production cwd-default (the 1t1b3 class) |
| AC-2 | required  | The observed defect: stray artifacts in the working tree |
| AC-3 | important | Guard effectiveness demonstrated once; ongoing value is the recurrence catch |
| AC-4 | required  | Suite-green is the delivery gate for all framework script changes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
|      |        |          |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-07-20 | Root cause identified by per-test bisection: four `test_setup_wavefoundry` tests call `setup_wavefoundry.main([])` (cwd-default root) with render/index/dry-run mocked but `memory_backfill.ensure_run` UNMOCKED — the real gate call created `.wavefoundry/index/memory-state.sqlite` under whatever cwd the suite ran from (the scripts dir under `run_tests.py`), matching the observed stray row (`entry_path='setup'`, `inventory_pending`). | Reproduced deterministically: the artifact appears after `tests.test_setup_wavefoundry` and after exactly those four test ids; the class setUp already mocked `sync_inventory`/`mark_indexed` but missed `ensure_run`. | Production cwd-default in setup (ruled out: setup's cwd-default root is its documented CLI contract; the defect is the test exercising it against the real tree) |
| 2026-07-20 | Fix is two layers: patch `ensure_run` in the class setUp AND sandbox the class cwd into a tempdir, so any future unmocked cwd-relative write lands in the sandbox rather than the repository. Recurrence guard added at the runner level (`run_tests.py` `stray_artifact_paths`/`_stray_artifact_failure`): a run that creates a nested `.wavefoundry` under the scripts dir fails with the offending paths listed; pre-existing artifacts are snapshotted so only run-created ones fail. Guard demonstrated against a seeded artifact by unit test. | The mock alone fixes today's writer; the sandbox and guard close the class | Guard inside a test module (rejected: ordering-fragile; the runner sees the whole run) |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
