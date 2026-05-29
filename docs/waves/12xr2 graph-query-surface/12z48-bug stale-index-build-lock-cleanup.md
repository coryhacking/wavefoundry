# Stale index-build lock blocks manual rebuilds

Change ID: `12z48-bug stale-index-build-lock-cleanup`
Change Status: `planned`
Owner: framework-maintainer
Status: planned
Last verified: 2026-05-29
Wave: `12xr2 graph-query-surface`

## Rationale

During graph-index rebuilds on 2026-05-29, repeated `setup_index.py --graph-only --full`
runs were skipped with:

```
build_index: Another index build is already running for <root>/.wavefoundry/index;
lock file busy: <root>/.wavefoundry/index/index-build.lock
Index update skipped: another project index build is already running ...
```

The `index-build.lock` marker named a process (`{"pid": 64859, ...}`, later `67494`) that
`ps -p <pid>` confirmed was **dead**. The only way to proceed was to manually `rm` the
marker file and retry. This happened twice in one session and forced the operator-facing
rebuild to fail in a way that looks like data corruption or a hang.

The current locking design (`indexer.py` `_index_build_lock`, ~line 1265) treats the OS
`flock`/`msvcrt.locking` handle as the authority and **intentionally keeps the marker file
after exit** so status tools can inspect the last owner. That is reasonable, but the
launcher/operator experience has two real gaps:

1. The marker is **not liveness-checked** — a dead owner's pid is reported verbatim, so the
   "already running" diagnostic is misleading when no build is actually running.
2. The post-edit hook fires a background reindex on **every** file edit, so legitimate
   manual rebuilds collide with a stream of overlapping hook-triggered builds, amplifying
   the confusing "busy" outcome.

## Requirements

1. A manual index/graph rebuild must not be blocked by a marker file whose recorded owner
   process is no longer alive; the build should reclaim the lock and proceed.
2. When a build is genuinely skipped because another build is running, the diagnostic must
   distinguish a **live** owner (true contention) from a **stale** marker (dead owner /
   expired `started_at`), and tell the operator which case occurred.
3. Lock reclaim must remain correct cross-platform (Linux, macOS, WSL2, native Windows) and
   must not allow two real builds to run concurrently against the same index directory.
4. Hook-triggered background reindexes should not produce unbounded overlapping builds that
   starve a manual rebuild (debounce/coalesce or single-flight behavior).

## Scope

**Problem statement:** Manual rebuilds are skipped with a "lock file busy" error whose
recorded owner pid is dead, because the `index-build.lock` marker is retained without a
liveness check and the post-edit hook can spawn overlapping background builds.

**In scope:**

- Liveness-aware acquisition in `indexer.py` `_index_build_lock`: when the OS lock is free
  but a marker exists, reclaim it; when the OS lock cannot be taken, classify the holder as
  live vs. stale using the recorded `pid` and `started_at` against `LOCK_STALE_SECONDS`.
- Clearer skip diagnostics in `indexer.py` and the `setup_index.py` skip handler that report
  whether the blocker is a live build or a reclaimed/stale marker.
- Investigate whether inherited file descriptors (hook/dashboard `subprocess.Popen` children)
  can keep an `flock` open description alive after the indexer child exits.
- Coalesce/debounce post-edit-hook reindex triggers so rapid edits do not spawn a queue of
  overlapping background builds.

**Out of scope:**

- Per-table `.lock` markers inside `docs.lance/`/`code.lance/` (already have stale cleanup
  via `LOCK_STALE_SECONDS` in `_table_lock`); only revisit if the root cause overlaps.
- Replacing the OS-level locking strategy itself (cross-process `flock`/`msvcrt` is correct
  and recently added) — this change hardens reclaim and diagnostics, not the primitive.

## Acceptance Criteria

- [ ] AC-1: With a stale `index-build.lock` (owner pid dead, or `started_at` older than
  `LOCK_STALE_SECONDS`) and no live build, a fresh `indexer.py` run acquires the lock and
  completes instead of raising `IndexBuildAlreadyRunning`.
- [ ] AC-2: With a genuinely live concurrent build, a second build is still rejected and the
  diagnostic identifies it as a **live** owner.
- [ ] AC-3: The skip message text distinguishes "live build in progress" from
  "reclaimed stale lock" so operators are not misled by a dead pid.
- [ ] AC-4: Post-edit-hook-triggered reindexes are coalesced so that N rapid edits do not
  leave N overlapping background builds contending for the lock (verified by a test or a
  documented single-flight/debounce mechanism).
- [ ] AC-5: Cross-platform locking behavior is preserved (no concurrent real builds); covered
  by the existing `IndexBuildLockTests` plus new stale-reclaim cases.

## Tasks

- [ ] Reproduce deterministically: create an `index-build.lock` with a dead pid, run
  `indexer.py`, and confirm the current "busy" skip.
- [ ] Add liveness detection helper (pid alive + `started_at` age) and reclaim path in
  `_index_build_lock`.
- [ ] Differentiate live vs. stale in `IndexBuildAlreadyRunning` and in the `setup_index.py`
  skip handler messaging.
- [ ] Investigate fd inheritance in `render_platform_surfaces` hook template,
  `dashboard_server.py`, and `server_impl.py` background refresh (`close_fds`, inherited
  open descriptions keeping `flock` held).
- [ ] Add hook reindex coalescing/debounce (single-flight or short debounce window).
- [ ] Extend `test_indexer.IndexBuildLockTests` with stale-reclaim and live-contention cases.

## Agent Execution Graph


| Workstream            | Owner               | Depends On  | Notes                                                  |
| --------------------- | ------------------- | ----------- | ------------------------------------------------------ |
| lock-reclaim          | framework-maintainer | —           | Liveness check + reclaim in `_index_build_lock`        |
| diagnostics           | framework-maintainer | lock-reclaim | Live vs. stale messaging in indexer + setup_index      |
| hook-coalescing       | framework-maintainer | —           | Debounce/single-flight for post-edit reindex triggers  |
| fd-inheritance-probe  | framework-maintainer | —           | Confirm whether inherited fds prolong `flock` ownership |


## Serialization Points

- `indexer.py` `_index_build_lock` is shared by every layer/content build; changes here must
  land before diagnostics work that depends on the new live/stale classification.

## Affected Architecture Docs

`docs/architecture/cross-cutting-concerns.md` (index build locking / concurrency) likely needs
a note on liveness-aware reclaim and hook coalescing. Confirm at Prepare wave; otherwise `N/A`
if the change stays confined to `indexer.py` locking internals.

## AC Priority

| AC | Priority | Rationale |
| -- | -------- | --------- |
| AC-1 | required | Core bug — stale lock blocks operator rebuilds |
| AC-2 | required | Must not allow concurrent real builds |
| AC-3 | important | Operator diagnostics clarity |
| AC-4 | important | Hook storm amplification fix |
| AC-5 | required | Cross-platform lock correctness |


## Progress Log


| Date       | Update                                             | Evidence                                  |
| ---------- | -------------------------------------------------- | ----------------------------------------- |
| 2026-05-29 | Logged from graph-rebuild session; symptom + suspected causes captured. | `indexer.py` `_index_build_lock` ~L1265 |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk                                                        | Mitigation                                                              |
| ----------------------------------------------------------- | ---------------------------------------------------------------------- |
| Liveness reclaim races two builds into concurrent execution | Keep OS `flock` as authority; reclaim only after re-acquiring the lock |
| pid reuse makes a dead owner look alive                     | Combine pid liveness with `started_at` age vs. `LOCK_STALE_SECONDS`    |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
