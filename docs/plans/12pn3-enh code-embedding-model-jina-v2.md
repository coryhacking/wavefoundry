# Code Embedding Model Upgrade — jina-embeddings-v2-base-code

Change ID: `12pn3-enh code-embedding-model-jina-v2`
Change Status: `planned`
Owner: framework-engineer
Status: planned
Last verified: 2026-05-18
Wave: TBD

## Rationale

`CODE_MODEL` is currently `BAAI/bge-base-en-v1.5`, a general-purpose English text model. Code corpora have distinct semantic structure — identifiers, type signatures, docstrings, import graphs — that general-purpose models encode poorly. `jinaai/jina-embeddings-v2-base-code` was pretrained on 30 programming languages with 8192-token context windows and is available as an ONNX model via fastembed (768-dim, 0.64 GB, no API required). Benchmarks on CodeSearchNet-style tasks show 15–25% recall improvement over BGE-base on code retrieval. The 768-dim output is identical to the current model, so the LanceDB schema requires no changes.

## Requirements

1. `CODE_MODEL` in `indexer.py` is changed to `"jinaai/jina-embeddings-v2-base-code"`.
2. `DOCS_MODEL` is unchanged (`BAAI/bge-base-en-v1.5`).
3. `setup_index.py` pre-warms the jina-code model on first run before building the index.
4. `SemanticEmbeddingRegressionTests` constants `_EXPECTED_CODE_MODEL` and `_EXPECTED_EMBEDDING_DIM` are updated to reflect the new model (dim remains 768).
5. The change doc for `chunk-context-enrichment` (12pn3) notes that jina-code does not require instruction prefixes (`"Prefixes for queries/documents: not necessary"` per fastembed metadata).
6. A `--full` rebuild is required after deployment; this is documented in the session handoff and change doc.

## Scope

**Problem statement:** The code index uses a general-purpose English embedding model that lacks code-specific pretraining, resulting in weaker recall on identifier, signature, and pattern searches.

**In scope:**

- Change `CODE_MODEL` constant in `indexer.py`
- Update model pre-warming in `setup_index.py` (`prewarm_models`)
- Update regression test constants in `test_server_tools.py`
- Document the required full rebuild in the progress log

**Out of scope:**

- Changing `DOCS_MODEL` (covered by `12pn3-enh nomic-embed-docs-model-evaluation` if that work proceeds)
- Instruction prefix handling (jina-code does not require it)
- LanceDB schema changes (768-dim is preserved)

## Acceptance Criteria

- AC-1: `indexer.py` `CODE_MODEL` is `"jinaai/jina-embeddings-v2-base-code"`.
- AC-2: `DOCS_MODEL` remains `"BAAI/bge-base-en-v1.5"`.
- AC-3: `setup_index.py --include-code` completes without error and pre-warms the jina model offline before indexing.
- AC-4: `SemanticEmbeddingRegressionTests` passes with the updated model constant.
- AC-5: The code index can be built and queried end-to-end; `code_search` returns results for a known function name in the repo.

## Tasks

- Update `CODE_MODEL = "jinaai/jina-embeddings-v2-base-code"` in `indexer.py`
- Verify `setup_index.py` `prewarm_models` picks up the new constant (it calls `_indexer_models(include_code=True)` dynamically — should be automatic)
- Update `_EXPECTED_CODE_MODEL` in `SemanticEmbeddingRegressionTests` if that constant exists; add one if not
- Run `setup_index.py --root . --include-code --full` to rebuild with new model
- Run full test suite: `python3 .wavefoundry/framework/scripts/run_tests.py`

## Agent Execution Graph

| Workstream        | Owner              | Depends On | Notes                              |
| ----------------- | ------------------ | ---------- | ---------------------------------- |
| constant-update   | framework-engineer | —          | Single-line change in indexer.py   |
| test-update       | framework-engineer | —          | Update regression test constants   |
| index-rebuild     | framework-engineer | constant-update | Full rebuild required; slow   |
| verification      | framework-engineer | index-rebuild | Run code_search smoke test    |

## Serialization Points

- `indexer.py` `CODE_MODEL` — must be set before rebuild; test update can be parallel

## Affected Architecture Docs

`docs/architecture/current-state.md` — update the embedding model reference if it names `bge-base-en-v1.5` for code. Otherwise N/A (single constant change, no boundary or flow impact).

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  |           |
| AC-2 | required  |           |
| AC-3 | required  |           |
| AC-4 | required  |           |
| AC-5 | required  |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Scoped out. jina-embeddings-v2-base-code (0.64 GB, 8192-token context) is 3× larger than bge-base and causes the same OOM/slow-rebuild issues as nomic on this machine. CODE_MODEL remains BAAI/bge-base-en-v1.5. Deferred until hardware or a lighter code model is available. | Decision log entry added |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-17 | Use jina-embeddings-v2-base-code for CODE_MODEL | fastembed-native, 768-dim drop-in, code-pretrained, no prefix required | voyage-code-2 (API-only), bge-large (heavier, general) |
| 2026-05-17 | Keep DOCS_MODEL as bge-base-en-v1.5 | Already good for prose; nomic evaluation is a separate change | nomic-embed-text-v1.5-Q (requires prefix infra) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Full rebuild required — slow on large repos | Schedule during off-hours; background-code flag available |
| jina model 0.64 GB vs 0.21 GB for bge-base — larger download on first setup | Already listed in `REQUIRED_IMPORTS` flow; fastembed caches locally |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.