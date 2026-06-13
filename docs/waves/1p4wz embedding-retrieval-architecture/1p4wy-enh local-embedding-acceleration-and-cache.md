# Local FP16 embedding acceleration + on-disk compile cache

Change ID: `1p4wy-enh local-embedding-acceleration-and-cache`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-12
Wave: `1p4wz embedding-retrieval-architecture`

> **Scope reduced (operator decision 2026-06-12): this change landed the `_get_embedder`
> singleton (the prerequisite) only; the FP16 + CoreML-cached acceleration core is deferred to a
> follow-on, `1p517-enh fp16-coreml-embedding-acceleration.md` (now the 4th change in this wave).**
> A feasibility probe overturned this change's "download the FP16 ONNX" assumption (none is
> published); a later dtype check then corrected the precision framing entirely — **the cached
> weights are FP, not INT8: code/bge-small is already FP16, docs/arctic is FP32** — so bge-small
> needs no conversion and CoreML MLProgram likely compiles FP16 itself (so even arctic may need no
> pre-conversion). The path needs a bespoke static-shape ORT session (fastembed can't run static
> shapes). Those findings + the re-decided approach are carried in `1p517`. AC-5 (singleton) + AC-7
> (suite green) are met here; AC-1/2/3/4/6 move to `1p517`.

## Rationale

Wave `1p4u5` made provider *selection* hardware-aware, but indexing/query still run the **INT8
fastembed** model on every provider — so on Apple Silicon and NVIDIA the GPU is selected yet the
fast path is never used. This session proved the win is real and large: FP16 + static-shape +
CoreML(GPU) is **~8.75× over INT8/CPU** for bge-small (and arctic-embed-xs ran ~330 ch/s, correct),
with vectors **cosine-identical to INT8** (so a model is one global quality choice; the
provider/format is a per-machine speed choice — see [[project_fp16_coreml_gpu_win]]).

Two facts make this a runtime+cache change, not a model change:

1. **The CoreML compile is per-`InferenceSession` and NOT cached by default** (~35–40s every
   process). ONNX-Runtime 1.21+ exposes a `ModelCacheDirectory` option that caches the compiled
   `.mlmodelc` to disk — first compile ~40s, every later session/process ~7s (verified
   cross-process). Without it, every fresh process recompiles.
2. **The MCP server rebuilds the embedder on every query** (`server_impl.py:814` `_get_embedder` has
   no cache guard, unlike `_get_reranker`). Harmless on INT8/CPU (cheap), fatal on CoreML (recompile
   per query). A server-side embedder singleton is a prerequisite for the query path.

So: activate the FP16 path when a GPU provider is selected, freeze static shapes, and cache the
static ONNX + compiled CoreML model under `~/.wavefoundry/` so the compile is paid once at setup.

## Requirements

1. **Provider-conditional execution + single-format download.** CPU keeps INT8 fastembed (best for
   CPU — CPUs lack native FP16 ALUs, so FP16 runs at FP32 speed, slower than INT8). When CoreML (or
   CUDA) is selected and passes the `1p4u5` probe, run the **FP16 ONNX** for the active model.
   Download/cache **only the format the selected provider uses** — INT8 for CPU machines, FP16 for GPU
   machines — not both; a GPU machine does not need the embedding INT8 (the correctness probe can
   reference FP16-on-CPU). The reranker is a separate model that stays INT8/CPU and is never accelerated.
2. **FP16 ONNX sourcing — RESOLVED: download-and-cache.** When a GPU provider is selected and the
   machine is online, download the model's FP16 ONNX at setup and cache it under `~/.wavefoundry/`;
   INT8-on-CPU is the always-available offline fallback (an offline machine stays on the CPU path).
   Keeps the pack lean. Honor `HF_HUB_OFFLINE=1` / `local_files_only=True` for the cached read.
3. **Static-shape freeze — RESOLVED: single fixed shape `64×512` (batch tunable).** Pin the FP16 ONNX
   input dims (`make_dim_param_fixed`) to a single `(64, 512)`; zero-pad the remainder batch and slice
   the output. Bucketing rejected — chunks cluster near 512 tokens (chunker cap) so seq-buckets save
   little, and multiple shapes mean multiple ~40s compiles + more resident models. Batch 64 (not
   larger) fits the **dominant workload — incremental embedding of a few changed chunks over the
   project's life** — where a static shape pads every pass up to the batch size, so a small fixed
   batch wastes far less padding and memory than 128/256 (full rebuilds, the only case a big batch
   helps, are rare). The batch stays a setup-tunable; peak attention memory scales batch×heads×seq²,
   and 137–330 ch/s was measured at batch 32, so a modest batch keeps both memory and throughput in
   hand. Cache the static ONNX under `~/.wavefoundry/`.
4. **CoreML compiled-model cache.** Pass `ModelCacheDirectory=~/.wavefoundry/cache/coreml/` so the
   compiled `.mlmodelc` persists across processes; fold model name + format + `MLComputeUnits` +
   `ModelFormat` into `COREML_CACHE_KEY` so a model/format change invalidates the cache (ORT does no
   automatic staleness check).
5. **Server embedder singleton.** `WaveIndex._get_embedder` caches the embedder per process
   (mirroring the `_get_reranker` guard) so queries reuse the compiled session.
6. **Build the cache at setup**, eating the ~40s compile once; later processes (server, re-index)
   load in ~7s.
7. **Vector compatibility preserved.** INT8-built and FP16-built indexes of the same model remain
   interchangeable (cos ≈ 1.0); `model_versions` keys on the model name, not the format, so swapping
   providers does not force a re-embed.

## Scope

**Problem statement:** The hardware-accelerated fast path is selected but never executed, and the
CoreML compile is re-paid per process/query; activate FP16 + cache the compiled model locally.

**In scope:**

- Provider-conditional FP16 execution path in `indexer.py` / `provider_policy.py` / `setup_index.py`.
- FP16 ONNX sourcing (per the resolved fork) + static-shape freeze + `~/.wavefoundry/` cache.
- `ModelCacheDirectory` wiring + `COREML_CACHE_KEY`.
- `WaveIndex._get_embedder` singleton.
- Provider-conditional `EMBED_BATCH_SIZE` (larger on GPU).

**Out of scope:**

- Model choice (`1p4wx`) and the framework-index fold (`1p4ww`).
- CUDA install hardening beyond the `1p4u5` plan (note the `onnxruntime-gpu` + CPU-onnxruntime
  `#608` double-install footgun as a CUDA-path follow-up).
- Reranker acceleration (the reranker never receives a `providers=` arg today — separate).

## Acceptance Criteria

> AC-1/2/3/4/6 were re-scoped out of this change into `1p517` (the FP16/CoreML acceleration core) and
> are **delivered there** — `1p517` is implemented (both layers GPU-accelerated). They are checked here
> to reflect that the wave delivers them; the implementing change is `1p517`.

- [x] AC-1: On a CoreML-capable machine, the index build runs the GPU path at cos 1.0 — **delivered in `1p517`** (docs + code, both on CoreML).
- [x] AC-2: The model's ONNX resolves offline once cached — **delivered in `1p517`**.
- [x] AC-3: A static-shape `(64,512)` ONNX is produced + cached under `~/.wavefoundry/` — **delivered in `1p517`**.
- [x] AC-4: `ModelCacheDirectory` cross-process compiled-model cache — **delivered in `1p517`**.
- [x] AC-5: `WaveIndex._get_embedder` (and `indexer._get_embedder`) returns a cached instance within a
  process (no per-query recompile); a query-path test asserts a single construction. — Done here:
  `EmbedderSingletonTests` (single construction + per-model caching), suite green.
- [x] AC-6: Setup compile-once + provider/cache diagnostics — **delivered in `1p517`** (`_prewarm_gpu_accel`).
- [x] AC-7: Full framework suite green; provider tests mock hardware. — **green** (the singleton landed
  here; the FP16 provider/mock tests landed with `1p517`).

## Tasks

- [x] `_get_embedder` singleton in `server_impl.py` (+ `indexer._get_embedder` process cache) + tests.
- [x] Resolve the FP16-sourcing fork — RESOLVED by the probe: **convert-from-FP32, not download** (no
  FP16 ONNX is published for either model); carried to `1p517`.
- [x] Provider-conditional FP16 path + static-shape freeze + `~/.wavefoundry/` cache — **done in `1p517`**.
- [x] `ModelCacheDirectory` + `COREML_CACHE_KEY` wiring — **done in `1p517`**.
- [x] Provider-conditional static batch (64) on the GPU path — **done in `1p517`**.
- [x] Setup-time cache build + diagnostics — **done in `1p517`** (`_prewarm_gpu_accel`).
- [x] FP16 mocked-provider tests — **done in `1p517`** (`tests/test_accel_embedder.py`).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| FP16 sourcing decision | architect | — | the open fork |
| FP16 path + static freeze + cache | implementer | FP16 sourcing | the core |
| CoreML compile cache | implementer | FP16 path | ModelCacheDirectory + key |
| server singleton | implementer | — | small, independent |
| setup diagnostics + tests | qa-reviewer | all | mocked providers |

## Serialization Points

- `provider_policy` / `setup_index` provider-selection contract (format becomes part of it).
- `~/.wavefoundry/` cache layout (static ONNX + CoreML cache dir).
- `_get_embedder` (shared by every query).

## Affected Architecture Docs

`docs/contributing/build-and-verification.md` (provider/format + cache) and
`docs/architecture/embedding-model.md` (FP16 runtime). Likely an ADR for the cache layout + the
FP16-sourcing decision.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The acceleration itself, correctness-gated. |
| AC-2 | required | Offline-safe contract. |
| AC-3 | required | Static shape is mandatory for the CoreML win. |
| AC-4 | required | Without the cache the compile is re-paid per process. |
| AC-5 | required | Without the singleton, queries recompile (~40s each). |
| AC-6 | important | Operator visibility. |
| AC-7 | required | No regressions; CI without GPU. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | Scoped (doc-first) from the session's FP16/CoreML findings. | [[project_fp16_coreml_gpu_win]]: 8.75× bge-small, arctic-xs 330 ch/s; compile ~40s→~7s with `ModelCacheDirectory` (cross-process); `_get_embedder` per-query recompile gap. |
| 2026-06-12 | **AC-5 singleton IMPLEMENTED + suite green; FP16 core deferred to `1p517` (operator).** Added a per-process embedder cache to `WaveIndex._get_embedder` (keyed by model name, mirroring `_get_reranker`) + a module-level `indexer._EMBEDDER_CACHE` — so the CoreML/ONNX session compile is paid once per process, not per query. +2 tests (`EmbedderSingletonTests`: single construction + per-model caching). **Feasibility probe (verified live in the venv) overturned the "download the FP16 ONNX" design:** ORT 1.26 CoreML `ModelCacheDirectory`/`MLProgram`/`MLComputeUnits` confirmed real; **fastembed can't run a static-shape FP16 graph → the path needs a bespoke raw ORT `InferenceSession`** (tokenize → pad 64×512 → run → mean-pool → L2-normalize); **no FP16 ONNX is published for either model → FP16 = convert-from-FP32**, adding new deps `onnx` + `onnxconverter_common`; **bge-small's fastembed graph is INT8 → needs a clean FP32 source** (the open fork). Full findings + re-decided approach captured in `docs/plans/1p517-enh fp16-coreml-embedding-acceleration.md`. Suite **3134 green**. | `run_tests.py` 3134 green; `EmbedderSingletonTests`. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | Cache the static ONNX + compiled CoreML model under `~/.wavefoundry/`. | The compile is per-session (~40s); caching makes it once-at-setup, ~7s after, cross-process. | Recompile per process (rejected: ~40s/process; fatal for the per-query server path). |
| 2026-06-11 | Keep INT8 on CPU; FP16 only when a GPU provider is selected+probed. | INT8 is best for CPU; FP16 wins only on GPU; vectors are cross-compatible (cos≈1.0). | FP16 everywhere (rejected: no CPU benefit, larger cache). |
| 2026-06-11 | FP16 ONNX sourcing = download-and-cache at setup (GPU + online); INT8-CPU offline fallback. | Operator decision; keeps the pack lean; GPU machines are typically online at setup. | Ship FP16 in the pack (rejected: +~130MB for every user incl. CPU-only); convert from FP32 (rejected: needs FP32 source + tooling). |
| 2026-06-11 | Static shape = single fixed 64×512 (batch tunable), pad remainder. | Incremental embedding of a few chunks dominates the project's life, and a static shape pads every pass to the batch size, so a small fixed batch wastes less padding + memory than 128/256; one ~40s compile; chunks cluster near 512 (chunker cap) so seq-buckets save little; 137–330 ch/s measured at batch 32. | Bucketed seq lengths (rejected: limited benefit + multiple compiles/resident models); batch 128/256 (rejected: more padding waste on incrementals + ~2–8× activation memory for little gain). |
| 2026-06-11 | Download only the provider's format (INT8↔CPU, FP16↔GPU), not both. | FP16-on-CPU is slower than INT8 (no native FP16 ALU), so CPU wants INT8; a GPU machine does not need the embedding INT8 (the probe can reference FP16-on-CPU). | Always download both (rejected: wasteful). The reranker stays INT8/CPU separately and is unaffected. |
| 2026-06-11 | GPU format = FP16, not FP32. | FP16 matches FP32 retrieval quality (cos≈1.0 measured; INT8 — lower precision still — already saturates quality), runs ~2× faster on Metal/CUDA, uses half the activation memory, and is required for the ANE (FP32 cannot run there). Softmax/LayerNorm/epsilon accumulation stays FP32 (standard mixed-precision hygiene, applied by the FP16 export). | FP32 (rejected: ~2× slower + 2× memory + no ANE, for zero quality gain). |
| 2026-06-12 | **Land the `_get_embedder` singleton here; defer the FP16/CoreML acceleration core to `1p517`.** A probe overturned the "download the FP16 ONNX" assumption (no FP16 exists → convert-from-FP32 → new deps `onnx`+`onnxconverter_common` + a clean FP32 bge-small source). The dep/footprint change and the bge-small fork warrant a clean follow-on rather than reworking this change's resolved decisions in place. | Push through the FP16 core now under this change (rejected: would build ~400 lines of bespoke, hardware-coupled ORT code on a just-invalidated sourcing assumption with an unresolved FP32-source fork). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| FP16 ONNX not available offline. | AC-2 + the sourcing-fork decision (ship or cache). |
| Stale CoreML cache silently reused after a model/format change. | `COREML_CACHE_KEY` includes model+format+compute-units (ORT does no auto-staleness check). |
| Per-query recompile if the singleton is missed. | AC-5 query-path test. |
| Multiple static shapes → multiple ~40s compiles. | Keep the shape set small; each is cached once. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
