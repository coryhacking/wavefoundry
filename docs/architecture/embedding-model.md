# Embedding Model

Owner: Engineering
Status: active
Last verified: 2026-07-01

## What This Document Covers

How semantic search works in Wavefoundry, why the design choices were made the way they were, what the regression tests protect, and what to do when the model needs to change.

---

## Why Semantic Search at All

Wavefoundry's docs corpus (wave records, change docs, prompts, seeds, architecture docs) is navigated by agents that often don't know the exact file name or keyword to search for. They might ask "how do I start a wave?" when the relevant docs say "prepare wave" or "wave lifecycle." Lexical search fails this class of query; embedding-based semantic search handles it naturally.

The trade-off is operational complexity: the model must be cached locally before the server can embed queries, and the stored index vectors must have been produced by the same model that's used at query time. Both of these constraints are enforced explicitly rather than left implicit.

---

## Current Model

| Constant | Value | Dimension | Defined in |
|----------|-------|-----------|------------|
| `DOCS_MODEL` | `Snowflake/snowflake-arctic-embed-xs` | 384 | `indexer.py` |
| `CODE_MODEL` | `BAAI/bge-small-en-v1.5` | 384 | `indexer.py` |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` (logical) → `Xenova/ms-marco-MiniLM-L-6-v2` `onnx/model_fp16.onnx` (GPU) | logit | `indexer.py` |

### Reranker (cross-encoder), FP16-on-GPU / INT8-on-CPU (1p52p, ADR `1p52q`)

The cross-encoder reranker scores query↔passage **pairs** on every search, embedded as a
**rerank-FIRST** stage in `code_ask`'s agent ranking (see `search-architecture.md`)
(`accel_embedder.StaticShapeReranker`). It runs on whatever hardware is present: **FP16 on the GPU**
(CoreML/CUDA/ROCm/DirectML, ~350 ms/query) or **INT8 on the CPU** (`model_int8.onnx` on
`CPUExecutionProvider`, ~960 ms/query — 2× faster than FP32, no ranking loss). Reranking is skipped
(→ vector/coverage order) only when explicitly disabled (`WAVEFOUNDRY_DISABLE_RERANKER`) or unbuildable.

**Active model: `ms-marco-MiniLM-L-6-v2`** (6-layer, 22M) via its Xenova FP16 export. It was chosen
over the SOTA-but-heavy `bge-reranker-base` (278M) after a head-to-head on this index:

| | bge-reranker-base | **ms-marco-MiniLM-L-6** |
| --- | --- | --- |
| Known-answer recall (mean rank) | 1.67 | **1.07** |
| Per-query rerank (~60 cands) | ~1,650 ms | **~380 ms** |
| Process RSS | 6.3 GB | **0.77 GB** |
| Warm load / restart | ~26 s (cache ineffective) | **3.1 s** (cache works) |
| CoreML cache | 2.0 GB | **0.2 GB** |

ms-marco-L6 matched or beat bge on every axis here. The restart difference is structural: ORT's
`ModelCacheDirectory` caches the ONNX→CoreML conversion, but for a 278M model CoreML re-specializes the
2 GB MLProgram into ~6 GB of runtime every session regardless — so bge stays ~26 s/restart while
ms-marco-L6 (small enough that the cached conversion dominates) warm-loads in 3.1 s. Newer small
rerankers were evaluated and rejected: `gte-reranker-modernbert-base` fragments + crashes on CoreML
(ANE error), `jina-reranker-v2` is the same size as bge, `mxbai-rerank-xsmall` ships no FP16 export.
`bge-reranker-base` remains resolvable (`CLEAN_ONNX_SOURCES`) for back-compat. Confidence is calibrated
on the cross-encoder `sigmoid(logit)` scale (high ≥0.5, low <0.1), unchanged by the model swap.

### Embedder precision: FP16-on-GPU / INT8-on-CPU (1p93a, ADR `1p92d`)

Wave `1p93a` brings the **embedders** to the reranker's precision parity: **one per-machine
classification drives the whole pipeline** — a machine with a working GPU runs **FP16 end-to-end**
(embed + rerank), a CPU-bound machine (no GPU) runs **INT8 end-to-end**. Both embedders
(`arctic-embed-xs` docs, `bge-small` code) resolve through `accel_embedder.make_embedder` →
`StaticShapeEmbedder`, which is now dual-precision by provider (mirroring `StaticShapeReranker`):

- **GPU** (CoreML/CUDA/ROCm/DirectML): the FP16 clean export (`CLEAN_ONNX_SOURCES`), static-shape
  `64×512`, CLS-pooled + L2-normalized — the proven ~24× path. Arctic's own export is already clean
  (no `com.microsoft` contrib ops), so its `CLEAN_ONNX_SOURCES` entry points at the base Snowflake
  repo, which publishes **both** `model_fp16.onnx` (GPU) and `model_int8.onnx` (CPU).
- **CPU** (no GPU): the INT8 export (`EMBEDDER_CPU_ONNX_FILE = onnx/model_int8.onnx`,
  `_resolve_embedder_cpu_files`) on `CPUExecutionProvider`, a distinct `cpu_int8_static_…` cache key
  so it never collides with the FP16 GPU graph. A gold-labeled NL→code eval (ADR `1p92d`) showed
  **INT8 = FP16** recall on the reranked retrieval path (recall@1/3/5 identical, 0/30 regressions),
  so INT8-on-CPU is retrieval-equivalent while cutting the full CPU pipeline ~176 MB → ~80 MB.

A GPU machine whose specific graph doesn't offload falls back to **fastembed FULL** (not INT8) —
INT8 is only the classification for a machine with no GPU at all, so the pipeline precision never
splits. `make_embedder` returns `None` (→ fastembed) only when neither a GPU offload nor an INT8
clean-export source is available. The **query** side (`server_impl.WaveIndex._get_embedder`) selects
its precision from the **index's recorded class** (below), not the current host's classification, so
query and index precision agree even across machines. Provider selection is resolved once
(`indexer._onnx_providers()`) and threaded to both `make_embedder` and `make_reranker` (wave
`1p937`), so embed and rerank precision can never diverge on the same machine.

**Precision class in `model_versions` (wave `1p936`).** Each layer's `model_versions` value carries a
precision-class suffix: `"<model>@<class>"` where `class ∈ {full, int8}`. **FP16 and FP32 collapse to
`full`** (cos 1.0, interchangeable per `1p517` AC-8 — a GPU FP16 index and its FP32-resident CPU
queries must not look like a precision change); only **INT8** is a distinct class. A precision-class
change (`full ↔ int8`, e.g. moving an index from a GPU machine to a CPU-bound one) forces a full
re-embed of that layer; a same-class provider/format swap does not. A legacy bare-name value (no
`@class`) is treated as `full` — existing indexes are full-precision and must not spuriously rebuild
on upgrade. The compare site (`_predicted_precision_class`) and the write site use the **same**
predictor so a same-machine incremental build never perpetually re-embeds; `make_embedder` is
constructed to resolve exactly what that predictor reports, so the recorded class stays truthful
about the stored vectors.

**Incremental small-batch → CPU routing (wave `1p938`).** The GPU accel embedder pins a `64×512`
static shape and pads every call to 64 rows — optimal for a bulk index build, wasteful for the
post-edit hook's incremental reindex of a handful of chunks. When a run on a GPU machine would embed
fewer than `INCREMENTAL_GPU_MIN_CHUNKS` (= `STATIC_BATCH` = one full GPU batch) chunks, it routes to
the full-precision CPU fastembed path instead (cos 1.0 with the FP16 index → same `full` class → no
re-embed). No effect on a CPU-bound machine (no GPU session to skip). Threshold and measurement in
ADR `1p92d`.

Wave `1p4wx` **split the docs and code models** (ADR `1p50s`). Docs use the asymmetric
`arctic-embed-xs` (best on the 45-query docs bake-off: 82% vs bge-small 67%); code stays on the
symmetric `bge-small` (unbeaten on the 62-query code set). Both are 384-d, so there is no
vector-dimension ripple and the docs-model swap reuses the code index unchanged. The split was
unblocked by `1p4ww` (the framework-index fold made the docs vector space uniform).

### Docs/code split and the arctic query prefix (1p4wx)

`arctic-embed` is **asymmetric**: a query carries the instruction prefix
`"Represent this sentence for searching relevant passages: "` while a document/passage carries
none. The pipeline embeds with fastembed `.embed()`, which does **not** auto-apply prefixes, so:

- The **query** prefix is applied explicitly in `server_impl._embed_query` via
  `indexer.query_embedding_prefix(model_name)` (which reads `EMBEDDING_PREFIXES`). It is empty for
  the symmetric code model (`bge-small`), so code queries pass through unchanged.
- The **document** side stays prefix-free (correct for arctic). An import-time invariant,
  `indexer._assert_active_models_have_empty_document_prefix()`, guards that no active model declares
  a document prefix the build path would silently drop.

Changing `DOCS_MODEL` trips the `model_versions["docs"]` model-name mismatch (compared on the name
prefix, ignoring the `@class` suffix — wave `1p936`), forcing a docs-only re-embed; the post-edit
hook's default `content='docs'` never loads the code embedder, so the code index is reused. The
model name **is** the version — no numeric bump. A precision-class change (`full ↔ int8`) forces the
same re-embed independently of the name (see the precision-class section above).

### Historical: BAAI/bge-base-en-v1.5 (superseded)

The sections below record the earlier `bge-base` benchmark (wave `12br9`) and the code-specific
model research. They predate the move to `bge-small` for code and the `1p4wx` docs split, and are
retained for the decision history.

### Why BAAI/bge-base-en-v1.5

**Measured retrieval quality.** A benchmark evaluation in wave `12br9` against a 32-query ground-truth set drawn from this repository showed `bge-base` at 90.6% top-3 accuracy overall (100% code-intent, 90% docs-intent) vs `bge-small` at 81.2% (88.2% code, 80% docs). The 12pp improvement on code-intent queries was the deciding factor — `bge-small` has no code-specific training and structurally underperforms on code retrieval queries.

**fastembed offline compatibility.** The critical operational constraint is `local_files_only=True`. `bge-base-en-v1.5` is a first-class entry in fastembed's curated offline model list (served from `qdrant/bge-base-en-v1.5-onnx-q`).

**Full rebuild time is acceptable.** With sorted-batch embedding (chunks sorted by length before batching to minimise padding waste), a full rebuild of this repository's ~3,100-chunk corpus takes ~280s at 11 chunks/s. Incremental updates (633ms for 5 chunks) are fast for day-to-day use. Full rebuilds only occur on first setup or forced re-index.

**Alternatives evaluated (wave 12br9 benchmark):**

| Model | Dim | Code acc | Overall acc | Full rebuild | Reason not chosen |
|-------|-----|----------|-------------|-------------|-------------------|
| `BAAI/bge-small-en-v1.5` | 384 | 88.2% | 81.2% | 85s | Replaced — code quality gap |
| `jinaai/jina-embeddings-v2-base-code` | 768 | — | — | — | No INT8 fastembed export; FP32 too slow |
| `nomic-embed-text-v1.5` | 768 | — | — | — | FP32 only; fastembed INT8 registry broken |
| `nomic-embed-code` | 3584 | — | — | — | 28 GB 7B-parameter model; disqualified |
| `text-embedding-ada-002` (OpenAI) | 1536 | — | — | API only | Requires network; unacceptable for offline-first |

**Code-specific models researched (2026-05-04):**

Prompted by community reports (r/LocalLLaMA, March 2026) of newer code retrieval models, and decision log note in wave 12c86 to revisit when a code-specific INT8 ONNX model in fastembed outperforms bge-base on the ground truth set.

| Model | Params | CoIR | In fastembed | INT8 ONNX | Verdict |
|-------|--------|------|-------------|-----------|---------|
| `google/embeddinggemma-300m` | 300M | strong on CoIR (community reports) | ✓ (builtin_sentence_embedding.py, not yet in public docs) | ✗ FP32 only (1.24 GB) | Blocked: no INT8; 10× heavier than bge-base |
| `SFR-Embedding-Code-400M_R` (Salesforce) | 400M | 61.9 | ✗ | — | Blocked: not in fastembed |
| `CodeSage-Small` (Salesforce) | 130M | 54.4 | ✗ | — | Blocked: not in fastembed |
| `nomic-embed-code` | 7B | — | ✗ | — | Blocked: not in fastembed; 7B param model |
| `Voyage-Code-002` | — | 56.3 | ✗ | — | Blocked: cloud API only |
| `voyageai/voyage-4-nano` | 340M | RTEB-code 80.66 (not CoIR) | ✗ | int8/binary output, not via fastembed | Evaluated 2026-06-19, **not tested** — parked locally; remote-GPU candidate (see note below) |

**Conclusion (2026-05-04):** No code-specific model with INT8 ONNX exists in fastembed. `google/embeddinggemma-300m` is the closest candidate but lacks quantization and is 10× larger. Revisit when fastembed adds an INT8 build for embeddinggemma or a comparable code-specific model.

**Update — `voyageai/voyage-4-nano` (2026-06-19, evaluated only, NOT tested against our corpus):** Open-weights (Apache-2.0; loadable via Transformers / Sentence-Transformers / vLLM, so local-only-compatible — unlike API-only Voyage models), ~340M params (≈3× `bge-base`), 32k context, Matryoshka dims 256–2048, int8/binary output precision. RTEB-code 80.66 (+5.5pp over `voyage-3.5-lite`'s 75.13) — but RTEB is VoyageAI's own benchmark and the sheet had no `bge`/OpenAI/Cohere rows for an apples-to-apples comparison. **Parked for the local path** for the reasons this section already documents: it's ~3× the size (the shipped FP16/CoreML speed win is tuned for `bge-base` and would not transfer for free), and the embedder is not the code-retrieval lever here — deep-rank misses are an NL→code vocabulary gap fixed by hybrid-lexical + reranker + chunking, not a base-model swap (ADR `1p52q`, `1p50s`). The one genuinely differentiated axis is the 32k context (a capability, not quality vs `bge`'s 512). **However, the size objection inverts for a future remote embedding *compute* backend** (a planned, opt-in direction — *only the embed call is offloaded* to dedicated/enterprise GPU hardware via API; the LanceDB vectors, `meta.json`, and all change-detection stay **local**): there the 3× params is not a local-throughput blocker, and the open weights mean it can be **self-hosted on the enterprise GPU** rather than consumed as VoyageAI's cloud API (fits a no-external-SaaS posture). Re-evaluate `voyage-4-nano` (and the larger `voyage-4` / `voyage-4-large` tiers) as a remote-compute candidate when that backend lands — gated on a `code_ask` test-pack head-to-head, not RTEB. Remote embedding *compute* must remain **opt-in**; the local index (DB + meta) and the local-compute default stay unchanged.

**Merkle tree for index change-detection — evaluated, low value (2026-06-19):** Considered a Merkle tree to answer (a) "did anything change?" (root-hash compare) and (b) "what changed?" (subtree diff) for semantic + graph indexing. **Not worth adding** for this architecture. Change-detection is already content-hash-based and entirely **local**: per-file SHA-256 in `meta.json` (`_detect_changes`) + per-chunk `chunk_hash` in LanceDB for semantic, and per-file `source_hash` in `project-graph-state.json` for the graph — so "what changed" is already answered precisely at file/chunk granularity (a Merkle tree is just the hierarchical generalization of this flat map; it adds no precision). A Merkle tree's only real wins are (1) an O(1) root-compare to skip the no-op directory walk and (2) subtree pruning — both *optimizations of the walk*, both requiring an incrementally-maintained tree fed by a **trusted, complete change feed** (the post-edit hook misses `git pull`/`checkout` and external edits, so a fallback walk is still needed for correctness), and both marginal at the current corpus scale (~1.1k files; the no-op path already skips file *reads* via the stat cache). The one case where Merkle trees genuinely shine — diffing **remote** index state to ship only changed leaves — **does not apply here**: the planned remote backend is stateless embedding *compute* only (DB + meta stay local), so there is no remote index state to diff. Merkle is also a **weak fit for the graph** specifically — edges cross file/subtree boundaries (a change in one file invalidates referrer edges elsewhere), so subtree-locality breaks and you cannot prune cross-file edge re-resolution by subtree (this is why the graph merge pass already runs over the full edge set every build). **Revisit only** if the corpus grows large enough that the per-refresh walk becomes a *measured* bottleneck — profile first.

The model is not special or irreplaceable. The regression tests exist to make future upgrades safe and auditable.

---

## How It Works

### Index build time (`setup_index.py` + `indexer.py`)

1. `walk_repo()` yields all non-excluded files (respects `.gitignore`, `.aiignore`, hardcoded excludes)
2. `chunker.py` splits each file into chunks — Python files via AST, Markdown via header splits, JS/TS/Go/Rust/Java/C/C++/C#/Bash/Kotlin/SQL via tree-sitter AST (wave 12c86 + SQL follow-up), others via line windows. Tree-sitter grammar packages must be installed alongside `fastembed`; `setup_index.py` checks for them. Chunking quality depends on these grammars being present; fallback to regex/line-window chunkers occurs automatically if any grammar is absent.
3. `fastembed.TextEmbedding` embeds each chunk's text — chunks are globally sorted by length before batching (minimises padding waste), fastembed batches internally at 256
4. The resulting float32 matrix and chunk metadata are saved as:
   - `.wavefoundry/index/docs.npy` — float32 matrix, shape `[n_chunks, dim]`
   - `.wavefoundry/index/docs.json` — list of chunk dicts, row-parallel with `.npy`
   - `.wavefoundry/index/meta.json` — records `model_versions`, file hashes for incremental rebuilds

Subsequent builds are incremental: only files whose SHA-256 has changed are re-chunked and re-embedded.

### Query time (`server.py` `WaveIndex`)

1. `_ensure_loaded()` reads the project index (`.wavefoundry/index/`) — the single index, into which the framework seeds and README are folded (as project docs) at setup/upgrade
2. **Compatibility check**: each layer's `meta.json` `model_versions` must match the current `DOCS_MODEL` / `CODE_MODEL` constants, and its vector matrix must have matching row count and dimension. Incompatible layers are skipped silently — no crash, no results from that layer. This is the safety net for partial or mid-upgrade states.
3. `_embed_query()` embeds the user's query with the same model, using `local_files_only=True` and `HF_HUB_OFFLINE=1` to prevent network calls during agent sessions
4. `_cosine_search()` computes L2-normalized dot products (cosine similarity), filters out negative scores, and returns top-n ranked chunks

### Why `local_files_only=True` and `HF_HUB_OFFLINE=1`

MCP servers run embedded in the IDE process. A surprise network call to HuggingFace Hub during a query would stall the agent for several seconds or fail silently in air-gapped environments. Forcing local-only mode makes query time both fast and predictable. The model is pre-downloaded and verified once by `setup_index.py`, which explicitly allows network access during setup.

### Lexical fallback

When semantic search is unavailable (model not cached, fastembed not installed, or index not built yet), `docs_search` automatically falls back to `search_docs_lexical`. The response includes `data.mode: "lexical"` and a diagnostic explaining why, so agents know they are getting degraded results. The server is always functional without the index — just at lower retrieval quality.

---

## Regression Tests

`SemanticEmbeddingRegressionTests` in `test_server_tools.py` exercises the real fastembed path — no mocks. The tests skip automatically when fastembed is not installed or the model is not locally cached, so they don't block CI environments that haven't run `setup_index.py`.

The purpose of these tests is to make model changes fail loudly rather than silently. Without them, you could change `DOCS_MODEL` and the system would appear to work — `docs_search` would return results — but those results would be garbage because the stored vectors and the query vectors were produced by different models (the layer compatibility check would catch _that_ specific case, but a dimension-compatible new model with a different embedding space would not be caught).

### What each test protects

| Test | What it pins | Why it matters |
|------|-------------|----------------|
| `test_docs_model_constant_matches_expected` | `DOCS_MODEL == "BAAI/bge-base-en-v1.5"` | Records which model is intentionally in use; fails loudly on an unannounced change |
| `test_embedding_dimension_matches_expected` | output dim == 768 | A dimension change invalidates all stored `.npy` files and the merged-layer logic |
| `test_embedding_is_float32` | dtype is `float32` | The cosine math and `.npy` format assume float32; a dtype mismatch produces wrong scores silently |
| `test_same_text_produces_identical_vectors` | embedding is deterministic | Non-deterministic embeddings make search results unpredictable across restarts |
| `test_different_texts_produce_different_vectors` | model is not degenerate | All-same-output models pass every other test but return identical scores for every query |
| `test_similar_text_scores_higher_than_unrelated` | semantic ranking order is meaningful | The core guarantee: if this test fails after a model change, the new model doesn't work for the use case |
| `test_round_trip_search_returns_correct_chunk` | full embed → write .npy → load → search pipeline | Exercises every link end-to-end; catches bugs in the index write or load path that unit tests miss |
| `test_stale_model_name_in_index_causes_layer_skip` | layer compatibility gate works | Verifies the upgrade safety net; ensures a partial upgrade (new code, old index) produces empty results rather than wrong results |

### Anchor constants

Two constants at the top of `SemanticEmbeddingRegressionTests` are the single update point for a model upgrade:

```python
_EXPECTED_DOCS_MODEL = "BAAI/bge-base-en-v1.5"
_EXPECTED_EMBEDDING_DIM = 768
```

When these are updated, all 8 tests should pass against the new model before the index is rebuilt.

---

## How to Upgrade the Model

When switching to a new model, follow this checklist in order. Partial upgrades leave incompatible index files on disk — the compatibility check will skip them silently, producing empty search results with no visible error.

### 1. Research the new model

- [ ] Read the model card: confirm output dimension, license, and that it supports offline-safe usage with fastembed
- [ ] Verify it is available: `python3 -c "from fastembed import TextEmbedding; print([m['model'] for m in TextEmbedding.list_supported_models()])"`
- [ ] Note the model name string exactly as fastembed expects it, and the output dimension

### 2. Update code

- [ ] Change `DOCS_MODEL` in `indexer.py` (and `CODE_MODEL` if upgrading code search)
- [ ] Update `_EXPECTED_DOCS_MODEL` in `test_server_tools.py` (`SemanticEmbeddingRegressionTests`)
- [ ] Update `_EXPECTED_EMBEDDING_DIM` if the dimension changed
- [ ] Update the "Current Model" table in this file

### 3. Rebuild the index

```bash
# Delete old index — must not leave stale files
rm -rf .wavefoundry/index/

# Prewarm model cache and rebuild
python3 .wavefoundry/framework/scripts/setup_index.py --root . --include-code
```

### 4. Verify

```bash
python3 .wavefoundry/framework/scripts/run_tests.py
```

All 8 `SemanticEmbeddingRegressionTests` must pass. If `test_similar_text_scores_higher_than_unrelated` or `test_round_trip_search_returns_correct_chunk` fails, the new model may not be suitable for this use case — investigate before shipping.

Also spot-check manually:

```
wave_validate()                   # docs-lint still passes
docs_search(query="prepare wave") # results look reasonable
code_search(query="def walk_repo") # code results look reasonable
```

### 5. Record the decision

- [ ] Create an ADR in `docs/architecture/decisions/` describing why the new model was chosen
- [ ] Update `Last verified` on this file
