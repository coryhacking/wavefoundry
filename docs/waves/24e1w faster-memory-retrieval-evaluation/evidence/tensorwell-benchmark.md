# Tensorwell memory retrieval evaluation

Owner: Engineering
Status: verified
Last verified: 2026-11-26

Use local query-vector reuse and groups of eight on this qualified Tensorwell provider. Batching reduced full evaluation time by 31.3%, from 587.59 seconds to an average of 403.43 seconds. Scalar reuse alone averaged 477.07 seconds. Each configuration produced the same ordered results and scores.

## Full frozen workload

Each run evaluated 576 distinct logical queries. The table counts comparison query vectors and actual HTTP requests at the transport boundary, including any retries. Total HTTP calls include all timed embedding and reranking operations. The comparison time includes query inference and ordering both matrices.

| Run order | Elapsed s | Comparison vectors | Comparison HTTP calls | Total HTTP calls | Comparison s | Production handler s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Reference | 587.59 | 1,152 | 1,152 | 2,902 | 219.88 | 246.68¹ |
| Scalar reuse 1 | 472.55 | 576 | 576 | 2,326 | 95.18 | 258.89 |
| Batch 1 | 403.83 | 576 | 72 | 1,822 | 12.53 | 263.18 |
| Batch 2 | 403.03 | 576 | 72 | 1,822 | 12.35 | 259.95 |
| Scalar reuse 2 | 481.60 | 576 | 576 | 2,326 | 98.24 | 260.98 |

¹ The reference handler time includes 90 target-only lookup calls. Subsequent timings isolate the 576 scored production calls. In each run the dense control and sanity floor made 588 query requests, the two matrices embedded 306 documents in 10 requests, and production made 576 query requests and 576 reranking requests over 2,880 candidate documents.

Batching saved 68.72 seconds in the first scalar/batch pair and 78.57 seconds in the reverse-order pair. Within-mode elapsed times differed by 9.05 seconds for scalar and 0.80 seconds for batch. The production handler averaged 261.56 seconds, or 64.8% of batched elapsed time. It is the largest remaining cost.

## Ranking and fallback checks

For every case, the harness hashed its identity and both ordered ID lists (ranked and shown) before the evaluator could exclude a fallback arm. All four optimized runs matched the reference on all nine arms (no memory, grep, BM25, dense, hybrid, production, full context, summary-only and compact). All aggregate scores, bootstrap intervals, qualification counts and fallback reasons matched. The combined ranking digest was `4d5b3c938fc4bae8fd3012338d721284e790125eeb16d6623edbf72aece4d4d7`. Each full run had 389 held-out and 187 development cases. The real production handler qualified all 576.

In three additional runs the harness selected the first three frozen cases and injected a stale source response into the production vector lookup for the second case. Each configuration ran the real handler three times, recorded two qualified probes and one `memory_source_state_stale` fallback, and returned identical ordered outcomes before the production arm was excluded. A separate 20-input query-role check used groups of 8, 8 and 4, a duplicate and a raw input beginning with instruction text. All 384 float32 components of every batched vector exactly matched the corresponding scalar vector.

## Runtime and GPU observations

The host ran macOS 27.3 on arm64, Python 3.14.8, Tensorwell 0.5.2 and ONNX Runtime 1.30.0. Tensorwell selected the pinned 384-dimensional `arctic-fp16-coreml` embedder and `minilm-fp16-coreml` reranker. Every measured comparison response in the instrumented pair reported the CoreML execution provider and an executed CoreML partition. The wire operation used query role and interactive workload. The service advertised up to 128 items per request.

| Run | GPU samples | Mean device utilization | 95th percentile | Peak | Comparison server execution s | Comparison server queue s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Batch 2 | 199 | 74.6% | 81% | 100% | 12.00 | 0.06 |
| Scalar reuse 2 | 237 | 72.7% | 79% | 85% | 96.84 | 0.25 |

The repeat pair sampled the macOS IORegistry `Device Utilization %` counter approximately every two seconds across the whole evaluation. It covers every process on the host. Tensorwell reported `physical_gpu_proven=false`. Process-specific device occupancy and saturation remain unknown. Server timing sums come from the corresponding comparison responses.

## Reproduction conditions

The target was a filesystem snapshot of the current corpus and index. It contained 153 surfaced records, 100 archive register entries and published docs generation 6698 (epoch `34c315f20d8d4d92b1b3a748c445a3cb`). All runs read the same frozen v2 query set, digest `f46822136134ae634e4d975b3b864ed4c9135e428adf39a70e98e25a4a326a00`, and SQLite snapshot SHA-256 `501b1e5a3592270c0977db65147084fdce6a8ac488c9f35b38ab400479e7c5b1`. The harness loaded the reference evaluator from commit `c811fe09` and the wave implementation from a separate code snapshot. To select scalar reuse on the same provider it disabled the evaluation batch factory on the index instance.

Each fresh client warmed one generic embedding and one rerank through the resident service before timing `run_curated`. Both experimental matrices and the 12-query sanity floor ran inside the timer. Runs were serial and the framework suite waited. Ordinary host activity continued. One-minute system load at run boundaries ranged from 2.5 to 5.2. Service cache contents were unobserved. Client call counts measure requests reaching the service.

The dense control, production and the two comparison matrices still request 1,728 query vectors for 576 distinct inputs after local reuse. Ask Tensorwell whether a bounded, model- and role-specific cache would save inference across those independent callers, and how to measure hit rates with cold-cache controls. Persistent caching remains a separate decision.
