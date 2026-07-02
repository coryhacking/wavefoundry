# Route small incremental embed batches to CPU (skip the 64×512 GPU pad-waste)

Change ID: `1p938-enh incremental-embed-cpu-routing`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-30
Wave: `1p93a embedding-precision-policy`

## Rationale

The GPU accel embedder runs a fixed static shape `STATIC_BATCH × STATIC_SEQ = 64 × 512` and pads every call up to 64 rows. That's optimal for the **bulk** index build (full batches amortize the GPU dispatch — benchmarked at 2.46 ms/chunk at batch 64), but the **post-edit hook fires an incremental reindex** on every file edit, embedding only the handful of chunks that changed. Those few chunks get padded into the 64-row GPU batch: a 3-chunk update pays one ~157 ms GPU call for 3 chunks (~52 ms/chunk effective) when **CPU fastembed would do it in ~1–2 ms/chunk** (no dispatch tax). Measurement (B) in ADR `1p92d` confirmed GPU per-chunk only wins by amortizing over a large batch; below that it loses to CPU.

The fix routes **small** embed runs to the CPU path on a GPU machine. It is precision-safe: the CPU fallback on a GPU machine is the fastembed-resident model (bge FP16 / arctic FP32) — **cos 1.0 with the FP16 GPU-built index** (same `full` precision class), so the incremental vectors are interchangeable, force no re-embed, and don't change `model_versions`. On a CPU-bound machine it's a no-op (no GPU session to skip; small and bulk already share the one CPU path).

## Requirements

1. **Batch-size threshold routing.** When a build run would use the GPU accel embedder *and* the number of chunks to embed is below a threshold, embed via the full-precision CPU fastembed path instead of constructing/using the `64×512` GPU session.
2. **Threshold.** Default to `STATIC_BATCH` (64) — i.e. route to CPU only when the run has **less than one full GPU batch** of chunks (so a typical incremental edit → CPU; a bulk/full build → GPU). Make it a named constant (tunable; benchmarked default).
3. **Decision point.** Apply where the run's chunk count is known — in the build path after `chunks_to_embed` is computed (or via an `n_chunks` hint into `_get_embedder`) so the routing sees the actual run size, not a per-file count.
4. **Precision-safe on a GPU machine.** The small-N CPU path must be the **full-precision** fastembed-resident embedder (FP16/FP32, cos 1.0 with the FP16 index) — **not** the INT8-CPU embedder (which would mismatch the FP16 index). On a CPU-bound machine the run is already INT8 throughout; this change does not alter it.

## Scope

**Problem statement:** small incremental reindex runs waste the GPU by padding a handful of chunks into the 64×512 batch, when CPU would be faster.

**In scope:**

- `indexer.py`: a chunk-count threshold (`INCREMENTAL_GPU_MIN_CHUNKS` = `STATIC_BATCH` default) in the build/dispatch; route runs below it to the full-precision CPU embedder on a GPU machine.
- `tests/test_indexer.py`: small-run → CPU path, bulk-run → GPU path, CPU-bound machine → unchanged, and a precision-class no-op assertion.

**Out of scope:**

- The GPU `STATIC_BATCH` value itself (benchmarked 2026-06-30: keep 64 — smaller batches cost throughput and save no memory).
- The INT8-CPU embedder (`1p935`) and the precision-version guard (`1p936`).
- Server query path (queries are single-text and already on CPU).

## Acceptance Criteria

- [x] AC-1: on a GPU machine, a build run embedding fewer than the threshold chunks uses the CPU fastembed path (not the GPU accel session) — verified by the resolved embedder/log. Evidence: `indexer._get_embedder(n_chunks=...)` small-run branch; `test_small_run_on_gpu_machine_uses_cpu_fastembed` (`IncrementalGpuRoutingTests`).
- [x] AC-2: a bulk/full build (≥ threshold) uses the GPU accel path unchanged. Evidence: `test_bulk_run_on_gpu_machine_uses_accel`, `test_no_n_chunks_hint_uses_accel`.
- [x] AC-3: on a CPU-bound machine, behavior is unchanged (no GPU session exists to skip). Evidence: `has_gpu` gate → `small_run` is False without a GPU; `test_cpu_bound_machine_small_run_unchanged`.
- [x] AC-4: the small-N CPU path on a GPU machine produces full-precision (`full`-class) vectors — it does **not** trigger a precision-class change or re-embed (composes with `1p936`); vectors are cos 1.0 with the FP16 index. Evidence: the small-run path uses fastembed-resident (full) on a GPU machine, which `_predicted_precision_class` also reports as `full` (GPU → full); `test_small_run_cpu_path_is_full_precision_class`.
- [x] AC-5: full framework suite + docs-lint green. Evidence: 3,755 tests OK; docs-lint clean.

## Tasks

- [x] Add `INCREMENTAL_GPU_MIN_CHUNKS` (default `STATIC_BATCH`) + the routing in the build/dispatch (`framework_edit_allowed`). Done: `indexer.py` module constant + `_get_embedder(n_chunks=...)`; call sites pass `len(new_doc_chunks)`/`len(new_code_chunks)`.
- [x] Ensure the small-N CPU path uses the full-precision fastembed embedder on GPU machines (not INT8). Done: the small-run branch skips `make_embedder` (which would resolve GPU FP16) and goes straight to `_text_embedding_cached_first` (fastembed full); a distinct cache key avoids poisoning the bulk-run GPU embedder cache.
- [x] Add tests for small→CPU / bulk→GPU / CPU-bound-unchanged / precision-class-no-op. Done: `IncrementalGpuRoutingTests` (6).
- [x] Run suite + docs-lint. Done: 3,755 tests OK; docs-lint clean.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| threshold routing | implementer | — | `indexer.py` build/dispatch |
| precision-safety wiring | implementer | threshold routing | full-precision CPU path on GPU machines |
| tests | qa-reviewer | both | small/bulk/CPU-bound + precision-class no-op |

## Serialization Points

- Shares the embedder dispatch with `1p935` (the routing decides GPU-accel vs CPU before `make_embedder`); land after/with `1p935` so the dispatch shape is settled. Composes with `1p936` (the small-N CPU path must stay in the `full` precision class).

## Affected Architecture Docs

`docs/architecture/embedding-model.md` — note the incremental small-N → CPU routing and its precision-safety (cos 1.0 with the FP16 index). ADR `1p92d` records the measurement.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The core optimization — small runs off the GPU pad-waste. |
| AC-2 | required | Must not regress bulk-build GPU throughput. |
| AC-3 | required | No change on CPU-bound machines. |
| AC-4 | required | Must not break precision-class interchangeability / trigger re-embed. |
| AC-5 | required | No regressions. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-30 | Drafted from ADR `1p92d` measurement (B) — GPU only amortizes at large batch; small incremental runs lose to CPU. | `1p92d-adr` measurement B; `accel_embedder.py:27` (`STATIC_BATCH`). |
| 2026-06-30 | Implemented: `INCREMENTAL_GPU_MIN_CHUNKS` + `_get_embedder(n_chunks=...)` small-run → full-precision CPU routing (GPU machines only), distinct cache key. AC-1..5 met. | `indexer.py` diff; `IncrementalGpuRoutingTests` (6); 3,755 tests OK |
| 2026-06-30 | **Bug found by a real full rebuild (operator-run):** the streaming full-rebuild path produces chunks AFTER the embedder is loaded, so `new_doc_chunks` was empty at load time — passing `len()==0` routed a FULL rebuild of 1252 files / 28,830 chunks to the CPU fastembed path, defeating GPU acceleration. Fixed: pass `n_chunks=None` for a full build (never small-route a bulk rebuild). Added a build-level regression test. Unit tests missed it because they passed `n_chunks` explicitly. | `indexer.py:_build_index_locked` (`n_chunks=None if full else len(...)`); `test_full_rebuild_never_passes_small_n_chunks`; confirmed by a post-fix rebuild logging "using GPU-accelerated embedder" for both models |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-30 | Threshold = `STATIC_BATCH` (64): route to CPU when a run has less than one full GPU batch. | A run with ≥1 full batch amortizes the GPU dispatch; below that CPU wins (measurement B). | A dedicated small-batch GPU session (rejected — measurement B: CPU beats any small GPU batch, and each shape costs a CoreML compile). |
| 2026-06-30 | Small-N CPU path uses full-precision fastembed-resident, not INT8, on GPU machines. | The index is FP16 (`full`); INT8 increments would mismatch and (via `1p936`) be a precision-class change. | Use the INT8-CPU embedder uniformly (rejected — mismatches the FP16 GPU index). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Threshold too high → a moderate build needlessly runs on CPU. | Default = one full GPU batch (`STATIC_BATCH`); tunable constant; AC-2 guards bulk on GPU. |
| Small-N CPU path accidentally uses INT8 → FP16-index mismatch. | AC-4 asserts `full`-class vectors + cos 1.0; explicit full-precision selection. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
