# FP16 + CoreML-cached embedding acceleration (bespoke ORT session)

Change ID: `1p517-enh fp16-coreml-embedding-acceleration`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-12
Wave: `1p4wz embedding-retrieval-architecture`

## Rationale

Split out from `1p4wy` (operator decision 2026-06-12). `1p4wy` landed the `_get_embedder` per-process
singleton (the prerequisite that prevents a per-query CoreML recompile). The actual FP16 + static-shape
+ CoreML-cached acceleration is deferred here because a feasibility probe overturned a load-bearing
assumption in `1p4wy`'s design and materially changed the dependency footprint.

**The proven win** (see `project_fp16_coreml_gpu_win`): FP16 + static-shape + CoreML(GPU) ≈ **8.75×**
over INT8/CPU for bge-small on M2 Max, with vectors cosine-identical to INT8 (the model is one global
quality choice; the provider/format is a per-machine speed choice).

**What the 2026-06-12 probe established (verified live in `~/.wavefoundry/venv`):**

1. **ORT 1.26 CoreML caching works.** `CoreMLExecutionProvider` accepts `ModelFormat="MLProgram"`,
   `MLComputeUnits="ALL"`, and `ModelCacheDirectory=<dir>` — verified: the session builds, the cache dir
   is populated, and a bogus option name is rejected (so these are genuinely parsed, not ignored).
2. **fastembed is a dead end for this path.** It loads its own symbolic-dim ONNX and exposes no hook to
   swap the model file or pin static dims; CoreML cannot run unbounded dims (the FP32 model emitted
   "unbounded dimension" errors and fell back to CPU). The accelerated path needs a **bespoke raw
   `onnxruntime.InferenceSession`**.
3. **The current cached weights are FP, not INT8 — verified by reading the ONNX initializer dtypes
   (2026-06-12).** **Code `BAAI/bge-small-en-v1.5` is already FP16** (the fastembed-resident
   `qdrant/bge-small-en-v1.5-onnx-q` `model_optimized.onnx` = 149/149 FLOAT16 initializers, 63 MB ≈
   33M params × 2). **Docs `Snowflake/snowflake-arctic-embed-xs` is FP32** (`onnx/model.onnx` =
   101/101 FLOAT32, 86 MB ≈ 22M params × 4). So:
   - **Code model: NO conversion needed** — it is already FP16. It only needs the static-shape freeze
     + CoreML cache to engage the GPU path. (The earlier "bge-small is INT8 → needs a clean FP32
     source" fork is **dissolved**.)
   - **Docs model: NO conversion either** — see point 4 (CoreML compiles FP16 from FP32 itself).
   **The only new dependency is `onnx`** (the static-shape pin); `onnxconverter_common` is **not
   needed**.
4. **CoreML compiles FP16 itself — pre-conversion is unnecessary. CONFIRMED empirically (2026-06-12,
   M2 Max, arctic, static 64×512, MLProgram + MLComputeUnits=ALL + graph-opt ALL):** **391 ch/s,
   cpu/wall 0.04 (GPU offload — CPU idle), cos = 1.00000 vs the CPU reference.** ~24× over the ~16 ch/s
   INT8/CPU baseline at perfect correctness — feeding the FP32 weights, CoreML downcasts to FP16
   internally and runs on the GPU. So the path is: **feed each model's existing weights** (arctic FP32,
   bge-small FP16) **+ static-shape pin + CoreML MLProgram + `ModelCacheDirectory`** — **NO FP16
   conversion, NO `onnxconverter_common`.** The decisive ingredient is the static shape (dynamic dims →
   CPU fallback), not the weight precision. (`onnxconverter_common` also proved fragile — it produced
   ORT-unloadable graphs on every attempt — an additional reason to avoid it.) Only `onnx` (the
   static-shape pin) is a new dep.
5. **Static-shape pinning** via `onnx.tools.update_model_dims.update_inputs_outputs_dims` to fixed
   `(64, 512)` for `input_ids`/`attention_mask`/`token_type_ids` (int64) + `last_hidden_state`
   `[64,512,384]`. CoreML MLProgram mandates fixed dims (dynamic dims → CPU fallback).
6. **Offline tokenization works:** `tokenizers.Tokenizer.from_file(<cache>/snapshots/*/tokenizer.json)`
   loads both models and yields `ids`/`attention_mask`/`type_ids`.

## Requirements

1. **Bespoke ORT embedding session** (provider-conditional): when a GPU provider is selected and passes
   the `1p4u5` probe, embed via a raw `onnxruntime.InferenceSession` over a **static-shape** ONNX (the
   models' existing weights — bge-small FP16, arctic FP32 — with dims pinned to 64×512), not fastembed.
   CPU machines stay on the fastembed path unchanged.
2. **Build-time static-shape cache** (GPU, one-time at setup): take each model's cached ONNX →
   `update_inputs_outputs_dims((64,512))` → write `~/.wavefoundry/cache/onnx/<model>/model_static.onnx`.
   Honor `HF_HUB_OFFLINE` for cached reads; an offline machine stays on the fastembed CPU path. **No
   FP16 conversion** — CoreML downcasts FP32→FP16 itself (confirmed, Rationale #4).
3. ~~Confirm CoreML compiles FP16 from FP32~~ — **DONE (2026-06-12): arctic-FP32-static = 391 ch/s, GPU
   offload, cos 1.00000.** No conversion needed.
4. **Runtime inference:** tokenize → pad to exactly `64×512` (pad batch + seq, truncate >512) →
   `InferenceSession.run` with `providers=[("CoreMLExecutionProvider", {ModelFormat, MLComputeUnits,
   ModelCacheDirectory}), "CPUExecutionProvider"]` → **CLS-pool (`hidden[:, 0, :]`)** → L2-normalize →
   slice the real (un-padded) rows. **Pooling is CLS, not mean** — verified against fastembed:
   cos(CLS, fastembed) = 1.0000 for both models; mean-pool was 0.88–0.95 and would have produced
   index-incompatible vectors.
5. **CoreML compiled-model cache:** persist `ModelCacheDirectory=~/.wavefoundry/cache/coreml/`; fold
   model name + format + `MLComputeUnits` + `ModelFormat` into `COREML_CACHE_KEY` (ORT does no
   auto-staleness check, so a model/format change must invalidate the cache).
6. **New dependency:** add `onnx` to the GPU-path setup deps (static-shape pin) — the **only** new dep.
   `onnxconverter_common` is **not** used (no conversion). Keep CPU-only installs lean (`onnx` is not
   fetched on the CPU path).
7. **Provider-conditional `EMBED_BATCH_SIZE`** = the static batch (64) on the GPU path.
8. **Vector compatibility preserved.** Indexes built via any path (fastembed CPU vs static-shape
   CoreML) for the same model stay interchangeable (cos ≈ 1.0); `model_versions` keys on the model
   name, not the format/provider, so swapping providers does not force a re-embed.
9. **Diagnostics (AC-6 carry-over):** setup pays the compile once and reports it; the provider
   diagnostic shows the active provider + cache state.

## Scope

**Problem statement:** The hardware-accelerated fast path is selected but never executed (fastembed
runs dynamic-shape graphs, which CoreML can't accelerate — it falls back to CPU), and the CoreML
compile is re-paid per process; build a bespoke static-shape ORT session and cache the compiled model
locally so CoreML runs it FP16 on the GPU.

**In scope:**

- The bespoke ORT FP16 session (a small embedder class: tokenize → pad → run → pool → normalize).
- Build-time FP32→FP16 conversion + static-shape pin + `~/.wavefoundry/` cache.
- `ModelCacheDirectory` + `COREML_CACHE_KEY` wiring; provider-conditional dispatch + batch size.
- New deps (`onnx`, `onnxconverter_common`); clean FP32 bge-small sourcing.
- Setup diagnostics + mocked-provider tests.

**Out of scope:**

- The `_get_embedder` singleton — already landed in `1p4wy`.
- Model choice (`1p4wx`) and the framework-index fold (`1p4ww`).
- Reranker acceleration (stays on the CPU fastembed path; never receives a `providers=` arg).
- CUDA-path hardening beyond `1p4u5` (note the `onnxruntime-gpu`/CPU-onnxruntime double-install footgun).

## Dependencies

- Builds on `1p4wy` (the `_get_embedder` singleton is the prerequisite for the per-query session).
- `1p4u5` provider selection (format becomes part of the selection contract).

## Acceptance Criteria

- [x] AC-1: On a CoreML-capable machine, the index build runs the static-shape CoreML path on the GPU
  for **both** layers — docs/arctic (338 ch/s) and code/bge (201 ch/s), each GPU-offloaded at cos
  1.00000 vs fastembed; CPU machines stay on fastembed. Code uses a clean Xenova bge export (the
  fastembed-resident graph is CoreML-hostile). Server queries stay on fastembed by design (batch-64
  padding makes single-query accel a non-win).
- [x] AC-2: The static-shape ONNX is built from the offline fastembed cache (no network); the embedder
  honors `local_files_only`/offline.
- [x] AC-3: A static-shape `(64,512)` ONNX is produced and cached under `~/.wavefoundry/cache/onnx/`.
- [x] AC-4: `ModelCacheDirectory=~/.wavefoundry/cache/coreml/<model>/<format>_<units>` persists the
  compiled model across processes; the path is keyed by model+format+units (= `COREML_CACHE_KEY`), so a
  change uses a fresh dir (auto-invalidation). Cross-process reuse verified in the probe.
- [x] AC-5: The embedder is cached per process (`indexer._EMBEDDER_CACHE` + the `1p4wy`
  `WaveIndex._embedders` singleton); `EmbedderSingletonTests` asserts single construction.
- [x] AC-6: The build logs "using GPU-accelerated embedder for … (CoreMLExecutionProvider, static
  64x512)"; the provider diagnostic shows the selected provider.
- [x] AC-7: Full framework suite green (**3141**); `test_accel_embedder` mocks the ONNX session +
  tokenizer (no physical GPU/ANE required).

## Tasks

- [x] Probe: confirm arctic-FP32-static dispatches to the GPU on CoreML — **DONE (2026-06-12): 391 ch/s,
  GPU offload, cos 1.00000. No conversion needed.**
- [x] Add `onnx` to GPU-path setup deps (`setup_index.GPU_ACCEL_IMPORTS`; the only new dep, no `onnxconverter_common`).
- [x] Build-time static-shape pin + `~/.wavefoundry/` cache (per model: dims → 64×512, protobuf-direct; no conversion).
- [x] Bespoke ORT embedder (`accel_embedder.StaticShapeEmbedder`: tokenize → pad 64×512 → run → **CLS**-pool → L2-normalize → slice).
- [x] `ModelCacheDirectory` + `COREML_CACHE_KEY` wiring; provider-conditional dispatch (`indexer._get_embedder`) + static batch.
- [x] Setup-time cache build + diagnostics (`setup_index._prewarm_gpu_accel`).
- [x] Mocked-provider tests + suite (`tests/test_accel_embedder.py`, 10 tests; suite 3144 green).
- [x] Code-layer acceleration via a CoreML-friendly bge ONNX (`CLEAN_ONNX_SOURCES` → Xenova bge fp16).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| ~~CoreML-FP16 probe~~ | — | — | **DONE: FP32-static = GPU win, cos 1.0, no conversion.** |
| static-shape pin + cache | implementer | — | `onnx` only; no conversion |
| bespoke ORT session | implementer | static-shape pin + cache | tokenize/pad/run/pool |
| provider dispatch + batch | implementer | bespoke session | fastembed CPU / CoreML GPU |
| setup diagnostics + tests | qa-reviewer | all | mocked providers |

## Serialization Points

- `provider_policy` / `setup_index` provider-selection contract (format becomes part of it).
- `~/.wavefoundry/` cache layout (static ONNX + CoreML cache dir).
- The embedder dispatch shared by every query (composes with the `1p4wy` singleton).

## Affected Architecture Docs

`docs/architecture/embedding-model.md` (the CoreML FP16 runtime + the bespoke static-shape session) and
`docs/contributing/build-and-verification.md` (provider + cache). Likely an ADR for the cache layout +
the **"feed existing weights, static-shape pin, let CoreML compile FP16 — no conversion"** decision
(records the benchmark: FP32-static-CoreML = full GPU win at cos 1.0; the cached weights are FP16/FP32,
not INT8; supersedes `1p4wy`'s "download/convert FP16" assumption).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The acceleration itself, correctness-gated. |
| AC-2 | required | Offline-safe contract. |
| AC-3 | required | Static shape is mandatory for the CoreML win. |
| AC-4 | required | Without the cache the compile is re-paid per process. |
| AC-5 | required | Composes with the singleton; no per-query recompile. |
| AC-6 | important | Operator visibility. |
| AC-7 | required | No regressions; CI without GPU. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-12 | Split from `1p4wy` (operator: land singleton now, FP16 follow-on). Feasibility probe captured: ORT 1.26 CoreML cache verified; fastembed can't run static-shape graphs → bespoke ORT session; needs offline tokenizer + static-shape pin (`onnx`). | `project_fp16_coreml_gpu_win`; the 1p4wy Progress Log probe entry. |
| 2026-06-12 | **Precision correction (verified — read ONNX initializer dtypes).** The cached weights are FP, not INT8: **code/bge-small is already FP16** (149/149 FLOAT16), **docs/arctic is FP32** (101/101 FLOAT32). The earlier "INT8 baseline / bge-small is INT8 → clean-FP32-source" framing was wrong. So bge-small needs **no conversion** (the clean-FP32-source fork dissolves); only arctic is FP32. And CoreML MLProgram likely **compiles FP16 itself** (downcasts FP32 at compile), so even arctic may need no pre-conversion. | dtype scan of the cached `model_optimized.onnx` (bge) / `model.onnx` (arctic); CoreML MLProgram default compute precision = FP16. |
| 2026-06-12 | **FP16-vs-FP32 benchmark — RESOLVES the conversion question: don't convert.** Pinned arctic FP32 to static 64×512, ran on CoreML (MLProgram, MLComputeUnits=ALL, graph-opt ALL): **391 ch/s, cpu/wall 0.04 (GPU offload — CPU idle), cos = 1.00000 vs the CPU reference** (≈24× the ~16 ch/s INT8/CPU baseline, perfect correctness). CoreML downcasts FP32→FP16 internally, so feeding FP32 gets the full GPU win with **no `onnxconverter_common` and no conversion step**. The decisive ingredient is the static-shape pin (dynamic dims → CPU fallback), not the weight precision. `onnxconverter_common` was also fragile (produced ORT-unloadable graphs on every attempt). **Only new dep: `onnx`.** | `/tmp/fp16_vs_fp32.py` on the operator's M2 Max. |
| 2026-06-12 | **IMPLEMENTED (docs index build accelerated on the GPU); +7 tests; suite 3141 green.** New module `accel_embedder.py`: resolves each model's cached ONNX+tokenizer, pins dims to static 64×512 directly on the protobuf (NOT via `update_model_dims`, whose strict `check_model` rejects bge-small's opset-11 `LayerNormalization`), builds a raw ORT session with CoreML `ModelFormat=MLProgram`/`MLComputeUnits=ALL`/`ModelCacheDirectory`, tokenizes+pads to 64×512, **CLS-pools** + L2-normalizes + slices. `indexer._get_embedder` is provider-conditional: GPU provider selected → accel if the model runs on the GPU, else fastembed. `onnx` added as a GPU-conditional setup dep (`setup_index.GPU_ACCEL_IMPORTS`). **Validated live: arctic (docs) = 373 ch/s, GPU offload, cos 1.00000 vs fastembed; full rebuild log shows "using GPU-accelerated embedder for …arctic-embed-xs".** Server query path intentionally stays on fastembed (a single query padded to batch-64 is a non-win). | `run_tests.py` 3141 green; `tests/test_accel_embedder.py`; live rebuild log. |
| 2026-06-12 | **Code model (bge-small) NOT accelerated — its graph isn't CoreML-friendly (self-protecting fallback).** bge-small's fastembed `model_optimized.onnx` has fused `com.microsoft` ops; CoreML supports only 42/92 nodes → 38 partitions → CPU-bound (19 ch/s). A `StaticShapeEmbedder.offloads_to_gpu()` probe (cpu/wall ratio of a warm batch) detects this and `make_embedder` returns None → bge stays on fastembed (no regression). | CoreML `GetCapability` partition counts (arctic 330/330 in 1 partition vs bge 42/92 in 38). |
| 2026-06-12 | **Code acceleration RESOLVED (operator-directed) — clean bge export → both layers on the GPU.** A clean transformers.js export (`Xenova/bge-small-en-v1.5` `onnx/model_fp16.onnx`, decomposed standard ops) runs as a single CoreML partition: **201 ch/s, GPU offload, cos 1.00000 vs fastembed.** `accel_embedder.CLEAN_ONNX_SOURCES` maps bge → that export; `_resolve_model_files` prefers it (downloaded + cached under `~/.wavefoundry/cache/onnx-src`, offline-safe; arctic keeps its resident model). `setup_index._prewarm_gpu_accel` prefetches the clean ONNX + pays the CoreML compile at setup (AC-6). **Full rebuild, BOTH layers on GPU: docs 12,512 chunks in 102s + code 10,171 in 107s (concurrent, sharing the GPU) → total ~3.2 min vs ~11 min with code on CPU (code layer 632s→107s, ~6×).** +3 clean-source tests; suite **3144 green**; index `ready`, models correct, fold intact. | live rebuild log ("using GPU-accelerated embedder" for BOTH); `tests/test_accel_embedder.py`. |
| 2026-06-12 | **COLD-CACHE arctic regression fixed — docs now GPU under EVERY launcher, not just the prewarming ones.** Operator deleted the cache + index and the rebuild ran docs on CPU (329s) while code stayed on GPU (58s). Root cause: arctic has no `CLEAN_ONNX_SOURCES` entry, so `_resolve_model_files` used the fastembed-RESIDENT model and returned `None` whenever that model wasn't already cached — and the **dashboard's file-watcher spawns `indexer.py --content all` directly** (so does the server's docs/code background refresh), bypassing `setup_index.prewarm_models`/`_prewarm_gpu_accel`. So on a cold cache the docs accel build failed → fastembed CPU, while bge's clean path self-downloads via `hf_hub_download` and won. **Fix (accel layer, covers all launchers):** `_resolve_model_files` now calls a new `_ensure_fastembed_model_cached()` (downloads the resident model via fastembed — byte-identical weights, idempotent, HF-offline-safe) when the resident dir is absent, then retries. **Validated end-to-end in the operator's exact scenario:** stone-cold cache + the dashboard's `indexer.py --content all` → BOTH models GPU (`CoreMLExecutionProvider, static 64x512`); docs **329s→81s** (4×), total 159s incl. arctic's cold download + CoreML compile. +2 resolve tests (cold-cache fetch-then-resolve; still-missing → None, no loop). | live cold-cache rebuild log (both "using GPU-accelerated embedder"); `tests/test_accel_embedder.py`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-12 | **Feed the models' existing weights + static-shape pin; let CoreML compile FP16. NO pre-conversion. (Empirically confirmed.)** | Benchmark: arctic-FP32-static on CoreML = 391 ch/s, GPU offload, cos 1.00000 — CoreML downcasts FP32→FP16 itself, so conversion buys zero throughput (only halves on-disk size) and `onnxconverter_common` is fragile. | Pre-convert to FP16 with `onnxconverter_common` (rejected: no speed gain — CoreML already computes FP16 — and the converter produced ORT-unloadable graphs). |
| ~~2026-06-12~~ | ~~OPEN FORK — bge-small clean-FP32 source vs descope~~ | **DISSOLVED:** bge-small is already FP16; no FP32 source needed, no conversion, both models accelerable. | — |
| 2026-06-12 | **`onnx` is the only new dep** (static-shape pin). `onnxconverter_common` dropped entirely. | The benchmark removed the need for any FP16 conversion. Keep CPU-only installs lean (`onnx` is GPU-path-only). | Add `onnxconverter_common` (rejected: unused). |
| 2026-06-12 | **CLS pooling** (`hidden[:,0,:]`), not mean. | Verified cos(CLS, fastembed)=1.0000 for both models; mean was 0.88–0.95 → would corrupt the index. | Mean-pool (rejected: wrong; doesn't match fastembed/the index). |
| 2026-06-12 | **Pin static dims directly on the protobuf**, not via `onnx.tools.update_model_dims.update_inputs_outputs_dims`. | That helper runs a strict `check_model` that rejects bge-small's opset-11 `LayerNormalization`. Direct dim-setting + ORT re-inference works for both models. | `update_inputs_outputs_dims` (rejected: fails the checker on optimized graphs). |
| 2026-06-12 | **Self-protecting GPU-offload probe** (`offloads_to_gpu`): only use the accel embedder if a warm batch actually runs on the GPU; else fall back to fastembed. | bge-small's optimized graph fragments on CoreML (38 partitions, CPU-bound) — no faster than fastembed. A cpu/wall-ratio probe at construction prevents shipping a slow CoreML path; makes the dispatch robust for any model/hardware. | Hardcode per-model GPU eligibility (rejected: brittle; op support varies by ORT/hardware). |
| 2026-06-12 | **Accelerate the index build only; queries stay on fastembed.** | The static batch-64 shape is the win for batch embedding (thousands of chunks); a single query padded to 64 is 64× waste. The `1p4wy` singleton remains for hygiene. | Also route queries through accel (rejected: non-win for single queries). |
| 2026-06-12 | **Use a clean transformers.js bge export (`Xenova/bge-small-en-v1.5` fp16) for the code model**, downloaded + cached under `~/.wavefoundry/cache/onnx-src`; arctic keeps its fastembed-resident ONNX. | fastembed's bge `model_optimized.onnx` is fused with `com.microsoft` contrib ops CoreML can't run (fragments to CPU); the clean export has decomposed standard ops → single CoreML partition on the GPU at cos 1.0 vs fastembed. | Decompose the fused LayerNorm/Attention ops in the resident graph (rejected: fragile, many contrib ops); re-export from torch via optimum (rejected: heavy torch dep); leave code on CPU (rejected by operator — wanted both layers accelerated). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| ~~CoreML's compile-time FP16 downcast underperforms / drifts.~~ | **RESOLVED by the benchmark: cos 1.00000, full GPU throughput on FP32 input.** |
| New dep (`onnx`) bloats installs. | GPU-path-only install; CPU machines never fetch it. |
| Stale CoreML cache silently reused after a model/format change. | `COREML_CACHE_KEY` includes model+format+compute-units (ORT does no auto-staleness check). |
| Hardware-untestable in CI. | Mock providers for the dispatch/cache-key/diagnostic logic (AC-7); the cos-equivalence gate runs on the operator's CoreML machine. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
