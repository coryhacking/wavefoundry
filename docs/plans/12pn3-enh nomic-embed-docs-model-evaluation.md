# Nomic Embed Text v1.5-Q — Docs Model Evaluation

Change ID: `12pn3-enh nomic-embed-docs-model-evaluation`
Change Status: `planned`
Owner: framework-engineer
Status: planned
Last verified: 2026-05-18
Wave: TBD

## Rationale

`nomic-ai/nomic-embed-text-v1.5-Q` is a quantized (INT8 ONNX) English text embedding model available via fastembed. At 0.13 GB it is 40% smaller than the current `BAAI/bge-base-en-v1.5` (0.21 GB) while maintaining competitive MTEB scores (~62 vs ~64). It supports 8192-token context (vs ~512 for bge-base), making it better suited for long wave docs and architecture documents.

However, nomic-embed-text-v1.5 requires asymmetric instruction prefixes to function correctly:
- Index time (passages): `"search_document: {text}"`
- Query time: `"search_query: {query}"`

Without these prefixes the model is degraded — they are part of its training contract. This means it is **not** a drop-in constant change: both the indexer (embedding preparation) and server (query embedding) must be updated to prepend the correct prefix per context.

This change evaluates whether the quality–size tradeoff is favorable and implements the prefix infrastructure needed to support nomic (and any other instruction-prefixed model) as `DOCS_MODEL`.

## Requirements

1. An `EMBEDDING_PREFIXES` configuration structure in `indexer.py` maps model name → `{"document": str, "query": str}` prefixes (empty string = no prefix). Prefix values include a trailing space so that `prefix + text` produces correctly formatted input (e.g., `"search_document: "` not `"search_document:"`).
2. `_embed_chunks` uses `EMBEDDING_PREFIXES.get(model_name, {}).get("document", "")` to prepend the passage prefix before calling `_embed_texts`. When chunk-context-enrichment (12pn3-enh chunk-context-enrichment) is also active, the composition order is: `model_prefix + context_prefix + chunk_text` (model-required prefix wraps the full passage including metadata).
3. `_embed_query` in server.py accesses `EMBEDDING_PREFIXES` via the established `self._indexer_constant("EMBEDDING_PREFIXES")` pattern (which calls `getattr(_load_script("indexer"), name)`), then prepends the query prefix: `prefix + query` before passing to `_embed_query`'s embedder call.
4. `DOCS_MODEL` is changed to `"nomic-ai/nomic-embed-text-v1.5-Q"` and `EMBEDDING_PREFIXES` includes its required prefixes.
5. The prefix infrastructure is generic — adding a future model requires only a new entry in `EMBEDDING_PREFIXES`, not code changes.
6. `SemanticEmbeddingRegressionTests` constants are updated to reflect the new docs model.
7. A full index rebuild is required; documented in session handoff.

## Scope

**Problem statement:** nomic-embed-text-v1.5-Q is a strong candidate for a smaller, faster docs embedding model but requires instruction prefix infrastructure that does not currently exist.

**In scope:**

- `EMBEDDING_PREFIXES` map in indexer.py
- Prefix application in `_embed_chunks` (indexer) and `_embed_query` (server)
- Changing `DOCS_MODEL` to nomic-embed-text-v1.5-Q
- Updating regression test constants
- Full index rebuild

**Out of scope:**

- Changing `CODE_MODEL` (covered by `12pn3-enh code-embedding-model-jina-v2`)
- Evaluating nomic-embed-text-v1.5 (non-quantized) — the -Q variant is preferred for size
- Multi-model routing (one DOCS_MODEL at a time)

## Acceptance Criteria

- AC-1: `EMBEDDING_PREFIXES` exists in indexer.py with entries for `nomic-ai/nomic-embed-text-v1.5-Q` (`"search_document: "` / `"search_query: "`, both with trailing space) and `BAAI/bge-base-en-v1.5` (empty strings).
- AC-2: The string passed to `_embed_texts` for a doc chunk when `DOCS_MODEL` is nomic starts with `"search_document: "` (prefix value applied directly; trailing space separates prefix from passage content).
- AC-3: The string passed to `_embed_query` when `DOCS_MODEL` is nomic starts with `"search_query: "`.
- AC-4: `DOCS_MODEL` is `"nomic-ai/nomic-embed-text-v1.5-Q"`.
- AC-5: `SemanticEmbeddingRegressionTests` passes with updated model constant.
- AC-6: `docs_search("wave lifecycle stage gate enforcement")` returns a result within the top 3 where `path` contains `wave-coordinator` and `score > 0.4`.

## Tasks

- Add `EMBEDDING_PREFIXES: dict[str, dict[str, str]]` to indexer.py; prefix values must include trailing space (e.g., `"search_document: "` not `"search_document:"`)
- Update `_embed_chunks` to read and apply document prefix; apply model prefix first, then context enrichment prefix (if change 12pn3-enh chunk-context-enrichment is also active)
- Update `_embed_query` in server.py to read and apply query prefix via `self._indexer_constant("EMBEDDING_PREFIXES")` — same pattern used by `_indexer_constant("DOCS_MODEL")` and other constants throughout server.py
- Change `DOCS_MODEL = "nomic-ai/nomic-embed-text-v1.5-Q"`
- Update regression test model constants
- Run `setup_index.py --root . --full` to rebuild docs index
- Run full test suite

## Agent Execution Graph

| Workstream       | Owner              | Depends On       | Notes                                    |
| ---------------- | ------------------ | ---------------- | ---------------------------------------- |
| prefix-infra     | framework-engineer | —                | EMBEDDING_PREFIXES + _embed_chunks patch |
| server-prefix    | framework-engineer | prefix-infra     | _embed_query prefix in server.py         |
| model-constant   | framework-engineer | prefix-infra     | Change DOCS_MODEL constant               |
| test-update      | framework-engineer | model-constant   | Regression test constants                |
| index-rebuild    | framework-engineer | model-constant   | Full rebuild required                    |

## Serialization Points

- `EMBEDDING_PREFIXES` must land before `model-constant` and `server-prefix` workstreams

## Affected Architecture Docs

`docs/architecture/current-state.md` — update docs model reference. Otherwise N/A.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  |           |
| AC-2 | required  |           |
| AC-3 | required  |           |
| AC-4 | required  |           |
| AC-5 | required  |           |
| AC-6 | required  |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Scoped out. nomic-embed-text-v1.5-Q (8192-token context) caused OOM during full rebuild at batch_size=256; reducing batch_size to 32 made rebuilds prohibitively slow (~30+ min). EMBEDDING_PREFIXES infrastructure is implemented and committed (ready for future model adoption). DOCS_MODEL reverted to BAAI/bge-base-en-v1.5. | Decision log entry added |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-17 | Use EMBEDDING_PREFIXES map (generic) | Supports any future instruction-prefix model without code changes | Hard-code per-model if/else |
| 2026-05-17 | Target nomic-embed-text-v1.5-Q (quantized) | 0.13 GB vs 0.52 GB full; MTEB ~62 acceptable for docs | nomic-embed-text-v1.5 full (larger, marginal quality gain) |
| 2026-05-17 | Evaluate before committing to DOCS_MODEL swap | prefix infra is the blocking work; quality vs size tradeoff should be verified post-rebuild | Skip evaluation, keep bge-base |
| 2026-05-17 | Prefix values include trailing space (`"search_document: "`) | `prefix + text` produces correct format without extra logic at application site; consistent with nomic training contract | Store without space and add at apply site (error-prone, two places to get wrong) |
| 2026-05-17 | Access EMBEDDING_PREFIXES from server.py via `_indexer_constant` | Established pattern; single source of truth in indexer.py; avoids duplicating the map | Shared constants module (extra file for one dict); duplicate in server.py (fragile) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Quantized model may have noticeably worse quality on wavefoundry-specific docs | Run recall eval post-rebuild; easy rollback by reverting DOCS_MODEL constant |
| Prefix infrastructure adds complexity to embed path | EMBEDDING_PREFIXES is a simple dict lookup; low risk |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
