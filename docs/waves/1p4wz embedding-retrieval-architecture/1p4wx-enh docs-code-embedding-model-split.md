# Docs/code embedding model split (arctic-embed-xs for docs)

Change ID: `1p4wx-enh docs-code-embedding-model-split`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-12
Wave: `1p4wz embedding-retrieval-architecture`

## Rationale

`DOCS_MODEL` and `CODE_MODEL` are already independent constants (`indexer.py:39-40`), and the
docs/code LanceDB tables are separate, so the two layers can use different embedding models. An
expanded bake-off (62 code + 45 docs queries = the hand-written 32 hard set + an auto-generated
broad set from docstrings/doc-headings, FP16/CoreML, breadcrumb applied per `1p4w9`) showed a clear
asymmetry:

- **Docs:** `snowflake-arctic-embed-xs` beats the current `bge-small` **82% vs 67%** (all) and
  **80% vs 60%** (hard set) — +15–20pp, robust across hard and auto cuts. `arctic-embed-s` is close
  (80%) but `arctic-xs` edges it and is smaller/faster (6-layer MiniLM base).
- **Code:** `bge-small` is unbeaten — `jina-base-code` (code-trained) lost on every cut (85% vs 82%
  all, 47% vs 41% hard); 0/8 deep-rank code queries rescued by any of five models. Code-specialization
  does not help this NL→code short-chunk regime (see [[project_code_retrieval_quality_levers]]).

So: **`DOCS_MODEL = arctic-embed-xs`, `CODE_MODEL = bge-small`.** arctic-xs is fastembed-resident
(INT8 for the CPU floor, FP16 for GPU), 384-d (no dim ripple), Apache-2.0, and CPU-viable.

## Requirements

1. `DOCS_MODEL = "Snowflake/snowflake-arctic-embed-xs"`; `CODE_MODEL` stays `BAAI/bge-small-en-v1.5`.
2. `EMBEDDING_PREFIXES` gains the arctic entry — it is asymmetric: query prefix
   `"Represent this sentence for searching relevant passages: "`, document prefix empty.
3. `setup_index._MODEL_CACHE_DIR_ALIASES` gains the arctic INT8 fastembed cache-dir mapping so the
   offline cache-resolution checks pass.
4. The docs regression anchor (`_EXPECTED_DOCS_MODEL` in `test_server_tools.py`) updates to the
   arctic model; `_EXPECTED_EMBEDDING_DIM` stays 384.
5. The model-name change in `model_versions["docs"]` auto-forces a **docs-only** re-embed (the
   existing `old_model_versions.get("docs") != DOCS_MODEL` trigger; code layer untouched, reuses
   vectors). No numeric version bump and no new metadata field — the textual model name *is* the
   version (operator decision 2026-06-11).
6. An ADR records the docs-model split and the bake-off evidence.

## Scope

**Problem statement:** A single shared embedding model is suboptimal — a different docs model
materially improves docs retrieval while bge-small remains best for code.

**In scope:**

- `indexer.py` `DOCS_MODEL` + `EMBEDDING_PREFIXES`; `setup_index._MODEL_CACHE_DIR_ALIASES`; the test
  anchor; an ADR.

**Out of scope:**

- The framework-index fold (`1p4ww`) — a hard dependency, see below.
- Any code-model change (bge-small confirmed best for code).
- Reranker / hybrid-lexical / chunking changes.

## Dependencies

- **Hard-depends on `1p4ww` (fold framework index into core docs).** The docs model must be uniform
  across all docs vectors; while a separately-shipped framework docs index exists with the old model,
  switching `DOCS_MODEL` would make `docs_search` mix two vector spaces. Land the fold first (or
  together), then this becomes effectively a one-constant change.
- Composes with `1p4w9` (docs breadcrumb) — both improve docs retrieval and were measured together.

## Acceptance Criteria

- [x] AC-1: `DOCS_MODEL` is arctic-embed-xs and `CODE_MODEL` is bge-small; verified by the updated
  `_EXPECTED_DOCS_MODEL`/`_EXPECTED_CODE_MODEL` anchors (`SemanticEmbeddingRegressionTests` +
  `DocsCodeModelSplitTests.test_model_constants_are_split`). arctic-xs warmed locally (dim 384).
- [x] AC-2: The arctic query prefix is applied to docs queries (and only docs); verified by
  `DocsCodeModelSplitTests.test_embed_query_applies_docs_prefix` /
  `test_embed_query_no_prefix_for_code_model` (mocked embedder captures the exact query text).
- [x] AC-3: `_MODEL_CACHE_DIR_ALIASES` resolves the arctic cache; offline warm succeeds
  (`local_files_only=True`) — `test_setup_index.test_arctic_docs_model_cache_alias_resolves_lowercase_dir`
  + the real-embed regression tests run offline. **Note:** fastembed ships the FP32 `onnx/model.onnx`
  for arctic-xs (≈90 MB), not an INT8 build; it loads fine on the CPU floor. FP16/GPU is `1p4wy`.
- [x] AC-4: Switching the docs model forces a docs-only re-embed and leaves the code index untouched;
  verified by `test_indexer.test_docs_model_change_reembeds_docs_only_code_untouched` (content='docs'
  re-embeds docs, never loads the code embedder, code.lance byte-identical).
- [x] AC-5 (important): Docs retrieval on `retrieval_eval.json` ≥ the bge-small baseline. **Measured on
  the live arctic index (2026-06-12): docs recall@5 = 7/10 = 70%** (via `search_docs`, arctic query
  prefix + reranker). That **matches the bge-small baseline (70% docs on this same committed set, per
  `project_bge_base_real_world_quality`) → ≥ baseline, no regression**. Caveat: the committed
  `retrieval_eval.json` has only 10 docs queries — too few to show the bake-off's +15–20pp arctic gain,
  which was measured on the larger 45-query expanded set (not committed). Code retrieval is unchanged
  (the code model didn't change; the rebuilt code vectors are cos 1.0 vs the prior fastembed bge).
- [x] AC-6: Full framework suite green — **3131 tests** (`run_tests.py`).

## Tasks

- [x] `indexer.py`: set `DOCS_MODEL`; add the arctic `EMBEDDING_PREFIXES` entry + `query_embedding_prefix`/`document_embedding_prefix` helpers + an import-time empty-document-prefix invariant.
- [x] `server_impl.py`: `_embed_query` applies the query prefix (the wiring gap — `EMBEDDING_PREFIXES` was previously unused; `.embed()` does not auto-apply prefixes).
- [x] `setup_index.py`: add the `_MODEL_CACHE_DIR_ALIASES` entry (maps capital-S name → lowercase fastembed cache dir).
- [x] Update `_EXPECTED_DOCS_MODEL` (+ add `_EXPECTED_CODE_MODEL`); `_EXPECTED_EMBEDDING_DIM` stays 384.
- [x] ADR for the docs-model split (`1p50s`, bake-off evidence) + `embedding-model.md` current-model table.
- [x] Tests (prefix wiring, cache alias, docs-only re-embed) + run the suite (3131 green).
- [x] Re-validate docs delta on `retrieval_eval.json` after a real re-index — done 2026-06-12: arctic docs recall@5 = 70% on the live index (≥ the bge baseline; see AC-5).

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| ---------- | ----- | ---------- | ----- |
| model + prefix | implementer | 1p4ww | `DOCS_MODEL` + `EMBEDDING_PREFIXES` |
| cache alias + anchor | implementer | model + prefix | offline resolution + gate |
| ADR + tests | qa-reviewer | model + prefix | evidence + verification |

## Serialization Points

- `indexer.py` model constants + `EMBEDDING_PREFIXES`.
- The `_EXPECTED_DOCS_MODEL` gate anchor.
- Ordering vs `1p4ww` (fold first).

## Affected Architecture Docs

`docs/architecture/embedding-model.md` — current-model table updated to the docs/code split + a new
"arctic query prefix" section (the prior `bge-base` content marked superseded/historical). New ADR
`docs/architecture/decisions/1p50s-adr docs-code-embedding-model-split.md`.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| ---- | ---------------------------------------------------- | --------- |
| AC-1 | required | The core change. |
| AC-2 | required | Arctic is asymmetric — wrong/missing prefix degrades retrieval. |
| AC-3 | required | Offline-safe warm. |
| AC-4 | required | Correct, scoped re-embed. |
| AC-5 | important | Confirms the measured docs gain. |
| AC-6 | required | No regressions. |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-11 | Scoped (doc-first). | Expanded bake-off: arctic-xs docs 82%/80%(hard) vs bge-small 67%/60%; bge-small code 85%/47%(hard) vs jina 82%/41%. [[project_code_retrieval_quality_levers]]. |
| 2026-06-12 | **IMPLEMENTED + green (suite 3131).** Found and closed a wiring gap the doc didn't anticipate: `EMBEDDING_PREFIXES` was defined but **never consumed** — the pipeline embeds via fastembed `.embed()`, which does not auto-apply prefixes. So I wired the arctic QUERY prefix explicitly in `server_impl._embed_query` (via new `indexer.query_embedding_prefix`); the document side stays prefix-free (correct for arctic) and is guarded by an import-time `_assert_active_models_have_empty_document_prefix` invariant. `DOCS_MODEL=Snowflake/snowflake-arctic-embed-xs`, `CODE_MODEL=bge-small`. Cache alias maps the capital-S name → the lowercase `models--snowflake--…` dir fastembed downloads to. arctic-xs warmed locally (384-d, FP32 `onnx/model.onnx` — **not INT8** as the rationale assumed; loads fine on CPU). `SemanticEmbeddingRegressionTests` now run (not skip) and pass on arctic. +9 tests (6 `DocsCodeModelSplitTests` + 1 cache-alias + 1 docs-only-re-embed + the code-model anchor). ADR `1p50s` + `embedding-model.md` updated (the stale `bge-base`/768 table was corrected → arctic/bge-small/384). AC-5 (real retrieval delta) pending operator re-index. | `run_tests.py` 3131 green; `_embed_query` prefix test captures exact query text; AC-4 test confirms code.lance byte-identical after a docs-only re-embed. |
| 2026-06-12 | **AC-5 measured on the live arctic index (re-index done via `1p517` rebuild).** Docs recall@5 = 7/10 = 70% on the committed `retrieval_eval.json` (`search_docs`, arctic query prefix + reranker) = **≥ the bge baseline (70% on the same set) → no regression.** The bake-off's +15–20pp gain was on the larger 45-query expanded set (not committed; the 10-query committed set is too small to show it). Code retrieval unchanged. | live `search_docs` over the arctic index; `project_bge_base_real_world_quality` for the bge baseline. |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-06-11 | `DOCS_MODEL = arctic-embed-xs`. | +15–20pp docs over bge-small on 45 queries; 384-d (no ripple), Apache-2.0, fastembed-resident, CPU-viable. | `arctic-embed-s` (close, slightly behind, 12-layer); keep bge-small (worse docs). |
| 2026-06-11 | Keep `CODE_MODEL = bge-small`. | Unbeaten on 62 code queries; jina (code-trained) and all general models lose; 0/8 deep-rank rescued. | jina-base-code / a code-specialized export (rejected: no lift + SFR disqualified by CPU floor). |
| 2026-06-11 | Use the textual model name as the docs version (no numeric bump). | Operator decision; `model_versions["docs"]` already stores the name and the change triggers the docs re-embed. | A numeric/embed-tag version (rejected). |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Landing before `1p4ww` mixes two docs vector spaces. | Hard dependency — fold first/together. |
| Arctic prefix mis-wired → degraded docs retrieval. | AC-2 prefix test; bake-off used the prefix. |
| Auto-eval queries skew easy; real-index gain may differ. | AC-5 re-validate post-rebuild on the hard set. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
