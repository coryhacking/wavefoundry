# Expose authoritative index-build lock status via MCP — by testing the actual lock

Change ID: `1p99o-enh expose-index-build-lock-status`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-07-01
Wave: `1p99p expose-index-build-lock-status`

## Rationale

Agents read `.wavefoundry/index/index-build.lock` **directly** and assume the file's existence means a
build is in progress. It does not. The lock file persists **by design** — `_index_build_lock` never
unlinks it on exit; it is a crash-safe "last owner" breadcrumb, and the OS lock is the real authority.
The file is reclaimed lazily on the **next** acquire. So **file presence ≠ lock held**, and an agent
inferring "a build is running" from the file is reading the wrong signal. The framework amplified the
mistake: the `wave_index_build` early-exit diagnostic told callers to *"remove …/index-build.lock and
retry"* — teaching the wrong model.

Fix: expose an **authoritative** "is a build running?" answer on `wave_index_build_status`.

**Design pivot (operator review, 2026-07-01).** A first cut derived `held` from a PID/cmdline
heuristic (`classify_index_build_lock_owner`, wave `1p98u`) and reported `live`/`stale`/`completed`.
Operator feedback, correctly:
1. `stale` and `completed` are **not distinct states** — they differ only by an age threshold; both
   mean "no build running / not held". They should collapse to a single `held: false`.
2. Nothing in the status path **actually tests the lock** — it only reads metadata + PID liveness, so
   `held` was an *inference*, not the truth. `held` should mean **the lock is currently, actively held.**

So `held` must be determined by **testing the real OS lock non-destructively**, not by classifying a
PID. That requires changing the lock primitive so it *can* be tested without acquiring it, on both
POSIX and native Windows.

## The mechanism (cross-OS)

**Symmetric sentinel-byte lock.** On **both** POSIX and Windows the lock is taken on a single
**sentinel byte** (a shared offset constant), kept **distinct from the metadata region**. The JSON
metadata `{pid, started_at, ended_at, cmdline}` lives at byte 0 and is therefore always readable/
writable regardless of lock state — so status can read `owner_pid`/`ended_at` even during a live build
(the `dashboard-server.lock` lesson: a mandatory lock over the metadata bytes would block that read on
Windows), and the finalize path can write `ended_at` while still holding the lock.

- **POSIX (Linux + macOS):** hold the sentinel byte as a **`fcntl` record lock** (`F_SETLK`/`F_WRLCK`)
  instead of `flock`. Status reads it with **`F_GETLK`** — the POSIX operation purpose-built to test
  whether a lock *would* conflict and return the **holder PID**, **without acquiring anything**. Truly
  non-destructive; portable; holder PID from the kernel. Bonus: `fcntl` locks are **not**
  `fork`-inherited, which removes the inherited-fd edge case `1p98u` had to reason around.
- **Native Windows:** no `F_GETLK` equivalent — the sentinel byte is an `msvcrt` byte lock, tested with
  a **momentary, non-blocking `LK_NBLCK`** acquire-and-release. A momentary acquire, not a pure query —
  accepted because Windows has no defunct/zombie problem (the original bug is POSIX-only), the race
  window is microseconds and self-heals, and the only pure-query alternative (Restart Manager
  `RmGetList`) is heavyweight `ctypes` not worth it for a status poll.

**`ended_at` — how the last build ended.** `_index_build_lock`'s `finally` block writes `ended_at`
(best-effort) into the metadata JSON just before releasing the lock. Its best-effort nature is the
feature: a clean exit records it; a `SIGKILL`/power-loss cannot — so **absent `ended_at` (with
`started_at` present, lock not held) means the last build was interrupted** (crashed/killed) and the
index may be partial. This replaces the meaningless age-based `stale`/`completed` split with a real
event-based signal.

`classify_index_build_lock_owner` (wave `1p98u`) is **retained** — but only for the **reclaim decision**
inside `_index_build_lock` (should the stale metadata file be unlinked before acquire). It is no longer
used to determine status `held`.

## Requirements

1. `held` on `wave_index_build_status`'s `lock` object is determined by **testing the actual OS lock**
   (POSIX `F_GETLK`; Windows momentary `LK_NBLCK`), never by file presence or a PID heuristic. `held:
   true` iff the lock is currently held by a running builder.
2. Collapse the states: the `lock` object is `{ held (bool), present (bool), owner_pid, owner_cmdline,
   started_at, ended_at, note }`. **Drop `live` / `stale` / `completed` / the `classification` field.**
   `present` = a lock file exists; `held` = the OS lock is actively held. `owner_pid`/`owner_cmdline`
   come from `F_GETLK`'s returned PID when held (ground truth), else from the metadata (last owner).
2a. The metadata records **`ended_at`**, written best-effort in `_index_build_lock`'s `finally` block
    before releasing the lock. Status derives the last-build outcome from it: `held:false` +
    `ended_at` set ⇒ finished cleanly (surface the time); `held:false` + `started_at` set +
    **`ended_at` absent** ⇒ **the last build was interrupted** (crashed/killed) — the `note` must say so
    and suggest a rebuild may be warranted. No age heuristic.
3. `_index_build_lock` (the builders' acquire path) takes its lock on a **single sentinel byte** on
   **both** OSes — a `fcntl` record lock on POSIX (was `flock`), an `msvcrt` byte lock on Windows —
   using one shared offset constant, kept off the byte-0 metadata region so the JSON stays readable/
   writable under the lock. Crash-safety is preserved (the lock releases when the holder process dies),
   and the acquire/reclaim behavior is otherwise unchanged.
4. A cross-OS `indexer._index_build_lock_held(root)` (or equivalent) returns `(held: bool, holder_pid:
   int | None)` using `F_GETLK` on POSIX and momentary `LK_NBLCK` on Windows; degrades safely (on any
   probe error, `held` falls back conservatively and never raises).
5. The status tool never blocks and never holds the lock beyond the instant Windows test.
6. Fix the `build_skipped_lock_busy` recovery message: do not instruct deleting the lock file; point at
   `wave_index_build_status`; keep the live-holder "wait" case. **(Already landed — keep.)**
7. `wave_index_health` surfaces a `present-but-not-held` indicator (reusing the same lock test).
8. Plain terminology — no "zombie" in any operator/agent-facing text.
9. Guidance on every doc surface (tool docstring, AGENTS.md, `mcp-tool-surface.md`, seeds `211-guru` +
   `140-reindex`): "read `lock.held`, don't read the file." Seeds carry no wave/ADR IDs.
   **(Already landed — reconcile wording to the collapsed shape.)**
10. Backward-compatible response: additive field, no new tool, no signature change, no reconnect.
11. No regression on the concurrency-critical acquire path — full framework suite green; the
    lock-conflict path (`test_main_fails_fast_when_another_process_holds_index_lock`) still passes.

## Scope

**In scope:**

- `indexer.py`: `_index_build_lock` POSIX `flock` → `fcntl` record lock; Windows lock → sentinel byte;
  new `_index_build_lock_held(root)` cross-OS tester (`F_GETLK` / `LK_NBLCK`).
- `server_impl.py`: `_index_build_lock_info` uses `_index_build_lock_held` for `held`; response
  collapsed to `held`/`present`/`owner_pid`/`owner_cmdline`/`started_at`/`note`; the (already-landed)
  recovery-message fix and `wave_index_health` indicator reconciled to the collapsed shape.
- Docs/seeds/docstring/spec (already landed) reconciled to the `held`/`present` shape (drop
  `classification` from `mcp-tool-surface.md`).
- Tests: `F_GETLK`/`LK_NBLCK` held vs not-held; the status `held` reflects a real concurrent holder;
  collapsed response shape; the acquire path still fails-fast under a real concurrent lock; Windows
  sentinel-byte path (mocked where the OS branch can't run in CI).

**Out of scope:**

- `_table_lock` (per-table locks) — separate from the whole-index build lock; unchanged.
- Restart Manager / `/proc/locks` — rejected (heavyweight / non-portable) per Decision Log.
- Renaming `_process_is_zombie` (internal, shipped in closed `1p98u`).

## Acceptance Criteria

- [x] AC-1: `held` is determined by testing the actual OS lock — `F_GETLK` (POSIX) / momentary
      `LK_NBLCK` (Windows) — not by file presence or the PID classifier. Evidence:
      `IndexBuildLockHeldTests.test_held_detects_concurrent_holder_and_clears_after` (real subprocess
      holder ⇒ `held:true` + kernel PID; after exit ⇒ `held:false`); `test_held_true_from_lock_test_uses_kernel_pid`.
- [x] AC-2: the `lock` object is `{held, present, owner_pid, owner_cmdline, started_at, ended_at, note}`
      with **no** `classification`/`live`/`stale`/`completed`. Evidence: `test_shape_has_no_classification`,
      `test_no_file_not_present_not_held`.
- [x] AC-2a: `_index_build_lock` writes `ended_at` best-effort on clean exit; status reports "finished
      cleanly" (`ended_at` set) vs an **interrupted** build (`started_at` set, `ended_at` absent, not
      held). Evidence: `test_ended_at_written_on_clean_exit`, `test_clean_finish`, `test_interrupted_build`.
- [x] AC-3: `_index_build_lock` takes its lock on a single **sentinel byte** on both OSes (`fcntl`
      record lock POSIX / `msvcrt` Windows) off the byte-0 metadata; crash-safety + acquire/reclaim
      preserved; metadata readable while held. Evidence:
      `test_main_fails_fast_when_another_process_holds_index_lock` + the 18 `IndexBuildLockTests` still
      green; the held test asserts metadata readable while held.
- [x] AC-4: `_index_build_lock_held` returns `(held, holder_pid)` via `F_GETLK` (per-platform struct),
      degrades safely on any probe error (returns `(None, None)`, never raises). Evidence:
      `test_held_false_when_no_lock_file`; `test_undetermined_treated_not_held`.
- [x] AC-5: `wave_index_health` flags an **interrupted** build (`index_build_interrupted`); plain
      terminology, no "zombie". Evidence: `test_health_flags_interrupted_build`, `test_no_zombie_terminology`.
- [x] AC-6: the recovery message + all doc surfaces (docstring/AGENTS/spec/seeds `211`+`140`/arch doc)
      match the `held`/`present`/`ended_at` shape (dropped `classification`); seeds carry no wave/ADR IDs.
      Evidence: diffs + grep.
- [x] AC-7: backward-compatible (additive, no new tool/signature/reconnect); `run_tests.py` (3,801) +
      `wave_validate` pass; live MCP reload + `wave_index_build_status` shows the lock-tested `held`
      (below). Evidence: suite + docs gate + live call.

## Tasks

- [x] (superseded first cut) `_index_build_lock_info` + `lock` field wired into `wave_index_build_status`;
      recovery-message fix; `wave_index_health` indicator; docstring/AGENTS/spec/seed guidance. Kept;
      being reconciled to the collapsed lock-tested shape below.
- [x] `indexer._index_build_lock`: locks the shared `INDEX_BUILD_LOCK_SENTINEL` byte on both OSes
      (POSIX `flock` → `fcntl.lockf`; Windows `msvcrt`); writes **`ended_at`** best-effort in `finally`
      before release. Done.
- [x] Added `indexer._index_build_lock_held(index_dir)` (`F_GETLK` per-platform struct / momentary
      `LK_NBLCK`; `(None,None)` safe fallback). Done.
- [x] Rewired `server_impl._index_build_lock_info` to lock-test `held`, collapse the response, add
      `ended_at` + interrupted note; health emits `index_build_interrupted`; docstring/AGENTS/spec/seeds
      reconciled (dropped `classification`). Done.
- [x] Tests: real-concurrent-holder held + kernel PID / clears after (`IndexBuildLockHeldTests`);
      collapsed shape; `ended_at` on clean exit; interrupted; metadata-readable-while-held; fail-fast
      under a real lock (existing); helper fallback; server shape (`IndexBuildLockStatusTests`, 10). Done.
- [x] `run_tests.py` (3,801 OK) + `wave_validate` (ok); live MCP reload + `wave_index_build_status`. Done.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| [workstream-1] | implementer | — | Single lane, ordered: `indexer.py` lock primitive + `_index_build_lock_held`, then `server_impl` rewire + response collapse, then doc/test reconciliation. Concurrency-critical — full suite + re-review. |

## Serialization Points

- `indexer._index_build_lock` is the shared acquire path for **all** builders (upgrade phase-4,
  `wave_index_build`, hook, CLI, setup). The primitive swap must preserve mutual exclusion and
  crash-safety; verified by the existing fail-fast lock-conflict test plus the full suite.

## Affected Architecture Docs

`docs/architecture/chunking-and-indexing-pipeline.md` "Build Coordination" section — update the lock
description: the build lock is a `fcntl` record lock (POSIX) / sentinel-byte `msvcrt` lock (Windows),
and `wave_index_build_status` reports an authoritative, lock-tested `held`. No boundary/flow change.

## AC Priority

| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The whole point — `held` must test the real lock, not infer it. |
| AC-2 | required   | Collapse the meaningless states; the response must be the authoritative shape. |
| AC-3 | required   | Concurrency-critical: the primitive swap must not weaken mutual exclusion or crash-safety. |
| AC-4 | required   | The cross-OS tester must be correct and never raise. |
| AC-5 | important  | Health-level visibility of a leftover lock. |
| AC-6 | required   | Docs/message must match the new shape (no dangling `classification`). |
| AC-7 | required   | Backward-compatible, no reconnect; no regression. |

## Progress Log

| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-07-01 | Planned (field-addition design). Expose a `lock` field on `wave_index_build_status`, plain terminology, fix the delete-the-file message. | prior revision. |
| 2026-07-01 | Implemented first cut (PID-heuristic `held` + `live`/`stale`/`completed`). Recovery message + docstring/AGENTS/spec/seed guidance landed; 8 tests; suite 3,796 OK. | `IndexBuildLockStatusTests`; live MCP call. |
| 2026-07-01 | **Design pivot (operator review).** `stale`/`completed` aren't distinct states, and status never tested the actual lock. Revised: `held` from testing the real OS lock — POSIX `fcntl`+`F_GETLK` (non-destructive, holder PID, no fork-inherit), native Windows sentinel-byte `msvcrt` + momentary `LK_NBLCK`. Collapse the response to `held`/`present`. Re-council before implementing the primitive swap. | this revision; operator feedback. |
| 2026-07-01 | **Folded in `ended_at` + symmetric sentinel (operator).** Lock a shared sentinel byte on BOTH OSes (metadata JSON at byte 0, always readable). `_index_build_lock` writes `ended_at` best-effort in `finally`; status reports clean-finish (`ended_at` set) vs **interrupted** (`started_at` set, `ended_at` absent, not held) — the meaningful event-based replacement for the age heuristic. | this revision; operator feedback. |
| 2026-07-01 | Implemented the full revised design. `indexer`: `flock`→`fcntl.lockf` on `INDEX_BUILD_LOCK_SENTINEL` (1<<20), `_index_build_lock_held` via per-platform `F_GETLK` struct (darwin/linux) + momentary Windows `LK_NBLCK`, `ended_at` best-effort in `finally`. `server_impl`: lock-tested `held`, collapsed response, `ended_at`/interrupted note, `index_build_interrupted` health flag. Docs/docstring/AGENTS/spec/seeds/arch reconciled (dropped `classification`). **Live macOS smoke test:** subprocess holder ⇒ `F_GETLK` returns `(True, holder_pid)`, metadata readable while held, `ended_at` on clean exit, fail-fast preserved. AC-1..7 met. | `indexer.py`/`server_impl.py` diffs; `IndexBuildLockHeldTests` (3) + `IndexBuildLockStatusTests` (10); 3,801 tests OK; docs-lint ok. Linux `F_GETLK` struct is per-platform (linux format) — CI is macOS; a Linux run confirms that path. |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-07-01 | Fold `lock` into `wave_index_build_status`, not a new tool. | Same "is a build running" question; a new tool needs an MCP reconnect, a field addition does not. | New tool (rejected — reconnect + proliferation). |
| 2026-07-01 | Determine `held` by **testing the actual lock**, not a PID heuristic; collapse `stale`/`completed`/`live` to `held`/`present`. | Operator review: the heuristic was inferential and the stale/completed split is meaningless for "is a build running". | PID/metadata heuristic (rejected — inferential; the original defect). |
| 2026-07-01 | POSIX: switch the build lock to a `fcntl` record lock and read it with `F_GETLK`. | `F_GETLK` is the only portable operation that tests a lock **without acquiring it** and returns the holder PID; `fcntl` locks also aren't `fork`-inherited (removes the inherited-fd edge). | Keep `flock` + momentary `LOCK_NB` test (rejected — not non-destructive; has a race). `/proc/locks` (rejected — Linux-only). |
| 2026-07-01 | Windows: keep an `msvcrt` byte lock on a **sentinel byte**, test via momentary `LK_NBLCK`. | Windows has no `F_GETLK`; the sentinel byte keeps metadata readable under the mandatory lock; Windows has no zombie problem so the momentary-acquire race is immaterial. | Restart Manager `RmGetList` (rejected — heavyweight ctypes for a status poll). Lock the metadata bytes (rejected — mandatory lock blocks status reads, the `dashboard-server.lock` bug). |
| 2026-07-01 | Lock a **sentinel byte on BOTH** POSIX and Windows (one shared offset), metadata JSON at byte 0. | Symmetric + simplest; keeps the JSON always readable/writable (status reads owner/`ended_at`, finalize writes `ended_at`) regardless of lock state; avoids the mandatory-lock-over-metadata trap. | Lock the whole file / byte 0 (rejected — collides with the metadata region). |
| 2026-07-01 | Add **`ended_at`** (best-effort in `_index_build_lock`'s `finally`) as the last-build-outcome signal; **absent `ended_at` (not held, `started_at` present) = interrupted build**. | Event-based and meaningful (clean finish vs crash/kill), unlike the arbitrary age-based `stale`/`completed`; best-effort is the feature — a hard kill can't write it, so absence reliably signals an interrupted build (possibly-partial index). | Age-based staleness (rejected — meaningless, operator feedback). A separate "outcome" file (rejected — the lock JSON already carries build identity). |
| 2026-07-01 | Retain `classify_index_build_lock_owner` for the reclaim decision only. | Still the right heuristic for "unlink stale metadata before acquire"; just wrong for status `held`. | Delete it (rejected — the reclaim path needs it). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Swapping the core build-lock primitive weakens mutual exclusion or crash-safety. | `fcntl` locks release on process death (crash-safe) and are mutually exclusive on the inode; AC-3 verifies via the existing fail-fast lock-conflict test + full suite + re-review. |
| POSIX-lock footguns (released on any close of the fd in the process; not fork-inherited). | `_index_build_lock` opens the file once, holds one fd for the build, releases on exit — the footgun cases (multiple opens, fork-sharing) don't apply; not fork-inheriting is desired here. |
| Windows momentary `LK_NBLCK` test races a build starting in the same microsecond. | Negligible window, self-heals on retry; Windows has no defunct-owner correctness gap to close, so a rare transient false-busy is acceptable. |
| `F_GETLK` / `LK_NBLCK` probe errors (permission, odd FS). | AC-4: the tester degrades safely and never raises; `held` falls back conservatively. |
| Response-shape change breaks a consumer reading `classification`. | The field was added earlier the same wave and never released; no shipped consumer depends on it. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
