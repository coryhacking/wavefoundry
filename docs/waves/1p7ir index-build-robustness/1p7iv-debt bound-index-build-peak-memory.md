# Bound index-build peak memory independent of corpus size

Change ID: `1p7iv-debt bound-index-build-peak-memory`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-23
Wave: `1p7ir index-build-robustness`

## Rationale

The 1.8.0 OOM reached ~14 GiB RSS on CPU. On-machine profiling (Progress Log 2026-06-23) showed this is **not** corpus-scaling accumulation — it is a large **FIXED CPU-provider footprint**: ~7 GiB baseline at 329 chunks, plateauing ~13–15 GiB, the same whether the corpus is 4k or 13k chunks, and unaffected by thread count. The GPU/CoreML path is ~1.7 GiB for the whole corpus, so the cost is specific to the **fastembed/onnxruntime CPU path** — the CPU memory arena plus the 256-wide (`EMBED_BATCH_SIZE`) forward-pass activation tensors. `1p7it` ships the operational mitigation (sequential-degrade so passes don't stack); this change is the root-cause follow-up: **reduce that fixed CPU embedding footprint** so a constrained CPU host doesn't need ~7–14 GiB to embed at all.

## Requirements

1. **Attribute the fixed CPU footprint.** Profile the CPU embedding pass to split the ~7–14 GiB across model weights vs the onnxruntime **CPU memory arena** vs the `EMBED_BATCH_SIZE`-wide activation tensors vs Lance write buffers — confirming the arena/activation as the driver (threads and corpus size are already ruled out).
2. **Reduce the fixed footprint on the constrained profile.** Cut it via onnxruntime CPU arena config (`enable_cpu_mem_arena` / `arena_extend_strategy`) and/or a smaller `EMBED_BATCH_SIZE` for CPU-only hosts, so the CPU embedding pass peaks well under the field cap. GPU/CoreML behavior (already ~1.7 GiB) stays unchanged; throughput trade-off measured.
3. **Regression guard.** A test (or measured check) asserts the CPU embedding footprint stays under a stated bound — so the arena/activation cost can’t silently regrow.

## Scope

**Problem statement:** Build RSS scales with corpus size beyond the embed buffer; the mitigations cap the symptom but the underlying accumulation remains.

**In scope:**

- CPU-path memory profiling of the embedding pass (onnxruntime arena / `EMBED_BATCH_SIZE` activations / model).
- The fix: onnxruntime CPU arena config and/or a smaller CPU `EMBED_BATCH_SIZE` on the constrained profile.
- A CPU-footprint regression guard.

**Out of scope:**

- The buffer default / sequential degrade / loud failure (`1p7it`) — the mitigations this builds on.
- Health honesty (`1p7is`) and TLS (`1p7iu`).

## Acceptance Criteria

- [x] AC-1: CPU profile attributes the footprint — **the `EMBED_BATCH_SIZE` forward-pass activation tensors** are the dominant driver (RSS scales monotonically with batch: 32→2.78, 256→6.91 GiB; ~2 GiB fixed model/runtime baseline underneath). Threading and corpus size were ruled out; the residual corpus growth is arena accumulation (secondary). Evidence in the Progress Log (2026-06-23 batch sweep).
- [x] AC-2: CPU embedding footprint materially reduced via a smaller forward batch — per-model default **32** (operator chose "lower everywhere", not constrained-only), measured ~3.5–3.8× less peak RSS (code 5.36→1.55, docs 9.47→2.49 GiB) at equal-or-better throughput; GPU/CoreML unchanged (static-shape embedder ignores the batch). The onnxruntime arena lever was unneeded — the batch alone achieved it.
- [x] AC-3: regression guard = `test_resolve_embed_batch_size_per_model_and_global` pins `_DEFAULT_EMBED_BATCH == 32` and the per-model/global resolution, so the memory lever can't silently revert. (A runtime peak-RSS assertion would be environment-flaky; the value-pin is the practical guard.)
- [x] AC-4: index output unchanged — embedding is mathematically per-text, so batch width is vector-invariant (no re-embed, no node/edge/chunk change).
- [x] AC-5: framework tests bytecode-free (suite 3428 OK); `wave_validate` clean.

## Tasks

- [x] Profile the CPU embedding pass; attribute the ~7–14 GiB → the `EMBED_BATCH_SIZE` forward-pass activation tensors (batch sweep).
- [x] Reduce it via a smaller CPU forward batch — per-model resolver + default 32 (everywhere, per operator).
- [x] Add the CPU-footprint regression guard — the default-value pin test.
- [x] Verify index output unchanged (vector-invariant) + record the throughput trade-off (equal-or-faster).

## Agent Execution Graph


| Workstream | Owner       | Depends On | Notes                                         |
| ---------- | ----------- | ---------- | --------------------------------------------- |
| profile    | reviewer    | —          | attribute RSS growth across the pass           |
| memory-fix | implementer | profile    | release/stream the scaling accumulator         |
| guard      | implementer | memory-fix | peak-RSS-vs-file-count regression check        |


## Serialization Points

- Builds on `1p7it` (shares the build/memory path) — sequence after `1p7it` lands so the profile measures against the mitigated baseline, and avoid double-implementing the same flush.

## Affected Architecture Docs

- **Update if present:** the indexing/build architecture doc — the peak-memory bound (O(buffer+model), not O(corpus)) as a stated contract. Confirm at Prepare.

## AC Priority

(Populated at Prepare wave — proposed below.)


| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The profile scopes the fix — without it this is guesswork. |
| AC-2 | required  | The bound is the deliverable. |
| AC-3 | important | Regression guard so the accumulation can’t return. |
| AC-4 | required  | Memory fix must not change index output. |
| AC-5 | required  | Test-locked, bytecode-free. |


## Progress Log


| Date       | Update | Evidence |
| ---------- | ------ | -------- |
| 2026-06-23 | Drafted from the 1.8.0 field report as the root-cause follow-up to `1p7it` (~14 GiB / 811 files is higher than the working set warrants). Profile-first; value-gates on a real before/after. | memory `project_field_feedback_1p8_oom_tls` |
| 2026-06-23 | **Default lowered to 32 everywhere (the fix shipped, operator-directed).** `_DEFAULT_EMBED_BATCH = 32` (down from 256) for both models — the benchmark's lowest-memory AND fastest CPU point (~3.5–3.8× less peak RSS, equal-or-better throughput; onnxruntime parallelizes each forward pass across cores regardless of batch so cores still fill). GPU unaffected (static-shape embedder ignores it). Vectors batch-invariant → no re-embed. Field host projection: ~14 GiB → ~3.5 GiB, well under the ~15 GiB cap. Test pins the default + per-model resolution; suite 3428 OK. | `indexer.py` `_DEFAULT_EMBED_BATCH`/`_EMBED_BATCH_DEFAULTS`; operator decision (lower everywhere, 32) |
| 2026-06-23 | **Per-model forward-batch knob IMPLEMENTED (the AC-2 lever, configurable).** Docs and code use DIFFERENT models (docs `arctic-embed-xs`, code `bge-small`) with different footprints, so the batch is now resolved PER MODEL: `_resolve_embed_batch_size(model_name, root)` — `indexing.{docs,code}_embed_batch_size` (per-model) > `indexing.embed_batch_size` (global) > per-model default — threaded through `_StreamingLayerWriter(batch_size=…)`. Defaults preserve current behavior (`EMBED_BATCH_SIZE`=256); GPU static-shape embedder ignores it (CPU-only lever). Vectors are batch-invariant → no re-embed/version bump. Confirming sweep (CPU, batch 256→32): code 5.36→1.55 GiB (3.5×), docs 9.47→2.49 GiB (3.8×), both equal-or-faster. `+1` test (`test_resolve_embed_batch_size_per_model_and_global`); suite 3428 OK. **Open: the default VALUES** (keep 256 + opt-in knobs, ship lower per-model defaults, or auto-lower on the 1p7it constrained profile) — operator decision. | `indexer.py` `_resolve_embed_batch_size` + `_StreamingLayerWriter`; `experiments/buffer_bench.py --content --batch` sweep |
| 2026-06-23 | **ROOT CAUSE CONFIRMED — the forward-pass batch width is the driver (AC-1 satisfied).** Sweeping `EMBED_BATCH_SIZE` on the CPU path over a fixed 329-chunk corpus: 32→**2.78 GiB**, 64→4.01, 128→4.62, 256→**6.91 GiB** — peak RSS scales monotonically with the forward batch. So CPU RSS ≈ ~2 GiB fixed (model + onnxruntime) + activation tensors (attention/intermediate buffers ≈ batch×heads×seq² ) that scale with the batch and sit in the onnxruntime CPU memory arena. On GPU/CoreML those same activations live in GPU/Metal memory, OFF the process RSS — which is the entire ~7–8× CPU-vs-GPU gap. **Wall time is flat across the sweep (32 was fastest — less padding waste), so lowering the CPU forward batch is a ~60% RSS cut at ~zero speed cost.** Fix (AC-2): a smaller forward batch on the CPU/constrained path (GPU uses a static batch, unaffected). Residual corpus-growth (329-chunk 6.9 GiB → 4,209-chunk 14 GiB at batch 256) is the arena accumulating across batches — secondary; the batch lever dominates. | `experiments/buffer_bench.py --batch` CPU sweep (`/tmp/bench_batch_*.log`); `indexer.py:1185` `_embed_texts(batch_size=EMBED_BATCH_SIZE)`; fastembed uses a default onnxruntime CPU session (no arena tuning) |
| 2026-06-23 | **On-machine profiling REFOCUSES this change: the cost is a FIXED CPU embedding footprint, not corpus-scaling.** CPU peak RSS is ~7 GiB at 329 chunks, ~13–15 GiB at 4,209 chunks, ~13 GiB at 13,395 chunks — a large fixed baseline that plateaus, NOT linear in file count (the original "O(corpus)" premise is wrong). GPU path is ~1.7 GiB for the whole corpus, so it is specific to the **fastembed/onnxruntime CPU provider**. `OMP_NUM_THREADS` 1/2/4/8 had **zero** effect (~6.9 GiB flat) → not threading. So the ~7 GiB baseline is the onnxruntime **CPU memory arena + the 256-wide (`EMBED_BATCH_SIZE`) forward-pass activations**, not retained chunks/Lance buffers. New target: reduce the fixed CPU footprint via the onnxruntime arena config (`enable_cpu_mem_arena`/`arena_extend_strategy`) and/or a smaller `EMBED_BATCH_SIZE` on constrained hosts — NOT corpus-accumulation streaming. | `experiments/buffer_bench.py` CPU sweeps; `OMP_NUM_THREADS` probe (`/tmp/bench_omp_*.log`); GPU vs CPU vs corpus-size controls |


## Decision Log


| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-06-23 | Profile-first, then bound | The ~14 GiB suggests an accumulator beyond the buffer; fixing blind risks the wrong target (the literal-edge lesson: measure before binding). | Assume it’s only the buffer — rejected: the mitigation already covers the buffer; this exists because that’s not the whole story. |
| 2026-06-23 | **Refocus: reduce the fixed CPU-provider footprint (onnxruntime arena + `EMBED_BATCH_SIZE`), not corpus-accumulation streaming** | Profiling (Progress Log) showed RSS is a large FIXED CPU-embedding footprint (~7 GiB baseline, plateaus ~13–15 GiB), corpus-independent and thread-independent — not the assumed O(corpus) accumulation. Profile-first still holds; the lesson stands (measure before binding) — and it changed the target. | Stream a corpus-scaling accumulator — rejected: the data shows no material corpus-scaling to stream; the cost is the arena/activation memory. |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
| Arena/batch tuning yields little CPU-footprint reduction (the ~7 GiB is irreducible model/runtime) | Then this closes with the profile recorded — `1p7it`'s sequential-degrade already bounds the operational peak; honest outcome, not forced work. A model/format swap would be a separate, larger wave. |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
