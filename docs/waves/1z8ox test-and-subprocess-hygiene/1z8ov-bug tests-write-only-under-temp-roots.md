# Tests Write Only Under Temporary Roots

Change ID: `1z8ov-bug tests-write-only-under-temp-roots`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-28
Wave: 1z8ox test-and-subprocess-hygiene

## Rationale

A downstream validation (RFC bug B8) reports that the framework test suite writes into the repository it runs in. A test run can then leave files in a checkout, change tracked state, or make results depend on what an earlier run left behind. It also means a suite run in a downstream fork writes into that fork. Which tests do this has not yet been established here, so this change starts with a census.

The readiness review found likely writers:

- Child Python processes write `__pycache__` into `scripts/`. `run_tests._run_file` passes `-B`, but child processes do not inherit it and no `PYTHONDONTWRITEBYTECODE` is set.
- SQLite reads of the live `.wavefoundry/index` can create `-wal` and `-shm` files.
- An unpatched server `ROOT` could record telemetry or index state into the real repository.

It found no direct write, `mkdir` or `unlink` against a repository-root constant.

## Requirements

1. **Census in an isolated checkout.** The census runs against a temporary clone with no MCP server, dashboard or index monitor attached. A clone, not a `git worktree`: a worktree shares the live repository's `.git`, so a test's git writes would land outside every snapshot.
   - The clone reproduces the current working tree, not HEAD: uncommitted changes and untracked non-ignored files are applied (for example `git diff HEAD` plus the untracked files), because the code under test is uncommitted. The Progress Log records the digest of what was applied.
   - `.wavefoundry/index` is copied in (never symlinked: a symlinked directory under `.wavefoundry` is refused by the lock-path rule and would send writes into the live index), while `index_build_status.lock.held` is false, with the SQLite `-wal` and `-shm` files together, so the tests that need a persisted graph run instead of being skipped. The census compares its skip count with a live run to confirm they ran.
   - The tree, including the clone's `.git`, is snapshotted before and after the run: every file's path, size and modification time, including ignored and untracked files.
   - The only exclusions are the test receipt and lock that `run_tests.py` writes.
   - Every test that creates, modifies or deletes anything else is listed with the path it touches.
   - The census also names, as its own assertion, whether the edit-gate state `.wavefoundry/guard-overrides.json` is unchanged. It is a security control.
2. **Static pass.** A short static pass covers what a snapshot cannot see: a test that writes and then cleans up.
   - Patterns: `REPO_ROOT`, `PROJECT_ROOT` or `SCRIPTS_ROOT` used as a write target; `--root={REPO_ROOT}`; `cwd=PROJECT_ROOT`.
   - Each hit is classified as a writer or as allowed, with a reason. For example, `test_graph_quality_eval._repo_probe` deliberately targets `docs/reports/` to check that the write is refused.
3. **Fix each writer.** Each listed test writes under a temporary root (a `tempfile` directory or a copied fixture tree), not the repository. A test that must read repository content reads it and writes elsewhere. `run_tests._run_file` sets `PYTHONDONTWRITEBYTECODE=1` in the environment it passes to the worker.
4. **Standing guard.** The guard generalises the existing stray-artifact guard in `run_tests._execute_files` (`stray_artifact_paths`, `_stray_artifact_failure`), in the same place. It snapshots, after the run lock is acquired, every tracked file and every untracked file that git does not ignore, plus `.wavefoundry/guard-overrides.json`. On any change it fails the run, naming the paths.
   - Ignored runtime paths (`.wavefoundry/logs/`, `.wavefoundry/index/`, `.wavefoundry/locks/`, `__pycache__`) are outside the standing guard, so it needs no host allowlist; the isolated census (Requirement 1) has no allowlist and catches test writes there. `.git/` is outside the snapshot.
   - The only exclusions are the receipt and lock `run_tests.py` itself writes.
   - A failed guard makes the run fail, so `main` writes no green receipt (it writes the cache only when the run succeeds). `--file` and `--schedule-control` share `_execute_files`, so the guard behaves the same there, and neither writes a receipt.
   - The failure message says that a concurrent edit by an operator or agent during the run, including opening an edit gate, also trips it.
5. **Document.** `docs/architecture/testing-architecture.md` states the rule that tests write only under temporary roots, and describes the standing guard (what it snapshots, and that ignored runtime paths are left to the isolated census).
6. **CHANGELOG.** A Fixed line.

## Scope

**Problem statement:** the test suite writes into the repository under test.

**In scope:**

- The census and static pass, the listed tests, the child bytecode setting, the guard.

**Out of scope:**

- Writes under the system temporary directory, and the user's tool venv or model cache. These are outside the repository; the telemetry case is covered by `1z8or`.

## Acceptance Criteria

- [x] AC-1: the census and the static pass are recorded in the Progress Log, with every writer and path (or an explicit statement that there are none) and the classification of each static hit. The census run happens after `1z8ow`'s new process fixtures land, or is repeated then.
- [x] AC-2: a full suite run in the isolated clone of Requirement 1 leaves the tree (including its `.git`) unchanged apart from the receipt and lock, the edit-gate file is unchanged, and its skip count matches a live run.
- [x] AC-3: the standing guard fails, names the path, and writes no green receipt when a scratch mutant writes a tracked or non-ignored file, or changes the gate file.
- [x] AC-4: the change's own suites pass, and the documents it edits validate.

## Tasks

- [x] Census in an isolated clone reproducing the working tree, with the index copied in; static pass.
- [x] Move each writer to a temporary root; set `PYTHONDONTWRITEBYTECODE=1` in `_run_file`.
- [x] Extend the stray-artifact guard in `_execute_files` to tracked and non-ignored files plus the gate file; tests.
- [x] `testing-architecture.md`; CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Census and fixes | implementer | readiness, `1z8ow` routing | Census after `1z8ow`'s fixtures land |
| Review | combined reviewer | Census and fixes | QA |

## Serialization Points

- `.wavefoundry/framework/scripts/tests/`, `.wavefoundry/framework/scripts/run_tests.py`
- `docs/architecture/testing-architecture.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/testing-architecture.md`, in the Framework Script Hygiene and Canonical Runner sections: the rule that tests write only under temporary roots, and the guard.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Establishes the scope |
| AC-2 | required | The fix |
| AC-3 | required | Keeps it fixed |
| AC-4 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Delivery repair DEL-F1 and DEL-F3. The guard failed runs whenever the framework's own context-efficiency projection rewrote the open `wave.md` mid-run. `repo_state_snapshot` now keeps each wave record's bytes (waves root from `record_paths.unvalidated_record_roots`, record name from `vocabulary_profile.RECORD_FILENAME`, both stdlib-only and imported lazily, with `docs/waves/` and `wave.md` as the fallback); `_repo_state_changes` tolerates a changed wave record only when `_strip_projected_regions` (legacy markers canonicalized, the `wave:context-efficiency` and `wave:exploration-avoided` regions with their headings and state comments removed, seam whitespace collapsed) gives identical text. Marker constants are pinned against `context_efficiency` and `exploration_avoided`. `.wavefoundry/guard-overrides.json` is compared by SHA-256 content hash. An end-of-run snapshot that cannot be taken now fails the run with the cause (it was silently skipped). New tests in `test_run_tests_repo_guard.py`: `WaveRecordProjectionTests` (projection-only rewrite passes and writes the receipt; projection appending its blocks passes; body edit, edit inside the `wave:review-status` region, and projection plus body edit each fail naming the record; `test_dropping_the_tolerance_fails_the_projection_only_run`; marker and matcher pins), `GuardOverridesHashTests` (2), `GitListingTimeoutTests` (5); fixtures rendered with the real `replace_checkpoint_block` producers. Scratch mutant (tolerance removed from `_repo_state_changes`): the two projection-only tests fail. `test_secrets_prefix_collapse._NoRepoWrites` records the bytes the real `save_exceptions` writes into a temporary root instead of re-serializing. CHANGELOG 1z8ox bullets and the testing-architecture guard paragraph state the tolerance; the retrieval baseline row names `1yxyw-e3` as the former baseline (its `evaluator_identity.source_sha256` `bb129af8...` matches neither HEAD's nor the current `retrieval_eval.py`), and the `test_docs_lint` pin follows. Gapfill: grep and sed read `run_tests.py`, the projection code and the test files for bulk context after `code_*` lookups were loaded, because the edits needed exact surrounding text | focused runs: repo_guard 29, run_tests_cache 97, run_tests_lock 15, tree_kill_routing 29, secrets_prefix_collapse 17, setup_wavefoundry 46, doc_drift 103, docs_lint 1115, all OK; scratch mutant |
| 2026-09-28 | Post-fix census (AC-2). New clone of HEAD `c490e286` with the current working tree applied (`git diff --binary HEAD` sha256 `89be0718...`, verified identical in the clone; 30 untracked non-ignored files, list sha256 `b826206d...`), index copied without the receipt as below, no MCP server attached. Full run: 9942 tests in 140 files, skipped 16 (the live suite reports 16), and the before/after snapshot of every file, including `.git/`, `.wavefoundry/index/` and ignored files, is identical apart from the receipt and lock. `.wavefoundry/guard-overrides.json` unchanged. Two files failed, neither a write: `test_review_policy` (the same corpus assertion as census 1) and `test_tree_kill_routing`, whose census counted the new timed `git ls-files` call in `run_tests.repo_state_snapshot`; the timeout was removed (a local read that takes no lock), and a per-file re-run in the clone with the final runner of `test_tree_kill_routing` and every file that wrote in census 1 changed nothing and passed | clone census 2, per-file re-run |
| 2026-09-28 | Fixes and standing guard. `test_secrets_prefix_collapse`: the three scans of `REPO_ROOT` run under `_NoRepoWrites`, which records `update_scanner_skips` and `save_exceptions` instead of writing; the fixtures test compares what would be written with the ledger bytes. `test_server_tools_retrieval`: the live-graph tests read a copy of the project index under a temporary root (`_repo_index_copy_root`, files copied and never opened, copy-on-write on macOS, receipt not copied). `run_tests._run_file` sets `PYTHONDONTWRITEBYTECODE=1`. `test_run_tests_cache.test_cache_hit_bypasses_lock_acquisition` now patches `_read_cache` (it depended on the real receipt existing; in a clone it ran the suite path and errored). Guard: `repo_state_snapshot` (tracked and non-ignored files from `git ls-files -co --exclude-standard`, plus the gate file, size and mtime, receipt and lock excluded, `None` outside git with a stated skip message) is taken after the lock in `_execute_files`; `_stray_artifact_failure(preexisting, repo_before)` keeps its old call shape and adds the repository-state check, evaluated before the failed-files branch so a failing run still names changed paths. New `test_run_tests_repo_guard.py` (14 tests) runs real worker subprocesses against a temporary git repository. Mutants: disabling the check fails 6 tests, dropping the gate file fails 3, dropping the bytecode variable fails 1. A focused live run tripped the guard on a concurrent `wave.md` edit, as documented | focused runs; scratch mutants |
| 2026-09-28 | Static pass (Requirement 2). No write, `mkdir`, `unlink` or copy targets `REPO_ROOT`, `PROJECT_ROOT` or `SCRIPTS_ROOT`; every `shutil.copytree` hit copies FROM them into a temporary directory. `--root={REPO_ROOT}`: `test_graph_quality_eval` 1096 (report goes to a temporary file) and 1178 (`_repo_probe`, refusal checked), both allowed. `cwd=PROJECT_ROOT`: `test_docs_lint` 57, 5516, 5804 (the target is the temporary `PROJECT_ROOT` in the environment), `test_render_platform_surfaces` 365, 2484 and `test_render_agent_surfaces` 1185, 1223, 3313 (`--repo-root` is a temporary directory), allowed. `cwd=SCRIPTS_ROOT`: `test_render_agent_surfaces` 1147, 1169 and `test_per_area_agents_context` 151 (`--repo-root` temporary), allowed. `cwd=REPO_ROOT`: `test_per_area_agents_context` 212 and `test_python_parse_diagnostics` 221 run `git ls-files` (read-only), allowed. The writers the snapshot cannot see were found by the census instead: `check_hardcoded_secrets(REPO_ROOT, ...)` publishes the guard-skip ledger and may save `docs/scan-findings.json` | code_keyword, code_pattern |
| 2026-09-28 | Census 1 (AC-1), after `1z8ow`'s fixtures landed in the working tree. Clone of HEAD `c490e286` plus `git diff --binary HEAD` (sha256 `7365419d...`, verified identical in the clone) and 29 untracked non-ignored files (list sha256 `318ee325...`); `.wavefoundry/index` copied (not linked) while the index-build lock was not held, checked with the indexer's own probe because MCP `index_build_status` reported no lock during a running build. Full run: 9928 tests in 139 files, skipped 25 against 16 live. Writers: `test_server_tools_retrieval` created `.wavefoundry/index/index.sqlite-wal` and `-shm` (live-graph tests open the real index); `test_secrets_prefix_collapse` modified `.wavefoundry/index/scan/guard-skips.json`. A per-file re-run with a snapshot after each file also found Python children writing `__pycache__` under `scripts/` and `scripts/wf_server/` (`test_dashboard_server`, `test_design_token_build`, `test_indexer`, `test_lifecycle_mutation_lock`, `test_per_area_agents_context`, `test_render_agent_surfaces`, `test_sqlite_storage_migration`, `test_storage_upgrade_resume`, `test_upgrade_wavefoundry`), hidden in the full run by the runner's closing cleanup. No tracked or non-ignored file changed, `.git/` unchanged, `.wavefoundry/guard-overrides.json` unchanged. The 9 extra skips were all `test_server_tools_retrieval` live-graph tests: the storage-migration receipt pins the index to its original path, so readers fail closed with `storage_receipt_identity_mismatch` in a copy; census 2 omits the receipt from the copied index. Two failures, neither a write: `test_review_policy` (a corpus assertion over the untracked `1zbrq` change document, outside this change) and `test_run_tests_cache` (read the real receipt, fixed) | clone census 1, per-file attribution |
| 2026-09-28 | Delta readiness review after the serialization fix brought in the architecture lane: B1 (the host allowlist missed the Stop hook, index and other logs) resolved by the red-team alternative, a standing guard over tracked and non-ignored files plus the gate file with ignored paths left to the isolated census; B2 (a worktree or clone checks out HEAD) resolved by a clone that reproduces the working tree; N1 extend the existing stray-artifact guard; N2 no shards; N3 moot; N4 copy the index, never symlink, and compare skip counts | delta readiness review |
| 2026-09-28 | Planned from a downstream validation report (B8); census not yet run | report |
| 2026-09-28 | Readiness review folded in: the census runs in an isolated worktree because the live session writes telemetry, index and locks; the standing guard gets a reasoned allowlist; static pass; child bytecode; ordering after `1z8ow` | readiness review B5, N1, N2, N5 |
| 2026-09-28 | Confirmation round folded in: exact allowlist paths, SQLite siblings, `locks/` is runtime state not gate state | confirmation review N-D |
| 2026-09-29 | Delivery repair DEL-F4 (operator review). The literal `docs/waves/` and `wave.md` fallback in `_wave_record_matcher` failed the record-layout and vocabulary censuses and was removed; this supersedes the fallback described in the DEL-F1 row. The matcher now returns `None` when `record_paths` or `vocabulary_profile` cannot be imported, `_is_wave_record` treats `None` as no wave record, and the projection tolerance is then off so the guard stays strict. `test_without_the_layout_modules_no_file_is_a_wave_record` blocks each module in turn. Reverified independently: scratch mutants restoring the literal fallback, making the `None` branch tolerant, and building the default without literals each fail a test. Full suite 9963 tests OK. | independent-delivery-review.md; events.jsonl DEL-F4 |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | Census by tree snapshot in an isolated worktree, plus a static pass | The snapshot finds writers that leave files behind; the static pass finds those that write and then clean up; isolation removes writes by the live host | Snapshot the live checkout (not deterministic) |
| 2026-09-28 | The standing guard covers tracked and non-ignored files plus the gate file; ignored runtime paths are left to the isolated census | A host allowlist is either too narrow (flaky: the Stop hook and index logs write every run) or too wide (blind); tests must never write tracked or non-ignored files (readiness red-team) | Allowlist live-host paths |

## Risks

| Risk | Mitigation |
| --- | --- |
| A test writes into an ignored runtime path (for example telemetry through an unpatched server root), which the standing guard does not see | The isolated census of AC-2 has no allowlist, so it catches these |
| Copying `.wavefoundry/index` (about 500 MB) into the clone is slow | Copy only for the census run; never symlink it; the standing guard does not copy |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
