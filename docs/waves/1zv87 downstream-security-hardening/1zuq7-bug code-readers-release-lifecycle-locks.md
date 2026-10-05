# Code Readers Can Release The Framework's Runtime Locks

Change ID: `1zuq7-bug code-readers-release-lifecycle-locks`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-05
Wave: 1zv87 downstream-security-hardening

## Rationale

Downstream report (Waveforge S2, reproduced here in-process at `fdd8de15`): the lifecycle lock is a POSIX record lock (`runtime_lock.RuntimeFileLock(style="record")`, `fcntl.lockf`), which the kernel releases when ANY descriptor of the file is closed in the holding process. `code_read` resolves any repository path (`server_impl._resolve_repo_path` checks containment only), so reading `.wavefoundry/lifecycle-mutation.lock` while a lifecycle mutation holds the lock lets another process (a `wf` command or a second host) take it and mutate wave records concurrently. The same holds for the other record (`lockf`) lock, `index/index-build.lock` (and `framework/test-run.lock`, record-style on Windows only); `locks/*.lock` use `flock` and are not released this way, but are refused too so the rule stays simple.

## Requirements

1. `server_impl._resolve_repo_path` refuses (returns `None`) any path that resolves under `<root>/.wavefoundry/` and whose name ends in `.lock`, comparing the root-relative parts case-folded (`os.path.normcase` plus `casefold`) on every platform so a case variant on a case-insensitive filesystem cannot bypass it, so `code_read`, `code_outline`, `code_hover`, `code_dependencies` and the graph impact heuristic cannot open a framework lock file; the refusal message is the existing invalid-path one.
2. The walk-based readers (`code_keyword`, `code_pattern`, `code_lexical`, `code_list_files`, `code_constants`, `docs_search`, and any other tool that opens repository files) are censused by one criterion (opened in the server process, which holds the lock; the dashboard is a separate process); any that can open a `.wavefoundry/**/*.lock` file gets the same refusal through one shared predicate (`server_impl._is_runtime_lock_path`), applied to the RESOLVED target, so a committed symlink (for example `notes.py -> .wavefoundry/lifecycle-mutation.lock`) found by `indexer.walk_repo` is skipped too.
3. The lock implementation is unchanged: switching to `flock` or OFD locks would stop excluding the installed older code that takes `lockf` on the same files during an upgrade, and macOS Python has no OFD constants.
4. CHANGELOG gets a bullet under `## [1.29.0]` `### Security`.

## Scope

**Problem statement:** a generic read tool can silently drop a lock the server holds.

**In scope:**

- `.wavefoundry/framework/scripts/wf_server/server_impl.py` resolver and predicate; any walk-based reader the census finds; tests; CHANGELOG.

**Out of scope:**

- Changing the lock style.
- Reads of lock metadata that the framework itself performs through the holding lock object.

## Acceptance Criteria

- [x] AC-1: With the lifecycle lock held in-process, `code_read` of `.wavefoundry/lifecycle-mutation.lock` is refused, and a child process's non-blocking `lockf` still reports the lock busy afterwards.
- [x] AC-2: `code_read` of `.wavefoundry/index/index-build.lock`, `.wavefoundry/locks/<name>.lock` and a case variant (`.WAVEFOUNDRY/Lifecycle-Mutation.LOCK` on a case-insensitive filesystem) is refused; `code_read` of a normal file and of `.wavefoundry/framework/...` files still works.
- [x] AC-3: The census of file-opening tools is recorded in the Progress Log, every one that could open a lock file is covered by a test, and a committed symlink to the lifecycle lock is not opened by `code_keyword` or `code_pattern` while the lock is held (a child `lockf` still sees it busy).
- [x] AC-4: Removing the resolver refusal fails the AC-1 test (scratch copy).
- [x] AC-5: CHANGELOG Security bullet; docs validate.

## Tasks

- [x] Add `_is_runtime_lock_path` and use it in `_resolve_repo_path`
- [x] Census every MCP tool that opens repository files; cover any that can reach a lock file
- [x] Add the held-lock regression test and scope tests
- [x] Show the mutant fails in a scratch copy
- [x] CHANGELOG Security bullet

## Agent Execution Graph


| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| reader-guard | implementer | — | server_impl resolver and census |


## Serialization Points

- `.wavefoundry/framework/scripts/wf_server/server_impl.py`, `.wavefoundry/framework/scripts/wf_server/codenav_handlers.py`, `.wavefoundry/framework/scripts/indexer.py`, `.wavefoundry/framework/scripts/tests/test_server_tools.py`

## Affected Architecture Docs

N/A: an input guard on existing tools.

## Platform Behavior

POSIX (macOS, Linux, WSL2): the guard prevents the record-lock release. Windows: `msvcrt.locking` is per-handle, so a read never released the lock; the refusal applies on every platform for consistency.

## AC Priority


| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | the reproduced release |
| AC-2 | required | scope of the rule |
| AC-3 | required | no second door |
| AC-4 | required | pin catches a revert |
| AC-5 | required | release notes |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-10-05 | Gapfill: implementation was delegated to three implementer subagents briefed MCP-first; their retrieval calls run in their own sessions and are not attributed to this wave's implement-stage telemetry, and the coordinator's own edits were bookkeeping and docs | retrieval_posture_gap advisory |
| 2026-10-05 | Implemented: `server_impl._is_runtime_lock_path` (root-relative parts, `normcase` + `casefold`) in `_resolve_repo_path`; `_repo_rel_path_refused` for index-derived reads (`code_ask` receipt and line count, `code_references` file and snippet reads, graph call-site scans); walker mirror `indexer._walk_target_is_runtime_lock` for symlinks only (parity test). Census: resolver readers (`code_read`, `code_outline`, `code_hover`, `code_dependencies`, `code_impact`), walker readers (`code_keyword`, `code_pattern`, `code_constants`, `code_list_files`, walk-based refs, `index_health` hashing), index-derived reads (above); `docs_search`, `code_search`, `code_lexical` open no repository files. No walker or graph version bump: literal `*.lock` names were already excluded as binary, only symlinks to lock files are newly skipped. Tests `test_code_reader_lock_guard.py` | mutants (resolver refusal, case folding, walker check) fail |
| 2026-10-05 | Follow-up (residual, not in this change): a committed `docs/**/*.md` symlinked to a lock file and read in-process by a docs or lifecycle tool is outside the code-reader surface | implementer report |
| 2026-10-05 | Readiness review folded in: case-folded comparison, predicate on the resolved target in the walker, census criterion, which locks are record locks | readiness F2, F3 |
| 2026-10-05 | Planned from the Waveforge private report S2; reproduced in-process by the verification reviewer | child `lockf` busy, then `code_read` of the lock file, then the child acquired it |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-10-05 | Guard the readers, not the lock type | a different lock style would stop excluding older installed code during upgrades; macOS lacks OFD locks | flock / OFD locks |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| A tool opens a lock file through a path the census misses | the predicate is shared and the census is recorded; reviewers re-derive it |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
