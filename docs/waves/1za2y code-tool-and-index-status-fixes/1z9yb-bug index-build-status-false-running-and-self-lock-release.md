# Index Build Status Neither Misreports Nor Releases the Build Lock

Change ID: `1z9yb-bug index-build-status-false-running-and-self-lock-release`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-29
Wave: 1za2y code-tool-and-index-status-fixes

## Rationale

`index_build_status` has been seen reporting a lock that looked stale. The original observation does not say which field showed it; the code has two defects that produce such reports, and the second one is more serious than a wrong label.

1. **A false "running".** `index_handlers._background_build_status` reports the background code build as `running` whenever `server_impl._pid_is_running` succeeds for the pid in `.wavefoundry/index/background-build.pid`. On POSIX that is `os.kill(pid, 0)`, which also succeeds for a finished child that has not been reaped, a pid the OS has reused for another program, and a child started by an earlier server instance. The sibling check `_background_refresh_active` reaps finished children and verifies the command line; this one does neither. The response can then say `state: running` while `lock.held` is false, and `index_health` chooses its next action from the same status.
2. **The server can release its own build lock.** `index_build(content='fts')` holds the index build lock inside the MCP server process (`idx_mod._index_build_lock`, a POSIX `lockf` record lock). The status path (`_index_build_lock_info`, reached from `index_build_status` and from the quiet-period monitor thread through `_background_refresh_active`) opens and closes the same lock file in the same process: `indexer._index_build_lock_held` does `os.open` then `os.close` around `F_GETLK`, and the owner record is read from the file. Closing any descriptor of a file releases every POSIX record lock the process holds on it, so a status check during an in-process build silently drops the lock. The quiet-period monitor then sees `held: false` and can start a background refresh, whose child takes the released lock: two builds write the index at once. `F_GETLK` also never reports a lock the calling process holds, and a second `_index_build_lock` in the same process succeeds today (a process can always re-take its own record lock), after which its release frees the first holder's lock too. Two builds hold the lock inside the server process: the fts rebuild and `index_optimize` (`optimize_index_tables`). Both reviewers reproduced the release with a scratch `lockf` probe on macOS.

The builder-conflict message (`indexer.format_index_build_lock_conflict`) still says the owner pid "appears stale ... possible inherited lock descriptor", wording from the earlier `flock` design; `lockf` locks are not inherited by children.

## Requirements

1. The background build is reported `running` only when the pid in `background-build.pid` is still a live index builder for this root: a finished child is reaped when it is ours, and a pid whose command line is not an index build is not running. The predicate is extracted from `_background_refresh_active` (reaping, `_process_cmdline`, `_index_builder_cmdline_targets_root`) and shared by both checks, not duplicated. `background-build.pid` is written by `setup_index`, so the command-line check is what corrects most cases.
2. `_index_build_lock` records that this process holds the lock in process-wide state that an MCP reload does not replace: a registry keyed by the resolved lock path in a module the reload leaves in `sys.modules` (for example `runtime_lock`), not a variable of the indexer module, which a reload rebuilds. Every in-process reader consults that registry. Change `1z9u7` removes the per-call fresh indexer loads, so no reader bypasses it.
3. While this process holds the lock, no code in the process opens the lock file. The set to cover is every in-process opener of the lock file, derived from the probe and the lock-metadata readers; at planning time it is `_index_build_lock_info` (probe and metadata read, reached from `index_build_status` and from `_background_refresh_active`), the metadata read in the quiet-period monitor `_maybe_refresh_if_stale`, the lock-owner read in `index_handlers.py`, the metadata read at the start of `_index_build_lock` itself, and `format_index_build_lock_conflict`. Status during an in-process hold reports `held: true` with this process as owner.
4. A second `_index_build_lock` in the same process while it already holds the lock raises `IndexBuildAlreadyRunning` before reading the lock file.
5. `state` and `lock.held` in `index_build_status` are not reported as `running` from the background build together with `held: false` without a note stating which is authoritative.
6. The conflict message describes the current `lockf` design and names `index_build_status` `lock.held` as the check.
7. Every document that says `held` comes only from the OS probe states the in-process rule: the `index_build_status` row in `docs/specs/mcp-tool-surface.md` (plus the AC-5 note), the docstrings of the `index_build_status` tool in `server_impl.py`, `_index_build_lock_info` and `indexer._index_build_lock_held`, and seed `140-reindex-ongoing.prompt.md` (a seed edit under the `seed_edit_allowed` gate).

## Scope

**Problem statement:** status can call a finished build running, and a status check during an in-process build releases that build's lock.

**In scope:**

- `_background_build_status`, the lock status path in `wf_server/index_handlers.py` and `indexer.py`, the in-process holder tracking, and the conflict message.
- Tests for a finished or reused background pid and for a status check during an in-process build.

**Out of scope:**

- The lock-file-as-last-owner-record design and the age-based `classify_index_build_lock_owner` labels, beyond the message wording.
- Moving the fts rebuild out of the server process.
- The unused `stale_locks_cleaned` response field (removing it changes the response shape; it can go in a later change).

## Acceptance Criteria

- [x] AC-1: with `background-build.pid` naming a live process that is not an index build for this root, or a finished child, `index_build_status` does not report the background build as `running`, and `index_health` does not recommend waiting for it.
- [x] AC-2: while this server process holds the index build lock (fts rebuild and `index_optimize` paths), `index_build_status` and the quiet-period monitor's path through its metadata read leave the lock held as observed from a second process, and status reports `held: true` with this process as owner.
- [x] AC-3: a second `_index_build_lock` in the same process raises `IndexBuildAlreadyRunning` and the first hold is still observed from a second process afterwards.
- [x] AC-4: with a hold open in the process, clearing the script cache and reloading `server_impl` (as `wf_reload_mcp` does) leaves status reporting the hold without opening the lock file, and the lock is still observed from a second process.
- [x] AC-5: `index_build_status` never reports `state: running` from the background build together with `held: false` without a note stating which is authoritative.
- [x] AC-6: the conflict message no longer mentions an inherited descriptor or a stale owner pid and names `lock.held` as the check, and the documents in Requirement 7 state the in-process rule.
- [x] AC-7: the change's own suites and every test it adds pass, and the documents it edits validate.

## Tasks

- [x] Extract the shared liveness predicate and use it for the background build status.
- [x] Record in-process ownership in a reload-surviving registry keyed by lock path, refuse a second in-process acquire, and make every opener in Requirement 3 skip the file while held.
- [x] Reconcile `state` with `lock.held`; update the conflict message and the existing message assertions.
- [x] Tests: non-builder pid, finished child, holds on both in-process paths observed from a second process, the monitor path, second acquire, reload during a hold, and the message.
- [x] Docs in Requirement 7, seed 140 under the seed gate; CHANGELOG Fixed entry.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Status and lock ownership | implementer | 1z9u7 | Needs the shared indexer module |
| Review | code, QA, architecture reviewers | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/index_handlers.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/wf_server/server_impl.py`
- `.wavefoundry/framework/scripts/tests/`
- `docs/specs/mcp-tool-surface.md`, `.wavefoundry/framework/seeds/140-reindex-ongoing.prompt.md`

Root release note: CHANGELOG.md.

## Affected Architecture Docs

N/A unless implementation changes the lock ownership model; the fix keeps `lockf` and the last-owner record and adds in-process bookkeeping.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | False running state |
| AC-2 | required | A status check must never release a held build lock |
| AC-3 | required | A second in-process acquire must not free the first |
| AC-4 | required | Reload must not reopen the lock file during a hold |
| AC-5 | important | Consistent status fields |
| AC-6 | important | Accurate wording and docs |
| AC-7 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-29 | DEL-F3 reverified RESOLVED by a fresh code and security reviewer (review script: restored unlink gives path_exists false and an external ACQUIRED; repaired gives path_exists true and the external probe blocked; the three tests fail only with the unlink restored). Their optional Q-1 applied: `test_stale_lock_file_is_reused_and_its_metadata_replaced` read the lock file inside the hold, which releases the process's record lock; it now reads the metadata from a subprocess. Informational: a stale carrier the user cannot write now fails at open with a clear `RuntimeLockError` instead of being unlinked | `test_indexer.IndexBuildLockTests` 18 OK |
| 2026-09-29 | Delivery repair round 2, DEL-F3 (operator review, blocking): `_index_build_lock` unlinked a lock file whose metadata looked stale before its own acquire, so a contender refused because another build had just locked that inode had already deleted the carrier, and a third process locked a fresh file alongside the running build (AC-3). The unlink is removed in `indexer._index_build_lock`: the carrier is never deleted and `write_metadata` truncates and rewrites the same inode after acquire, which keeps wave 1p2q3's goal (status never shows the dead owner). `test_indexer.test_stale_lock_file_is_unlinked_before_acquire` (which pinned a fresh inode) is replaced by `test_stale_lock_file_is_reused_and_its_metadata_replaced`; new cross-process test `test_a_refused_acquire_never_replaces_a_held_carrier` (holder process with dead-pid metadata; contender refused; inode unchanged; third-process lockf probe still held) and the review's interleaving as `test_a_contender_paused_after_classifying_stale_keeps_the_hold` (contender paused after classifying stale, another thread acquires, external exclusion checked throughout). Scratch mutant restoring the unlink fails all three. `chunking-and-indexing-pipeline.md` last-owner paragraph and the CHANGELOG 1za2y status bullet updated. No other code deletes `index-build.lock` (census: unlink/os.remove/rmtree near lock in non-test scripts; the upgrade runner's unlink is the separate legacy root lock) | focused suites 27 OK; scratch mutant |
| 2026-09-29 | Delivery repair round 1. DEL-F1 (red-team RT-1, code CODE-1, QA-2): `wf setup` and `wf update-indexes` run `setup_index.main` in the `wf_cli.py` process, which stamps `background-build.pid` with its own pid, so the new predicate reported a live setup as completed; `_pid_is_live_index_build(unbound_ok=True)` now also accepts setup entry points (`_is_setup_entry_cmdline`: `setup_wavefoundry.py`, or `wf_cli.py` followed by `setup` or `update-indexes`) under the same root rule and a zombie check, while the lock-reclaim classifier keeps its narrower markers. DEL-F2 (architecture ARCH-1, CODE-2, RT-2): the hold is now registered as part of acquiring, under a re-entrant `runtime_lock.process_hold_guard()` that `read_index_build_lock_metadata` and `_index_build_lock_held` also take around check-and-open, so a monitor-thread reader cannot open the file between acquire and registration; the second-acquire check repeats under the guard. ARCH-3: the predicate uses `server_impl._indexer_module()`, so a refused fresh load no longer fails open to running. ARCH-2: `docs/architecture/chunking-and-indexing-pipeline.md` gained the in-process hold rule (this change's Affected Architecture Docs answer predates it). QA-1, QA-3: the startup-load test now clears the loaded indexer and runs only `register_mcp_surface`; the non-builder test uses a real other process. DOC-1, DOC-3, DOC-5 wording fixed. Tests: `test_a_reader_thread_during_acquire_cannot_release_the_lock`, `test_live_setup_entry_points_are_running`, `test_other_cli_commands_and_other_roots_are_not_running`, `test_a_refused_fresh_indexer_load_does_not_make_a_stranger_running`. Scratch mutants: no guard and late registration each fail the reader-thread test; no setup-entry acceptance fails 4 setup subtests; `_load_script` in the predicate fails the refused-load test; no startup load fails the startup test | focused suites OK; scratch mutants |
| 2026-09-29 | Full suite run: the first run failed `test_mcp_tool_registry.HandlerDigestTests` (the handler-digest fixture pins tool docstrings; exactly `code_constants`, `code_keyword`, `code_list_files`, `code_pattern` and `index_build_status` moved, all edited on purpose by 1z9ya and 1z9yb, and only those entries were refreshed) and `test_server_package.RetiredFlatNameCensusTests` (new tests used `from wf_server import <evicted module>`, which reads a stale module after a reload; changed to `import wf_server.<name> as <name>`). Rerun green | `run_tests.py --no-cache`: 10031 tests across 143 files OK |
| 2026-09-29 | Implemented. `_pid_is_live_index_build` (reap first; server-registered child, or classifier `live` plus a command line that targets the root; probe failure stays live) is shared by `_background_refresh_active` and `_background_build_status`, the latter with `unbound_ok` because `wf setup` may run without `--root`. `runtime_lock` gains a process hold registry keyed by resolved lock path; `_index_build_lock` refuses a second in-process acquire before touching the file, registers after writing metadata and releases before unlocking; `read_index_build_lock_metadata` and `_index_build_lock_held` answer from the registry without opening the file. `index_build_status` adds `state_note` when the background run is live without the lock. Conflict wording, spec row, three docstrings and seed 140 (under `seed_edit_allowed`) updated. Four existing tests that used the test runner's own pid as a running build now use a real idle process shaped like `setup_index.py --root <root>` (`spawn_index_builder_process`). Scratch mutants: disabling registration fails 4 of the hold tests; restoring bare liveness fails the non-builder and other-root tests, and also dropping the reap fails the finished-child test. Found while running: `test_indexer.FileWalkerTests.test_wave_ledger_predicate_is_the_single_review_evidence_definition` fails when loaded in one process with `test_index_source_guard`, also at HEAD, so it predates this wave. Gapfill: lock openers enumerated with grep over the edited files, because the MCP code tools run in the server whose lock handling is being changed | `tests/test_index_build_lock_process_hold.py` 7 OK; `BackgroundBuildStatusTests` 7 OK; lock suites 467 run, 1 pre-existing order failure |
| 2026-09-29 | Readiness confirmation: the ownership record moved from the indexer module (rebuilt by reload) to a reload-surviving registry keyed by lock path; AC-4 states how the reload is simulated. | code and QA confirmation |
| 2026-09-29 | Readiness review folded in (security S1/S2, code C1/C2/C5, QA Q3/Q4, docs D1, architecture A1): shared module instance via 1z9u7, full opener list, second-acquire refusal, `index_optimize` as a second holder, reload during a hold, extracted liveness predicate, docs and seed 140. Reviewers reproduced the self-release with a scratch `lockf` probe. | readiness review |
| 2026-09-29 | Planned from code reading. Defect 1 follows from `_background_build_status` using a bare `_pid_is_running`. Defect 2 follows from the in-process `lockf` hold in the fts rebuild and the `os.open`/`os.close` in `_index_build_lock_held`; how often the two overlap in practice is unmeasured. Neither is reproduced yet; implementation starts with a reproduction of each. | `index_handlers._background_build_status`, `_index_build_lock_info`, `indexer._index_build_lock_held`, the fts branch of `index_build` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-29 | Share one indexer module (via 1z9u7), record ownership there, refuse a second in-process acquire | The red-team's simpler path: one module instance fixes the invisible-flag problem the readiness review found | A flag in the per-call fresh indexer module (never seen by the status path) |
| 2026-09-29 | Track in-process ownership and skip the probe while held; reuse the reap-and-command-line liveness check | Smallest change that removes both defects and keeps the lock design | Run the fts rebuild in a subprocess (larger change to a working build path); derive `state` only from `lock.held` (loses the build-log progress the background status reports) |

## Risks

| Risk | Mitigation |
| --- | --- |
| Another in-process opener of the lock file is missed | Derive the set from the probe and the metadata readers; the AC-2 test observes the lock from a second process |
| The ownership record is lost on reload or invisible to a reader | Keep it in a reload-surviving registry, not the indexer module; AC-2 and AC-4 observe the lock from a second process |
| The ownership flag outlives a lock release on error | Set and clear it inside the lock's context manager, with a test that raises inside the hold |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
