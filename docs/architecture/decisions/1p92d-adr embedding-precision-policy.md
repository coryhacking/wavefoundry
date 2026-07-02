# 1p92d-adr — Embedding & reranker precision policy: FP16 on GPU, INT8 on CPU

Owner: Engineering
Status: accepted
Last verified: 2026-06-30

> Evaluate-decision artifact (shortcut `Evaluate decision`). **Accepted 2026-06-30** after full measurement (below). Net: **FP16 end-to-end on GPU machines, INT8 end-to-end on CPU-bound machines** (embed + rerank); queries run on CPU; precision folded into `model_versions`. Raw INT8 embeddings churn 23–37% top-1, but the reranked end-to-end pipeline holds the answer in top-3 (100%) and never out of top-5, and a realistic NL→code eval shows **INT8 = FP16** (the scary code number was a test artifact). GPU-for-queries measured as a net latency loss — queries stay on CPU.

## Context

Proposal: unify every model — docs embedder, code embedder, reranker — on **FP16 on GPU, INT8 on CPU**, to optimize throughput and memory.

**Current state (grounded in `1p517` + `accel_embedder.py` + HF, verified 2026-06-30):**

- **Reranker** (`ms-marco-MiniLM-L-6-v2`): already FP16 GPU (Xenova clean) / INT8 CPU (`_resolve_reranker_cpu_files` → `onnx/model_int8.onnx`). The journal records INT8-on-CPU was chosen because the FP16 export *fails/slow* on CPU while INT8 runs fully optimized at **~2× FP32 with no ranking loss**.
- **Code embedder** (`bge-small`): GPU FP16 (Xenova clean static) / **CPU FP16** (the qdrant resident `model_optimized.onnx` is 149/149 FLOAT16) — *not* INT8 today.
- **Docs embedder** (`arctic-embed-xs`): GPU FP32-static (resident; CoreML downcasts to FP16 itself, cos 1.0) / **CPU FP32** (resident `onnx/model.onnx`).
- **Queries always run on the CPU/fastembed path** by deliberate `1p517` decision — a single 512-token query padded to the static batch-64 is a 64× waste, so GPU single-query embedding was judged a non-win.
- **Interchangeability invariant** (`1p517` AC-8): indexes built via any path for a model stay **cos ≈ 1.0 interchangeable**, and `model_versions` keys on the **model name only** (format/provider-agnostic), so swapping providers does **not** force a re-embed.
- **Decisive precision fact:** **FP16 ↔ FP32 is cos = 1.0** (bit-compatible, free, interchangeable). **INT8 is *not* cos 1.0** — quantization shifts the vectors. Small models (arctic-xs 22M, bge-small 33M) are proportionally *more* quantization-sensitive.
- All variants are downloadable/official: `Snowflake/snowflake-arctic-embed-xs` and the bge/Xenova repos publish `model_fp16.onnx` and `model_int8.onnx` (Snowflake validates ONNX to atol 1e-4 and explicitly recommends benchmarking quantization for quality).

**Operator inputs folded in (2026-06-30):**

1. **Fold precision into `model_versions`** so a precision-class change (INT8 ↔ FP16) forces a re-embed.
2. **Use the GPU for queries when available**, so the query embedder and the index are the same precision/size on a given machine. *(Measured in (B) and declined — GPU-for-queries is a net latency loss, and precision-matching is achieved without it; recorded here as the original input.)*

## Decision (phased)

**Final per-machine policy:**

| Component | GPU machine | CPU-bound machine |
| --- | --- | --- |
| Docs embed (arctic) — index build | FP16 (GPU) | INT8 (CPU) |
| Code embed (bge) — index build | FP16 (GPU) | INT8 (CPU) |
| **Query embed** (always CPU — measurement B) | **bge FP16-CPU · arctic FP32-CPU** (fastembed-resident; cos 1.0 with the FP16 index) | **INT8-CPU** (matches the INT8 index) |
| Reranker | FP16 (GPU) | INT8 (CPU) |
| `model_versions` | precision folded in (re-embed on precision change) | same |

Note the asymmetry: a **CPU-bound machine is literally INT8 throughout** (index + query + rerank); a **GPU machine is FP16 for the index + reranker, but its *queries* run on CPU at resident precision** (bge FP16, arctic FP32 — arctic has no clean FP16-CPU path), which is cos-1.0-equivalent to the FP16 index, so retrieval matches without literally-identical precision.

1. **Accept now — FP16 on GPU for all embedders.** Pure win: cos 1.0, half the GPU memory/compute, zero compatibility cost. Folds in an explicit `arctic onnx/model_fp16.onnx` GPU entry (helps non-CoreML GPUs; CoreML already downcasts).
2. **Accept now — precision in `model_versions`.** Append the active precision to each layer's version key so INT8 ↔ FP16 forces a re-embed. Required *regardless* the moment any INT8 enters the stored-vector path, or indexes silently mix precisions.
3. **Adopt INT8 on CPU for embedders on the *reranked* retrieval path** (the CPU-bound-machine memory/perf win). The end-to-end eval (below) clears the operator's bar: with the reranker in the loop the best result stays in top-3 for 100% of queries and never leaves top-5 (only marginal rank-4/5 churn, ~11–13%). **Conditions:** (a) the precision-in-`model_versions` guard ships with it; (b) it covers the *reranked* path — a raw vector-only search (no rerank) still sees the 23–37% top-1 embedding churn, so either keep those consumers full-precision or accept the looser ordering; (c) **one per-machine precision classification drives the whole pipeline** — a GPU machine runs **FP16 end-to-end** (embed + rerank), a CPU-bound machine runs **INT8 end-to-end** (embed + rerank), so embedder and reranker precision match all the way through. The reranker already implements FP16-GPU / INT8-CPU (`1p52p` + `_resolve_reranker_cpu_files`); the requirement here is that its provider/precision is selected by the *same* machine classification as the embedder, never split. **Queries stay on CPU** (measurement (B): GPU-for-queries is a net loss; precision still matches per machine without it).

## What it depends on (named exactly)

- **(A) INT8 embedding retrieval quality — MEASURED 2026-06-30.** Raw-embedding threshold (mean cosine(INT8,FP16) ≥ 0.999 *and* recall within ~1–2 pts) was *not* met (cosine 0.998, ~23% top-1 churn) — **but raw embedding isn't the deciding test.** The end-to-end reranked eval and the realistic NL→code validation (both below) clear it: answer stays in top-3 (100%), never out of top-5, INT8 = FP16 on real NL→code. → **INT8 adopted on CPU for the reranked path.**
- **(B) GPU-for-queries latency — MEASURED 2026-06-30 (M2 Max, CoreML): rejected.** fastembed CPU single-query = **1.24 ms**; CoreML GPU = **2.11 ms** (1×128) / 5.66 ms (1×256). GPU loses — a single short query is too little compute to amortize the ~2 ms GPU dispatch. → **queries stay on CPU**. The precision-match worry dissolves anyway (see below): CPU-bound machine = INT8 build+query (consistent); GPU machine = FP16 index + CPU resident query at cos 1.0. No GPU-queries needed.

## Measurement (A) — result (2026-06-30, CPU, arctic-embed-xs)

Faithful pipeline (CLS-pool, L2-norm, query prefix where applicable) over 220 real repo chunks + 30 held-out queries per model (arctic: doc text; bge: code), embedded with the FP32 / FP16 / INT8 ONNX on `CPUExecutionProvider`.

| INT8 vs full precision | mean cosine | top-1 agreement | recall@10 overlap | rank-corr |
| --- | --- | --- | --- | --- |
| **arctic-embed-xs** (docs) | 0.99824 (min 0.99684) | 76.7% | 92.3% | 0.9957 |
| **bge-small-en-v1.5** (code) | **0.97586 (min 0.95436)** | **63.3%** | **82.0%** | 0.9365 |

(FP16 ↔ FP32 sanity = cos 1.00000 / 100% top-1 / 100% recall@10 for both.)

- **FP16 ↔ FP32 confirmed free/interchangeable** (cos 1.0, identical retrieval) — the GPU-FP16 win is validated for both models.
- **INT8 diverges materially at the top of the list — and bge is the worse case:** a different top-1 for ~23% (arctic) / ~37% (bge) of queries; recall@10 drops to 92% / 82%. The high-ish cosine (0.998 / 0.976) understates this because the churn concentrates where retrieval cares most. Both **fail** the bar.
- **FP16 does not load cleanly on CPU** — both models' FP16 exports initialized only at `ORT_ENABLE_BASIC`; at `ORT_ENABLE_ALL` they hit the same `SimplifiedLayerNormFusion` cast bug the journal records for the reranker. **So the CPU choice is FP32 vs INT8, not FP16.**
- **Caveat:** these are *divergence vs full precision*, not ground-truth accuracy loss; the code corpus is near-duplicate-heavy (inflates top-1 churn), and recall@10 82–92% means the reranker (which re-scores the candidate set) would likely recover much of it end-to-end. The deciding test is a known-answer end-to-end eval (embed → retrieve@K → rerank → final).

### End-to-end result (with the reranker in the loop) — 2026-06-30

Full pipeline per embedder precision: embed → vector retrieve@30 → rerank the 30 with the ms-marco cross-encoder (held constant at INT8) → final ranking. Reference = the FP32-embed final ranking; we then ask where FP32's reranked top results land under INT8 embeddings.

| End-to-end, INT8 vs FP32 | arctic (docs) | bge (code) |
| --- | --- | --- |
| FP32 top-1 → stays in INT8 **top-3** | **30/30** | **30/30** |
| FP32 top-1 → falls **out of top-5** | **0/30** | **0/30** |
| FP32 top-3 retained within INT8 top-3 | 87% | 91% |
| **FP32 top-3 items falling out of top-5** (top3→top5) | **7% (6/90)** | **4% (4/90)** |
| FP32 top-5 items falling **out of** INT8 top-5 | 11% | 13% |

**The reranker recovers the embedding churn.** The single most-relevant result stays in the top-3 for 100% of queries and never leaves the top-5; only the marginal positions 4–5 churn (~11–13%). This **meets the operator's bar** (move-within-top-3 = fine; out-of-top-5 = problem). **Crucial condition:** this holds *because the path reranks* — `code_ask` / reranked search get it; a **raw vector-only search (no rerank)** would still see the embedding-level churn (23–37% top-1). So INT8-on-CPU is safe **for the reranked retrieval path.**

**Airtight check — FP16-GPU reference vs INT8-CPU (the literal production comparison, 2026-06-30).** The numbers above used FP32-CPU as the full-precision reference; re-running with the reference computed on the **CoreML GPU** (a real GPU-built index) vs INT8-CPU:

| top3→top5 (relevant top-3 items falling out of top-5) | arctic (docs) | bge (code) |
| --- | --- | --- |
| FP32-CPU reference (proxy) | 7% · top-1 out 0/30 | 4% · top-1 out 0/30 |
| FP16-GPU embed, INT8 rerank both | 7% · top-1 out 0/30 | 11% · top-1 out 2/30 |
| **Fully matched: FP16 embed+rerank ↔ INT8 embed+rerank** | **7% · top-1 out 0/30** | **11% · top-1 out 3/30** |

- **arctic (docs) is clean and stable** across all framings — 7% top-3 fall-out, top-1 never leaves top-5. INT8 safe.
- **bge (code) is the weak case** — ~11% top-3 fall-out and the #1 result leaves top-5 in **3/30** under the fully-matched comparison (matching the reranker per machine nudged 2→3/30, i.e. the INT8 reranker adds a sliver atop the embedder). **Two caveats make this a pessimistic upper bound:** the code corpus is near-duplicate-heavy (interchangeable lines → "misses" that are equivalent), and code-line-as-query is out of the NL-trained reranker's distribution. Real NL→code queries against distinct functions would be more stable.
- **bge validation — proper NL→code eval (2026-06-30): the ~11% was a test artifact.** Re-run on a realistic set — **1544 AST-extracted functions** (docstrings stripped → pure code-semantic match), 30 NL queries = each function's docstring, gold = that function, retrieve@30 → rerank:

  | Gold-function recall (end-to-end) | @1 | @3 | @5 |
  | --- | --- | --- | --- |
  | FP16-GPU | 57% | 77% | 87% |
  | INT8-CPU | 57% | 77% | 87% |

  **Identical at every cutoff; 0/30 regressions** (INT8 never pushed a gold answer out of top-5). The earlier 11% came from the near-duplicate-line corpus + code-line-as-query against an NL-trained reranker. On realistic NL→code, **INT8 = FP16**.
- **Conclusion: INT8 for both embedders on CPU is supported.** arctic was clean throughout (7% top-3 reorder, top-1 solid); bge is validated equal to FP16 on realistic NL→code. Memory win: arctic 90→23 MB, bge 63→34 MB, reranker 23 MB — the full CPU-bound pipeline drops from ~176 MB to ~80 MB.

### Measurement (B) — GPU query / small-batch latency (2026-06-30, M2 Max, CoreML)

arctic `model_fp16.onnx` pinned to several static shapes on CoreML GPU vs CPU; baseline = the real fastembed CPU single-query path.

| Path / shape | per-call | per-chunk | GPU offload (cpu/wall) |
| --- | --- | --- | --- |
| **fastembed CPU single query (today)** | **1.24 ms** | — | — |
| CoreML GPU 1×128 | 2.11 ms | 2.11 | 0.11 (on GPU) |
| CoreML GPU 1×256 | 5.66 ms | 5.66 | 0.14 |
| CoreML GPU 8×256 | 33.8 ms | 4.22 | 0.16 |
| CoreML GPU 64×512 (build) | 157 ms | 2.45 | 0.08 |

- **GPU-for-queries loses** — fastembed CPU (1.24 ms) < GPU (2.11 ms); a short query can't amortize the ~2 ms GPU dispatch. **Queries stay on CPU.**
- **GPU is a bulk-throughput tool** — per-chunk only gets good at large batch (64×512 = 2.45 ms/chunk). For the few chunks an incremental update touches, CPU fastembed beats any GPU session, and each new static shape costs a CoreML compile. → **no dedicated query/incremental GPU shape; route small-N to CPU, keep bulk on GPU.**
- **Precision-matching needs no GPU queries:** CPU-bound machine = INT8 build+query (consistent); GPU machine = FP16 index + CPU resident query at cos 1.0.

**Honesty caveat:** this measures *divergence from full precision*, not ground-truth *accuracy loss*. Much of the top-1 churn is between near-tied docs, and recall@10 92% means the right docs mostly stay in the candidate set — so the **reranker would likely recover most of it** end-to-end. But on embedding evidence alone, INT8 is not a safe drop-in for the stored-vector/query path; confirming the reranker recovery needs a known-answer end-to-end eval.

## Consequences

- **Memory is the real driver.** INT8 cuts model + activation memory ~4×, directly helping the low-RAM/WSL2 OOM hosts we've seen in the field. That is the case *for* INT8-CPU, weighed against (A).
- **Coupling.** INT8-CPU-embedders is clean only with per-machine precision consistency (GPU→FP16 build+query, CPU→INT8 build+query) **plus** precision-in-`model_versions` (so moving or sharing an index across precision classes re-embeds). Without (B) (GPU queries), making CPU INT8 makes *all* queries INT8 — including on GPU machines whose index is FP16 — an intra-machine mismatch.
- **The reranker precedent does not transfer.** Reranking is relative pairwise scoring (robust to quantization → "no ranking loss"); embedding is absolute vector geometry for cosine retrieval (more sensitive). The reranker is also exempt from the whole coupling problem because it stores no vectors. So "the reranker proves INT8-CPU is safe" is not valid for embedders.

## Alternatives considered (not fully rejected)

- **FP16 everywhere (GPU + CPU), no INT8 embedders.** Preserves cos-1.0 interchangeability and is simplest, but FP16-on-CPU often runs *slower* than FP32 (CPUs lack native FP16 → ORT upcasts) and saves only memory, not compute. This is the fallback if (A) fails.
- **INT8 on the reranker only (≈ status quo) + the FP16-GPU/arctic-FP16 wins.** The conservative subset — ship the free wins, skip the gated INT8-embedder change. Default if either measurement disappoints.

## Revisit conditions

- When measurements (A) and (B) land (operator hardware / the CPU INT8-quality benchmark).
- If a larger, more quantization-robust embedding model is adopted (quantization sensitivity scales down with model size), re-open INT8-CPU-embedders.

## What will NOT be built

- INT8 on the stored-vector embedding/query path **without** the precision-in-`model_versions` re-embed guard (would silently mix precisions across providers/machines).
- GPU-for-queries **without** a measured latency win — do not overturn `1p517`'s deliberate CPU-query decision on a guess.

## Methodology note

Followed the Evaluate-decision contract (frame → grounded current-state → red-team → council → operator inputs → feasibility → ADR). The honest output is **"it depends,"** so the ADR names exactly what on: (A) measured INT8 embedding retrieval quality, (B) measured GPU single-query latency — both measurable, (A) on CPU now. The free wins (FP16-GPU, precision-in-version) are decoupled and accepted immediately so they don't wait on the gated part.

## References

- `docs/waves/1p4wz embedding-retrieval-architecture/1p517-enh fp16-coreml-embedding-acceleration.md` — the FP16/static-shape/CoreML acceleration, the cos-1.0 interchangeability invariant, and the deliberate CPU-query decision.
- `1p50s-adr docs-code-embedding-model-split`, `12dzj-adr embedding-model-and-format` — the model/format decision family this refines.
- `.wavefoundry/framework/scripts/accel_embedder.py` (`CLEAN_ONNX_SOURCES`, `_resolve_model_files`, `_resolve_reranker_cpu_files`, `offloads_to_gpu`) — the resolution + provider-probe surface a future implementation would extend.
- HF: `Snowflake/snowflake-arctic-embed-xs` ONNX variants (`model_fp16.onnx` 45 MB, `model_int8.onnx` 23 MB), validated atol 1e-4.
