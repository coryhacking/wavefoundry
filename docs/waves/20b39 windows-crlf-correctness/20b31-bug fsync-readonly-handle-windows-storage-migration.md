# Storage Migration fsync on a Read-Only Handle Fails on Windows

Change ID: `20b31-bug fsync-readonly-handle-windows-storage-migration`
Change Status: `implemented`
Owner: Engineering
Status: active
Last verified: 2026-10-10
Wave: 20b39 windows-crlf-correctness

## Rationale

Brief: a field upgrade on Windows failed with `OSError: [Errno 9] Bad file descriptor` while publishing the staged index during storage migration. The goal is that staging a migrated index never fails because of how the file handle is opened, on any platform. Consumers are Windows operators upgrading to a SQLite-storage release; constraint is no weakening of the durability guarantee (the staged file is still flushed before the atomic replace); success is observable through a test that fails on the unfixed code on Windows semantics and passes after the fix.

Verified at HEAD by reading the code:

- `.wavefoundry/framework/scripts/sqlite_storage_migration.py:1573-1574` in `migrate_legacy()` (starts at `:1380`) does `with staged.open("rb") as handle: os.fsync(handle.fileno())`, under the comment "Flush the staging file before atomic replace."
- `sqlite_storage_migration.py:1881-1882` is an identical pattern inside `_migrate_schema8` (`sqlite_storage_migration.py:1792`), after `_assert_sources` and `_hosts_gone`.
- Neither site checks `os.name == "nt"` or catches the error. On Windows `os.fsync` requires a writable descriptor, so a read-only handle raises Errno 9. The failure happens after staging and before cutover, so original stores are kept (field report; consistent with the code order described there, not independently re-run here).
- The Windows failure itself is taken from the field report and the documented behavior of `os.fsync` on Windows. It has not been reproduced in this macOS session.
- All other `os.fsync` calls under `.wavefoundry/framework/scripts` were enumerated and use a writable handle or are directory-fsync calls guarded by an `OSError` return (`sqlite_storage_migration.py:1259-1269`, `upgrade_extensions.py:639-644`, `upgrade_lib.py:36-41`). They are not defects.
- No existing test covers the read-only case (`tests/test_vocabulary_prompt_names.py:1094` and `tests/test_server_tools_lifecycle.py:16362` touch fsync but not this path).

## Requirements

1. A single helper in `sqlite_storage_migration.py` flushes a file's contents to disk by opening it with a writable mode (`r+b`, which writes nothing) and calling `os.fsync` on that descriptor.
2. Both sites at `:1573-1574` and `:1881-1882` use the helper, and no other site in the module opens a regular file read-only to fsync it. The set of sites is derived by rule: every `os.fsync` in the module whose handle was opened without write access.
3. The durability ordering is unchanged: the staged file is flushed before the atomic replace.
4. The helper does not modify file contents or timestamps beyond what fsync implies, and does not require the file to be larger than zero bytes.
5. Directory-fsync behavior (the existing `_sync_directory` guard) is unchanged.

## Scope

**Problem statement:** The storage migration fsyncs the staged index through a read-only handle, which raises Errno 9 on Windows and aborts the upgrade after hours of indexing work.

**In scope:**

- The helper and its two call sites in `sqlite_storage_migration.py`.
- A regression test that detects a read-only-handle fsync.
- Re-scanning the module for any further read-only fsync site per Requirement 2.

**Out of scope:**

- The other `os.fsync` call sites (verified fine).
- Index build, embedding, or xet download behavior (separate changes).
- Any change to the migration state machine.

## Acceptance Criteria

- [x] AC-1: A test drives the staged-file flush at both sites (`migrate_legacy` and `_migrate_schema8`) through a seam that does NOT depend on the native runtime: it stubs the runtime-dependent calls (for example the quiesce, hash and runtime-open calls those functions make, plus `_assert_sources`, `_hosts_gone` and `_write`, which both functions call before the flush) and calls the real functions, or the flush is extracted into the helper and each site's function is driven up to the helper call. The test lives outside any class gated by `skipUnless(_native_available(), ...)` (`tests/test_sqlite_storage_migration.py:705` and `:1528` are gated that way), so it runs, and does not skip, on a plain macOS, Linux or Windows host without the qualified APSW and sqlite-vec runtime. It asserts that the helper or the recording fsync stub was called at least once for EACH of the two sites, so it cannot pass without reaching them. A static text scan of the module may be added but never substitutes for exercising both call sites.
- [x] AC-2: A test wraps `Path.open` and `builtins.open` (and `io.open`) to record `{handle.fileno(): mode}` for every handle opened, and replaces `os.fsync` with a stub that looks the descriptor up in that map and raises `OSError(errno.EBADF)` when it came from a read-only mode (no `fcntl`, so it runs on Windows, macOS and Linux). A positive control calls the same stub with an `r+b` descriptor and shows it does not raise, so the stub is not simply always raising. The test passes through the helper and fails against the pre-change code.
- [x] AC-3: The helper leaves the file's bytes unchanged (test compares content before and after) for a non-empty file and for a zero-byte file (Requirement 4).
- [x] AC-4: The migration tests that exercise `migrate_legacy()` still reach the atomic replace after the flush (existing behavior, covered by the change's own suites).
- [x] AC-5: The suites that exercise `sqlite_storage_migration` (`tests/test_sqlite_storage_migration.py` and `tests/test_storage_upgrade_resume.py`) and every test this change adds pass; the documents this change authors or edits validate.

## Tasks

- [x] Add the mode-recording fsync stub test first (AC-2), including the positive control, and run it against the unfixed tree; record the observed failure in the Progress Log.
- [x] Confirm how `staged` is created at both sites (copy of a source, fresh file, or other) and whether any path can leave it read-only or held by another process; record a one-line result in the Progress Log. No fallback is planned unless this finds a real read-only path.
- [x] Add `_fsync_file(path)` to `sqlite_storage_migration.py` using `r+b`.
- [x] Replace both read-only fsync sites with the helper.
- [x] Re-scan the module for any other read-only fsync per Requirement 2 and log the result in the Progress Log.
- [x] Add the non-native-gated seam tests that reach `migrate_legacy` and `_migrate_schema8` and assert the helper is called at each (AC-1), plus the zero-byte case (AC-3).

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| windows-semantics-test | implementer | none | Stub fsync that rejects read-only descriptors |
| helper-and-callsites | implementer | windows-semantics-test | One module |


## Serialization Points

Windows (native), macOS, Linux and WSL2 behavior: on native Windows the fix removes Errno 9 because the descriptor is writable. On macOS, Linux and WSL2 POSIX allows fsync on read-only descriptors, so the previous code worked and the new code behaves identically (an `r+b` open of the staged file succeeds because the staged copy is a private file the migration owns; a read-only staged file is not expected, which is an assumption the "how `staged` is created" task confirms during implementation). The helper must not be guarded by `os.name`, so every platform exercises the same path.

**Review targets (repo-relative paths):**

- `.wavefoundry/framework/scripts/sqlite_storage_migration.py`

## Affected Architecture Docs

N/A: the change is confined to one helper and two call sites in a single module, with no boundary, flow or contract change. The testing seam (stubbed fsync) is local to the new test.

## AC Priority


| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Removes the field failure |
| AC-2 | required | Only way to prove the Windows case on non-Windows CI |
| AC-3 | important | Guards against the helper altering the staged file |
| AC-4 | important | Confirms ordering preserved |
| AC-5 | required | Change-local test and doc validity |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-10 | Planned from field report; both sites confirmed by code reading, Windows failure not reproduced here | Verification agent report |
| 2026-10-10 | Product Intent: waived (bug fix, no product scope; default applied by the planning agent, not yet confirmed by the operator) | Readiness review round 2 |
| 2026-10-10 | Round-2 readiness repair: non-native-gated test seam, fd-to-mode recording stub with positive control, zero-byte case, staged-creation task, unbacked scan claim removed | Council round-2 findings |

| 2026-10-10 | Readback: both real migration staging paths use one writable r+b fsync helper before atomic publication; native-runtime-independent descriptor-mode controls must reach each path, preserve empty/nonempty bytes and reject the old rb mode. Before: Windows semantics raise EBADF before cutover; after: same durability ordering with writable descriptor (AC-1–AC-5). Scope: sqlite_storage_migration.py helper/two sites, test_sqlite_storage_migration.py; no state-machine or directory-fsync change. | Parent activation and portable preflight controls |
| 2026-10-10 | Thought: add real-callsite mode recorder tests outside all native skip gates, prove old rb failures with an r+b positive control, then extract _fsync_file and assert the flush precedes the atomic replace seam. | Both preflight calls reached rb and raised EBADF |
| 2026-10-10 | Staging creation: migrate_legacy unlinks the candidate then runtime.backup or IndexStateStore creates it; _migrate_schema8 clears the staging tree then runtime.backup creates the candidate. Neither uses copy2 mode inheritance, and store handles close before the flush; no observed read-only staging path needs a fallback. | Live staging creation/closure statements in both functions |
| 2026-10-10 | Observe: WritableStagedFsyncTests ran three methods without skips on the old tree: both real staging paths fail with EBADF at rb fsync, and helper preservation cases fail because the helper is absent. The same stub accepts r+b and rejects rb explicitly; existing close/flush/replace ordering control passes. | temporary fsync-red.log; real functions, no native-runtime gate |
| 2026-10-10 | Observe: all three WritableStagedFsyncTests pass without skips. Both real functions reach the shared r+b descriptor; empty and nonempty bytes survive unchanged, and disposable candidates undergo actual atomic replace after store close and fsync. | temporary fsync-green.log; test_both_real_paths_flush_after_close_before_atomic_replace |
| 2026-10-10 | Census: module fsync statements are now only _fsync_file (r+b regular file) and _sync_directory (guarded O_RDONLY directory). Both migrate_legacy and _migrate_schema8 call _fsync_file before publication; no remaining regular-file read-only flush. Directory-fsync function AST is unchanged. | live token census; old/current AST equivalence |
| 2026-10-10 | Mutant: restoring rb in the shared helper fails test_both_real_staging_paths_require_writable_fsync_descriptors at BOTH real functions with EBADF, while the same r+b control succeeds; no unintended skips. | Executed in-memory helper mutant; two errors at the intended Windows-semantic boundary |

| 2026-10-10 | Observe: sqlite_storage_migration passes 127 tests (1 existing skip), including all three new portable methods with no skips; storage_upgrade_resume passes 14 tests using the existing tool venv and child PATH. An initial bare-Python resume run lacked numpy and is excluded as behavior evidence. | Focused module logs; no installation; final document validation pending |

## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-10 | Open the staged file `r+b` for fsync on all platforms | One code path everywhere; the staged file is a private copy | A: guard with `os.name == "nt"` and skip fsync on Windows (weakness: drops the durability guarantee on the platform that most needs it). B: catch `OSError` and continue (weakness: silently hides real I/O failures). C (selected): writable handle via a shared helper |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| `r+b` fails if the staged file is read-only or locked | The staged file is created by the migration itself; the "how `staged` is created" task records in the Progress Log whether any path can produce a read-only staged file |
| A third read-only fsync site exists | Requirement 2 derives the set by rule and the implementer re-scans the module and logs the result; no static test is claimed to guard it |
| The new tests skip on hosts without the native runtime and pass vacuously | AC-1 requires a non-gated seam and an assertion that the helper was called at each of the two sites |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
