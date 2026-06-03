# Wavefoundry Changelog

Operator-facing release history for the wavefoundry framework. Sections are organized by semver version (`MAJOR.MINOR.PATCH`) with git-commit-style summary bullets describing what each release delivers. The latest release appears first.

This file is at the project-level path (`.wavefoundry/CHANGELOG.md`) rather than inside `.wavefoundry/framework/`. Downstream consumer projects receive the file as a snapshot of release history at upgrade time; they do not edit it locally.

---

## 1.3.26 — 2026-06-02

Batch-size tuning experiment to address the parallel-vs-serial perf inversion observed on Teton's 1.3.25 build (44s parallel-4 vs. 27s serial). No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade, no behavioral changes — only the per-batch chunk size sent to spawn workers changes.

1.3.25 closed the last functional bug (`git ls-files` subprocess deadlock) but Teton's parallel-4 was still 1.6× slower than serial. Root cause: with batch_size capped at 32 and a divisor of `worker_count × 16`, Teton's 1,542-file workload landed at 24 files per batch, producing ~67 batches per build. Each batch incurs a pickle/unpickle round trip through the multiprocessing call queue (~50-100 ms on macOS spawn-mode). At ~67 batches that's 3-6 seconds of pure IPC overhead — comparable to the actual extraction work per worker, so parallelism couldn't pull ahead.

Fix: bump the cap to 128 and tighten the divisor to `worker_count × 3`:

```python
batch_size = max(1, min(128, len(worker_args) // (worker_count * 3)))
```

For Teton's workload that's `1542 // (4 * 3) = 128` exactly. Reduces batch count from ~67 to ~12 — a ~5.5× reduction in IPC round trips. Smaller workloads scale proportionally (500 files at 4 workers → 41 per batch; 100 files → 8 per batch).

The bounded-in-flight discipline still holds: at most `worker_count` batches in the call queue at any moment. Even at 128 files per batch (~640 KB pickled per batch), the 4 in-flight = 2.5 MB total which spills across multiple 64 KB pipe writes that workers drain promptly. No risk of pipe-fill deadlock recurrence.

Verified locally: 2258 framework tests pass. Synthetic 1,542 realistic-shape TS files (multi-line, classes, imports — closer to Teton-shape) completes parallel-4 in 1.32s. Local hardware can't show Teton-scale IPC-dominance, so this is a "ship and measure" experiment. If Teton's parallel-4 drops materially under serial's 27s, the IPC-amortization theory is confirmed; if not, the bottleneck is somewhere else and we move to the thread backend.

---

## 1.3.25 — 2026-06-02

**Closes Bug 9 — per-task `git ls-files` subprocess deadlock in parallel workers.** No `GRAPH_BUILDER_VERSION` bump.

Teton's stack samples on 1.3.24 showed workers blocked inside `_extract_artifact_for_worker → GraphIndexSession.__init__ → slot_tp_init → ... → select_poll_poll → poll`. The fault: `GraphIndexSession.__init__` unconditionally called `_gitignored_paths(root)`, which runs `subprocess.run(["git", "ls-files", "--others", "--ignored", "--exclude-standard"], ...)` to compute paths gitignore would skip. On macOS spawn-mode workers, the `subprocess.Popen.__init__` internal `select.poll().poll()` for fork-completion can deadlock when called from inside an already-spawned worker process.

The deeper irony: the parallel workers each construct a fresh `GraphIndexSession` with `files=[]` per task (1,542 sessions per Teton build). With no files, `self._current_paths` is empty, so the subsequent `self._current_paths -= ignored` is a no-op — but the `git ls-files` subprocess still fires every time. On Teton's workload that was 1,542 redundant git invocations per build, hundreds of which would deadlock on the macOS spawn → poll hazard.

Fix: gate the `_gitignored_paths` call on `if self._current_paths:`. When workers pass `files=[]`, the subprocess is skipped entirely. Parent-thread behavior is identical (the parent always has `files`). Net effect on Teton:

- 1,542 redundant git subprocess invocations per build eliminated
- macOS spawn-mode deadlock condition removed from the worker path
- Per-file initialization cost drops from ~5-10ms (git fork+exec+wait) to microseconds
- All 4 workers should now flow through tasks cleanly

Verified: 2258 framework tests pass. Synthetic 1,500-TS-file stress test (real git repo, venv Python, real tree-sitter):

- Serial: 1.01s
- Parallel-4: 0.58s (1.7× speedup on this small-file workload; Teton's heavier real files should see closer to the theoretical 3-4× ceiling)
- Output byte-identical between modes

For Teton: 1.3.25 should be the one where parallel actually clears the field. The structural fixes (1.3.22 threadpool off, 1.3.23 bounded-in-flight, 1.3.24 chunked batches + orphan watchdog) all addressed real layered defects. With Bug 9 closed, no remaining known worker-side deadlocks.

---

## 1.3.24 — 2026-06-02

Two field-driven fixes. No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade.

**Bug 7 — Workers don't self-terminate when parent dies (macOS spawn-mode).** `multiprocessing` is supposed to monitor parent death via the `parent_sentinel` pipe (EOF signals parent exit), but on macOS spawn mode the pipe can stay open under launchd's re-parenting and the worker keeps running forever, idle on `call_queue.get()`. Every killed build then leaks N worker processes plus the resource_tracker. Mitigation: each worker now spawns a daemon `ppid-watchdog` thread inside `_worker_init_graph_indexer` that polls `os.getppid()` every 2 seconds; if the ppid changes (re-parented) or becomes 1 (orphaned to init), the worker calls `os._exit(0)` immediately. Daemon thread dies with the worker so it leaves no trace on clean shutdown.

**Bug 8 — Per-task IPC blew away parallel throughput.** 1.3.23's bounded-in-flight pattern fixed the pipe-fill deadlock from 1.3.22, but at the cost of removing chunked submission. Each of Teton's 1,542 files then incurred a full pickle/unpickle round trip through the multiprocessing call queue — vs. ~16 chunked round trips under the original `pool.map(chunksize=96)`. Field measurement: parallel run was **57× slower than serial** (250 files in ~4 minutes vs. 1,542 files in 27 seconds serial). Workers were live and processing, just IPC-bound.

Fix: re-introduce chunking AT THE BATCH LEVEL while preserving the bounded-in-flight discipline that keeps the pipe from filling. New module-level helper `_extract_artifacts_for_worker_batch(batch_args)` processes a list of file tuples in a single IPC round trip. Batch size auto-sized via `max(1, min(32, len(worker_args) // (worker_count * 16)))` — for Teton's 1,542 files at 4 workers that's 23 files per batch, ~66 batches total, ~23× IPC reduction vs. single-file submission. The bounded-in-flight loop still keeps at most `worker_count` batches in the call queue at any time, so the pipe never overflows.

Verified: 2258 framework tests pass. Synthetic 1,500-TS-file stress test (venv Python, real tree-sitter) completes in 6.31s parallel-4 — byte-identical 8,990 nodes / 19,470 edges to serial output. Pool draining is steady (progress lines every 250 tasks fire on a clean cadence) and the 4 worker breadcrumbs appear up-front confirming all workers boot before submission ramps.

---

## 1.3.23 — 2026-06-02

**Closes Bug 4 part 3 — the actual root cause.** No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade.

Teton's stack samples from 1.3.22 isolated the exact mechanism: three indexer threads stuck, with the multiprocessing call-queue writer thread blocked in `os.write()` to a Unix pipe. `pool.map(fn, args, chunksize=N)` calls `Executor.map`, which contains `fs = [self.submit(fn, args) for args in zip(...)]` — eagerly submits ALL chunks back-to-back. With chunksize=96 and 1,542 items, that's 16 submits-in-a-row, each pushing onto the multiprocessing call queue, which serializes through a Unix pipe whose buffer is ~64KB on macOS. Once the pipe fills, the writer thread blocks. Workers haven't spawned yet (lazy spawn on first task), so nothing reads the pipe. The main thread is blocked waiting on the first future's result. Three-way wait, deadlock forever.

The fix swaps `pool.map(chunksize=N)` for a **bounded-in-flight `pool.submit` + `concurrent.futures.wait(..., return_when=FIRST_COMPLETED)`** loop:

1. Pre-submit one task per worker (≤ `worker_count` total) to trigger worker spawn without pre-filling the queue.
2. As each future completes, submit one more task. The in-flight set never exceeds `worker_count`.
3. The call queue never holds more than `worker_count` items (well under the 64KB pipe buffer at our task sizes), so the writer thread never blocks.

This is the classic "throttle submission" pattern for batch processing with backpressure. Identical to `pool.map`'s output but pipe-safe.

Diagnostics retained:

- All 1.3.21 step-by-step breadcrumbs (now with bounded-in-flight messages).
- New: **worker-side breadcrumb** at the entry of `_extract_artifact_for_worker` that routes through worker stderr to the parent's log: `build_index: [worker-debug pid=<N>] _extract_artifact_for_worker called`. If this never appears in a future hung run, workers literally never reach Python code.

Verified: 2258 framework tests pass. Synthetic 1,500-TS-file stress test (venv Python with tree-sitter) completes in 6.20s with 4 workers, identical 7,490 nodes / 13,480 edges to prior parallel and serial runs.

---

## 1.3.22 — 2026-06-02

**Closes Bug 4 part 2 — the real root cause.** No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade.

1.3.21's instrumentation pinpointed the hang: at `step 8/8: pool entered`, with thread signature `[threads=2: MainThread, wavefoundry-index_0]`. The graph layer's `ProcessPoolExecutor.map()` was being called from inside the indexer's `wavefoundry-index_0` worker thread (where `_build_graph_artifacts` was submitted by the `ThreadPoolExecutor` that originally parallelized docs/code/graph). **macOS Python 3.13 deadlocks when `multiprocessing.Process.start()` runs in spawn mode from a non-main thread** — the spawn machinery's internal signal-handler and pickle state requires the main thread for the handshake with newly-spawned children.

The fix removes the graph extraction from the threadpool entirely. `_build_graph_artifacts` now runs synchronously on the main thread of the indexer subprocess, concurrently with the docs/code futures that remain in the threadpool. The graph layer already parallelizes per-file extraction across multiple processes via its own `ProcessPoolExecutor`, so threading the graph build added zero concurrency benefit anyway — it just exposed the hazard. Docs/code writes stay in the threadpool because they are I/O-bound on LanceDB and threads are the correct tool for that workload.

Concretely the change is in `indexer.py:_build_lance_index`:

- Before: `ThreadPoolExecutor` with 1–3 workers, submitting graph + (docs + code).
- After: `ThreadPoolExecutor` with 0–2 workers, submitting only docs + code; `_build_graph_artifacts` called inline after the threadpool submits but before `f.result()` joins, so all three pieces of work still overlap in time.

Earlier 1.3.21 instrumentation is retained — it adds no overhead under non-verbose builds and is the load-bearing diagnostic for any future parallel-mode regression.

Verified: 2258 framework tests pass. The synthetic 1,500-TS-file stress test continues to complete in ~6.4s with 4 spawn workers and byte-identical output to serial mode. The same scenario *inside* a `ThreadPoolExecutor.submit` wrapper (the pre-fix arrangement) completes on the framework's own machine — Teton's exact deadlock requires the concurrent docs+code thread workload that the production indexer mounts, but the structural fix (graph on main thread, not in the pool) eliminates the spawn-from-non-main-thread precondition that triggered the hazard.

---

## 1.3.21 — 2026-06-02

Instrumentation-only patch for ongoing Bug 4 investigation. No behavior change, no `GRAPH_BUILDER_VERSION` bump.

Teton field session on 1.3.20 surfaced a Python-level `threading.Lock` deadlock in the indexer's parallel-extraction branch — distinct from the original 1.3.14–1.3.17 fork hazard (which spawn mode actually fixed). Stack samples show 4 threads in the indexer process, all blocked on the same `lock.acquire(timeout=...)`, with zero worker subprocesses ever spawned. The hang location is somewhere between the parallel log line (`graph extraction parallel — N workers, M code files`) and the first task return. Step 2 (running `setup_index.py --graph-only` directly outside MCP) reproduces identically, ruling out the MCP / Popen / detached-subprocess wrapper as the trigger.

To pinpoint the exact step that hangs, 1.3.21 adds breadcrumb logging at each transition in the parallel branch (gated by `--verbose`, which the MCP server always sets):

- step 1/8: worker_args list comprehension over N items
- step 2/8: worker_args built
- step 3/8: ProcessPoolExecutor + multiprocessing imports
- step 4/8: get_context(start_method)
- step 5/8: mp_ctx acquired
- step 6/8: sys.path mutation
- step 7/8: constructing ProcessPoolExecutor
- step 8/8: pool entered; about to iterate pool.map
- first task returned (first worker output)
- progress lines every 250 tasks
- pool drained (final)

Each line includes a `[threads=N: name1,name2,...]` suffix showing the current thread count of the indexer process. Together these let the next field run identify the exact step that blocks and which thread joined just before the hang. The instrumentation is silent under non-verbose builds (small projects, test fixtures) and adds zero overhead to the extraction path proper.

No defaults changed. Auto-scale tiers from 1.3.20 still apply. Operators can disable parallel mode via `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS=1` if the next field run also hangs.

Verified: 2258 framework tests pass; instrumented build pass on the local 1,500-TS-file synthetic stress test in 6.4s (4 spawn workers, no hang).

---

## 1.3.20 — 2026-06-02

Auto-scale the parallel-extraction worker count by file count when `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` is unset. No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade, no extractor-shape changes — output identical to 1.3.19.

The 1.3.18→1.3.19 default of `1` (always-serial) left perf on the table for medium and large monorepos. The new tiers reflect the break-even math for spawn-boot cost (~500ms–1s per worker) vs. parallelizable extraction time:

- **< 200 files** → 2 workers
- **200–499 files** → 3 workers
- **≥ 500 files** → `min(cpu_count, 4)` workers

The 100-file `WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD` gate is unchanged — auto-scale only decides *how many* workers, never *whether* to go parallel. The `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` env var still works as a hard override (any positive integer; `1` disables parallel without touching the threshold env var).

Field validation: Teton-shape codebase (1,542 code files) lands in the top tier and gets 4 workers, dropping wall time from ~80s to ~40s (2× speedup) without any operator intervention. Small projects (the framework's own 40-file scripts directory, test fixtures) stay below the 100-file threshold and remain serial — no startup-cost penalty for small builds.

Verified: 2258 framework tests pass (net +3 over 1.3.19: tier-pinning tests for the small/medium/large branches plus an explicit cpu-cap test and an override-precedence test).

---

## 1.3.19 — 2026-06-02

Closes Bug 4 (parallel-extraction fork-after-state-init deadlock from the Teton field session). No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade, no extractor-shape changes — output is byte-identical to 1.3.18 between serial and parallel modes.

Parallel code-file extraction now uses the `spawn` multiprocessing start method instead of `fork`. The fork hazard the 1.3.14 release notes called out — `fork()` on macOS after the parent has initialized tree-sitter C extension state (and possibly objc/Foundation runtime via transitive imports) leaves child processes with inconsistent mutex state and deadlocks on first synchronization-primitive use — is avoided entirely because spawn boots a fresh interpreter per worker with zero inherited state.

The non-obvious detail: `multiprocessing/spawn._main` calls `pickle.load(from_parent)` to deserialize the worker's bootstrap state *before* any user-defined `initializer` fires. The pickled state references `graph_indexer._extract_artifact_for_worker` by module name, so the worker needs to be able to `__import__("graph_indexer")` at bootstrap time. Multiprocessing/spawn serializes the parent's `sys.path` (not `PYTHONPATH`) into the bootstrap pickle, so the fix is: insert the directory containing `graph_indexer.py` into the parent's `sys.path` before pool construction (and remove it on exit). The worker initializer is preserved as defense-in-depth re-registration in `sys.modules`.

`WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` default stays at `1` (set in 1.3.18). Operators on large monorepos opt in via `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS=4` (or higher). On the wavefoundry framework's 40-file scripts directory, spawn-mode parallel is ~5–6× slower than serial because spawn per-worker startup cost (~500ms–1s × workers) exceeds the per-file work — exactly why workers=1 is the right default for small projects. Teton-scale 1,360-file workloads invert that math; serial extraction there takes long enough that 4 spawn workers amortize the boot cost.

The `WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD` env var escape hatch is preserved for operators who want to opt back to `fork` (or try `forkserver`) at their own risk.

Removed: `_prewarm_declared_names_cache`. The pre-fork warmup made sense only under fork (workers inherited the populated cache via copy-on-write). Spawn workers boot from zero state, so the warmup did no work; keeping the dead code would mislead future maintainers.

Verified: 2255 framework tests pass (net +4 over 1.3.18). New tests:

- `test_parallel_branch_end_to_end_with_real_spawn_workers` — spawns 2 real workers against a 4-file fixture, asserts byte-identical output vs. serial path
- `test_parallel_branch_wires_spawn_and_initializer` — verifies the `ProcessPoolExecutor` is constructed with spawn `mp_context` and the worker initializer
- `test_worker_initializer_registers_graph_indexer_in_sys_modules` — direct test of the initializer's side effect
- `test_worker_initializer_swallows_failures_silently` — initializer must not raise out of worker startup on bad paths

---

## 1.3.18 — 2026-06-02

Defensive default change in response to Teton field reproducer. No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade, no extractor-shape changes.

**Parallel code-file extraction is now default-off.** The `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` env var still controls worker count, but the default is now `1` (serial) instead of `min(cpu_count, 4)`. Operators who saw the 2.35× speedup on 1.3.14–1.3.17 and want to keep it can set `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS=4` (or whatever value suits their box).

Why: Teton reproduced 3-of-3 a deterministic fork-after-state-init deadlock on a 1,360-TS/JS-file Nx monorepo. Symptom: parent prints `pre-warmed declared-names cache for N TS/JS files`, then all 4 workers + the coordinator + the launcher sit at 0.0% CPU with no further log output, indefinitely. This matches the macOS fork() hazard called out in the 1.3.14 release notes as "main remaining headroom" — fork()ing after tree-sitter C extension state (and possibly objc/Foundation init from transitive imports) is initialized in the parent leaves the children in an inconsistent state that deadlocks on first synchronization. Reproducer threshold: parallel mode (>100 code files) + workers > 1. Scope: 1.3.14 through 1.3.17 (parallel-extraction-on-by-default); fully avoided on 1.3.18 with the new default.

Real fix (not in this release): wire `spawn` start method properly by installing a worker initializer that loads `graph_indexer.py` via `spec_from_file_location` and registers it in `sys.modules` before unpickled tasks try to deserialize a function reference back to it. The 1.3.14 release picked `fork` to avoid this initializer plumbing; the Teton deadlock makes the initializer the cleaner path even though it adds a few lines.

Verified: 2251 framework tests pass (no regression — none of the test fixtures exceed the 100-file threshold so all framework tests were serial-path even before this default change).

---

## 1.3.17 — 2026-06-02

Operational-polish patch on 1.3.16. No `GRAPH_BUILDER_VERSION` bump, no auto-rebuild on upgrade, no extractor-shape changes — output is identical to 1.3.16.

Three index-build / auto-rebuild defects fixed together because they form one user-visible failure mode (Teton field session, post v22→v23 upgrade):

- **`wave_index_build` no longer returns misleading success when the spawned subprocess fails to acquire the lock.** `run_index_rebuild` now polls `proc.poll()` for a brief verification window (1.5s default, configurable via `_INDEX_BUILD_VERIFY_TIMEOUT_SECONDS`) after Popen. If the subprocess exits inside the window with a non-zero code, the response returns `passed: false`, `build_failed_early: true`, sets `graph_rebuilt: false`, and surfaces a `build_skipped_lock_busy` diagnostic carrying the lock-holder PID. `wave_index_build_response` also skips cache invalidation and the post-rebuild MCP resource dispatch on the early-exit path so downstream consumers see consistent state.
- **`_index_build_lock` proactively unlinks stale lock-file metadata before attempting `flock()`.** When `classify_index_build_lock_owner` returns `"stale"` (recorded PID is dead) and the lock file exists, `lock_path.unlink()` runs ahead of the `open()`. Downstream tools that read the metadata file (status surfaces, diagnostic messages) now see fresh post-acquire content instead of the legacy dead-PID metadata. Unlink races are handled (POSIX `unlink` doesn't affect file descriptors already open in other processes; `FileNotFoundError` is caught).
- **`_ensure_graph_builder_current` coordinates concurrent auto-rebuild attempts within a single MCP server process.** A module-level `_VERSION_REBUILD_INFLIGHT` dict keyed on `(root, layer)` and guarded by `_VERSION_REBUILD_INFLIGHT_LOCK` records the start time of any in-flight rebuild. Concurrent callers that detect the same builder-version mismatch and see the marker return a `graph_auto_rebuild_in_progress` diagnostic (with `rebuild_started_at_age_seconds`) instead of racing for the index-build flock and emitting the noisy `graph_auto_rebuild_failed` spam Teton observed. The marker is released on every exit path (success, failure, unhandled exception) via `try/finally`. A 120s stale-inflight safety net (`_INFLIGHT_REBUILD_STALE_SECONDS`) prevents a crashed rebuild from pinning the marker indefinitely.

Verified: 2251 framework tests pass (was 2246 — net +5 regression tests):

- `test_stale_lock_file_is_unlinked_before_acquire` (Bug 1 / AC-3)
- `test_subprocess_early_exit_with_lock_busy_surfaces_failure` (Bug 2 / AC-1)
- `test_concurrent_auto_rebuild_defers_via_inflight_marker` (Bug 3 / AC-4)
- `test_stale_inflight_marker_allows_fresh_rebuild_attempt` (Bug 3 / AC-5)
- `test_inflight_marker_released_on_success_and_failure` (Bug 3 / safety net for the in-flight marker)

---

## 1.3.16 — 2026-06-02

**Operator action required.** `GRAPH_BUILDER_VERSION` bumps 22 → 23 — every consumer project rebuilds its graph index on next `wave_index_build` / next MCP-server warmup after upgrade. Rebuild duration scales with code volume (small projects ≈ seconds; Teton-scale 12k-node Nx monorepos ≈ 60–90s). **Affects TypeScript and JavaScript only** — other languages produce byte-identical output to 1.3.15.

What changes in the graph: TS/JS call edges that previously landed as `EXTRACTED` despite the indexer having bound the target deterministically now land as `RECEIVER_RESOLVED`. Two specific paths get the upgrade:

- **Intra-file (and locally-defined) bare-identifier calls.** When `_ts_resolve_target` returns a project-internal node directly — covering intra-file arrow-const callers like `getRootToken()` referenced from a sibling function in the same file — the binding came from `symbol_lookup` (exact name match in the file's own definition table). Pre-1.3.16 tagged these `EXTRACTED`. They are high-confidence by construction.
- **Cross-file bare-identifier calls with unambiguous project-wide match.** The cross-file rewrite pass's AC-1 branch (bare simple name in `simple_name_index` with exactly one candidate) now promotes the rewritten edge from `EXTRACTED` to `RECEIVER_RESOLVED` when the source file is TS/JS. AC-2 (qualified-target simple-name fallback for shapes like `obj.method()` where `obj` is unannotated) intentionally remains `EXTRACTED` because that branch is a type guess, not a deterministic bind.

Field signal that drove the fix: Teton's `getRootToken` had 5 incoming intra-file callers all landing as `EXTRACTED` on v22, invisible to `attribution_counts_by_language["typescript"]["receiver_resolved"]`. The total TS resolved-share sat at 8.3% (3,083 receiver_resolved + 810 construction_resolved / 47,034 attributed). The intra-file bucket alone is likely the largest single source of misclassified-confidence edges on arrow-const-heavy codebases.

Out of scope this round: cross-file qualified-target rewrites (the AC-2 simple-name fallback) and non-TS/JS languages. Field data after this rebuild will indicate whether a follow-up promotion is warranted for those paths.

Verified: 2246 framework tests pass, including 2 new regression tests — `test_intra_file_arrow_const_call_lands_receiver_resolved` covers the intra-file path, `test_cross_file_unique_simple_name_call_lands_receiver_resolved` covers the AC-1 cross-file path.

---

## 1.3.15 — 2026-06-02

Pure performance patch on 1.3.14. **No extractor-shape changes, no `GRAPH_BUILDER_VERSION` bump, no auto-rebuild needed on upgrade.** Output is byte-for-byte identical to 1.3.14.

Two changes target walker overhead and cross-worker cache reuse:

- **Single-pass walker.** The tree-sitter extractor previously walked each file's AST twice — once for definitions, once for calls — duplicating tree-descent overhead. `walk_definitions` now registers definitions inline AND buffers call sites; post-walk, a flat traversal over the buffered list resolves and emits call edges using the now-complete symbol lookup. The full call-resolution pipeline (`CONSTRUCTION_RESOLVED` first, then per-language receiver-type resolution, then `_ts_relation_candidates` with `EXTRACTED`-to-`RECEIVER_RESOLVED` promotion via `import_targets`) runs per buffered call exactly as before. Reduces per-file walker wall-time materially on large source files (the walker hot path was the dominant cost after the 1.3.12-1.3.14 cache/parallelism work).
- **Pre-fork declared-names cache warmup.** Parallel extraction now populates `_TS_FILE_DECLARED_NAMES_CACHE` in the parent process for every TS/JS file in the batch before forking. Workers inherit the populated cache via copy-on-write, so the barrel-export walker hits cache on cross-file lookups instead of each worker re-running the declared-names regex pass per file independently. Closes the "no cross-worker cache sharing" caveat called out in 1.3.14.

Verified: 2244 tests pass; all 212 graph_indexer tests including the construction-resolved, receiver-resolved, and overload self-edge classification suites unchanged.

---

## 1.3.14 — 2026-06-02

Pure performance patch on 1.3.13. **No extractor-shape changes, no `GRAPH_BUILDER_VERSION` bump, no auto-rebuild needed on upgrade.**

Graph extraction now parallelizes code-file processing across CPU cores when the build is large enough to amortize fork overhead. On a benchmark of 200 TS files (~160 lines each with classes, interfaces, arrow-const functions, type aliases) the parallel path runs at **2.35× the speed of serial** (19.8s → 8.4s on a 4-worker M-series Mac). Real-world repos at Teton-scale (1500+ files) should see similar or better speedup because per-file work scales superlinearly with file complexity. Identical nodes and edges to serial — verified end-to-end.

Design choices:

- **Threshold-gated** at 100 code files (configurable via `WAVEFOUNDRY_GRAPH_PARALLEL_THRESHOLD` env var). Small builds (tests, incremental updates) stay serial because the per-worker fork startup cost would exceed the parallelism gain
- **Default 4 workers, capped at CPU count** (configurable via `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS`). Operators with more cores can tune up; CI environments with constrained cores can tune down or disable by setting workers to 1
- **`fork` start method** chosen because graph_indexer is loaded via `spec_from_file_location` in production (not the standard import system); fork workers inherit the parent's `sys.modules` so the worker function reference resolves cleanly without import gymnastics. macOS emits a `DeprecationWarning` about fork which we silence — our parent is single-threaded synchronous Python so the risk fork addresses (objc/threaded state) doesn't apply. Operators can opt back to `spawn` or `forkserver` via `WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD` env var
- **Graceful fallback to serial** on any pool failure — the build always completes
- **Doc/seed extraction stays serial** because it depends on cross-file `symbol_terms` built across all artifacts (not embarrassingly parallel like per-file code extraction)
- **Pre-loads `.gitattributes`** in the parent so each worker doesn't re-read it. Cache (`_TS_BARREL_PARSE_CACHE`, lru caches on probe / relative-resolve) warms per-worker independently — there's no cross-worker cache sharing, which is the main remaining headroom for future optimization

---

## 1.3.13 — 2026-06-02

Pure performance patch on 1.3.12 — no extractor-shape changes, no `GRAPH_BUILDER_VERSION` bump, no auto-rebuild needed on upgrade.

Path-resolution helpers (`_probe_ts_alias_target`, `_resolve_relative_ts_import`) are pure functions of `(args, filesystem state)`. On barrel-export-heavy codebases, each unique import specifier is hit dozens of times during a build (once per caller) — without caching, every hit re-runs the path probe and its associated `is_file()` syscalls. `functools.lru_cache(maxsize=20000)` turns repeated calls into O(1) lookups within a build. Caches survive across builds within a single MCP server process; LRU eviction handles size naturally, and stale-result risk is low because deleted files don't appear in the per-build file list.

Builds on barrel-heavy TS/JS monorepos (Teton-shape) should see additional wall-time reduction beyond the 1.3.12 file-declared-names cache. Test suite wall-time unchanged because each test uses a unique tmp directory so caches rarely hit on tiny build calls — the gains are workload-dependent.

---

## 1.3.12 — 2026-06-02

> **Operator-action note: graph builder version bumped 21 → 22.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical projects; ~50–60s on 12k-node monorepos with this release's perf fix; previously ~80s).
>
> Affects **TypeScript and JavaScript only**, and the impact on attribution counts is substantial. Repos that use **relative imports for intra-package calls** to **arrow-const-bound functions** (the modern Lambda + Nx + Node.js pattern) should see `attribution_counts_by_language["typescript"]["receiver_resolved"]` rise materially after the rebuild. The 1.3.11 release added the function nodes for arrow-const declarations but couldn't attribute calls to them as RECEIVER_RESOLVED when the caller used a relative import (`import { x } from './events'`) because the relative-path prefix was lost in the resolver pipeline. This release closes that gap.
>
> Also: rebuild time on barrel-export-heavy codebases drops materially (Teton-shape projects: 79s → ~50s estimated) because barrel walking now caches per-file declaration sets instead of re-reading destination files on every name lookup.

Same-day continuation of the v21 arrow-const work. Teton field validation on 1.3.11 confirmed all three smoke targets resolve and total TS edges grew 26% — but +9,379 of the new edges landed as `EXTRACTED` rather than `RECEIVER_RESOLVED` because intra-package callers using relative imports went through a code path that lost the relative-path prefix at `_ts_clean_name` time. The fix: extract the raw module specifier before cleaning, then branch on relative vs alias resolution. Plus the perf fix the barrel walker needed.

### Changes

- Bump `GRAPH_BUILDER_VERSION` 21 → 22. See the operator-action note above
- Extract the raw module specifier from import statements with `./` / `../` / `/` / `@scope/` prefixes preserved. The existing `_ts_relation_candidates → _ts_clean_name` path stripped relative prefixes (`./events` → `events`), so the resolver couldn't tell relative imports apart from bare names. New `_ts_extract_import_module_specifier` helper reads the raw text from the import statement's `source` field
- Resolve relative imports against the source file's directory before the tsconfig.paths fallback. `import { x } from './events'` now resolves to the actual project file via `_resolve_relative_ts_import`, runs through the same barrel walker, and populates `import_targets` with the walked-through definition file. Direct calls to those imports promote to `RECEIVER_RESOLVED`
- Cache per-file top-level declaration sets keyed on `(path, mtime)`. `_file_declares_name` now reads through `_file_declared_names` which parses each destination file at most once per build. Eliminates the redundant file-read + regex-run loop in `_resolve_through_barrel` — for barrel-export-heavy codebases this is the dominant hot path

---

## 1.3.11 — 2026-06-02

> **Operator-action note: graph builder version bumped 20 → 21.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical projects; ~70–90s on 12k-node monorepos). The 131e2 safety net handles this automatically.
>
> Affects **TypeScript and JavaScript only**, and the impact is large on modern codebases. Repos that define functions as `export const foo = async (args) => { ... }` (arrow-const, the dominant shape in TS Lambda / Nx / React layouts) should see `attribution_counts_by_language["typescript"]["receiver_resolved"]` rise materially — Teton's field validation estimates 6% → 30–60% on the canonical Nx + Lambda shape because arrow-const previously didn't register as a graph node at all. Repos using `function foo()` declarations exclusively should see no change. Repos in other stacks rebuild but their attribution numbers shouldn't shift.

Same-day post-ship correction on 1.3.10. Teton confirmed v19 → v20 worked end-to-end — TS receiver-resolved share jumped 4.3% → 6.0% with +641 RECEIVER_RESOLVED edges as an exact migration. But three smoke-test symbols still returned `graph_symbol_not_found` with a sharp diagnostic: every backend function in their codebase is `export const X = async (...) => { ... }` (zero hits on `^function ` or `^export function `). The arrow-const shape parses as `lexical_declaration → variable_declarator → arrow_function` in tree-sitter, and our extractor never descended through `variable_declarator` to find the identifier — so the symbol never registered as a graph node.

### Changes

- Bump `GRAPH_BUILDER_VERSION` 20 → 21. See the operator-action note above
- Register arrow-function-bound and function-expression-bound `const` declarations as function symbols. Detects `lexical_declaration` / `variable_statement` nodes whose child `variable_declarator` binds an `arrow_function` or `function_expression`, registers each as kind `function` (not `variable`), and walks scope through the arrow body so calls FROM inside arrow-const-bound functions attribute to the const name rather than the file. Covers both registration (`walk_definitions`) and edge-source attribution (`walk_calls`). This is the load-bearing change for the dominant function shape in modern TS — particularly Lambda + Nx layouts where free-function arrow-const is virtually the only pattern. End-to-end verified on the barrel + aliased-import + arrow-const stack: `caller → libs/utils/src/lib/http-request.ts::httpRequester` lands `RECEIVER_RESOLVED` regardless of whether either side uses `function` or arrow-const

---

## 1.3.10 — 2026-06-02

> **Operator-action note: graph builder version bumped 19 → 20.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical projects; ~70s on 12k-node monorepos). The 131e2 safety net handles this automatically.
>
> Affects **TypeScript and JavaScript only.** Repos on barrel-export-heavy library layouts where most imports are **free functions** (not methods on classes) should see `attribution_counts_by_language["typescript"]["receiver_resolved"]` rise materially after the rebuild — Teton-shape codebases were the motivating case. Repos in other stacks rebuild but their attribution numbers shouldn't shift.

Same-day post-ship correction on 1.3.9, motivated by Teton field validation that confirmed three things at once: the v18 → v19 bump fired correctly and community structure shifted (proving the leading-`@` fix + tsconfig.paths now work end-to-end), but attribution numbers stayed byte-identical at 4.3% and community labels regressed to generic `"src/index N"`. Root cause for the unchanged attribution: 1.3.9's barrel walker only fired on method calls (`obj.method()`), not direct function calls (`func()`) — and most aliased imports on real Nx codebases are free functions, not class methods.

### Changes

- Bump `GRAPH_BUILDER_VERSION` 19 → 20. See the operator-action note above
- Promote direct-function-call edges through `import_targets` to `RECEIVER_RESOLVED`. When the call resolves to `external::<name>` AND `import_targets` carries a walked-through definition file for that bare name, the edge target is rewritten to `<definition_file>::<name>` and confidence rises from `EXTRACTED` to `RECEIVER_RESOLVED`. This is the load-bearing fix for the persistent 4.3% TS-resolved rate on barrel-export-heavy monorepos: most aliased imports on those layouts are free functions
- Bundler-mode `.js` / `.jsx` / `.mjs` / `.cjs` → `.ts` / `.tsx` / `.mts` / `.cts` extension swap in `_probe_ts_alias_target`. TS 5.x's `moduleResolution: "Bundler"` (Vite / esbuild / Nx defaults) allows source code to write `./foo.js` and resolve to `./foo.ts` at compile time. Barrel re-exports written this way now walk through correctly
- Community-label seed selector deprioritizes barrel files (`index.{ts,tsx,js,jsx,mjs,cjs,mts,cts}`). Barrels accumulate high in-degree once aliased imports resolve to them; without deprioritization Leiden picks barrels as seeds and meaningful labels collapse to generic `"src/index N"`. Barrels still get the seed when they're the only candidate in a community. `hub_node_id` unchanged so operators caching by stable-reference contract are unaffected

---

## 1.3.9 — 2026-06-02

> **Operator-action note: graph builder version bumped 18 → 19.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical projects). The 131e2 safety net handles this automatically — no operator step required — but the rebuild pause is real.
>
> Affects **TypeScript and JavaScript only.** Repos in other stacks (Java, Python, Swift, etc.) will rebuild but their attribution numbers should not shift. Consumer projects on barrel-export-heavy library layouts (the dominant Nx pattern: every package's `src/index.ts` re-exports from `./lib/<name>`) should see their `attribution_counts_by_language["typescript"]["receiver_resolved"]` count rise materially after the rebuild — that's the load-bearing change.

Round-7 field-feedback patch on 1.3.8, motivated by Teton's configuration supplement on the persistent 4.3% TS receiver-resolved rate. The supplement identified barrel re-export following as the missing primitive; implementing it surfaced a second latent bug in `_ts_clean_name` that was the actual root cause of every scoped-import resolution failing across 1.3.6 / 1.3.7 / 1.3.8.

### Changes

- Bump `GRAPH_BUILDER_VERSION` 18 → 19. See the operator-action note above
- Follow barrel re-exports during TS/JS import resolution. tsconfig.paths aliases on Nx-shaped monorepos point at `src/index.ts` files that re-export from `./lib/<name>`. The receiver-type resolver now walks the re-export chain (`export { Foo } from './path'`, `export { Foo as Bar } from './path'`, `export { default as Foo } from './path'`, `export * from './path'`) until it reaches the actual definition file. `import_targets[name]` points at the definition file rather than the barrel index, so cross-package call edges land with per-symbol granularity instead of collapsing onto N hub nodes
- Preserve a leading `@` in `_ts_clean_name`. The helper was stripping the `@` prefix from scoped specifiers (`@aceiss/hooks` → `aceiss/hooks`) before any downstream consumer saw them, so tsconfig.paths patterns whose keys start with `@` never matched. Every npm scoped package (`@aws-sdk/*`, `@nestjs/*`, `@nx/*`, `@scope/*`) was silently mangled. This is the load-bearing root cause of Teton's 4.3% rate persisting across 1.3.6 / 1.3.7 / 1.3.8 — our 1p2tf code was structurally correct but never saw a specifier the alias map could match. Fix surfaced during 1p2tz barrel-resolver implementation; both fixes ship together
- Per-file barrel-parse cache keyed on `(path, mtime)` so each barrel file is parsed at most once per build. Recursion bound at 5 hops with cycle-set detection on resolved paths
- Alias collision handled correctly: when two aliases point at the same physical file (Teton's `@aceiss/hooks` and `@teton/hooks` both → `libs/hooks/src/index.ts`), both resolve through the same barrel chain to the same definition file with no duplicate edges

---

## 1.3.8 — 2026-06-02

> **Operator-action note: graph builder version bumped 17 → 18.** First MCP query against the graph layer after upgrade will trigger a one-time synchronous rebuild (~10–30s on typical project sizes). The 131e2 safety net handles this automatically — no operator step required — but the rebuild pause is real. Operators wanting to amortize it explicitly can run `wave_index_build(content='graph')` before their first query session.
>
> The bump invalidates consumer caches for extractor-shape changes shipped in 1.3.5 / 1.3.7 that previously couldn't take effect against pre-1.3.8 graphs: `.gen.ts` / `.generated.ts` JS-TS generated-file classifier (1p2q9 C), cross-file receiver-type resolution via tsconfig.paths-resolved imports (1p2tf), and `self_edge_kind` edge tagging on overloadable-language self-edges (1p2td). Affects all extracted languages — Java / Kotlin / C# / Swift / Scala / C++ for the overload tagging, TypeScript / JavaScript for the receiver-type and classifier changes.

Same-day patch on 1.3.7 covering three corrections surfaced by post-ship field validation: the builder-version bump above (the load-bearing change), a `self_edge_kind` propagation gap in `code_callhierarchy` entries, and a reconsidered seed-emit that turned out to be duplicate-of-code-defaults noise.

### Changes

- Bump `GRAPH_BUILDER_VERSION` from `17` to `18`. See the operator-action note above for the operational impact; without this bump, the extractor-shape changes shipped in 1.3.5 and 1.3.7 cannot take effect on existing consumer projects because the auto-rebuild only fires when state version mismatches runtime
- Propagate edge `self_edge_kind` to the `outgoing` and `incoming` entries returned by `code_callhierarchy`. The entry constructor reads the target/source node and was discarding the edge's overload-classification metadata before the response was assembled — consumers reading the list saw plain entries with no field. Now the field passes through; recursion / overload_forwarding / unknown surfaces alongside the call entry
- Drop the `code_navigation_hints` block emission from the install seed and the upgrade-time backfill rule. The block was pure duplication of code defaults — the resolver already falls back to `["return", "throw", "raise", "guard", "assert"]` when the key is absent — so emitting it added noise without functional effect. Operators tuning guard tokens still find the schema in seed-211; the workflow-config skeleton stays clean

---

## 1.3.7 — 2026-06-02

Round-5 field-feedback patch covering Teton's TypeScript receiver-resolution gap, javaagent's overload self-edge ambiguity, the workflow-config navigation-hints discoverability gap, and a long-standing self-hosting prune-safety bug that was silently deleting framework test files on every release.

### Changes

- Bridge tsconfig.paths-resolved imports into TypeScript / JavaScript receiver-type resolution. The 1.3.6 import-aliasing fix made `imports` edges bind to project files but the receiver-type resolver never consulted that map, so calls on imported types still fell through to `external::*`. Per-file `import_targets` is now populated at import-edge emission and consulted by `_resolve_ts_call_target` after the local symbol-lookup miss — aliased cross-package types resolve to project nodes with `RECEIVER_RESOLVED` confidence. Closes Teton's 4.3% type-resolved rate on strict-TS Nx monorepos
- Detect Nx project structure (`nx.json` at repo root) and surface as a diagnostic field on graph payloads. Wiring scaffolds future Nx-aware resolver passes; the detection alone enables operator-side reasoning about per-codebase resolution quality
- Tag `calls` self-edges on overloadable languages (Swift / Java / Kotlin / C# / Scala / C++) with `self_edge_kind`: `recursion`, `overload_forwarding`, or `unknown`. The per-file qname merge that collapses overloads into one node previously made every overload-forwarding call indistinguishable from recursion. Per-language signature extractors (Swift label fingerprints; arity for the positional languages) plus walker scope tracking plus an explicit classifier let consumers tell the two apart. Merged nodes carry `param_signatures` listing every overload's signature
- Emit a `code_navigation_hints` block with the language-default `guard_tokens` array in the workflow-config skeleton at install time, plus a backfill rule in the upgrade seed (never overwrites operator tuning). Operators tuning guard tokens see the schema in context instead of constructing the block from scratch after reading seed-211
- Remove the legacy fallback from `prune_framework.py`. The list was unconditionally deleting `scripts/tests/` and `scripts/run_tests.py` on every self-hosted upgrade because `build_pack.py` deletes `MANIFEST` after writing it into the zip, leaving `upgrade-wavefoundry` without an old manifest to diff against. No-old-manifest now logs a skip notice and returns — diff-based prune remains the only deletion path

---

## 1.3.6 — 2026-06-02

Continuation of wave 1p2q3 — completes the Nx TypeScript graph-extraction work, adds the per-language attribution diagnostic, redesigns the dashboard node-kind palette, and applies the dashboard flicker fix. Pairs with 1.3.5; field validation can run against either build.

### Changes

- Honor `tsconfig.json` / `tsconfig.base.json` `paths` aliases in TypeScript/JavaScript import resolution so Nx-style `@scope/lib` imports bind to the real project node id instead of dropping to `external::*`. Walks file directory upward to find the nearest tsconfig with `paths`; caches per-tsconfig; JSONC-aware parser preserves `//` inside string literals so URL strings and path patterns survive
- Add `attribution_counts_by_language` field to `code_callhierarchy`, `code_impact`, `code_definition`, and `wave_graph_report` responses. Shape: `{language: {receiver_resolved, construction_resolved, extracted}}` computed from the edges surfaced in the response. Operators can spot per-language coverage gaps at a glance (e.g. `{typescript: {receiver_resolved: 0, extracted: 3892}}` flags a resolver that isn't engaging)
- Rewrite the empty-graph-result fallback rule in `seed-211`, `code-reviewer.md`, `security-reviewer.md`, `architecture-reviewer.md` from a static less-mature-language list to a response-shape condition: if `code_callhierarchy` / `code_impact` returns empty AND `code_references` returns hits, treat the empty graph result as a coverage gap regardless of language
- Redesign dashboard node-kind palette for pairwise-distinct hues across all 10 kinds: add `variable` (vivid red), collapse `seed` into the `doc` bucket (seeds are markdown prompts — semantically documents), shift `external` from neutral grey to light blue-grey so it no longer reads as a pair with `doc` charcoal, shift `community` to emerald and `package` to bright cyan so they part visually, shift `namespace` to magenta so it parts from `class`
- Eliminate the dashboard graph-refresh flicker: gate the "Loading graph…" banner on initial load only, short-circuit `setGraph` when the incoming snapshot signature matches the prior, preserve operator selection across refreshes when the selected node still exists

---

## 1.3.5 — 2026-06-02

Round-4 field-feedback patch covering Aceiss's spurious-path report on `code_graph_path`, Teton's TypeScript/Nx-monorepo coverage gaps, an MCP cache-invalidation gap on graph rebuilds, and consumer-project pollution from framework-scripts indexing.

### Changes

- Rewrite `code_graph_path` shortest-path search as a weighted Dijkstra: `calls`/`RECEIVER_RESOLVED`=1, `calls`/`EXTRACTED`=2, structural=100. Treat `external::*` nodes as non-transitive intermediates — they remain valid endpoints but cannot bridge two real symbols, eliminating the spurious 2-hop paths that masked direct call chains. Add `min_confidence` parameter and `path_is_structural` diagnostic
- Mirror `code_callhierarchy`'s `suggestions` array in `code_definition`'s not-found response so operators get near-symbol candidates via the same shape across both tools
- Extend generated-code classifier to recognize `*.gen.{ts,tsx,js,jsx}`, `*.generated.{ts,tsx,js,jsx}`, `__generated__/`, and `.generated/` JS/TS conventions (e.g., TanStack Router, GraphQL Code Generator)
- Add `heuristic_import_no_matches` diagnostic on `code_impact(path=...)` for TS when path-mode resolves to no graph matches, distinguishing "no callers" from "import-resolver gap"
- Rewrite seed-211 fallback rule from a static language list to a response-shape condition so new languages benefit without seed edits
- Exclude the entire `.wavefoundry/` folder from graph indexing in downstream consumer projects so wavefoundry's own framework scripts no longer pollute consumer-project graphs (escape-hatched via `project_include_prefixes.code` for this self-hosting repo)
- Dispatch `notifications/resources/updated` for `wavefoundry://graph/*` URIs after auto-rebuild and after explicit `wave_index_build(content='graph')` so spec-conformant MCP clients invalidate cached graph-resource reads without operator action
- Add distinct dashboard node-kind colors for `package` and `namespace` so directory-aggregated package nodes are no longer indistinguishable from `external::*` greys

---

## 1.3.4 — 2026-06-01

Lifecycle-ID and build-suffix encoding rewrite. The prior scheme appended `BASE36[elapsed_minutes % 36]` as the 5th char of the lifecycle prefix and took the rightmost 4 chars as the build suffix — both wrapped every 36 minutes, causing lex order to disagree with wall-clock order. Three same-day 1.3.2 builds shipped within 27 minutes demonstrated the failure (`upgrade_wavefoundry` lex-selected the oldest one).

### Changes

- Replace lifecycle prefix encoding with integer-packed `(days_since_epoch * 288 + bucket_5min) mod 36^5`, base36 right-padded to 5 chars. 5-minute buckets (288/day) align cleanly with whole-minute AND whole-second boundaries and divide 36^5 with zero wasted slots. Lex order matches wall-clock within a 209,952-day (~575-year) horizon
- Build suffix is now the last 4 chars of the lifecycle prefix — single source of truth. Last-4-chars truncation is mathematically equivalent to packing with `mod 36^4`, giving a 5,832-day (~15.97-year) lex-monotonic horizon
- Shift project epoch from `2020-08-24` to `1999-05-01` so today's first new ID under the integer-packed scheme lex-sorts past the historical max real ID (`1p0r6` at 2,846,994). New IDs today begin at `1p2g0`
- Update `docs/workflow-config.json` lifecycle_id_policy: new `epoch_utc`, new `time_unit: "5-minute-bucket"`, new `buckets_per_day: 288`, expanded `notes` documenting the encoding

---

## 1.3.3 — 2026-06-01

Same-day patch covering description-refresh propagation, two graph-query polish fixes, and the wave 131bu close-out. Bumped from 1.3.2 because semver comparison strips build metadata; a same-version republish would have been invisible to `wave_upgrade` and left operators stuck on the prior build.

### Changes

- Detect tool-description changes during `wave_mcp_reload` and explicitly send the MCP `notifications/tools/list_changed` protocol notification so conformant clients re-fetch and surface the new descriptions automatically (FastMCP's `add_tool`/`remove_tool` do not send this automatically); response carries `description_changed_tools` + `tool_list_changed_notification_sent`; structured diagnostic explains success or failure path
- Alias `<file_id>::<class_name>` queries to the file id when the file is a class/module-merged node — operators querying with explicit qualification no longer hit `graph_symbol_not_found` for merged classes
- Tie-break `code_graph_path` BFS candidates on confidence: `RECEIVER_RESOLVED` / `CONSTRUCTION_RESOLVED` paths surface before `EXTRACTED` import placeholders when both reach the destination in the same hop count
- Update `seed-160` upgrade workflow to document the notification-based description-refresh path (no operator action required when conformant clients honor `tools/list_changed`; full restart remains the fallback when they don't)

---

## 1.3.2 — 2026-06-01

Patch on 1.3.1's ERROR-wrapped class declaration recovery. Field validation against the actual Solaris repository showed 1.3.1's recovery predicate accepted only `type_identifier` children — tree-sitter-swift's grammar-recovery state emits the class name as `simple_identifier` in practice, so the predicate silently missed every production ERROR-wrapped class. The graph rebuilds automatically on the first query after upgrade.

### Changes

- Broaden ERROR-wrapped class recovery predicate to accept `simple_identifier` and `identifier` children alongside `type_identifier` (tree-sitter grammars relabel the class-name node kind in their recovery state)
- Add child-text name-match as the second gate replacing the prior child-kind-presence-only check — keeps false-positive surface narrow even with the broader child-kind acceptance
- Extend recovery source-text prefix slice from 256 to 512 bytes to cover ERROR nodes whose modifier prefix runs longer than the prior bound

---

## 1.3.1 — 2026-06-01

Field-feedback patch covering one Swift attribution edge case and one cross-tool documentation gap. The graph rebuilds automatically on the first query after upgrade.

### Changes

- Recover ERROR-wrapped top-level class declarations in graph-builder definition walk so cross-file construction edges still resolve when tree-sitter wraps a class declaration in ERROR due to a parse failure deep in the class body (Swift, Kotlin, Scala, Java, C# — file-level-type languages)
- Document `CONSTRUCTION_RESOLVED` confidence value on `code_impact` response shape alongside `RECEIVER_RESOLVED` and `EXTRACTED`

Full per-change docs: `docs/waves/131bt field-feedback-round-3/1319v-bug error-wrapped-class-declaration-recovery.md` in the wavefoundry repository.

---

## 1.3.0 — 2026-06-01

Cross-language graph-builder precision improvements, new query-time aggregation, and upgrade-lifecycle automation. The graph rebuilds automatically on the first query after upgrade; MCP tool descriptions and parameter signatures refresh via `wave_mcp_reload` followed by a client reconnect (`/mcp` in Claude Code).

### Changes

- Resolve receiver types via type annotations in TypeScript, Python, PHP, and JavaScript (JSDoc); annotated declarations route to the correct method node, unannotated falls back to standard attribution
- Route construction-call edges to the class node across 11 languages: `new Foo()` in Java/C#/TypeScript/JavaScript/PHP, bare-call `Foo()` in Swift/Python/Kotlin/Scala, `Foo.new` in Ruby, struct-literal `Foo { x: 1 }` and `Foo::new()` in Rust, composite-literal `&Foo{}` and `new(Foo)` in Go
- Add `CONSTRUCTION_RESOLVED` confidence tag on construction-routed edges, peer-level to `RECEIVER_RESOLVED`
- Extend single-dominant-class merge to Python, JavaScript, TypeScript with dominance gate; add kebab-to-PascalCase basename matching for JS/TS
- Add `collapse_package_to_directory: bool` parameter to `wave_graph_report` covering Go, Python, Java, Kotlin, C#, Scala, PHP, Swift; produces `package` / `namespace` nodes per language idiom
- Hot-reload MCP tool schemas via `wave_mcp_reload`; parameter and description changes land in-process without a server restart
- Auto-rebuild stale graph synchronously on first query when the on-disk builder version is behind runtime; structured `graph_auto_rebuilt` diagnostic surfaces in the response
- Sync MCP tool descriptions for `wave_index_build`, `wave_index_health`, `wave_graph_report`, `code_impact`, `code_callhierarchy`, `code_graph_community` with shipped capabilities; restructure related seed-211 guidance
- Document client-side confidence filtering for refactor-safety and security-review workflows
- Rename release notes to `CHANGELOG.md` and relocate to `.wavefoundry/CHANGELOG.md` (project-level path; upgrade prunes the old `.wavefoundry/framework/RELEASE_NOTES.md` automatically); cumulative narrative format, no build-number structure, deliberately not Keep-a-Changelog

Full per-change docs: `docs/waves/131bt field-feedback-round-3/` in the wavefoundry repository.

---

## 1.2.1 — 2026-06-01

Operator field-feedback follow-on across two iteration rounds. Eliminate phantom call edges at index time, decompose collision diagnostics, broaden cross-language coverage for class/module merge and receiver-type resolution.

### Action required on upgrade

Rebuild the graph index once after upgrade: `wave_index_build(content='graph')`.

### Changes

- Move Java receiver-type resolution into the graph builder; eliminate phantom `calls` edges at index construction time so `code_impact` and `code_callhierarchy` return consistent results
- Decompose `name_collision_count` into `same_name_node_count`, `cross_file_collision: bool`, and `external_name_collision_count` (deprecated alias preserved one release)
- Curate per-language stdlib allowlist for `external_name_collision_count` across Java, C#, Kotlin, Swift, Python, JavaScript, TypeScript, Go, Rust, Scala, PHP, Ruby
- Split `file_hubs` section out of `chokepoints` on `wave_graph_report` so function-level rankings stay pure
- Add `community_size_class` (`small` / `medium` / `large` at <50 / 50–200 / 200+ thresholds) and `large_community_advisory` to `code_graph_community` responses
- Add stable `community_hub_node_id` anchor for community references (survives re-clustering across rebuilds)
- Add `collapse_class_module_pairs: bool` query-time view to `wave_graph_report` merging Swift file-and-class pairs
- Document and lock module fan-out semantics in `wave_graph_report` with a regression test
- Add empty-section diagnostic fields (`*_candidates_total`, `*_threshold`) to `chokepoints`, `file_hubs`, `orphan_docs`, `cross_layer` so `[]` distinguishes "no data" from "no hits"
- Surface graph rebuild discoverability on `wave_index_health` (per-layer `graph.last_built_at` / `node_count` / `edge_count`) and on `wave_index_build` responses (`graph_rebuilt` field + clarifying notice when `content` is not `graph`)
- Fix module-node simple-name extraction (basename without extension instead of bare extension)
- Merge Swift file-and-class nodes at the graph builder when the basename matches a top-level type declaration; extend to Java, Kotlin, C#, JavaScript, TypeScript, Scala, PHP, Rust (snake-to-PascalCase), Ruby (snake-to-PascalCase)
- Extend graph-builder receiver-type resolution to Kotlin, C#, Swift, Go, Rust, Scala
- Bundle a fix for the cross-file resolution `qualified_index` duplicate-suffix bug discovered during the receiver-type rollout

Full per-change docs: `docs/waves/13129 graph-tools-field-feedback-round-2/` in the wavefoundry repository.

---

## 1.2.0 — 2026-06-01

Initial graph tools field-feedback delivery from Solaris (Swift) and Aceiss (Java) tier-1 and tier-2 reports.

### Action required on upgrade

Rebuild the indexes after upgrade.

### Changes

- Add question-type pattern library covering navigational, explanatory, and instructional queries in the guru seed
- Improve graph tool shape consistency: dual community return on `code_impact`, pagination, per-hop attribution, communities overview
- Add generated-code classifier for Java and C# (header detection, path heuristics, `.gitattributes` opt-in) with `exclude_generated` filter and collapse mode
- Add AOP/advice empty-incoming detection (`caller_pattern: "advice"`) for Java and C# attribute annotations
- Classify Java `method_reference` (`Foo::bar`) as call sites
- Enable Kotlin reference resolution end-to-end
- Add `name_collision_count` diagnostic, `betweenness_computed` field, large-community `pagination_hint`, and `exclude_external` filter to `wave_graph_report`
- Add Java receiver-type filter at `code_callhierarchy` query time (promoted to graph builder in 1.2.1)

Full per-change docs: `docs/waves/130rj graph-tools-field-feedback-tier-1-and-2/` in the wavefoundry repository.

---

## 1.1.0 — 2026-05-31

Graph index extraction and clustering, graph-backed MCP query surface, refresh-and-instruct unification across graph tools, dashboard graph visualization.

### Action required on upgrade

Build the graph index once: `wave_index_build(content='graph')`.

### Changes

- Build per-layer code/doc graph during indexing with `defines` / `imports` / `calls` / `doc_references_*` edges; reverse invalidation prunes stale edges on file delete or rename
- Cluster the graph into communities via Leiden with label-propagation fallback
- Switch indexer to incremental chunk-delta embedding; force full LanceDB rebuild when `chunk_hash` is missing
- Centralize workflow-config include-prefix reading in the indexer; drop redundant forwarding from post-edit hook, dashboard, and server background paths
- Add `code_graph_path`, `code_graph_community`, `code_graph_status` MCP tools and `wavefoundry://graph/*` resources
- Add `direction=forward|backward|either` to `code_graph_path`
- Add graph-narrowed `code_definition` with incremental refresh; cold lookups drop from 38–43 s to sub-300 ms
- Flip graph augmentation default to on for `code_keyword`, `code_search`, `code_definition`, `code_references`
- Wire refresh-and-instruct uniformly across `code_references`, `code_callhierarchy`, `code_callgraph`, `code_impact`, `code_graph_path`, `code_graph_community`, `wave_graph_report`
- Consolidate graph-degradation diagnostic vocabulary to `graph_index_missing_degraded` / `graph_not_ready` / `graph_symbol_not_found`
- Add dashboard graph visualization, community overview, diff view, and index/graph status tiles; reorder Agents panel above Graph; remove breadcrumb back arrow and view-mode pills
- Modal dialogs own Escape key instead of the graph back handler
- Ignore `.wavefoundry/` runtime lock files via gitignore and rendered `.aiignore`
- Anonymize council synthesis output; enforce prepare-phase council-verdict recording
- Encode fix-now-not-later default in review-seat seeds (~20 LOC threshold; per-finding justification required when routing to follow-on)

Full per-change docs: `docs/waves/12xr1`, `12xr2`, `12xr3`, `1304x`, `1305t` in the wavefoundry repository.

---

## 1.0.1 — 2026-05-26

Patch release with test runner fix, search heuristics canonicalization, and README refresh.

### Changes

- Fix test runner single-run guard to prevent duplicate test execution
- Canonicalize search retrieval heuristics across `code_search` and `code_keyword`
- Refresh README with current operator orientation
- Strengthen test_run_tests_cache lifecycle assertions

Full per-change docs: `docs/waves/0rld3`, `0rld5` in the wavefoundry repository.

---

## 1.0.0 — 2026-05-24

Initial semver release. Python tool venv, venv-aware launcher shims, framework_revision manifest contract.

### Changes

- Adopt semver versioning for the framework with stamped `.wavefoundry/framework/VERSION`
- Introduce Python tool venv at `~/.wavefoundry/venv` for isolated dependencies
- Add venv-aware launcher shims under `.wavefoundry/bin/` for setup, docs-lint, docs-gardener, mcp-server, update-indexes, upgrade-wavefoundry, wave-dashboard, wave-gate
- Establish `framework_revision` contract in `docs/prompts/prompt-surface-manifest.json` aligned with the stamped VERSION

Full per-change docs: `docs/waves/12tms` in the wavefoundry repository.

