# Embedding Model

Owner: Engineering
Status: active
Last verified: 2026-05-01

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
| `DOCS_MODEL` | `BAAI/bge-small-en-v1.5` | 384 | `indexer.py` |
| `CODE_MODEL` | `BAAI/bge-small-en-v1.5` | 384 | `indexer.py` |

Both constants currently point to the same model. They are intentionally separate to allow independent upgrades — docs search and code search have different quality/size trade-offs and may diverge in the future.

### Why BAAI/bge-small-en-v1.5

**Size and latency.** At 384 dimensions, the model weighs ~33 MB on disk. The MCP server loads on demand inside the IDE process; a model that takes several seconds to cold-start would make every first query feel broken. The 768-d `bge-base` is ~130 MB and roughly 2–3× slower to load; `bge-large` (1024-d, ~600 MB) is out of the question for an embedded tool server. The size of the stored `.npy` index also scales with dimension: a 10,000-chunk docs corpus at 384-d is ~15 MB; at 1536-d it would be ~60 MB. Neither is large in absolute terms, but the ratio matters for incremental rebuild speed.

**The corpus is small and domain-specific.** Wavefoundry's indexed corpus is a few hundred to a few thousand doc chunks — wave records, architecture docs, prompts, seeds. A large general-purpose retrieval model is over-fit for this problem. The retrieval task is "find the right change doc or prompt" not "find a relevant passage in all of English Wikipedia." Small models trained on general English text handle short structured documents like these well.

**fastembed offline compatibility.** The critical operational constraint is `local_files_only=True`. Not every model in the HuggingFace ecosystem behaves correctly under this flag; some silently fall back to network calls, others raise obscure errors. `fastembed` explicitly bundles and validates a curated list of models for offline use, and `bge-small-en-v1.5` is one of the first-class entries on that list. This was the deciding constraint — a nominally better model that requires network access at query time is not acceptable.

**MTEB retrieval benchmarks.** On the MTEB English retrieval benchmark, `bge-small-en-v1.5` scores around 51–52 NDCG@10 — comparable to models 3–4× its size from 2022–2023. The `bge` family from BAAI specifically optimized for the retrieval task rather than general language modeling, which is why the quality-to-size ratio is favorable. For the Wavefoundry use case the absolute score doesn't matter much; what matters is that semantically related chunks rank above unrelated ones, which this model does reliably on English technical prose.

**Alternatives considered at the time of adoption:**

| Model | Dim | Approx size | Reason not chosen |
|-------|-----|-------------|-------------------|
| `BAAI/bge-base-en-v1.5` | 768 | ~130 MB | 4× larger for marginal retrieval gain on short structured docs |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | ~22 MB | Similar size but lower retrieval quality than bge-small; not in fastembed's first-class offline list at adoption time |
| `text-embedding-ada-002` (OpenAI) | 1536 | API only | Requires network on every query; unacceptable for offline-first operation |
| `nomic-embed-text-v1.5` | 768 | ~270 MB | Higher quality but too large for the use case at the time |

The model is not special or irreplaceable. If a future model provides meaningfully better retrieval quality at similar or smaller size and maintains fastembed + offline compatibility, upgrading is the right call. The regression tests exist specifically to make that upgrade safe and auditable.

---

## How It Works

### Index build time (`setup_index.py` + `indexer.py`)

1. `walk_repo()` yields all non-excluded files (respects `.gitignore`, `.aiignore`, hardcoded excludes)
2. `chunker.py` splits each file into chunks — Python files via AST, Markdown via header splits, others via line windows
3. `fastembed.TextEmbedding` embeds each chunk's text in batches (batch size 64 for docs, 16 for code)
4. The resulting float32 matrix and chunk metadata are saved as:
   - `.wavefoundry/index/docs.npy` — float32 matrix, shape `[n_chunks, dim]`
   - `.wavefoundry/index/docs.json` — list of chunk dicts, row-parallel with `.npy`
   - `.wavefoundry/index/meta.json` — records `model_versions`, file hashes for incremental rebuilds

Subsequent builds are incremental: only files whose SHA-256 has changed are re-chunked and re-embedded.

### Query time (`server.py` `WaveIndex`)

1. `_ensure_loaded()` reads both the project index (`.wavefoundry/index/`) and the packaged framework index (`.wavefoundry/framework/index/`) and merges compatible layers
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
| `test_docs_model_constant_matches_expected` | `DOCS_MODEL == "BAAI/bge-small-en-v1.5"` | Records which model is intentionally in use; fails loudly on an unannounced change |
| `test_embedding_dimension_matches_expected` | output dim == 384 | A dimension change invalidates all stored `.npy` files and the merged-layer logic |
| `test_embedding_is_float32` | dtype is `float32` | The cosine math and `.npy` format assume float32; a dtype mismatch produces wrong scores silently |
| `test_same_text_produces_identical_vectors` | embedding is deterministic | Non-deterministic embeddings make search results unpredictable across restarts |
| `test_different_texts_produce_different_vectors` | model is not degenerate | All-same-output models pass every other test but return identical scores for every query |
| `test_similar_text_scores_higher_than_unrelated` | semantic ranking order is meaningful | The core guarantee: if this test fails after a model change, the new model doesn't work for the use case |
| `test_round_trip_search_returns_correct_chunk` | full embed → write .npy → load → search pipeline | Exercises every link end-to-end; catches bugs in the index write or load path that unit tests miss |
| `test_stale_model_name_in_index_causes_layer_skip` | layer compatibility gate works | Verifies the upgrade safety net; ensures a partial upgrade (new code, old index) produces empty results rather than wrong results |

### Anchor constants

Two constants at the top of `SemanticEmbeddingRegressionTests` are the single update point for a model upgrade:

```python
_EXPECTED_DOCS_MODEL = "BAAI/bge-small-en-v1.5"
_EXPECTED_EMBEDDING_DIM = 384
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

If this is a framework release, also rebuild the packaged framework index:

```bash
python3 .wavefoundry/framework/scripts/build_pack.py
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
