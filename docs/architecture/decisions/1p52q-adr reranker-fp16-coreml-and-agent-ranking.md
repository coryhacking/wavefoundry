# 1p52q-adr — FP16/CoreML reranker acceleration + cross-encoder in agent ranking

Owner: Engineering
Status: accepted
Last verified: 2026-06-12

## Context

The cross-encoder reranker (`RERANKER_MODEL = "BAAI/bge-reranker-base"`) runs on every
`docs_search`/`code_search`/`code_ask`, scoring ~30–60 query–passage pairs per query. It ran on
**CPU via fastembed** using the **FP32** `onnx/model.onnx` (a 1.0 GB download — the heaviest cache
item) and was the dominant search latency: ~10.6 s/query for 60 candidates on an M2 Max.

Two things made a better path available:
- The `1p517` work built a static-shape CoreML/CUDA acceleration harness (`accel_embedder`) and
  proved a clean transformers.js FP16 export runs as a single CoreML partition on the GPU.
- `Xenova/bge-reranker-base` ships exactly such an export (`onnx/model_fp16.onnx`, decomposed ops).

A probe on the operator's M2 Max measured **GPU FP16 766 ms/query vs CPU FP32 10,622 ms/query
(~13.9×)**, `cpu/wall=0.08` (genuine offload), with **identical ranking** (Spearman 0.9999, top-10
10/10, same #1) and **identical score scale** (fastembed returns the raw logit; FP16-vs-FP32 absolute
logits differ by max 0.0154 / mean 0.0067).

A separate force: the **docs/code embedding-model split (`1p4wx`)** put docs (arctic-embed-xs) and
code (bge-small) on **different cosine scales**. `code_ask`'s agent mode mixes docs+code candidates,
so its cosine-based selection AND its confidence band were comparing incomparable scores — a latent
correctness gap the cross-encoder can close (it scores relevance on one scale regardless of source).

## Decision

0. **Reranker model: `ms-marco-MiniLM-L-6-v2` (6-layer, 22M), Xenova FP16 export.** Initially this work
   accelerated `bge-reranker-base` (278M), but an operator-flagged restart-cost investigation led to a
   head-to-head that ms-marco-L6 won outright on this index: **better known-answer recall (mean rank
   1.07 vs 1.67)**, ~4–5× faster per query (~380 ms vs ~1,650 ms), ~8× less memory (0.77 vs 6.3 GB RSS),
   and — decisively — its CoreML compile cache actually accelerates restarts (3.1 s vs bge's ~26 s; bge
   re-specializes its 2 GB MLProgram into ~6 GB runtime every session regardless of `ModelCacheDirectory`,
   which only caches the ONNX→CoreML conversion). Newer small rerankers were evaluated and rejected:
   `gte-reranker-modernbert-base` fragments into 24 CoreML partitions and crashes on the ANE;
   `jina-reranker-v2-base` is the same 278M size as bge; `mxbai-rerank-xsmall` ships no FP16 ONNX.
   `bge-reranker-base` stays resolvable in `CLEAN_ONNX_SOURCES` for back-compat. (References below to
   "Xenova FP16 / drop BAAI" describe the acceleration mechanism, which is model-agnostic.)

1. **Accelerate the reranker with the Xenova FP16 export on the GPU.** New
   `accel_embedder.StaticShapeReranker` (cross-encoder pair tokenization; static-shape pin with a
   logit `[batch,1]` output; raw-logit `rerank()`; `offloads_to_gpu` self-protection).
   `make_reranker` picks the path for the hardware (GPU FP16 / CPU INT8, below).

2. **Drop the BAAI FP32 reranker; run the cross-encoder on whatever hardware is present.** On a GPU
   machine the reranker is the FP16 export (~350 ms/query). On a **CPU-only** machine it is the **INT8**
   export on `CPUExecutionProvider` at `ORT_ENABLE_ALL` (~960 ms/query — 2× faster than FP32, **no
   ranking loss**: all known answers still rank #1). FP16-on-CPU was rejected (fails to init at
   `ORT_ENABLE_ALL` — a `SimplifiedLayerNormFusion` cast bug — and is slow at `BASIC`); INT8 is the CPU
   precision. The fastembed `TextCrossEncoder` dependency is removed; BAAI FP32 is never downloaded.
   Reranking is skipped (→ vector/coverage order, logged once) only when explicitly disabled
   (`WAVEFOUNDRY_DISABLE_RERANKER`) or unbuildable. *(An earlier iteration of this ADR was GPU-only and
   dropped reranking on CPU; once the active model became the small ms-marco-L6 (Decision 0), the CPU
   INT8 path became viable and that limitation was removed.)*

3. **All GPU providers, not just CoreML.** `GPU_PROVIDERS` attempts CoreML, CUDA, ROCm, DirectML;
   CoreML gets the MLProgram/compile-cache options, every other EP takes the provider name with
   defaults (a latent CUDA-hardcode bug in the non-CoreML branch was fixed). `offloads_to_gpu`
   self-protects any provider that doesn't actually offload.

4. **Embed the cross-encoder into `code_ask`'s agent ranking as a rerank-FIRST stage; remove the
   other `code_ask` ranking paths.** Agent mode never used the cross-encoder; now `_agent_rerank`
   scores the full retrieved pool with the cross-encoder **before** `_agent_candidate_select`,
   replacing each candidate's `score` with the unified `sigmoid(logit)` ∈ [0,1]. This is required,
   not cosmetic: the per-index floor / relevance drop-off / text budget AND the confidence band now
   key off one scale instead of mixed arctic-vs-bge cosines. The `rerank="local"` cross-encoder path
   and the `rrf_fallback` (RRF) path in `search_combined` are removed — `code_ask` has a single path.
   `docs_search`/`code_search` keep their own independent rerank (unchanged). The `rerank` param is
   retained for API back-compat (`"agent"` default; `"local"` a deprecated alias); `rerank_mode` is
   always `"agent"` and the `reranked` bool tells whether the cross-encoder ran. The keyword-based
   second-hop symbol expansion (a `"local"`-path feature) is removed; agent mode's graph-based
   `graph_related` expansion (`1p4hu`) is the structural counterpart.

5. **Confidence recalibrated to the reranker's sigmoid scale.** The old `0.72` bge-cosine band is
   retired (invalid for mixed docs+code). When the cross-encoder ran, confidence uses
   `CONF_AGENT_RERANK_HIGH=0.5` / `CONF_AGENT_RERANK_LOW=0.1`; when reranking is disabled or
   unbuildable, confidence is count-based. Validated on live-index retrievals: on-topic reranked top sigmoid
   0.954–1.0, off-topic 0.0–0.069 — a clean gap the bands sit inside.

6. **Keep the doc-demotion prior.** The explanatory "code > narrative docs" demotion
   (`_demote_doc_results`) stays — a domain prior the cross-encoder doesn't encode. It multiplies the
   sigmoid score, so a strongly-relevant doc can still surface; the invariant is "demoted but present".

## Consequences

- **Every install keeps the cross-encoder** — GPU (FP16, ~350 ms) or CPU-only (INT8, ~960 ms, no
  ranking loss). Reranking is skipped (→ vector order) only when explicitly disabled. (Earlier
  iterations were GPU-only; the CPU INT8 path resolved that.)
- `code_ask` is simpler (one ranking path) and now returns relevance-ranked, best-first citations
  whenever the cross-encoder builds (FP16 on GPU, INT8 on CPU).
- Cache drops the large BAAI FP32 reranker; GPU machines cache the FP16 export and CPU-only machines
  cache the INT8 export.
- Score-parity (FP16 vs BAAI FP32, ≤0.05) doubles as a supply-chain integrity gate on the Xenova
  re-export.

## Alternatives considered

- **Hardware-aware reranker** (GPU FP16, CPU keeps BAAI FP32 fastembed): no CPU regression, but keeps
  the 1 GB on CPU boxes and two code paths. Rejected by operator for the single GPU path + cache win.
- **Global FP16 incl. CPU**: rejected — FP16-on-CPU is slower than today and fragile.
- **Reorder-only (cross-encoder for order, cosine for confidence/selection)**: rejected — the
  mixed-model cosine is not a valid selection/confidence scale post-`1p4wx`; rerank-first is required.

## References

- Change: `docs/waves/1p4wz embedding-retrieval-architecture/1p52p-enh fp16-coreml-reranker-acceleration.md`
- Builds on: `1p517` (accel harness), `1p4wx` (docs/code model split), `1p4hj`/`1p4hu` (agent mode).
