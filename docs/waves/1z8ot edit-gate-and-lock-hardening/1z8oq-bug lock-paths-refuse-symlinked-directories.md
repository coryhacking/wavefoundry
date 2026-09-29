# Lock Paths Refuse Symlinked Directories

Change ID: `1z8oq-bug lock-paths-refuse-symlinked-directories`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-09-28
Wave: 1z8ot edit-gate-and-lock-hardening

## Rationale

Wave `1z822` made lock carriers refuse a symlink at the lock file itself. A downstream validation of `d295b92` found two remaining paths:

- `runtime_lock.RuntimeFileLock.acquire` and `runtime_lock.write_json_in_place` call `os.makedirs` on the carrier's parent before `_open_carrier`. `makedirs` follows symlinked directories, so a committed `.wavefoundry/locks` symlink puts every lock, and the metadata rewrite, at the link's target outside the repository.
- `upgrade_bridge_bootstrap._StrictLock.__enter__` does `self.path.parent.mkdir(parents=True, ...)` and `self.path.open("a+b")`. So a committed symlink at `.wavefoundry/lifecycle-mutation.lock`, or at a directory above it, creates and locks files outside the repository, and on Windows writes a carrier byte into an empty target.

The same report found that `tests/test_runtime_lock.py` `test_windows_branch_refuses_only_links_and_junctions` errors on Python 3.11. Its fake `lstat` builds `Path(path)` while `os.name` is patched to `"nt"`, and Python 3.11 cannot instantiate `WindowsPath` there.

## Requirements

1. **The boundary.** A lock path's check boundary is the last path component named `.wavefoundry`, found lexically in the path as given. Callers build lock paths as `Path(root).resolve() / ".wavefoundry" / ...`, so only the root is resolved.
   - The `.wavefoundry` directory itself, and every component below it down to the carrier's parent, must not be a symlink (on Windows, not a symlink or junction, judged by the existing name-surrogate tag set, never "any reparse point", because OneDrive directories are reparse points).
   - Components above `.wavefoundry` (the repository root and its parents, for example macOS `/var` to `/private/var`, or a symlinked checkout) are not checked.
   - A path with no `.wavefoundry` component (temporary-directory locks, `build_index` with an explicit `index_dir`) keeps today's final-component check.
   - Callers verified at readiness all pass paths under `.wavefoundry`: `index_source_guard`, `lifecycle_lock`, `review_evidence`, `dashboard_lib`, `gen_codebase_map`, `scanner_skips`, the `indexer` build lock, the `context_efficiency` leases and the `upgrade_wavefoundry` legacy root lock.
2. **A race-free walk on POSIX.** `RuntimeFileLock.acquire` and `write_json_in_place` walk the path with directory file descriptors instead of calling `os.makedirs`:
   - create `.wavefoundry` under the resolved root when it is missing (`mkdir`, tolerating `EEXIST`), then open it with `O_RDONLY | O_DIRECTORY | O_NOFOLLOW`;
   - for each component, `os.mkdir(name, dir_fd=fd)`, tolerating `EEXIST`, then `os.open(name, O_DIRECTORY | O_NOFOLLOW, dir_fd=fd)`;
   - open the carrier with `O_NOFOLLOW` and `dir_fd=parent_fd`.

   Every directory handle is closed in a `try`/`finally`. A symlinked component raises `RuntimeLockError` naming it. The refusal mapping handles both `ELOOP` and `ENOTDIR`, because macOS reports a symlinked directory opened with `O_DIRECTORY | O_NOFOLLOW` as `ENOTDIR`.
3. **Windows.** There is no `openat` on Windows, so each component is checked with `lstat` against the name-surrogate tags before it is created or opened. The window between check and use remains a known limit (Requirement 6).
4. **The upgrade bridge.** It applies the same rule inline, because the bootstrap runs standalone. `mkdir` and `open` in `_StrictLock.__enter__` move inside the `BridgeError` translation, so a refusal surfaces as `BridgeError`, not a raw `OSError`. The Windows carrier byte is written only after the link check passes.
5. **Fix the Windows-branch test on Python 3.11.** Use `os.path.basename(path)` instead of `Path(path).name`. The new directory walk also uses `os.path`, not `pathlib`, while `os.name` is patched.
6. **Document the changes and limits.**
   - The refusal message tells the operator to replace the symlink with a real directory. There is no configuration alternative: `.wavefoundry/index` is a fixed path (`indexer.INDEX_DIR_NAME`).
   - The CHANGELOG notes that a symlinked `.wavefoundry` subdirectory is now refused, and that a symlinked `.wavefoundry/index` therefore blocks index builds until it is replaced.
   - The Windows check-then-use window is recorded in `docs/architecture/threat-model.md` under `## Current Risks`, and in the CHANGELOG operator note so target operators see it.

## Scope

**Problem statement:** a committed symlinked directory can redirect Wavefoundry's lock writes outside the repository.

**In scope:**

- `runtime_lock.py`, `upgrade_bridge_bootstrap.py` and their tests; the `threat-model.md` row.

**Out of scope:**

- Other writers under `.wavefoundry/` that are not lock carriers. The readiness review listed them, and they are a follow-up:
  - `.wavefoundry/index/**` (sqlite files, markers, `scan/guard-skips.json`, `sqlite-migration.json`);
  - `.wavefoundry/logs/**`;
  - `.wavefoundry/cache`;
  - `guard-overrides.json`, `upgrade-in-progress.json`, `dashboard-server.json`, `install-log.md`, `memory-purge-dispositions.json`;
  - `repair-backups/`, `upgrade-assets/`;
  - `framework/test-cache.json`, `framework/test-run.lock`;
  - the renderer's writes under `bin`, `hooks` and `git-hooks`.

  The readiness red-team's alternative covers them all at once: a single startup check that refuses to run when `.wavefoundry` or any of its first-level children is a symlink. It is the candidate for that follow-up.

## Acceptance Criteria

- [x] AC-1: with `.wavefoundry/locks` (or `.wavefoundry` itself) a symlink to a directory outside the repository, acquiring a lock, including a nested `sub/x.lock`, and `write_json_in_place` raise `RuntimeLockError`, and nothing is created outside the repository. Tests do not assert a particular errno.
- [x] AC-2: with `.wavefoundry/lifecycle-mutation.lock` a symlink, or `.wavefoundry/locks` a symlinked directory, the bridge bootstrap fails with `BridgeError` and creates nothing outside the repository.
- [x] AC-3: a simulated-Windows junction on a directory component is refused. A reparse point that is not a name surrogate (the OneDrive case) is allowed.
- [x] AC-4: ordinary lock acquisition, nested lock paths, metadata rewrites, a symlinked repository root above `.wavefoundry`, and paths with no `.wavefoundry` component are unchanged; a missing `.wavefoundry` is created and used; existing lock tests pass.
- [x] AC-5: `test_windows_branch_refuses_only_links_and_junctions` passes on Python 3.11 and later.
- [x] AC-6: the change's own suites pass, and the documents it edits validate.

## Tasks

- [x] The lexical `.wavefoundry` boundary; the `dir_fd` walk on POSIX; the `lstat` walk on Windows; `ELOOP` and `ENOTDIR` mapping.
- [x] The bridge's inline rule, with `mkdir` and `open` inside the `BridgeError` translation.
- [x] Tests (POSIX symlinked directories, simulated Windows junction, root symlink allowed, no-`.wavefoundry` path); the Python 3.11 test fix.
- [x] `threat-model.md` row; CHANGELOG.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Locks | implementer | readiness | Two modules |
| Review | combined reviewer | Locks | Code, QA, security |

## Serialization Points

- `.wavefoundry/framework/scripts/runtime_lock.py`, `.wavefoundry/framework/scripts/upgrade_bridge_bootstrap.py`, `.wavefoundry/framework/scripts/tests/`
- `docs/architecture/threat-model.md`
- `CHANGELOG.md`

## Affected Architecture Docs

`docs/architecture/threat-model.md`: the Windows check-then-use row.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Runtime lock redirection |
| AC-2 | required | Bridge lock redirection |
| AC-3 | required | Windows parity |
| AC-4 | required | No regression |
| AC-5 | required | Suite correctness on 3.11 |
| AC-6 | required | Verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-09-28 | Reverification correction to the DEL-F2 row below: its "60 of 60 with a plain full-path open" came from a harness whose mode check (`'at' in mode`) also matched `path`, so those runs used `openat`. A correctly separated harness reproduced the spurious `ENOENT` only with `openat(dir_fd)` (59 of 60) and never with a full-path open (0 of 640), so the implementation row's original observation stands. The full-path retry stays as a defensive measure; the docstrings and test comments now say so | independent reverification race harness; `runtime_lock._open_retrying` and `upgrade_bridge_bootstrap._open_retrying` docstrings |
| 2026-09-28 | Delivery repair DEL-F2. Correction to the implementation row below: the claim that the full-path open never showed the spurious `ENOENT` is wrong. A reviewer race harness (macOS, two processes creating the same new name) saw the loser get `ENOENT` 59 of 60 times with `openat(dir_fd)` and 60 of 60 with a plain full-path open; one retry always succeeded across 1760 opens. The bounded retry moved into `runtime_lock._open_carrier` through `_open_retrying` (replacing `_open_at_retrying`), so it covers the `dir_fd` form and the no-`.wavefoundry` full-path form; `upgrade_bridge_bootstrap` gained a standalone `_open_retrying` used by both its POSIX and Windows carrier opens. The `..` refusal now says the lock path contains a `..` component below `.wavefoundry` in both modules. Gapfill: shell `grep` over three test files to find assertions on the old message and existing carrier tests, since MCP keyword search over the tree returned index-database hits that swamped the result | `test_runtime_lock.py` (21 OK, new `test_full_path_open_without_boundary_retries_spurious_enoent`, `test_parent_component_below_boundary_is_refused_with_accurate_message`), `test_upgrade_protocol.py` (32 OK, new `test_bridge_carrier_open_retries_spurious_enoent_in_every_form`), `test_review_evidence.py`, `test_server_package.py` OK (focused runs) |
| 2026-09-28 | Implemented Requirements 1 to 5 and the refusal message. `runtime_lock._open_lock_carrier` splits at the last lexical `.wavefoundry`, walks with `dir_fd` and `O_NOFOLLOW` on POSIX (confirming a link with a no-follow `stat` on `ELOOP`/`ENOTDIR`), and checks name-surrogate tags with `lstat` on Windows; `upgrade_bridge_bootstrap._open_strict_carrier` inlines the same rule inside the `BridgeError` translation. Found while verifying: macOS returns a spurious `ENOENT` to the loser of two concurrent `openat(O_CREAT)` calls (38 of 40 two-process runs; the full-path open never did), which failed `test_publication_lock_is_cross_process_exclusive`; the carrier open now retries `ENOENT` a bounded 5 times (0 of 40 after). Caller census confirmed every caller path is under `.wavefoundry`; temp-dir and explicit `index_dir` paths keep the final-component check. AC-5 also confirmed under Python 3.11.13 with a scratch harness. Gapfill: shell `grep -l` to list test files by name, since MCP keyword search returns lines, not a file list | `test_runtime_lock.py` (19 OK), `test_upgrade_protocol.py` (31 OK), `test_review_evidence.py`, `test_lifecycle_mutation_lock.py`, `test_index_source_guard.py`, `test_scanner_skips.py`, `test_run_tests_lock.py`, `test_context_efficiency.py`, `test_graph_snapshot_readers.py`, `test_dashboard_server.py`, `test_indexer.py`, `test_upgrade_wavefoundry.py` all OK (focused runs) |
| 2026-09-28 | Readiness confirmation: all findings resolved; R2 adopted (a missing `.wavefoundry` is created before the `O_NOFOLLOW` open; handles closed in `finally`); the Windows limit is also in the CHANGELOG operator note; the startup-check alternative is recorded for the non-lock follow-up | readiness confirmation |
| 2026-09-28 | Readiness review. B2: the boundary is the last lexical `.wavefoundry` component, checked inclusive, with no check above it, and a no-`.wavefoundry` path keeps the final-component check. B3: a `dir_fd` walk with `O_NOFOLLOW` on POSIX, mapping `ENOTDIR` and `ELOOP`; `lstat` with name-surrogate tags on Windows. N6: no configuration alternative exists, so the message says to replace the link. N7: bridge `mkdir` and `open` move inside the `BridgeError` translation. N8: `os.path` in the walk, a simulated-Windows junction test, and the index-build side effect accepted | readiness review |
| 2026-09-28 | Planned from a downstream validation report. Confirmed in the tree: `os.makedirs` precedes `_open_carrier` in `RuntimeFileLock.acquire` and `write_json_in_place`; `_StrictLock.__enter__` uses `parent.mkdir` and `open("a+b")`; the test builds `Path(path)` under a patched `os.name` | `runtime_lock.py`; `upgrade_bridge_bootstrap._StrictLock`; `tests/test_runtime_lock.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-09-28 | No exception for a relocated index symlink | The reporter found every exception bypassable (case variants, submodules, a checkout without `.git`, cached answers) | Allow an untracked `.wavefoundry/index` link |
| 2026-09-28 | Find the boundary lexically at the last `.wavefoundry` component | No caller change needed; every current caller builds paths that way | Callers pass an explicit boundary (the readiness red-team alternative; more churn across about ten callers) |
| 2026-09-28 | Walk with `dir_fd` and `O_NOFOLLOW` on POSIX | A check-then-open by path string leaves a swap window | `lstat` after `mkdir` |

## Risks

| Risk | Mitigation |
| --- | --- |
| An operator who relocated `.wavefoundry/index` with a symlink can no longer build the index | The refusal names the component and says to replace the link with a real directory; CHANGELOG operator note |
| A platform reports the symlinked-directory refusal with an unexpected errno | Map `ELOOP` and `ENOTDIR`; tests assert the refusal, not the errno |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
