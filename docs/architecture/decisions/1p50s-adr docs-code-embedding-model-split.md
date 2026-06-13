# 1p50s-adr — Docs/code embedding-model split (arctic-embed-xs for docs)

Owner: Engineering
Status: accepted
Last verified: 2026-06-12

## Context

`DOCS_MODEL` and `CODE_MODEL` have always been independent constants (`indexer.py`), and the
docs/code LanceDB tables are separate, so the two layers can use different embedding models — but
historically both pointed at the same model (`bge-small-en-v1.5`). Wave `1p4ww` folded the
framework docs into the single project docs index, making the docs vector space uniform and
removing the cross-layer model-pinning that previously blocked a docs-only model swap.

An expanded bake-off (62 code + 45 docs queries = a hand-written hard set plus an auto-generated
broad set from docstrings/doc-headings; FP16/CoreML; the `1p4w9` docs breadcrumb applied) showed a
clear asymmetry:

- **Docs:** `snowflake-arctic-embed-xs` beats `bge-small` **82% vs 67%** (all) and **80% vs 60%**
  (hard set) — +15–20pp, robust across hard and auto cuts. `arctic-embed-s` is close (80%) but
  `arctic-xs` edges it and is smaller/faster (6-layer MiniLM base).
- **Code:** `bge-small` is unbeaten — `jina-base-code` (code-trained) lost on every cut (85% vs 82%
  all, 47% vs 41% hard); 0/8 deep-rank code queries were rescued by any of five models.
  Code-specialization does not help this NL→code short-chunk regime
  (see `project_code_retrieval_quality_levers`).

## Decision

Split the embedding model by layer: **`DOCS_MODEL = "Snowflake/snowflake-arctic-embed-xs"`,
`CODE_MODEL = "BAAI/bge-small-en-v1.5"`.**

- arctic-embed-xs is 384-d (identical to bge-small — no vector-dimension ripple), Apache-2.0,
  fastembed-resident, and CPU-viable (≈90 MB ONNX).
- arctic-embed is **asymmetric**: queries carry the instruction prefix
  `"Represent this sentence for searching relevant passages: "`; documents carry no prefix. The
  pipeline embeds via fastembed `.embed()` (which does **not** auto-apply prefixes), so the query
  prefix is applied explicitly in `server_impl._embed_query` via `indexer.query_embedding_prefix()`,
  reading `EMBEDDING_PREFIXES`. The document side stays prefix-free; an import-time invariant
  (`_assert_active_models_have_empty_document_prefix`) guards that no active model needs a document
  prefix the build path doesn't apply.
- The model name stored in `model_versions["docs"]` **is** the version: changing `DOCS_MODEL`
  trips the existing `old_model_versions.get("docs") != DOCS_MODEL` trigger, forcing a docs-only
  re-embed. The natural trigger path — the post-edit hook's default `content='docs'` — never loads
  the code embedder, so the code index is left untouched (its vectors reused). No numeric version
  bump and no new metadata field.
- `setup_index._MODEL_CACHE_DIR_ALIASES` maps the capital-S model name to the lowercase
  `snowflake/snowflake-arctic-embed-xs` HF repo dir that fastembed actually downloads to, so the
  offline (`local_files_only=True`) cache resolution succeeds.

## Consequences

**Positive:**
- +15–20pp docs retrieval over bge-small on 45 queries, with no change to code retrieval.
- No dimension ripple (both 384-d); the code index is reused unchanged on the docs-model swap.
- Offline-safe and CPU-viable; Apache-2.0.

**Negative / tradeoffs:**
- Two embedding models are now loaded (docs + code) instead of one — a small extra memory/warm cost.
- The docs corpus must be re-embedded once with arctic (auto-triggered by the model-name change).

**Constraints imposed:**
- arctic queries MUST carry the instruction prefix; the document side must stay prefix-free. The
  `EMBEDDING_PREFIXES` table + the import-time invariant enforce this.
- A future asymmetric-document model cannot be activated without first wiring the document prefix
  into the build embed path (the invariant fails loudly otherwise).

## Alternatives Considered

| Alternative | Reason rejected |
|-------------|----------------|
| `snowflake-arctic-embed-s` for docs | Close (80%) but slightly behind arctic-xs and larger/slower (12-layer). |
| Keep a single shared `bge-small` for both | Leaves ~15–20pp of docs retrieval on the table. |
| `jina-embeddings-v2-base-code` for code | Code-trained but lost on every code cut; 0/8 deep-rank rescued. |
| A numeric/embed-tag docs version field | Redundant — `model_versions["docs"]` already stores the name and triggers the re-embed (operator decision). |

## Notes

- The change doc anticipated an INT8 arctic artifact; the fastembed build for arctic-xs ships the
  FP32 `onnx/model.onnx` (≈90 MB), which loads fine on the CPU floor. FP16/GPU execution is the
  concern of `1p4wy`, not this change.

## References

- `docs/waves/1p4wz embedding-retrieval-architecture/1p4wx-enh docs-code-embedding-model-split.md`
- `docs/architecture/embedding-model.md`
- `docs/architecture/decisions/1p4xx-adr fold-framework-index-into-project-docs.md` (the fold that unblocked this)
- `project_code_retrieval_quality_levers`, `project_bge_base_real_world_quality` (memory)
