# Lifecycle Lock Holds Survive Re-entry and the Publication Probe

Change ID: `1zimg-bug lifecycle-lock-holds-survive-reentry-and-probe`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-10-01
Wave: 1zimc lifecycle-lock-hold-registry

## Rationale

`lifecycle_lock.lifecycle_mutation_lock` takes a POSIX record lock (`RuntimeFileLock(style="record")`, which calls `fcntl.lockf` at offset `1 << 30`). Record locks belong to the process, not to the descriptor: a second acquire in the same process succeeds, and unlocking or closing any descriptor of the file releases the process's lock. `runtime_lock` already keeps an in-process holder registry for this reason (`_PROCESS_RECORD_HOLDS`, `register_process_hold`, `process_hold_guard`, wave 1za2y), but only the index build lock in `indexer.py` uses it. The lifecycle lock does not register, so two paths silently drop a hold while its owner still believes it holds it:

1. **Re-entry.** Entering `lifecycle_mutation_lock` again in the process that holds it succeeds, and leaving the inner block unlocks and closes the file, releasing the outer hold. A second process can then take the lock.
2. **The publication probe.** `review_evidence.project_state_publication_lock(wait=True)`, on finding the publication lock busy, probes the lifecycle lock by opening `.wavefoundry/lifecycle-mutation.lock` and acquiring then releasing a record lock on it, to fail fast while Upgrade owns lifecycle state. When the calling process itself holds the lifecycle lock (the MCP middleware wraps every tool in `_LIFECYCLE_MUTATION_LOCK_TOOLS`, and several of those handlers then take the publication lock), the probe's acquire succeeds and its release drops the caller's own hold. With process A holding the lifecycle lock, process B holding the publication lock, and A entering `project_state_publication_lock(wait=True)`, a process C can take the lifecycle lock while A still runs its mutation.

Both paths were reproduced on macOS against the current tree with real processes (a scratch repository under the session scratchpad): after the inner block exits, and while A waits for the publication lock, a second process acquires the lifecycle lock.

A related same-process hazard exists on the publication lock: `lifecycle_publication_transaction` (used four times by the upgrade) acquires the publication file lock directly, outside `project_state_publication_lock`'s thread lock and depth counter. A `project_state_publication_lock(wait=True)` on the same thread inside that transaction finds its own lock busy, takes the probe path (dropping the lifecycle hold as above) and then blocks forever on its own lock; reproduced with a timeout on macOS (on Windows the probe reports busy and the wait fails fast instead). No shipped path does this today (the upgrade passes `current_lock_held=True` and finalizes through `finalize_staged_build_epoch`, which takes no publication lock), so it is latent.

## Requirements

1. **Lifecycle holds register.** `lifecycle_mutation_lock` acquires the record lock and registers the hold in `runtime_lock`'s process registry as one step under `process_hold_guard()`, the way `indexer._index_build_lock` does, and on exit removes the registry entry and releases the OS lock as one step under the guard, after the existing best-effort `released_at` stamp. The registry metadata names the pid, `acquired_at` and the owning thread (`threading.get_ident()`). Every existing exit guarantee holds: an exception or interrupt anywhere after a successful acquire still releases the OS lock and removes the entry (the 1zf1u release-protected region now also covers registration). The `strict=False` path that yields unlocked when the lock is unavailable registers nothing. On exit, removing the entry and releasing the OS lock run under the guard as `release_process_hold(...)` followed by `lock.release()` in a `finally`, so the entry is never present after the OS lock is released and the release always runs. No `yield` happens while the guard is held, including the `strict=False` unlocked fallback.
2. **Re-entry is refused.** When the registry shows this process holds the lifecycle lock, from any thread, `lifecycle_mutation_lock` raises `LifecycleLockBusy` before opening the file, with a message that says the lock is already held by this process (and whether by the calling thread or another one). The check is made again under the guard at acquire time, so two threads racing to acquire cannot both succeed. The middleware maps this to its existing `lifecycle_mutation_locked` busy response, so no state changes. `strict=False` callers also receive `LifecycleLockBusy` (re-entry never falls through to the unlocked fallback).
3. **The publication probe consults the registry.** In `project_state_publication_lock`'s waiting path the lifecycle probe first checks the registry, under `process_hold_guard()`:
   - held by the calling thread: skip the probe and wait for the publication lock as an ordinary publisher does. This is safe because lock order is fixed (lifecycle, then publication), so the publication holder never waits for the lifecycle lock;
   - held by another thread of this process: fail fast with `ProjectPublicationUnavailable`, as when another process holds it;
   - not held in this process: probe the file as today, with the check and the open under the guard so no in-process acquire can register between them.
   The probe never opens the lifecycle lock file while this process holds it. Its path and offset equal `lifecycle_lock.LIFECYCLE_MUTATION_LOCK_REL` and `LIFECYCLE_MUTATION_LOCK_SENTINEL` (`lifecycle_lock` imports `review_evidence`, so the probe cannot import them without a cycle); a test pins the equality. The own-publication-hold refusal (Requirement 4) is evaluated before these three cases.
4. **The transaction's publication hold registers.** `lifecycle_publication_transaction` registers its publication-lock hold (with the owning thread) the same way and removes it before releasing. `project_state_publication_lock` on a thread whose registry entry shows it holds the publication file lock outside the function's own depth counter raises `ProjectPublicationUnavailable` immediately, naming the same-process hold, instead of blocking on its own lock. Same-thread nesting of `project_state_publication_lock` itself stays re-entrant through its depth counter, unchanged. The own-hold check runs after the depth-counter test and before the first acquire attempt on the publication file, so it also holds where `flock` is emulated with process-owned record locks.
5. **Census of openers.** In shipped framework code the only openers of `.wavefoundry/lifecycle-mutation.lock` are `lifecycle_lock.lifecycle_mutation_lock`, the probe in `review_evidence.project_state_publication_lock`, and the standalone bridge installer `upgrade_bridge_bootstrap.install` (a separate stdlib-only process that takes it once). A source census test pins that list, so a new opener must route through the registry or be added deliberately.
6. **MCP reload.** `wf_reload_mcp` clears the script cache and re-executes `wf_server/server_impl.py`, which re-imports `lifecycle_lock` and `review_evidence`. The registry lives in `runtime_lock`, which is not evicted, so it is the same object before and after a reload, and neither re-imported module caches registry state. A hold registered before a reload stays visible after it through the re-imported modules, and re-entry stays refused. No code change is expected; a test pins it.
7. **Platforms.**
   - macOS and Linux: the lifecycle lock uses `fcntl.lockf` (process-owned record locks), where both defects reproduce; the fix applies there.
   - WSL2: runs the Linux path, including for repositories on `/mnt` drives; the registry is in-process, so its behaviour does not depend on the filesystem.
   - Windows: `RuntimeFileLock` uses `msvcrt.locking`, whose locks belong to the file handle. A second handle in the same process is refused and closing it releases nothing, so Windows does not lose holds today: re-entry already raises `LifecycleLockBusy`, and the probe in the caller's own scenario reports busy and fails fast rather than waiting. After this change Windows refuses re-entry before opening the file (same exception), and the caller's own hold skips the probe and waits, matching POSIX.
   - The publication lock uses `style="flock"` on POSIX (owned by the open file description, so a second descriptor in the same process conflicts and closing it releases nothing) and `msvcrt.locking` on Windows. It does not have the release-on-close defect on local filesystems on any platform. The same-thread self-deadlock inside `lifecycle_publication_transaction` happens on POSIX only: on Windows the lifecycle probe's second handle is refused, so the wait fails fast today. Requirement 4's check therefore runs before the Requirement 3 probe decision, so the new "calling thread holds lifecycle: skip the probe and wait" branch can never reach a blocking wait on this thread's own publication hold on any platform.
8. **No behaviour change for other locks.** The index build lock's registration, its readers and `probe_runtime_lock` are unchanged. The registry key stays the resolved path.
9. **The secrets scanner never opens a `.wavefoundry` lock file (operator direction, delivery finding DEL-1ZIMC-SECRETS-FALLBACK-OPENS-LOCK).** The scanner's own file selection (`secrets_validators._get_all_files` and `_get_changed_files`) skips, before reading it, at every branch of both functions (the `git ls-files` branch, the rglob fallback whether or not the root is inside a git worktree, and the changed-file loop), (a) every file under the `.wavefoundry/locks/` folder whatever its name (the folder is runtime lock state only; today `codebase-map.lock`, `dashboard-server.lock`, `dashboard-start.lock`, `index-source-mutation.lock`, `review-evidence-adoptions.lock` and `producers/<digest>.lock`), and (b) every `*.lock` file anywhere else under `.wavefoundry/` at any depth (the lifecycle lock `.wavefoundry/lifecycle-mutation.lock`, `index/index-build.lock`, `framework/test-run.lock`), independent of git and of the target's `.gitignore` (whose managed `.wavefoundry/**/*.lock` line covers them only inside a git worktree that carries it). `*.lock` files elsewhere in the repository (`Cargo.lock`, `Gemfile.lock` and similar, which can carry credentialed registry URLs) are still scanned. The same exclusion also drops such paths from an explicit `files=` list passed to `check_hardcoded_secrets` (defence in depth against a future caller), the `.wavefoundry/` prefix and `.lock` suffix are compared case-insensitively (safe, since the rule only excludes), and any existing finding whose file matches the exclusion is swept on the next scan, mirroring the allowlist sweep. The scan-rules hash and `SCANNER_VERSION` are unchanged. Same on Windows, macOS, Linux and WSL2 (paths compared with `/` separators).

## Scope

**Problem statement:** the lifecycle lock's process-owned record lock is released by a same-process re-entry and by the publication lock's lifecycle probe, so a second process can start a lifecycle mutation while the first is still running one; a publication wait inside the lifecycle-publication transaction deadlocks on its own lock.

**In scope:**

- `lifecycle_lock.py` (registration, re-entry refusal, transaction publication registration); `review_evidence.py` (registry-aware probe and own-hold refusal); `runtime_lock.py` only if a helper is needed for thread-aware lookups.
- Multi-process regression tests, the opener census test, the reload test, and unit tests for the threading cases.
- `docs/architecture/cross-cutting-concerns.md` lock section; a CHANGELOG entry.

**Out of scope:**

- `upgrade_bridge_bootstrap.py` (a standalone process that takes the lock once and never re-enters).
- Changing the publication lock's `flock` style or the lock order.
- Repositories on network filesystems where Linux emulates `flock` with record locks (recorded as a risk).

## Acceptance Criteria

- [x] AC-1: A multi-process test (real child processes, no mocks of the lock) holds `lifecycle_mutation_lock`, attempts re-entry in the same process, and asserts the re-entry raises `LifecycleLockBusy` naming this process, and that a second process still finds the lock held after the attempt and only acquires it after the outer block exits. On the current code the second process acquires it after the inner block exits (POSIX); the failing run is recorded as evidence. Every "second process" or "process C" in AC-1, AC-2, AC-4 and AC-5 is a fresh interpreter (`subprocess` with `sys.executable`, or a `multiprocessing` "spawn" context), never a forked child, because a fork inherits the registry.
- [x] AC-2: A multi-process test reproduces the probe scenario: process A holds the lifecycle lock, process B holds the publication lock, A enters `project_state_publication_lock(wait=True)`; while A waits, process C finds the lifecycle lock held; after B releases, A enters the publication lock and still holds the lifecycle lock (C still refused). On the current code C acquires it while A waits (POSIX); the failing run is recorded as evidence.
- [x] AC-3: The re-entry decision is pinned: same-thread and other-thread re-entry both raise `LifecycleLockBusy` without opening the lock file (verified by a test that fails if the file is opened), including under `strict=False`, and the MCP middleware returns `lifecycle_mutation_locked` for a re-entered tool call.
- [x] AC-4: Threading cases of the probe: with the lifecycle lock held by another thread of the same process and the publication lock held elsewhere, `project_state_publication_lock(wait=True)` raises `ProjectPublicationUnavailable` without opening the lifecycle file; with no in-process hold, the probe still fails fast when another process holds the lifecycle lock.
- [x] AC-5: Inside `lifecycle_publication_transaction`, `project_state_publication_lock(wait=True)` and `(wait=False)` on the same thread raise `ProjectPublicationUnavailable` naming the same-process hold within a bounded time (the test runs it in a child with a timeout), and a second process still finds the lifecycle lock held afterwards.
- [x] AC-6: The registry entry is removed and the OS lock released on a normal exit, a raising body, an interrupt during the release stamp, and an interrupt raised from `register_process_hold` (injected) after a successful acquire; in each case a later acquire in the same process succeeds and a second process can acquire the lock. The existing 1zf1u release tests pass unchanged.
- [x] AC-7: The opener census test scans non-test framework scripts for the literals `lifecycle-mutation`, `LIFECYCLE_MUTATION_LOCK_REL` and `LIFECYCLE_LOCK`. It asserts the openers are exactly `lifecycle_lock.py`, `review_evidence.py` and `upgrade_bridge_bootstrap.py`, with `wf_server/server_impl.py` allowed as a name-only reference (message constants). It fails when any other file matches; a test pins the probe's path and offset to the `lifecycle_lock` constants.
- [x] AC-8: A test registers a lifecycle hold, reloads `wf_server.server_impl`, and asserts the hold is still reported and re-entry still refused.
- [x] AC-9: The cross-cutting-concerns lock section states that lifecycle and transaction publication holds register in the process registry, that re-entry is refused, and how the probe treats the caller's own hold; the CHANGELOG entry describes the fix.
- [x] AC-10: The change's own suites (`test_lifecycle_mutation_lock`, `test_runtime_lock`, `test_review_evidence`, `test_review_policy`, `test_upgrade_protocol`, `test_upgrade_wavefoundry`, `test_lifecycle_gates`, `test_extension_tool_modules`, `test_setup_reconciliation`, `test_readiness_convergence`, `test_server_tools`, `test_server_tools_lifecycle`) and every test it adds pass; the documents this change authors or edits validate; and no failure elsewhere is attributable to this change.
- [x] AC-11: With the lifecycle lock held in the process, the in-process secrets scan (`check_hardcoded_secrets`, the `wf_scan_secrets` fallback) neither lists nor opens any file under `.wavefoundry/locks/` (including a planted non-`.lock` file there) or any other `.wavefoundry/**/*.lock` file, and a fresh second process still finds the lifecycle lock held after the scan. Outside a git worktree this covers `_get_all_files`, and on the current code the second process acquires the lock (POSIX). Inside a git worktree whose ignore file lacks the managed lock lines, both `_get_all_files` and `_get_changed_files` select neither the lifecycle lock nor the planted `.wavefoundry/locks/` file; on the current code both select them. A `Cargo.lock` at the repository root carrying a planted credential that a shipped rule matches is still scanned and reported. An explicit `files=` list naming an excluded path does not open it, a differently cased `.WaveFoundry/locks/x` or `X.LOCK` path is excluded, and an existing finding recorded for an excluded path is swept from the findings file on the next scan.

## Tasks

- [x] Write the AC-1 and AC-2 multi-process tests first and record their failure on the current code.
- [x] Register lifecycle holds (with owning thread) under the guard and refuse re-entry before opening the file.
- [x] Make the publication probe consult the registry, with the three cases in Requirement 3.
- [x] Register the transaction's publication hold and refuse a same-thread publication wait on it.
- [x] Record in the Risks row the actual exclusion evidence that the index walker, the secrets scan and the context-efficiency monitor never open `.wavefoundry/lifecycle-mutation.lock`.
- [x] Threading, release-path, census, constant-equality and reload tests (AC-3 to AC-8).
- [x] Mutation check in a scratch copy of the tree: removing the registration, the re-entry check, or the registry consult each fails a named test.
- [x] Architecture doc section and CHANGELOG entry.
- [x] Exclude the `.wavefoundry/locks/` folder and every `.wavefoundry/**/*.lock` file in the secrets scanner's file selection, with the AC-11 test (failing first) and one CHANGELOG sentence.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| Regression tests | implementer | readiness | fail on current code first |
| Registry fix | implementer | regression tests | lifecycle_lock, review_evidence |
| Docs | implementer | registry fix | architecture section, CHANGELOG |
| Review | code-reviewer, qa-reviewer, security-reviewer | implementation | |

## Serialization Points

- `.wavefoundry/framework/scripts/lifecycle_lock.py`, `.wavefoundry/framework/scripts/review_evidence.py`, `.wavefoundry/framework/scripts/runtime_lock.py`
- `.wavefoundry/framework/scripts/tests/test_lifecycle_mutation_lock.py`, `.wavefoundry/framework/scripts/tests/test_runtime_lock.py`
- `.wavefoundry/framework/scripts/wave_lint_lib/secrets_validators.py`, `.wavefoundry/framework/scripts/tests/test_secrets_validators.py`
- `docs/architecture/cross-cutting-concerns.md`

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` (the `lifecycle-mutation.lock` and `project_state_publication_lock` entries). `docs/architecture/chunking-and-indexing-pipeline.md` already describes the registry for the index lock and is unchanged.

## AC Priority

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | Reproduces the re-entry release with real processes |
| AC-2 | required | Reproduces the probe release with real processes |
| AC-3 | required | Pins the re-entry decision |
| AC-4 | required | The probe must not open the file while this process holds it, from any thread |
| AC-5 | required | A publication wait inside the transaction must not drop the lifecycle hold or hang |
| AC-6 | required | Registration must not weaken the existing release guarantees |
| AC-7 | required | Keeps new openers from reintroducing the defect |
| AC-8 | important | Reload already preserves the registry; the test pins it |
| AC-9 | required | The lock contract is documented |
| AC-11 | required | The secrets scanner must not drop an in-process lifecycle hold |
| AC-10 | required | Standard verification |

## Progress Log

| Date | Update | Evidence |
| --- | --- | --- |
| 2026-10-01 | Requirement 9 / AC-11 implemented and met (boxes left for the coordinator to mark), resolving the secrets-scan residual recorded in Risks. New `secrets_validators.is_wavefoundry_lock_path` (everything under `.wavefoundry/locks/` and every `.wavefoundry/**/*.lock`, case-insensitive, `/` separators) is applied before any read in the `git ls-files` branch, the rglob fallback (inside and outside a git worktree), the `_get_changed_files` loop and an explicit `files=` list, and a recorded finding for such a file is swept like the allowlist sweep; scan-rules hash and `SCANNER_VERSION` unchanged. Tests written first failed on the unmodified scanner (outside git a second process acquired the lifecycle lock after the in-process scan); `test_secret_scan_cache` git-branch expectations updated for the two lock paths it pinned as candidates. Full suite 10386 tests OK; each exclusion branch, the `files=` filter, the sweep and case folding removed in a scratch copy fails a named test | `wave_lint_lib/secrets_validators.py`, `tests/test_secrets_lock_exclusion.py`, `tests/test_secret_scan_cache.py` |
| 2026-10-01 | Repair round for DEL-1ZIMC-UNPINNED-GUARD-MECHANISMS, test-only: four mutations survived the focused file, so four tests now pin the mechanisms they removed. The in-guard re-entry re-check (two threads held past the up-front check by a barrier; one acquires, the other is refused), the thread test of the own-publication refusal (another thread's transaction hold gets the ordinary busy refusal), registration under the guard before the metadata write, and the probe's open under the guard. In a scratch copy all twelve mutations (M1 to M12) now fail named tests in the 45-test file; full suite 10377 tests OK. CHANGELOG bullet now names the two intended behaviour changes (cross-thread publication wait fails fast; Windows lifecycle holder waits) | `tests/test_lifecycle_mutation_lock.py` `LifecycleHoldGuardOrderingTests` |
| 2026-10-01 | Correction to Requirement 6 (recorded here, Requirements unchanged): `wf_reload_mcp` does evict `lifecycle_lock` and `review_evidence` (the eviction block near the top of `wf_server/server_impl.py`) and re-imports them. The conclusion holds because the hold registry lives in `runtime_lock`, which is not evicted, and neither evicted module caches registry state (both call `runtime_lock` functions that read its module-level dict). The AC-8 test pins the real behaviour: the reloaded modules are new objects and still see a hold taken before the reload | `tests/test_lifecycle_mutation_lock.py` `LifecycleHoldReloadTests` |
| 2026-10-01 | Implemented. AC-1, AC-2 and AC-5 tests written first and failed on the unmodified code (re-entry and the probe both let a second process acquire; the in-transaction wait hung past 30 s). `lifecycle_mutation_lock` registers holds with the owning thread and refuses re-entry before opening the file; the publication probe consults the registry; the transaction registers its publication hold and a same-thread publication request inside it is refused. Walker evidence recorded in Risks | `lifecycle_lock.py`, `review_evidence.py`, `tests/test_lifecycle_mutation_lock.py` |
| 2026-10-01 | Planned. Verified against the code: `lifecycle_mutation_lock` uses `RuntimeFileLock(style="record", offset=1 << 30)` and never calls `register_process_hold`; the only registry users are in `indexer.py`; the probe in `project_state_publication_lock` opens `.wavefoundry/lifecycle-mutation.lock` directly; `lifecycle_publication_transaction` takes the publication lock outside the depth counter; the publication lock is `style="flock"`; `RuntimeFileLock` uses `msvcrt.locking` on Windows; `core_handler` returns an unwrapped handler, so extension overrides do not re-enter the middleware; the upgrade runs in a child process of `wf_upgrade`. Reproduced both reported scenarios and the transaction deadlock on macOS in a scratch repository | `lifecycle_lock.py`, `review_evidence.py`, `runtime_lock.py`, `indexer.py`, `wf_server/server_impl.py` |

## Decision Log

| Date | Decision | Reason | Alternatives |
| --- | --- | --- | --- |
| 2026-10-01 | Keep the lifecycle lock on process-owned record locks and add the registry, rather than switching it to `flock` | `upgrade_bridge_bootstrap` and already-installed older runtimes take the lifecycle lock as a record lock at offset `1 << 30` (pinned in `test_upgrade_protocol`), and `flock` and `fcntl` locks do not exclude each other, so changing the style would break cross-version exclusion during upgrade | Switch to `flock` (an open file description owns the lock, so neither defect exists), rejected for mixed-version interop |
| 2026-10-01 | Refuse re-entry (raise `LifecycleLockBusy`) rather than count it | No shipped path re-enters: the census finds one acquisition per entry point (middleware per tool call, setup reconciliation, the four sequential upgrade transactions in a child process), and `core_handler` hands overrides an unwrapped handler. Windows already refuses re-entry today, so refusing keeps the platforms the same; it matches the index lock's precedent (wave 1za2y); and a nested lifecycle mutation is a design error that counting would hide | Count re-entry per thread, which would make POSIX and Windows diverge unless Windows also counted, and would let a nested caller assume it started a fresh exclusive operation |
| 2026-10-01 | The probe treats the calling thread's own hold as "wait" and another thread's hold as "fail fast" | The caller holding lifecycle is the normal lifecycle-tool path and the publication holder cannot be waiting for lifecycle (fixed lock order); another thread's hold is a concurrent lifecycle mutation, the case the probe exists to fail fast on | Fail fast on any in-process hold, which would make every lifecycle tool fail whenever another process briefly publishes |
| 2026-10-01 | Register the transaction's publication hold and refuse a same-thread wait on it | The publication lock does not lose holds (flock is per open file description), but a wait on it inside the transaction blocks forever on POSIX, and would block on Windows once the probe skips the caller's own lifecycle hold | Route the transaction through `project_state_publication_lock(wait=False)`, which changes the exception types the upgrade handles |
| 2026-10-01 | Registry metadata records the owning thread; the key stays the resolved path | Distinguishes same-thread from other-thread holds without changing the index lock's use | A per-thread registry, which would hide another thread's hold from readers |

## Risks

| Risk | Mitigation |
| --- | --- |
| A future caller legitimately needs nested lifecycle scope | The refusal names the same-process hold; the caller passes the held scope down instead of re-acquiring |
| A shipped path re-enters that the census missed | The middleware maps the refusal to a busy response with no state change, so the failure is visible rather than silent; the change's own suites exercise every lifecycle tool path |
| Linux repositories on NFS, where `flock` is emulated with record locks, would make the publication lock process-owned too | The same-thread case is covered by Requirement 4's registration; noted as a limit in the architecture doc |
| A reader opens the lifecycle file through a general file walk in the server process | The census predicate is "opens the lifecycle lock path by name", so generic walkers are not covered by it. Checked at implementation (2026-10-01): (1) index walker: `indexer.walk_repo` drops any `.lock` file through `BINARY_EXTENSIONS` (`".db", ".sqlite", ".lock"`, `indexer.py` around line 608) at `if suffix in BINARY_EXTENSIONS: continue`, which runs before the walk's only content read (the binary sniff `path.read_bytes()`); before it the walk only calls `path.is_file()`, a stat that opens no descriptor. The staleness monitor (`server_impl._index_inputs_stale` to `indexer.project_index_inputs_stale`) walks through `walk_repo`, so it inherits that exclusion; `PROJECT_INDEX_EXCLUDE_PREFIXES = (".wavefoundry/",)` also keeps the file out of the corpus. (2) secrets scan: `wf_scan_secrets` runs `run_secrets_scan.py` as a subprocess (`docs_handlers.py` around line 286), a separate process whose opens cannot release this process's hold. In a git worktree, `secrets_validators._get_all_files` and `_get_changed_files` select files with `git ls-files` and `--others --exclude-standard`, and the rendered ignore block lists `.wavefoundry/**/*.lock` (`render_platform_surfaces.py` around line 2394), so the file is never selected. Residual, not changed here: when the subprocess fails, `docs_handlers` falls back to an in-process `check_hardcoded_secrets`; outside a git worktree its `rglob` fallback excludes only machine-authority paths (`machine_authority.HARDCODED_EXCLUDE_PREFIXES` covers `.wavefoundry/locks/`, not `.wavefoundry/lifecycle-mutation.lock`), and `.lock` is not in `_BINARY_SKIP_EXTENSIONS`, so that fallback would read the file. Reported to the coordinator for a decision. (3) context-efficiency monitor: `_maybe_project_context_efficiency` publishes through `_project_context_efficiency_wave(automatic=True)`, which takes `project_state_publication_lock(root, wait=False)`; a busy lock raises before the lifecycle probe, and no context-efficiency module names the lifecycle lock path (the AC-7 census) |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
