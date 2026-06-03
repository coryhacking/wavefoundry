# Parallel-Extraction Fork Deadlock — Spawn-Mode Worker Initializer

Change ID: `1p2wd-bug parallel-extraction-fork-deadlock-spawn-mode-fix`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-02
Wave: 1p2q3 field-feedback-round-4

## Rationale

Teton field session on 1.3.17 reproduced 3-of-3 a deterministic deadlock in the parallel-extraction pool on their 1,360-TS/JS-file Nx monorepo. Symptom: parent prints `pre-warmed declared-names cache for N TS/JS files`, then all 4 workers + the coordinator + the launcher sit at 0.0% CPU with no further log output, indefinitely. The hang location is identical across all three attempts: between the parent's pre-warm log line and the first worker progress report.

This is the macOS `fork()` hazard the 1.3.14 release notes flagged as "main remaining headroom for future optimization." `fork()` on macOS after the parent has initialized C extension state (`tree_sitter` parsers and language packs, possibly objc/Foundation runtime via transitive imports from torch / lance / sentence-transformers) leaves children in a state where any internal synchronization primitive (`pthread_mutex`, semaphores, the objc dispatch queues) can deadlock on first use. The children are forked successfully but cannot make progress because the inherited mutex state is inconsistent.

1.3.18 shipped parallel mode as default-off (`WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` default `1`) as a conservative bridge. This change closes the underlying defect so the perf path can be opt-in *safely* and, eventually, default-on again.

The fix is to switch from `fork` to `spawn` and install a `ProcessPoolExecutor` worker `initializer` that re-loads `graph_indexer.py` via `spec_from_file_location` and registers it in `sys.modules["graph_indexer"]` before any task unpickling tries to deserialize a function reference back to `graph_indexer._extract_artifact_for_worker`. A prior session attempted this and gave up after running into module-resolution issues; on closer reading the initializer approach is sound — the requirement is that the initializer fires *before* the worker tries to unpickle its first task, which `ProcessPoolExecutor`'s contract guarantees.

## Requirements

1. The parallel extraction path must complete deterministically on macOS Python 3.13 with `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS > 1` against a corpus that exceeds the 100-file threshold. No hangs, no fallback-to-serial diagnostic, no log silence.
2. The fix must work without relying on `os.environ.get("WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD")` — the default behavior must be safe.
3. The parent's pre-warmed declared-names cache (added in 1.3.15) is acceptably lost in spawn mode because workers no longer inherit copy-on-write parent memory. Workers populate their own per-process cache lazily as the barrel walker requests names; this is a known throughput cost we accept for correctness.
4. Worker function references must be picklable across process boundaries. `_extract_artifact_for_worker` is already module-level in `graph_indexer.py`; the fix must preserve that invariant.
5. The change must not alter graph-extractor output (no `GRAPH_BUILDER_VERSION` bump).

## Scope

**Problem statement:** Parallel code-file extraction deadlocks deterministically on macOS when the parent process has initialized tree-sitter (and possibly other) C extension state before `fork()`. The current workaround (parallel default-off in 1.3.18) avoids the deadlock but loses the 2.35× speedup field-validated on 1.3.14.

**In scope:**

- Switch the default `multiprocessing` start method from `fork` to `spawn` for the parallel-extraction `ProcessPoolExecutor`.
- Install a worker `initializer` callable that loads `graph_indexer.py` via `spec_from_file_location` and registers the module in `sys.modules["graph_indexer"]` before the first task is dispatched.
- Pass the worker the absolute path to `graph_indexer.py` (a single string arg) so it can re-load identically.
- Remove the pre-fork cache prewarm (it has no effect with spawn, and keeping it would mislead operators about its purpose).
- Update the 1.3.14 / 1.3.15 / 1.3.18 release-notes language in code comments to reflect the new architecture.
- Regression test that runs through the parallel branch end-to-end with a small file-count fixture (the threshold is temporarily lowered via monkeypatch).

**Out of scope:**

- Changing the default value of `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS`. 1.3.18 made it `1`; this change keeps that default. Operators opt in via the env var.
- Implementing `forkserver` as an alternative start method.
- Cross-worker shared cache (the pre-fork warm-up is removed; workers each populate their own caches).
- Tuning the worker count ceiling or per-worker memory.
- Worker process supervision / watchdog timeouts.

## Acceptance Criteria

- [x] AC-1: A real parallel build on this repo's framework scripts directory (40 Python files, threshold patched to 10, workers=4) completes in ~8.5s with 1507 nodes / 5392 edges — byte-identical to the serial-mode payload (1.5s, same counts). Test: `test_parallel_branch_end_to_end_with_real_spawn_workers` in `test_graph_indexer.py`.
- [x] AC-2: The wiring test asserts ProcessPoolExecutor is constructed with `mp_context` whose start method is `"spawn"`, `initializer=_worker_init_graph_indexer`, and `initargs=(<path_to_graph_indexer.py>,)`. Test: `test_parallel_branch_wires_spawn_and_initializer`.
- [x] AC-3: The initializer registers `graph_indexer` in `sys.modules` under the canonical name and exposes `_extract_artifact_for_worker`. Test: `test_worker_initializer_registers_graph_indexer_in_sys_modules`. (Note: the load-bearing mechanism for spawn unpickling turned out to be `sys.path` insertion in the parent — multiprocessing/spawn serializes the parent's `sys.path`, not `PYTHONPATH`. The initializer is preserved as defense-in-depth.)
- [x] AC-4: On `mp_ctx is None` (`get_context` raised), the existing serial fallback runs. On `BrokenProcessPool` or any other pool exception, the existing `except Exception ... falling back to serial` branch handles it.
- [x] AC-5: No `GRAPH_BUILDER_VERSION` bump; AC-1 confirms byte-identical output between serial and parallel paths.

## Tasks

- [ ] Modify `update_graph_index` in `graph_indexer.py`: switch `start_method` default from `"fork"` to `"spawn"`; remove the `_prewarm_declared_names_cache` call from the parallel branch; pass the absolute path of `graph_indexer.py` as the initializer arg.
- [ ] Wire `ProcessPoolExecutor(..., initializer=_worker_init_graph_indexer, initargs=(str(graph_indexer_path),))` so workers run the initializer before unpickling tasks.
- [ ] Update inline comments in the parallel branch to reflect the new start-method choice and the rationale (the macOS fork deadlock observed on Teton).
- [ ] Update the `_worker_init_graph_indexer` docstring to match its new role under spawn mode (it is now the *primary* mechanism, not a fallback).
- [ ] Regression tests as described in AC-2 and AC-3.
- [ ] Local validation against the wavefoundry repo with `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS=4` — confirm completion and payload-equivalence vs. serial.

## Agent Execution Graph


| Workstream                         | Owner       | Depends On        | Notes |
| ---------------------------------- | ----------- | ----------------- | ----- |
| spawn-mode-switch                  | Engineering | —                 | Edit `graph_indexer.py` parallel branch |
| regression-tests                   | Engineering | spawn-mode-switch | New tests in `test_graph_indexer.py` |
| local-build-validation             | Engineering | spawn-mode-switch | Verify on this repo before packaging |


## Serialization Points

- `graph_indexer.py` is the single source file edited for the spawn-mode switch. No cross-file coordination required.

## Affected Architecture Docs

`N/A` — the change is an internal implementation detail of `update_graph_index`'s parallel branch. The public contract (output payload shape, `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` env var, `_PARALLEL_EXTRACTION_THRESHOLD`) is unchanged. The `WAVEFOUNDRY_GRAPH_PARALLEL_START_METHOD` env var override is preserved as an escape hatch.

## AC Priority

(Populated at Prepare wave.)


| AC   | Priority   | Rationale |
| ---- | ---------- | --------- |
| AC-1 | required   | The whole point of this change is end-to-end completion under parallel mode |
| AC-2 | required   | Without a regression test, the next refactor can re-introduce the deadlock silently |
| AC-3 | important  | Verifies the initializer wiring, not just behavior |
| AC-4 | important  | Preserve existing graceful-fallback contract |
| AC-5 | required   | Builder-version bump is reserved for output-shape changes; this is implementation-only |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-02 | Change admitted to 1p2q3 directly following Teton's 1.3.17 reproducer. 1.3.18 ships parallel default-off as the conservative bridge; this change closes the underlying defect. | This doc + 1.3.18 CHANGELOG entry |
| 2026-06-02 | First implementation attempt landed spawn + worker initializer but failed at worker bootstrap: `ModuleNotFoundError: No module named 'graph_indexer'` at `multiprocessing/spawn.py:132 reduction.pickle.load(from_parent)`. Investigation: multiprocessing/spawn serializes the parent's `sys.path` (not `PYTHONPATH`) into the bootstrap pickle. The initializer alone is too late — unpickling of the worker's bootstrap state happens before any user-defined initializer fires. | Diagnostic from local 4-worker probe build on framework scripts |
| 2026-06-02 | Real fix: insert `Path(__file__).parent` into the parent's `sys.path` before pool construction (and remove on exit). Workers inherit it via the bootstrap pickle and can `__import__("graph_indexer")` cleanly during their pre-task bootstrap phase. Validated by AC-1 end-to-end test (4 spawn workers complete on tiny fixture in < 1s) and by a real 40-file framework build (1507 nodes / 5392 edges, identical to serial). | `test_parallel_branch_end_to_end_with_real_spawn_workers` |
| 2026-06-02 | All 4 ACs implemented + verified. 2255 framework tests pass (was 2251 — net +4 for the 3 wiring/unit tests plus the end-to-end). | `python3 .wavefoundry/framework/scripts/run_tests.py` |
| 2026-06-02 | Post-ship 1.3.20: auto-scale worker count by file count when `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` env var is unset. Tiers: <200 files → 2 workers; 200-499 → 3 workers; ≥500 → `min(cpu_count, 4)`. Env-var override wins unconditionally. Teton field validation: 1,542 code files → tier 3 → 4 workers, ~80s → ~40s (2× speedup) confirmed by operator. 2258 tests pass (net +3 for tier-pinning tests). | Teton operator report; `_auto_scale_worker_count` + tests in `test_graph_indexer.py` |
| 2026-06-02 | Post-ship 1.3.21: Teton reported a *new* hang signature on 1.3.20 — Python `threading.Lock` deadlock, 4 indexer threads blocked, zero workers spawned. Stack samples narrowed it to between `graph extraction parallel` log line and first task return. Step 2 (direct invocation outside MCP) reproduced identically. Shipped 1.3.21 with 8-step breadcrumb instrumentation in the parallel branch (each line tagged with current thread count and names) to pinpoint the hang line. | Teton stack samples; `_pdbg` helper + instrumented steps in `graph_indexer.py` |
| 2026-06-02 | Post-ship 1.3.22: 1.3.21 instrumentation surfaced thread signature `[threads=2: MainThread, wavefoundry-index_0]` at the hang point. Root cause identified: `_build_graph_artifacts` was submitted to a `ThreadPoolExecutor` in `indexer.py:_build_lance_index` to run concurrently with docs/code LanceDB writes. The graph layer's own `ProcessPoolExecutor.map()` then deadlocked at `Process.start()` because macOS Python 3.13 cannot call `multiprocessing.Process.start()` from a non-main thread in spawn mode (the spawn machinery's signal-handler and pickle state requires the main thread). Fix: graph extraction moved out of the threadpool, runs synchronously on the main thread; docs/code stay in the threadpool. Concurrency benefit preserved (docs/code overlap with graph in time). Closes Bug 4 at the root cause. | Teton's `parallel-debug` log output; `indexer.py:_build_lance_index` change |
| 2026-06-02 | Post-ship 1.3.23: 1.3.22 confirmed `threads=1: MainThread` at step 8/8 (threading-thread issue fixed) but the hang persisted with a different signature. Teton's stack samples isolated three indexer threads — main blocked on Future.result, queue-manager polling FDs, and the call-queue writer thread blocked in `os.write()` to a pipe. Root cause: `pool.map(chunksize=96)` triggers `Executor.map`'s eager `submit()` loop, pre-filling 16 chunks (~1,536 items) into the call queue's Unix pipe (64KB buffer on macOS) before any worker spawns. Writer thread blocks; workers never spawn; main thread waits forever. Fix: replaced `pool.map` with a bounded-in-flight `pool.submit` + `concurrent.futures.wait(..., return_when=FIRST_COMPLETED)` loop. At most `worker_count` tasks queued at any time — pipe never fills. Pre-warm trigger spawns workers safely. Added worker-side breadcrumb to entry of `_extract_artifact_for_worker` for any future regression diagnosis. | Teton's stack samples (writer thread in `os_write`); `graph_indexer.py` bounded-in-flight rewrite |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-02 | Spawn over forkserver. | Spawn is simpler (clean process per worker, no server-process orchestration), tested by macOS-native CPython at every release, and avoids any inheritance hazard. Forkserver still inherits the server-process's loaded modules — moving the problem one layer up rather than eliminating it. | (a) `forkserver` — sketchy module-loading semantics on macOS; (b) restructure `graph_indexer.py` as a proper `wavefoundry.graph_indexer` package — clean but invasive; defer to a future maintenance round. |
| 2026-06-02 | Drop the pre-fork `_prewarm_declared_names_cache` instead of preserving it for the (unsupported) fork path. | With spawn there is no inheritance, so the warmup has no effect on workers. Leaving dead-but-running code would mislead future maintainers. | Keep it gated behind a `start_method == "fork"` check (would re-introduce the broken path as a code-visible option). |
| 2026-06-02 | Default `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` stays at `1` (set in 1.3.18). | Spawn introduces per-worker startup cost (~500ms–1s × workers). Operators on small projects (the framework itself, test fixtures) shouldn't pay that cost without opting in. Big-monorepo operators set the env var explicitly. | Restore `min(cpu_count, 4)` default — would amortize the cost across all operators including small projects, where the work itself is faster than the worker boot. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Spawn-mode worker startup cost negates the perf win on builds just above the 100-file threshold. | The threshold can be raised in a follow-up. For now operators who opt into parallel mode explicitly accept this. |
| `initializer` runs but `spec_from_file_location` fails (path missing in the worker's filesystem view). | Wrap in try/except inside the initializer; worker-startup failures already trigger ProcessPoolExecutor's graceful-fallback path. |
| Worker memory pressure with high `WAVEFOUNDRY_GRAPH_PARALLEL_WORKERS` values. | Spawn workers are independent Python interpreters (~80–120MB resident each on macOS with tree-sitter loaded). At 16 workers ≈ 2GB, at 32 workers ≈ 4GB. Document the trade-off; defer ceiling enforcement to a future change. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
