# FP16/CoreML reranker acceleration

Change ID: `1p52p-enh fp16-coreml-reranker-acceleration`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p4wz embedding-retrieval-architecture`

## Rationale

The cross-encoder reranker (`RERANKER_MODEL = "BAAI/bge-reranker-base"`) runs on **every** `docs_search`/
`code_search`/`code_ask` call, scoring ~30–60 query-passage pairs per query, and it is the dominant
search latency. It currently runs on **CPU via fastembed** using the **FP32** `onnx/model.onnx` (a
**1.0 GB** download — the single heaviest cache item).

The same static-shape + CoreML technique that accelerated the embedders (`1p517`) applies to the
reranker, and a clean FP16 export already exists (`Xenova/bge-reranker-base` `onnx/model_fp16.onnx`,
decomposed standard ops → single CoreML partition). A throwaway probe on the operator's M2 Max
(60 candidates/query) measured:

- **CPU fastembed BAAI FP32: 10,622 ms/query** → **GPU CoreML FP16 (Xenova): 766 ms/query** = **≈13.9×**,
  `cpu/wall = 0.08` (genuine GPU offload).
- **Ranking identical:** Spearman 0.9999, top-5 5/5, top-10 10/10, same #1.
- **Score scale identical:** fastembed's `_post_process_onnx_output` returns the **raw logit** (no
  sigmoid/softmax); our path takes the same raw logit. FP16-vs-FP32 absolute logits differ by
  **max 0.0154 / mean 0.0067** — numerically indistinguishable, so the server's logit-scale thresholds
  (`AGENT_RELEVANCE_DROPOFF`, doc-demote, RRF blends) remain valid without recalibration.

A follow-up feasibility check ruled out an FP16 **CPU** path: the FP16 graph fails to initialize on
the CPU EP at `ORT_ENABLE_ALL` (a `SimplifiedLayerNormFusion` cast bug — it only loads at `BASIC`/
`DISABLE_ALL`), and even at `BASIC` it runs **slower than today** (13.6 s vs 10.6 s for the same
batch) because ORT has no native FP16 CPU kernels (it casts FP16→FP32 per op) and we pad to 64. So
FP16-on-CPU is a latency regression with no quality benefit.

Operator decision (2026-06-12): **drop BAAI FP32 entirely; run the cross-encoder on whatever hardware
is present.** On a GPU machine it is the FP16 static-shape CoreML/CUDA path (~350 ms/query); on a
**CPU-only** machine it is the **INT8** export on `CPUExecutionProvider` (~960 ms/query, no ranking
loss — see the CPU benchmark). The fastembed `TextCrossEncoder` dependency is removed; BAAI FP32 is
never downloaded. Reranking is skipped (→ vector order, logged once) only when explicitly disabled
(`WAVEFOUNDRY_DISABLE_RERANKER`, used by the test suite) or when the model can't be built.

**Consumer impact:** every install — GPU or CPU-only — keeps the cross-encoder. (An earlier iteration
was GPU-only and dropped reranking on CPU; the small ms-marco-L6 model made the CPU INT8 path viable,
so that retrieval-quality reduction no longer applies.)

## Requirements

1. A `StaticShapeReranker` (in `accel_embedder.py`): cross-encoder **pair** tokenization, static-shape
   pin (batch×seq, output logit `[batch, 1]` — pin dim0 only, NOT dim1), and a
   `rerank(query, passages) -> list[float]` returning **raw logits**. **Dual precision by hardware:**
   FP16 on a GPU provider (CoreML/CUDA/ROCm/DirectML); **INT8** (`model_int8.onnx`) on
   `CPUExecutionProvider` when no GPU. `ORT_ENABLE_ALL` for both.
2. `server_impl._get_reranker()` returns the `StaticShapeReranker` for this hardware (GPU FP16 if the
   `offloads_to_gpu` probe passes, else CPU INT8). The fastembed `TextCrossEncoder` path is removed.
   It returns **`None`** only when reranking is explicitly disabled (`WAVEFOUNDRY_DISABLE_RERANKER`) or
   unbuildable — then the call sites degrade to vector order (logged once, observable).
3. `RERANKER_MODEL`'s clean source resolves to `Xenova/bge-reranker-base` `onnx/model_fp16.onnx`; the
   BAAI FP32 reranker is no longer downloaded, prewarmed, or shipped on any machine.
4. Cold-cache safe + prewarmed (GPU machines only): the reranker model self-downloads when missing
   (mirrors the embedder cold-cache fix), and the CoreML compile is prewarmed at setup/server start so
   the first live query does not pay the ~20 s compile.
5. The reranker runs in the **server (query) process** — the per-process `_reranker` singleton caches
   the compiled session (one CoreML compile per server lifetime).
7. **All GPU providers, not just CoreML** (operator 2026-06-12): the accel path attempts CoreML,
   CUDA, ROCm, and DirectML (`GPU_PROVIDERS`), selecting whichever is available; CoreML gets the
   MLProgram/compile-cache options, every other GPU EP takes the provider name with defaults. The
   non-CoreML session branch uses the *actually-selected* provider (was hardcoded to CUDA — a latent
   bug for ROCm/DirectML). `offloads_to_gpu` self-protects any provider that doesn't truly offload.
8. **Embed the cross-encoder into `code_ask`'s agent ranking; remove the other `code_ask` ranking
   paths** (operator 2026-06-12): agent mode has never used the cross-encoder. Wire it as a
   **rerank-FIRST** stage — the cross-encoder scores the full retrieved pool *before*
   `_agent_candidate_select`, replacing each candidate's `score` with the unified relevance score
   `sigmoid(logit)` ∈ [0,1]. This is REQUIRED, not cosmetic: since the docs/code model split (1p4wx),
   docs (arctic) and code (bge) cosines are on **different scales**, so the pre-existing agent
   selection (per-index floor, relevance drop-off, text budget) AND the confidence band were
   comparing incomparable cosines. The cross-encoder gives ONE scale across docs+code, so selection,
   ordering, AND confidence all key off it. The `code_ask` `rerank="local"` cross-encoder path and the
   `rrf_fallback` path in `search_combined` are removed — `code_ask` has a single ranking path (agent
   + cross-encoder). `docs_search`/`code_search` keep their own independent rerank (unchanged;
   `search_combined` is code_ask-only).
   - **Confidence is recalibrated to the reranker's sigmoid scale** (the old `0.72` bge-cosine band is
     retired): on-topic queries whose answer is retrieved score `sigmoid ≥ ~0.5` (the model's native
     relevance boundary); off-topic/no-answer score `sigmoid < ~0.1` (measured separation). This
     applies whenever the cross-encoder runs (GPU FP16 or CPU INT8). Confidence falls back to
     **count-based** only when reranking is disabled (no unified score; the mixed-model cosine is not a
     trustworthy band).
9. An ADR records the reranker FP16/CoreML acceleration, the BAAI-drop, and the CPU INT8 fallback,
   with the probe evidence.

## Scope

**Problem statement:** The reranker is the heaviest model and the dominant search latency, running
FP32 on CPU; a CoreML-friendly FP16 export gives ~14× with identical ranking and score scale.

**In scope:**

- `accel_embedder.py`: `StaticShapeReranker` (+ reranker-specific static-pin for the `[batch,1]` logit
  output) + a clean-source/cold-cache resolution entry for the reranker.
- `indexer.py`: `RERANKER_MODEL` → the Xenova FP16 source (or a reranker clean-source map).
- `server_impl.py`: `_get_reranker()` provider-conditional dispatch; remove the fastembed
  `TextCrossEncoder` path.
- `setup_index.py`: prewarm the hardware-selected reranker (GPU FP16 or CPU INT8) instead of BAAI
  FP32; drop the BAAI reranker from the model-cache prewarm/verify set.
- ADR + tests (mocked accel reranker + a **score-parity** test asserting FP16 logits ≈ the BAAI FP32
  reference within tolerance).

**Out of scope:**

- The embedder accel (shipped in `1p517`).
- Reranker model choice / quality tuning (same weights, FP16 export — ranking is identical).
- Pre-`1p52p` agent-mode candidate selection details; this change replaces that skipped-cross-encoder path
  with rerank-first agent selection.

## Dependencies

- Builds on `1p517` (the `accel_embedder` static-shape/CoreML machinery, `offloads_to_gpu` probe,
  cold-cache self-download).

## Acceptance Criteria

- [x] AC-1: `StaticShapeReranker.rerank(query, passages)` returns raw logits whose **absolute values
  match the BAAI FP32 fastembed reranker within ≤0.05 max abs diff across ≥3 distinct queries**
  (score-parity test) — so downstream logit-scale thresholds need no recalibration. The parity test
  also doubles as a **supply-chain integrity gate** on the `Xenova` re-export (a tampered/divergent
  export would not match the BAAI reference within tolerance). [council 2026-06-12] — **Measured 0.0154
  max / 0.0067 mean; `test_reranker_fp16_matches_baai_fp32_when_available` (GPU-gated, 3 queries).**
- [x] AC-2: With a GPU provider available, `_get_reranker()` returns the GPU accel reranker (CoreML
  static 64×512), verified by a live "using GPU-accelerated reranker" signal + `cpu/wall < 1`. —
  **Live: `make_reranker` → CoreML, 819 ms/batch, cpu/wall 0.08; ~13.9× vs CPU FP32.**
- [x] AC-3: With no GPU (or `WAVEFOUNDRY_EMBED_PROVIDER=cpu`), `_get_reranker()` returns the **CPU
  INT8 reranker** (same model, `model_int8.onnx` on `CPUExecutionProvider`, ~960 ms/query, no ranking
  loss) — CPU-only installs keep the cross-encoder. Reranking is skipped (→ vector order, logged once)
  only when explicitly disabled via `WAVEFOUNDRY_DISABLE_RERANKER` or when the model can't be built.
  No fastembed/BAAI reranker is loaded. Verified: `test_make_reranker_cpu_int8_when_no_gpu`,
  `test_make_reranker_gpu_fragmented_falls_back_to_cpu`, `test_make_reranker_disabled_returns_none`,
  + a live CPU-forced build (`provider=CPUExecutionProvider`). — **`_reranker_disabled` + one-time
  log; `test_make_reranker_none_when_no_gpu_available` / `_respects_explicit_cpu`.**
- [x] AC-4: The BAAI FP32 reranker is no longer downloaded/prewarmed/shipped on any machine; a fresh
  GPU setup caches the active Xenova FP16 export and a fresh CPU-only setup caches the active Xenova
  INT8 export (no `models--BAAI--bge-reranker-base`). — **fastembed `TextCrossEncoder` + `_warm_reranker`
  removed; reranker prewarms through `_prewarm_gpu_accel` on either hardware.**
- [x] AC-5: Cold-cache rebuild + first server query use the GPU reranker without a CPU-fallback
  regression (self-download + prewarm), and the first query does not pay the CoreML compile inline. —
  **Xenova FP16 self-downloads via `_resolve_clean_onnx` (CLEAN_ONNX_SOURCES); `_prewarm_gpu_accel`
  pays the compile at setup; server hardened to not import the heavy `onnx` package on a warm cache.**
- [x] AC-6 (important): End-to-end retrieval quality — agent ranking now uses the cross-encoder
  (rerank-first), and confidence is recalibrated on the unified sigmoid scale. **Validated on live-index
  retrievals: on-topic reranked top sigmoid 0.954–1.0, off-topic 0.0–0.069 (clean separation).**
  `docs_search`/`code_search` rerank paths unchanged.
- [x] AC-7: Full framework suite green. — **3153 tests OK (CPU-forced, hardware-independent), 83s.**

## Tasks

- [x] `accel_embedder.py`: `StaticShapeReranker` (pair tokenization; reranker static-pin for `[batch,1]`
  output via `build_static_onnx(output_is_logit=True)`; GPU FP16 / CPU INT8; `rerank()` raw-logit API;
  `offloads_to_gpu`) + `make_reranker` + reranker `CLEAN_ONNX_SOURCES` entry. Also generalized
  `GPU_PROVIDERS` to CoreML/CUDA/ROCm/DirectML (fixed the hardcoded-CUDA branch).
- [x] `indexer.py`: `RERANKER_MODEL` resolves (via `CLEAN_ONNX_SOURCES`) to the Xenova FP16 export.
- [x] `server_impl.py`: `_get_reranker()` hardware-selected via `make_reranker`; fastembed `TextCrossEncoder`
  removed. **Plus the agent-ranking integration: `_agent_rerank` (rerank-first), single `code_ask`
  path (local/RRF removed), sigmoid confidence recalibration.**
- [x] `setup_index.py`: reranker prewarms in `_prewarm_gpu_accel` (GPU FP16 or CPU INT8); `_warm_reranker` + the
  fastembed reranker prewarm/verify removed.
- [x] Tests: mocked accel-reranker dispatch + GPU-gated score-parity + CPU-fallback; 17 code_ask tests
  updated; `test_setup_index` reranker-prewarm tests fixed; suite forced CPU (hardware-independent).
- [x] ADR `1p52q-adr reranker-fp16-coreml-and-agent-ranking.md` + reranker row in `embedding-model.md`
  + `search-architecture.md` pointers.
- [x] Operator validation: cold-cache rebuild both-GPU; live reranker 13.9× + parity; confidence
  calibration on live retrievals. (Live before/after search-latency timing on the running MCP server is
  pending an MCP-server reload to pick up the new code.)

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| reranker accel class | implementer | — | `StaticShapeReranker` + pin + resolution |
| server dispatch + BAAI drop | implementer | reranker accel class | `_get_reranker` + prewarm |
| ADR + tests | qa-reviewer | reranker accel class | score-parity + dispatch |

## Serialization Points

- `accel_embedder.py` static-pin (shared with the embedder path — reranker output pin must not regress
  the embedder's `[batch, seq, hidden]` pin).
- `server_impl._get_reranker()` + all `reranker.rerank(...)` call sites (score scale must stay raw logit).
- `setup_index` prewarm set (dropping BAAI must not break offline cache verification).

## Affected Architecture Docs

`docs/architecture/embedding-model.md` (add a reranker model/format row + the FP16/CoreML note) and a
new ADR under `docs/architecture/decisions/`. `search-architecture.md` gets a discoverability pointer
(the reranker is part of the search ranking pipeline).

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | Score parity — without it the server thresholds mis-fire. |
| AC-2 | required | The acceleration itself. |
| AC-3 | required | CPU-only machines keep the cross-encoder via INT8; disabled/unbuildable rerankers degrade cleanly to vector order. |
| AC-4 | required | The BAAI-drop (cache savings + single GPU code path). |
| AC-5 | required | Cold-cache + prewarm robustness (the recurring failure mode). |
| AC-6 | important | Confirms retrieval quality is preserved. |
| AC-7 | required | No regressions. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-12 | Scoped after a feasibility probe. CPU FP32 10,622 ms/query → GPU FP16 766 ms/query (**13.9×**, cpu/wall 0.08); Spearman 0.9999, top-10 10/10, same #1; absolute logits max-diff 0.0154 / mean 0.0067 (fastembed returns raw logits — same scale). | `/tmp/rerank_fp16_probe.py` on the operator's M2 Max; fastembed `_post_process_onnx_output` returns `float(elem)` (raw logit). |
| 2026-06-12 | **CPU reranker fallback added (operator-directed) — reverses the GPU-only limitation.** Once the active model is the small ms-marco-L6, it runs usefully on the CPU EP too, so CPU-only installs no longer lose the cross-encoder. Measured on CPU: the FP16 export fails to init at `ORT_ENABLE_ALL` (the same SimplifiedLayerNormFusion cast bug, model-size-independent), but the **INT8 export** runs at full optimization at **~960 ms/query — 2× faster than FP32 (~1,910 ms) with ZERO ranking loss** (all 4 known answers still rank #1, off-topic still ~0). So: **GPU → FP16 (~350 ms), CPU → INT8 (~960 ms)**. `StaticShapeReranker` is now dual-precision (GPU FP16 / CPU INT8 via `_resolve_reranker_cpu_files` → `onnx/model_int8.onnx`); `make_reranker` builds whichever fits and falls GPU→CPU if a GPU graph doesn't offload. `WAVEFOUNDRY_EMBED_PROVIDER=cpu` now means "rerank on CPU"; a new `WAVEFOUNDRY_DISABLE_RERANKER` is the explicit off switch (set in `run_tests.py` to keep the suite fast). Prewarm + the server background-cache path build the reranker on either hardware. | CPU INT8 vs FP32 benchmark (958 vs 1913 ms, ranks [1,1,1,1]); live CPU reranker build (`provider=CPUExecutionProvider`). |
| 2026-06-12 | **Reranker model switched: bge-reranker-base → ms-marco-MiniLM-L-6-v2 (operator-directed, after head-to-head).** Operator flagged the ~26s CoreML compile/restart cost + the reranker's process footprint. Investigation: ORT's `ModelCacheDirectory` caches the ONNX→CoreML conversion, but bge (278M) re-specializes its 2 GB MLProgram into ~6.3 GB RSS every session regardless (warm load still ~26s); a small model (ms-marco-L6, 22M) is dominated by the cached conversion → warm load 3.1s. Head-to-head on the live index: ms-marco-L6 **beat bge on known-answer recall (mean rank 1.07 vs 1.67)**, ran **~4-5× faster** (~380ms vs ~1650ms/query), used **~8× less memory** (0.77 vs 6.3 GB RSS), 10× smaller cache. Newer small rerankers rejected: `gte-reranker-modernbert-base` fragments (24 partitions) + crashes on CoreML ANE; `jina-reranker-v2` = bge size; `mxbai-rerank-xsmall` has no FP16 export. Changed `RERANKER_MODEL` + added the ms-marco `CLEAN_ONNX_SOURCES` entry; rewrote the parity test to FP16-vs-FP32 of the ACTIVE model; confidence bands unchanged (ms-marco sigmoid separation on ≥0.99 / off ≤0.014). bge kept resolvable for back-compat. | live A/B recall eval (15/15 both, mean 1.07 vs 1.67); latency/RSS/cache measurements; `test_reranker_fp16_matches_fp32_when_available`. |
| 2026-06-12 | **Agent-ranking integration (operator req) — rerank-first + path removal + confidence recalibrated.** Wired the cross-encoder as a rerank-FIRST stage in `code_ask`'s agent path (unified `sigmoid(logit)` score before selection), removed the `rerank="local"` + `rrf_fallback` paths (`code_ask` single path now), generalized GPU support to CUDA/ROCm/DirectML. **Confidence band recalibrated on LIVE-index real retrievals:** on-topic reranked top sigmoid 0.954–1.0 (min 0.954), off-topic 0.0–0.069 (max 0.069) — clean separation, so `CONF_AGENT_RERANK_HIGH=0.5` / `_LOW=0.1` are well within the gap (the old `0.72` bge-cosine band retired; mixed arctic/bge cosine was never valid post-1p4wx). | live-index retrieval+rerank over 6 on-topic / 4 off-topic queries; `/tmp` calibration. |
| 2026-06-12 | **CPU-FP16 ruled out → temporary GPU-only decision (SUPERSEDED by the CPU INT8 row above).** The FP16 graph fails to init on the CPU EP at `ORT_ENABLE_ALL` (`SimplifiedLayerNormFusion` cast bug); loads at `BASIC`/`DISABLE_ALL` but runs **13.6 s vs 10.6 s** (slower than today — ORT has no native FP16 CPU kernels, casts per op, + 64-pad). Xenova FP32 is also 1 GB (no cache saving). The interim GPU-only path was replaced once the active small reranker proved viable as INT8 on CPU. | CPU-EP init error trace; CPU-FP16 BASIC = 13.6 s, max-diff 0.0071 vs BAAI; `Xenova onnx/model.onnx` = 1060 MB FP32. |
| 2026-06-13 | **Delivery review fixes applied.** Fixed CPU-only fresh-install dependency planning: `onnx` is now planned by default because the CPU INT8 reranker also builds a static 64×512 ONNX graph; only explicit `WAVEFOUNDRY_DISABLE_RERANKER` on a CPU/no-GPU machine omits it. Removed `_get_reranker()`'s unnecessary `HF_HUB_OFFLINE` mutation to avoid process-wide env races and allow the reranker resolver's own cached/download behavior. Corrected active `code_ask`/Guru/spec/ADR/change-doc contract text from the temporary GPU-only/no-cross-encoder wording to the final GPU FP16 / CPU INT8 behavior. | `run_tests.py` 3154 green; `wave_validate` docs-lint ok; new `test_planned_required_imports_respects_forced_cpu` + explicit disable case. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-12 | Accelerate the reranker with the Xenova FP16 export on CoreML. | ~14× per-query, identical ranking + score scale; reuses the `1p517` machinery. | Keep BAAI FP32/CPU (status quo — the search latency floor). |
| 2026-06-12 | **Hardware-selected reranker: GPU FP16, CPU INT8; BAAI dropped everywhere.** | FP16-on-CPU is slower and fragile, but the active small reranker has a viable INT8 CPU export (~960 ms/query, no ranking loss), so CPU-only installs keep the cross-encoder without the BAAI FP32 cache. | GPU-only vector-order fallback on CPU (rejected after the INT8 benchmark); keep BAAI FP32 fastembed on CPU (rejected: 1 GB cache + second code path). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| FP16 logits drift from FP32 → server thresholds mis-fire. | AC-1 score-parity test (≤0.05 max abs diff); measured 0.0154. |
| Reranker static-pin breaks the embedder's `[batch,seq,hidden]` output pin (shared helper). | Reranker-specific pin (dim0 only on the `[batch,1]` logit); embedder pin untouched; both unit-covered. |
| CoreML compile (~20 s) hits the first live query. | Prewarm at setup/server start; per-process singleton caches the compiled session. |
| CPU-only installs lose the cross-encoder rerank → lower retrieval quality. | RESOLVED: the CPU INT8 path keeps the cross-encoder on CPU-only installs (~960 ms/query, no ranking loss). Reranking is skipped only when explicitly disabled. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
