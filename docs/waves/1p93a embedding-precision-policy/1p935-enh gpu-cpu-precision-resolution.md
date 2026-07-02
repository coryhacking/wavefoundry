# Provider-aware embedding precision: FP16 on GPU, INT8 on CPU

Change ID: `1p935-enh gpu-cpu-precision-resolution`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-30
Wave: `1p93a embedding-precision-policy`

## Rationale

ADR `1p92d` (accepted) sets the policy: a GPU machine runs the embedders at **FP16**, a CPU-bound machine runs them at **INT8** — for memory and CPU throughput. Today only the GPU side is precision-aware: the index build uses the `StaticShapeEmbedder` (FP16 clean export for bge; FP32-static resident for arctic, which CoreML downcasts), while every **CPU** path uses the **fastembed-resident** model — `bge-small` at FP16 (qdrant resident) and `arctic-embed-xs` at **FP32** (`onnx/model.onnx`). There is **no INT8 embedder path** for either model; the reranker already does FP16-GPU / INT8-CPU (`_resolve_reranker_cpu_files`), and this change brings the embedders to parity.

The evaluation backing the policy (recorded in `1p92d`): raw INT8 embeddings churn 23–37% top-1, but end-to-end **with the reranker** the answer stays in top-3 (100% of queries) and never leaves top-5, and a gold-labeled NL→code eval shows **INT8 = FP16** (recall@1/3/5 identical, 0/30 regressions). So INT8-on-CPU is safe for the reranked retrieval path.

## Requirements

1. **Add arctic to `CLEAN_ONNX_SOURCES`** (`accel_embedder.py:69`): `"Snowflake/snowflake-arctic-embed-xs": ("Snowflake/snowflake-arctic-embed-xs", "onnx/model_fp16.onnx", "tokenizer.json")`. The base Snowflake repo publishes both `model_fp16.onnx` (45 MB) and `model_int8.onnx` (23 MB), so this one entry is the source for **both** the GPU FP16 path and the CPU INT8 path.
2. **CPU-INT8 embedder resolution.** Add `EMBEDDER_CPU_ONNX_FILE = "onnx/model_int8.onnx"` and `_resolve_embedder_cpu_files(model_name)` mirroring `_resolve_reranker_cpu_files` (`accel_embedder.py:184-200`) — resolve the INT8 graph + tokenizer from the model's `CLEAN_ONNX_SOURCES` entry, cached-first under `onnx-src`.
3. **Bespoke INT8-CPU ORT embedder.** A CPU embedder over the INT8 graph (tokenize → run on `CPUExecutionProvider` → CLS-pool → L2-normalize), reusing the `StaticShapeEmbedder` machinery where possible. Its static-shape / compile cache key must be **distinct** from the FP16 GPU graph cache (e.g. `cpu_int8_static_…`) to avoid colliding at `accel_embedder.py:278`.
4. **Wire into the dispatch.** In `make_embedder` (`accel_embedder.py:400-438`), the CPU fallback arm (currently `return None` at `:434`) builds the INT8-CPU embedder when `_resolve_embedder_cpu_files` resolves; otherwise it still returns `None` (→ fastembed). This makes `indexer._get_embedder` (`indexer.py:2066-2102`) return the INT8-CPU embedder on a CPU-bound machine instead of falling through to fastembed.
5. **Query path parity (second dispatch site).** `server_impl._get_embedder` (`server_impl.py:887-928`) is a separate, server-only embedder with **no accel path** — it always uses fastembed. Wire the same INT8-CPU resolution here so that on a CPU-bound machine **queries** embed at INT8 to match the INT8 index. (On a GPU machine, queries stay fastembed-resident — FP16/FP32, cos 1.0 with the FP16 index — per ADR `1p92d` measurement B.)
6. **Arctic GPU FP16 — CoreML safety.** Verify the arctic `model_fp16.onnx` clean export still **single-partitions and GPU-offloads on CoreML at cos 1.0** vs the current resident-FP32-static path. If it regresses CoreML (e.g. the `SimplifiedLayerNormFusion`/partition issue), make selection **provider-conditional**: CoreML keeps the proven resident-FP32-static path; the FP16 clean entry is used for **CUDA/DML** only. Do not regress the working CoreML path.
7. **Prewarm coverage.** `setup_index._prewarm_gpu_accel` (`setup_index.py:1026-1064`) short-circuits embedder prewarm on CPU-only machines via the GPU guard (`:1053`). Add a CPU-embedder prewarm block parallel to the reranker block (`:1037-1048`) so the INT8-CPU embedder is prewarmed on CPU-bound machines.

## Scope

**Problem statement:** the embedders have no INT8-CPU path; CPU-bound machines pay full-precision memory/latency (arctic FP32 90 MB, bge FP16 63 MB) when INT8 (23 / 34 MB) is retrieval-equivalent on the reranked path.

**In scope:**

- `accel_embedder.py`: arctic `CLEAN_ONNX_SOURCES` entry; `_resolve_embedder_cpu_files` + `EMBEDDER_CPU_ONNX_FILE`; the INT8-CPU embedder + its cache key; the `make_embedder` CPU-fallback wiring; the arctic FP16 CoreML verification (provider-conditional if needed).
- `indexer.py`: confirm `_get_embedder` returns the new CPU-INT8 embedder (the existing fall-through already does, once `make_embedder` returns non-`None`).
- `server_impl.py`: add the INT8-CPU path to `_get_embedder` for the query side.
- `setup_index.py`: CPU-embedder prewarm block.
- `tests/test_accel_embedder.py`: mocked-provider tests for CPU-INT8 dispatch; retrieval-parity gate (operator-run on real models).

**Out of scope:**

- Precision in `model_versions` (the re-embed guard) → change `1p936`.
- Reranker/embedder shared provider classification → change `1p937`.
- Incremental small-N → CPU routing → change `1p938`.
- Any model swap (arctic-xs / bge-small stay; ADR `1p92d` declined v1.5/v2.0).

## Acceptance Criteria

- [x] AC-1: on a CPU-bound machine (no GPU offload), both arctic and bge embed the **index** via the INT8 graph (`onnx/model_int8.onnx`) — verified by the resolved embedder/path, not fastembed-resident. Evidence: `accel_embedder.make_embedder` no-GPU arm builds `StaticShapeEmbedder(["CPUExecutionProvider"])` via `_resolve_embedder_cpu_files` (`accel_embedder.py`); `test_make_embedder_int8_cpu_when_no_gpu_registered_model`, `test_resolve_embedder_cpu_files_returns_int8_and_tokenizer` (`test_accel_embedder.py`); `indexer._get_embedder` returns it (`IndexerAccelDispatchTests`).
- [x] AC-2: on a CPU-bound machine, the **query** path (`server_impl._get_embedder` → `_embed_query`) also embeds at INT8, so query and index precision match. Evidence: `server_impl.py:_get_embedder` reads the recorded class and builds `accel_embedder.StaticShapeEmbedder([CPU])` when `int8`; `test_get_embedder_uses_int8_when_index_recorded_int8`, `test_get_embedder_uses_fastembed_when_index_recorded_full` (`test_server_tools.py`).
- [x] AC-3: on a CoreML GPU machine, arctic GPU embedding still GPU-offloads via the `model_fp16.onnx` clean export (single CoreML partition). **VALIDATED on real hardware (M2 Max, operator-run 2026-06-30):** a cold full rebuild (accel caches cleared → arctic FP16 static graph rebuilt from the new source) logged `using GPU-accelerated embedder for Snowflake/snowflake-arctic-embed-xs (CoreMLExecutionProvider, static 64x512)` — the `offloads_to_gpu()` probe passed (single-partition; a fragmented graph would have failed the probe → fastembed fallback). The uniform-FP16 path holds; the provider-conditional fallback is NOT needed. (cos 1.0 vs fastembed is the standing `SemanticEmbeddingRegressionTests` invariant, unchanged by the FP16 source swap.)
- [x] AC-4: end-to-end retrieval parity holds (reranked path). **VALIDATED on real models (M2 Max, operator-run 2026-06-30):** built an INT8-CPU index alongside the FP16-GPU index and ran the committed 32-query gold set (`retrieval_eval.json`) through the reranked `search_combined` path against BOTH. **(A) FP16 top-1 was rank-1 in the INT8 index for 32/32 queries** (within top-3: 32/32, top-5: 32/32). **(B) recall@k vs gold:** recall@1 10=10, recall@3 11=11, recall@5 FP16 15 / INT8 14 (Δ=−1, one docs query — within the ≤1 tolerance). Verdict PASS. **Caveat:** this reproduces the `1p92d` *spirit* using the only committed gold set (32-query, path-prefix matching); the ADR's exact 30-query AST-extracted NL→code set was never committed, so it is not a literal reproduction. Eval harness: `scratchpad/ac4_eval.py` (drives `WaveIndex` with an `index_dir` override per index; the same GPU-FP16 reranker rescopes both, isolating embed precision).
- [x] AC-5: `setup_index` prewarms the INT8-CPU embedder on a CPU-bound machine (no longer skipped by the GPU guard). Evidence: `setup_index._prewarm_gpu_accel` runs the embedder-prewarm loop unconditionally (the GPU-availability early-return was removed); `make_embedder` resolves INT8 on a CPU host.
- [x] AC-6: full framework suite + docs-lint green; `test_accel_embedder` covers the CPU-INT8 resolve + dispatch with mocked providers (no physical GPU required). Evidence: 3,755 tests OK; `AccelEmbedderTests` (make_embedder int8/gpu/no-offload dispatch), `IndexerAccelDispatchTests`, resolver tests.

## Tasks

- [x] Add the arctic `CLEAN_ONNX_SOURCES` entry (`framework_edit_allowed`). Done: `accel_embedder.py` (points at the base Snowflake repo; publishes both fp16 + int8).
- [x] Add `EMBEDDER_CPU_ONNX_FILE` + `_resolve_embedder_cpu_files` (mirror `_resolve_reranker_cpu_files`). Done: `accel_embedder.py`.
- [x] Build the INT8-CPU embedder + a distinct compile/static cache key; wire the `make_embedder` CPU-fallback arm. Done: `StaticShapeEmbedder` dual-precision branch (`cpu_int8_static_…` key); `make_embedder` no-GPU arm.
- [x] Wire the INT8-CPU path into `server_impl._get_embedder` (query side). Done: `server_impl.py` (reads recorded class → INT8 accel or fastembed).
- [x] Verify arctic `model_fp16.onnx` on CoreML (single-partition + cos 1.0); decide uniform-FP16 vs provider-conditional; record in Decision Log. **DONE (operator-run, M2 Max, 2026-06-30): arctic FP16 GPU-offloads on CoreML — uniform-FP16 confirmed, no provider-conditional fallback needed.** (See AC-3 + Decision Log.)
- [x] Add the CPU-embedder prewarm block in `setup_index._prewarm_gpu_accel`. Done: the embedder-prewarm loop now runs regardless of GPU availability.
- [x] Add mocked-provider tests; run the suite + docs-lint. Done: 3,755 tests OK; docs-lint clean. **The operator retrieval-parity gate (AC-4) is operator-run before close.**

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| arctic source + CPU-INT8 resolver | implementer | — | `accel_embedder.py` `CLEAN_ONNX_SOURCES` + `_resolve_embedder_cpu_files` |
| INT8-CPU embedder + dispatch wiring | implementer | resolver | `make_embedder` fallback arm; distinct cache key |
| query-side wiring | implementer | dispatch | `server_impl._get_embedder` |
| CoreML FP16 verification | implementer | arctic source | provider-conditional decision |
| prewarm + tests | qa-reviewer | all | `setup_index` block; mocked-provider tests; AC-4 gate |

## Serialization Points

- `accel_embedder.make_embedder` — both the index (`indexer._get_embedder`) and query (`server_impl._get_embedder`) dispatch paths converge here; land the resolver + embedder before wiring either site.
- `CLEAN_ONNX_SOURCES` — the arctic entry is shared by the FP16-GPU and INT8-CPU resolvers (and by change `1p937`'s reranker path conceptually); single source of truth.
- The CPU-INT8 embedder's compile/cache key must not collide with the FP16 GPU graph cache.

## Affected Architecture Docs

`docs/architecture/embedding-model.md` — add the provider-conditional precision (FP16-GPU / INT8-CPU) runtime and the dual dispatch sites. ADR `docs/architecture/decisions/1p92d-adr embedding-precision-policy.md` is already accepted and is the source of record.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The INT8-CPU index path is the core of the change. |
| AC-2 | required | Query must match index precision or retrieval degrades. |
| AC-3 | required | Must not regress the proven CoreML arctic GPU path. |
| AC-4 | required | Correctness gate — INT8 retrieval parity is the whole basis. |
| AC-5 | important | Prewarm avoids a cold first-call penalty on CPU hosts. |
| AC-6 | required | No regressions; CI without GPU. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-30 | Drafted from ADR `1p92d` + the implementation surface map. | `1p92d-adr`; guru map (accel_embedder/indexer/server_impl/setup_index line cites). |
| 2026-06-30 | Implemented all CI-verifiable scope: `StaticShapeEmbedder` dual-precision (FP16-GPU / INT8-CPU), `make_embedder` no-GPU→INT8 + GPU-no-offload→fastembed-full, query-side precision-from-index, prewarm. AC-1/2/5/6 met; AC-3/AC-4 operator-gated on real hardware. | `accel_embedder.py`, `indexer.py`, `server_impl.py`, `setup_index.py` diffs; new tests in `test_accel_embedder.py`/`test_server_tools.py`; 3,755 tests OK |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-30 | One arctic `CLEAN_ONNX_SOURCES` entry serves both GPU FP16 and CPU INT8 (both files in the Snowflake base repo). | Avoids a second source; matches the bge pattern. | Separate GPU/CPU source entries (rejected — both files coexist in one repo). |
| 2026-06-30 | Arctic CoreML path: prefer uniform `model_fp16.onnx`, but fall back to provider-conditional (resident-FP32 on CoreML) if it regresses. | The resident-FP32-static CoreML path is proven (cos 1.0, ~24×); FP16 mainly helps CUDA/DML. | Force FP16 on CoreML unconditionally (rejected — risks the `SimplifiedLayerNormFusion` partition issue). |
| 2026-06-30 | A GPU-present machine whose graph doesn't offload falls back to fastembed **full**, NOT INT8-CPU. | INT8 is the classification for a CPU-BOUND machine (no GPU); using it for one model while another runs FP16 on the same GPU machine would split the pipeline precision (1p937) AND diverge from `_predicted_precision_class` (which reports "full" whenever a GPU exists), forcing perpetual re-embeds via the 1p936 guard. | Fall through to INT8-CPU on any non-offload (rejected — the original cut; caused the perpetual-rebuild divergence, fixed during implementation). |
| 2026-06-30 | **Arctic CoreML = uniform `model_fp16.onnx`** (the provider-conditional resident-FP32 fallback is NOT needed). | Operator-run cold rebuild on M2 Max confirmed arctic FP16 single-partitions and GPU-offloads on CoreML (`offloads_to_gpu()` probe passed; log: `using GPU-accelerated embedder … CoreMLExecutionProvider`). The feared `SimplifiedLayerNormFusion`/fragmentation regression did not occur. | Provider-conditional (CoreML resident-FP32, FP16 for CUDA/DML only) — kept as a documented contingency but unused; arctic's own export is already clean, unlike bge-small's fastembed graph. |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Arctic `model_fp16.onnx` is CoreML-hostile (fragments to CPU). | AC-3 verifies single-partition; provider-conditional fallback keeps CoreML on resident-FP32. |
| Query path (`server_impl`) left on fastembed → INT8 index queried by full-precision vectors. | AC-2 wires INT8 into `server_impl._get_embedder`; query precision follows the index (change `1p936`). |
| Two dispatch sites drift (indexer vs server_impl). | Share the resolver/embedder construction through `accel_embedder`; test both paths. |
| INT8-CPU graph cache collides with FP16 GPU cache. | Distinct compile/static cache key (`cpu_int8_…`). |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
