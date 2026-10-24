# Host-Dependent Test Failures on Python 3.11 and Newer LanceDB

Change ID: `21goe-bug host-dependent-test-failures-on-3-11-and-newer-lancedb`
Change Status: `implemented`
Owner: Engineering
Status: planned
Last verified: 2026-10-24
Wave: 21ilf waveforge-1-36-follow-ups

## Rationale

A downstream distribution reports two test files failing on pristine 1.36.0 for reasons that are not product defects.

**`tests/test_verified_pack_stat_kinds.py`.** It fails on Python 3.11 with three failures and one error. This was reproduced here with 3.11.17; the module passes on 3.14.

Cause, traced by instrumenting `os.lstat`:
- The path-side subtests patch `os.lstat` and expect the shifted stat to reach the guard's own `Path.lstat()` comparison.
- On 3.12 and later, `pathlib.Path.lstat()` calls `os.lstat`, so the patch reaches that comparison.
- On 3.11 it calls `os.stat(..., follow_symlinks=False)`, so the patch misses the guard's comparison. The shifted stat then surfaces only inside `contained_files`, which refuses earlier with `ContainedFileRefused` or a different guard code.

So on 3.11 the `st_size` and `st_mtime_ns` subtests see no refusal at all (`ValueError not raised`): the simulated change never reaches any check. The product guard is unchanged. The tests simulate the change at a seam that depends on the Python version, and the two-site patch below lets the guard see it on every version (reproduced: 11 of 11 pass on 3.11.17 and 3.14.8 in a scratch copy). Python 3.11 is the supported minimum.

**`tests/test_storage_upgrade_resume.py`.** `StorageRebuildPublicationTests` runs whenever any `lancedb` imports. `sqlite_storage_migration._legacy_table` refuses every version except the pinned migration-only reader `0.33.0`. With a newer `lancedb`, `test_duplicate_transfer_refuses_then_explicit_rebuild_publishes_current_sources` therefore fails with `MigrationRequired: storage_legacy_reader_version` before it reaches the behaviour it tests.

## Product Intent

The framework suite runs green on every supported Python version and tool environment for maintainers and distributions. Before: these tests fail on Python 3.11 or with a newer `lancedb` although the product behaves correctly. After: the stat-kind tests pass on 3.11 through 3.14, and the legacy-reader tests skip with a stated reason when the pinned reader is absent. Boundaries: no product behaviour change; the only product edit is naming the pinned reader version once.

## Requirements

1. The path-side simulations in `tests/test_verified_pack_stat_kinds.py` shift the target's path stat at every call site that `Path.lstat()` uses on each supported version. That means `os.lstat` and `os.stat` with `follow_symlinks=False`. The guard's own comparison then sees the change on 3.11 as on 3.14, and the expected refusal codes are unchanged.
2. `sqlite_storage_migration` names its pinned migration-only reader version in one module constant. Every site that pins that reader reads it: `_legacy_table`, the provisioning requirement in `setup_index.ensure_migration_deps`, the availability check in `tests/test_storage_upgrade_resume.py`, and the version checks in `tests/test_sqlite_storage_migration.py`. The derived set is every literal `0.33.0` that names the migration reader in framework scripts and tests, re-run at implementation; the public vector evaluation scripts (`tests/vector_public_*.py`) pin an evaluation version, not the migration reader, and are out of scope.
3. The availability check is true only when the installed `lancedb` equals the pinned version. When it is false, the class skips with a reason that names the required version. This applies to every test in the class.
4. Platforms: Windows, macOS, Linux and WSL2 run the same test logic. Windows `Path.lstat()` also reaches `os.lstat` on 3.12 and later. The patch covers both call sites on every platform, so no platform branch is needed.

## Scope

**Problem statement:** two test files fail on supported hosts for host reasons, not product reasons.

**In scope:**

- `tests/test_verified_pack_stat_kinds.py` path-side patches.
- The `sqlite_storage_migration` reader-version constant and the `tests/test_storage_upgrade_resume.py` availability check.
- Other tests in the same files that patch only `os.lstat` for a path-side `Path.lstat()` comparison, found by census.

**Out of scope:**

- The reported dashboard child exit (`DashboardManagedIdentityTests.test_mcp_start_confirms_serving_own_child`). It passes here on 3.11.17 with the pinned environment and on 3.14, so it is not reproduced; the reply asks for the child's log.
- Provisioning the pinned reader in test environments.
- A permanent 3.11 test lane.

## Acceptance Criteria

- [x] AC-1: `tests/test_verified_pack_stat_kinds.py` passes on Python 3.11 with the pinned tool environment and on 3.14. Known-bad: with the path-side patch reduced to `os.lstat` alone, the same 3.11 run reproduces the three failures and one error.
- [x] AC-2: A subprocess test puts a fake `lancedb` module with a different `__version__` first on the import path, imports the test module, and runs `StorageRebuildPublicationTests`: every test reports skipped, with a reason naming the pinned version. A unit test of the availability check covers the pinned version (true), a non-pinned importable version (false) and a missing module (false). Known-bad: today's import-only check returns true for the non-pinned version.
- [x] AC-3: Every site in requirement 2's derived set reads the constant; a test fails if a migration-reader literal `0.33.0` remains in those files outside the constant's definition.
- [x] AC-4: The change's own suites and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.

## Tasks

- [x] Patch both path-stat call sites in the stat-kind tests; re-run on 3.11 and 3.14; census the file for other `os.lstat`-only path patches.
- [x] Add the reader-version constant; use it in `_legacy_table` and the test availability check; add the availability-check test.
- [x] CHANGELOG Unreleased entry (Fixed).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes |
| ---------- | ----------- | ---------- | ----- |
| tests      | implementer | —          |       |


## Serialization Points

- `.wavefoundry/framework/scripts/tests/test_verified_pack_stat_kinds.py`, `.wavefoundry/framework/scripts/tests/test_storage_upgrade_resume.py`, `.wavefoundry/framework/scripts/tests/test_sqlite_storage_migration.py`, `.wavefoundry/framework/scripts/sqlite_storage_migration.py`, `.wavefoundry/framework/scripts/setup_index.py`

## Affected Architecture Docs

N/A: test seams and one module constant; no boundary, flow or verification-topology change.

## AC Priority


| AC   | Priority | Rationale |
| ---- | -------- | --------- |
| AC-1 | required | the reported 3.11 failure |
| AC-2 | required | the reported lancedb failure |
| AC-3 | important | prevents the skip drifting from the product pin |
| AC-4 | required | change-local suites and docs |


## Progress Log


| Date       | Update  | Evidence |
| ---------- | ------- | -------- |
| 2026-10-24 | Planned | Waveforge 1.36.0 follow-up; 3.11.17 reproduction and `os.lstat` trace in session |
| 2026-10-24 | Readiness round 1 amendments: rationale narrowed (on 3.11 size and mtime see no refusal, the guard never saw the change); the pin set widened to every migration-reader literal, including `setup_index.ensure_migration_deps`; AC-2 names the fake-module subprocess and the non-pinned case; AC-3 pins the derived set. AC-1 oracle: `/opt/homebrew/bin/python3.11` venv with the tool-venv freeze (numpy floating below 2.5), run with `PATH=<venv>/bin:$PATH WAVEFOUNDRY_TOOL_VENV=<venv>`. | readiness code-reviewer, qa-reviewer, red-team |
| 2026-10-24 | Readiness round 2 clarifications (Progress Log only; Requirement 2's derivation rule governs over its examples): the derived pin set includes `tests/test_setup_index.py` (the three `ensure_migration_deps` expected requirement strings) and both `MigrationRequired` messages in `sqlite_storage_migration.py`, which interpolate the constant. Requirement 2's evaluation exclusion covers every evaluation record, including `tests/test_vector_public_compare.py` and `tests/fixtures/vector_backend_eval_*.json`. AC-3's scan covers the derived set and excludes its own literal. AC-2's subprocess requires the native SQLite runtime to be available, and the test asserts that the skip reason comes from the legacy-reader check, so a native-runtime skip cannot satisfy it. `tests/test_setup_index.py` is shared with 21ij7; the two edits touch different tests. | readiness code-reviewer and qa-reviewer recheck |
| 2026-10-24 | Readiness architecture note: the first task covers every site in Requirement 2's derived set, including `setup_index.ensure_migration_deps` and `tests/test_sqlite_storage_migration.py`; `setup_index` reads the constant lazily, as it already imports `sqlite_storage_migration`. | readiness architecture-reviewer |
| 2026-10-24 | Readback: the stat-kind path-side tests shift the target's no-follow path stat through both `os.lstat` and `os.stat(follow_symlinks=False)` via one helper, so the guard's own comparison sees it on 3.11 and 3.14 with unchanged expected codes (AC-1). `sqlite_storage_migration` gains `LEGACY_READER_VERSION`; `_legacy_table` and both messages, `setup_index.ensure_migration_deps`, the resume tests' availability check and the migration and setup tests read it (AC-2, AC-3). No product behaviour change. Files: the two test files above, `tests/test_sqlite_storage_migration.py`, `tests/test_setup_index.py`, `sqlite_storage_migration.py`, `setup_index.py`. Example: before, 3.11 reports 3 failures and 1 error; after, 11 OK. | implementation |
| 2026-10-24 | Implemented. AC-1: `shifted_no_follow_stat` patches `os.lstat` and `os.stat(follow_symlinks=False)`; 11 of 11 pass on 3.11.17 (scratch venv311, tool-venv freeze with numpy below 2.5) and on 3.14.8; the unpatched file gives 3 failures and 1 error on 3.11. AC-2: `_legacy_available` requires `LEGACY_READER_VERSION`; the native and legacy skips are separate decorators; `LegacyReaderPinTests` covers pinned, non-pinned and missing modules and a `-B` subprocess with a fake non-pinned `lancedb` that skips every rebuild test with the stated reason. AC-3: `_legacy_table` and both messages, `setup_index.ensure_migration_deps`, `tests/test_sqlite_storage_migration.py` and `tests/test_setup_index.py` read the constant; the scan test reads sources through `framework_files.source_path` (a first full run failed `test_server_package` on a direct read, fixed). Focused runs OK: stat kinds 11, storage resume 20, sqlite migration 133, setup index 204, server package 31. | implementation |
| 2026-10-24 | Delivery repair CODE-DEL-1 (red-team, confirmed by qa-reviewer and code-reviewer): the non-pinned-reader subprocess put a fake package on `PYTHONPATH`, which the child's tool-venv activation shadowed with the real pinned reader under any interpreter other than the tool venv (0 of 9 skips). The child is now a `-c` driver that plants the fake in `sys.modules` before the test module imports; it passes under the tool venv and system Python 3.14. Folded in: the stat-kind path-side assertion pins the guard's own `index_guard_durable_pack_invalid: replaced file identity` message, so a `contained_files` refusal cannot satisfy it (11 OK on 3.11 and 3.14). | delivery review |
| 2026-10-24 | Final full suite after delivery repairs: `run_tests.py --no-cache` ran 12100 tests across 208 files, OK; the framework test receipt is current. | `scratchpad/21ilf-full-2.log`; `.wavefoundry/framework/test-cache.json` |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-10-24 | Patch both path-stat call sites in the tests | Root cause is the test seam, traced on 3.11 and 3.14; the product refuses on both versions | Patch `pathlib.Path.lstat` (couples the test to pathlib internals that changed in 3.12); accept either refusal code (weakens the assertion about which check fires) |
| 2026-10-24 | Skip when the pinned reader is absent, keyed to one product constant | The tests exercise the pinned reader only; a literal in the test would drift from the pin | Provision the reader in tests (network and install work); compare a literal (drifts silently into a skip) |
| 2026-10-24 | Mechanism efficacy | Replay: the reported 3.11 run and the newer-lancedb run both turn green or skip with a reason. Control: tests decide the outcome directly. Wrong flags: a skip could hide a real failure if the check went too broad, so AC-2 fails when it returns true for any version. Cheaper path: none smaller. Measure: the distribution's next run reports these IDs passing or skipped. | — |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A future pathlib change moves `Path.lstat()` again | Patching both call sites covers each version's route; AC-1 runs on 3.11 and 3.14 |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
