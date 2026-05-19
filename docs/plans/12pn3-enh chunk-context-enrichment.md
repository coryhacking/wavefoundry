# Chunk Context Enrichment — Metadata Prefix at Index Time

Change ID: `12pn3-enh chunk-context-enrichment`
Change Status: `planned`
Owner: framework-engineer
Status: planned
Last verified: 2026-05-18
Wave: TBD

## Rationale

Embedding models encode the text they receive without awareness of where it came from. A function body chunk from `src/auth/middleware.py` and a similarly worded doc section from `docs/references/auth.md` produce vectors that compete on content alone. Prepending lightweight metadata — file path, section heading, language — before embedding makes each chunk self-describing. The embedding then encodes both the content and its context, improving retrieval precision when queries reference file types, module names, or architectural layers. This is a standard technique documented in LlamaIndex, LangChain, and Anthropic's RAG guidelines. The change is applied at index time only; the stored `text` field in the Lance table is unchanged (we prepend only for the embedding call, not for the displayed result).

## Requirements

1. At index time, before passing chunk text to the embedder, a context prefix is prepended: `"File: {path}\nSection: {section}\n\n"` for doc chunks and `"File: {path}\nLanguage: {language}\nSection: {section}\n\n"` for code chunks.
2. The `chunk["text"]` field stored in the Lance table (and returned to callers) is NOT modified — only the string passed to `_embed_texts` is prefixed.
3. The prefix is applied in `_embed_chunks` in indexer.py, not in the chunker.
4. At query time, no prefix is added to the query string (asymmetric: documents get context prefix, queries do not).
5. After this change lands, a full index rebuild is required; the chunker version or a new `embedding_prefix_version` field in meta.json is bumped to trigger rebuild detection.
6. jina-embeddings-v2-base-code is confirmed to not require asymmetric instruction prefixes (`"Prefixes for queries/documents: not necessary"`); the context prefix added here is complementary metadata, not a model-required instruction.

## Scope

**Problem statement:** Chunk embeddings carry no metadata about their origin, reducing retrieval precision for queries that implicitly reference file type, module, or layer (e.g., "auth middleware", "SQL schema", "wave lifecycle docs").

**In scope:**

- Modify `_embed_chunks` in indexer.py to construct prefixed text before calling `_embed_texts`
- Bump a version marker in meta.json to ensure incremental builds detect the change and re-embed
- Tests verifying the prefix is applied at embed time but not stored in the Lance text field

**Out of scope:**

- Changing the chunker output
- Modifying the stored `text` field in LanceDB
- Adding model-required instruction prefixes (that is nomic-specific and tracked in `12pn3-enh nomic-embed-docs-model-evaluation`)
- Query-side prefix (asymmetric by design)

## Acceptance Criteria

- AC-1: The string passed to `_embed_texts` for a doc chunk includes `"File: {path}"` as a prefix.
- AC-2: The `text` field stored in the Lance table does NOT contain the prefix.
- AC-3: After a rebuild, `meta.json` contains an updated version marker that would trigger re-embedding on the next incremental run if the prefix changes.
- AC-4: All existing tests pass.

## Tasks

- In `_embed_chunks` in indexer.py, construct `embed_text = f"File: {c['path']}\nSection: {c.get('section') or ''}\n\n{c['text']}"` (code chunks additionally include `Language: {c.get('language') or ''}`). This MUST be a new local variable — do NOT mutate `c["text"]` or `c` in place; the chunk dict is written to LanceDB after this point and the stored text must remain unmodified.
- Pass `embed_text` list to `_embed_texts` instead of raw `texts`
- Add `"embedding_context_prefix": "v1"` to meta.json fields written at build time
- Update `_build_index_locked` model-changed detection to treat a changed `embedding_context_prefix` as requiring re-embed
- Write a unit test asserting the prefix appears in embedded strings but not in Lance row `text`

## Agent Execution Graph

| Workstream     | Owner              | Depends On | Notes                                       |
| -------------- | ------------------ | ---------- | ------------------------------------------- |
| indexer-prefix | framework-engineer | —          | Modify _embed_chunks; bump version marker   |
| tests          | framework-engineer | indexer-prefix | Unit test prefix logic                 |

## Serialization Points

- indexer.py `_embed_chunks` — single change point

## Affected Architecture Docs

N/A — confined to indexer.py embedding preparation; no boundary or flow change.

## AC Priority

(Populated at Prepare wave.)

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  |           |
| AC-2 | required  |           |
| AC-3 | required  | Stale embeddings from a silent version marker mismatch are a correctness issue; a missing or unwired marker causes all incremental builds to skip re-embedding silently |
| AC-4 | required  |           |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-18 | Scoped out. Context prefixes are not beneficial for bge-base-en-v1.5 (symmetric, 512-token limit; prefixes waste token budget without retrieval benefit). This change is deferred until a long-context instruction-tuned docs model is adopted. | Decision log entry added |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-17 | Prefix at embed time only, not stored | Keeps stored text clean; prefix can change without schema migration | Store prefixed text (couples schema to prefix format) |
| 2026-05-17 | Asymmetric — no query prefix | jina-code and bge-base do not require query prefix; adding one risks degradation | Symmetric prefix (model-dependent) |
| 2026-05-17 | Context prefix applied before model-required prefix in `_embed_chunks` composition | When nomic lands, EMBEDDING_PREFIXES lookup runs first so model prefix wraps the entire passage (including metadata); matches nomic training contract | Context prefix wraps model prefix (wrong order) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Prefix consumes tokens from the 512-token limit on bge-base | Prefix is ~10 tokens; negligible for typical chunk sizes |
| Existing indexed repos will silently have mismatched vectors until rebuilt | Version marker ensures next incremental detects and re-embeds |
| Chunk dict mutated in `_embed_chunks` before Lance write corrupts stored `text` | Use a new `embed_text` variable; never assign back to `c["text"]`; unit test must assert Lance row `text` is clean |
| Prefix composition ambiguity when nomic change (12pn3-enh nomic-embed-docs-model-evaluation) also lands | When both changes are active the final embedded string is: `{EMBEDDING_PREFIXES[model]["document"]}{context_prefix}{chunk_text}` — model-required prefix first, context metadata second. `_embed_chunks` must apply EMBEDDING_PREFIXES lookup before constructing the context prefix string, not after. |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
