# Semantic Index Chunk Delta Embedding

Change ID: `12yiz-enh semantic-index-chunk-delta-embedding`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-28
Wave: `12xr1 graph-index-extraction-and-visualization`

## Rationale

The semantic indexer is incremental at the file level today: a changed file is re-chunked, all old LanceDB rows for that path are deleted, and every newly produced chunk for that file is re-embedded. That is correct, but it is unnecessarily expensive for large Markdown and source files where a one-line edit usually changes only one heading section, symbol chunk, or summary chunk.

The current chunk schema already stores the information needed to compare what was indexed with what a fresh chunking pass produces: chunk `id`, `path`, `kind`, `language`, `lines`, `section`, and `text`. Most Markdown chunks are heading-derived (`path#slug`) and most structure-aware code chunks are symbol-derived (`path::qualified_name`), so a chunk-level delta path can reuse existing vectors for unchanged chunks and only embed changed or new chunks.

The goal is to make normal index updates proportional to changed chunks, not changed files, while preserving full rebuild behavior and correctness when chunker/model versions change.

## Requirements

1. Add a stable per-chunk fingerprint to indexed rows, derived from the fields that affect retrieval semantics.
2. During incremental updates, read existing chunks for each stale path from the relevant LanceDB table before deleting rows.
3. Rechunk the changed file, compare new chunks with existing indexed chunks, and classify each chunk as unchanged, changed, added, or removed.
4. Reuse existing vectors for unchanged chunks; embed only added or changed chunks.
5. Delete removed and changed old chunk rows, then add changed/new rows with current metadata and vectors.
6. Preserve the current file-level metadata, version mismatch, full rebuild, table lock, FTS refresh, and compaction semantics.
7. Bump the chunker/index schema version so existing LanceDB tables are rebuilt once with the new `chunk_hash` column instead of mixing old-schema rows with new-schema rows.
8. Handle future chunker/model/schema upgrades conservatively: if stored rows do not have compatible chunk fingerprints or metadata, fall back to the existing file-level replacement behavior.
9. Keep line-window fallback chunks correct even when line shifts make their IDs unstable.

## Scope

**Problem statement:** A small edit in a large document or code file can trigger re-embedding for every chunk in that file, even when most chunk text is unchanged.

**In scope:**

- `.wavefoundry/framework/scripts/indexer.py`
- `.wavefoundry/framework/scripts/chunker.py` only if chunk fingerprint helpers belong near chunk serialization
- `.wavefoundry/framework/scripts/tests/test_indexer.py`
- `.wavefoundry/framework/scripts/tests/test_chunker.py` only if chunk serialization changes
- Architecture docs that describe incremental indexing behavior

**Out of scope:**

- Changing embedding models
- Changing semantic retrieval or reranking behavior
- Reworking graph extraction persistence
- Replacing LanceDB
- Making line-window chunk IDs fully stable for every insertion/deletion pattern

## Design Notes

The database should become the source of truth for "what was actually indexed" during incremental updates. For each stale path, the indexer can query the existing `docs` and/or `code` table rows by `path`, compare them against freshly generated chunks, and decide which rows need replacement.

The first implementation should optimize the stable-ID path:

- Markdown heading chunks such as `docs/foo.md#rationale`
- Markdown preamble chunks such as `docs/foo.md#preamble`
- Markdown summary chunks such as `docs/foo.md#doc-summary`
- Python and tree-sitter-backed symbol chunks such as `src/foo.py::Class.method`
- Code summary chunks such as `src/foo.py#summary`

Fallback line-window chunks need a more cautious path. If their IDs shift but the text hash is unchanged, reuse is desirable; if matching is ambiguous, correctness wins and the implementation should re-embed those chunks.

When a vector is reused for a chunk whose metadata changed, the row still needs to be rewritten with current metadata. Reuse applies to the embedding vector, not necessarily to the old row as a whole. This matters for line-window chunks with shifted line ranges and for any stable text whose `lines`, `section`, or generated chunk ID changes after rechunking.

## Acceptance Criteria

- [x] AC-1: Incremental indexing reads existing chunk rows for stale paths and compares them with freshly generated chunks before embedding.
- [x] AC-2: Unchanged chunks with compatible IDs and chunk fingerprints keep their existing vectors and are not sent through the embedder again.
- [x] AC-3: Added or changed chunks are embedded and written with current row metadata.
- [x] AC-4: Removed chunks are deleted from the LanceDB table.
- [x] AC-5: The implementation bumps the relevant chunker/index schema version so existing LanceDB tables are rebuilt once with `chunk_hash` present on all rows before chunk-level delta reuse is used.
- [x] AC-6: The fallback path preserves current behavior when old rows lack chunk fingerprints, the model/chunker version is incompatible, or chunk matching is ambiguous.
- [x] AC-7: Reused vectors are written with current chunk metadata when the chunk text is unchanged but `id`, `lines`, `section`, or other row metadata changes.
- [x] AC-8: Tests cover a large Markdown file where editing one heading section re-embeds only that section plus any affected summary chunk.
- [x] AC-9: Tests cover a structure-aware code file where editing one function or method re-embeds only the affected symbol chunk plus any affected summary/doc chunks.
- [x] AC-10: Tests cover a single stale path that has rows in both `docs` and `code` tables, such as a Python source file with docstring chunks or a Markdown file with extracted fenced code.
- [x] AC-11: Tests cover a line-window fallback file where shifted line IDs do not corrupt the index; ambiguous matches must re-embed rather than reuse the wrong vector.
- [x] AC-12: Existing full rebuild behavior, FTS index refresh, table locking, and compaction semantics remain intact.

## Tasks

- [x] Define `chunk_hash` / fingerprint inputs and add it to new LanceDB rows.
- [x] Bump the relevant chunker/index schema version so old LanceDB row schemas are rebuilt before incremental reuse starts.
- [x] Add helpers to read existing rows by `path` from the docs/code tables.
- [x] Add chunk delta classification for unchanged, changed, added, and removed chunks.
- [x] Update the incremental write path to delete only removed/changed rows and add reused/new rows as needed, rewriting current metadata even when the vector is reused.
- [x] Preserve a conservative fallback to the existing delete-all-for-path behavior.
- [x] Add focused tests for Markdown heading chunks, symbol code chunks, mixed docs/code table paths, and line-window fallback behavior.
- [x] Update architecture documentation for chunk-level incremental indexing.

## Agent Execution Graph

| Workstream | Owner | Depends On | Notes |
| --- | --- | --- | --- |
| delta design | implementer | current indexer contract | Define fingerprint and matching rules before code changes |
| LanceDB read/write plumbing | implementer | delta design | Query current rows by path, handle schema rebuild, and write partial replacements safely |
| tests | qa-reviewer | implementation | Verify embedder call counts and correctness across docs/code/fallback chunks |
| architecture docs | docs-contract-reviewer | implementation | Document the updated incremental indexing behavior |

## Serialization Points

- `.wavefoundry/framework/scripts/indexer.py`
- LanceDB row schema compatibility
- Chunker/index schema version bump and one-time table rebuild behavior
- FTS index refresh after incremental row changes
- Tests that patch or fake embedding calls

## Affected Architecture Docs

Update `docs/architecture/chunking-and-indexing-pipeline.md` and `docs/architecture/search-architecture.md` to describe chunk-level reuse during incremental indexing. Update `docs/architecture/data-and-control-flow.md` if the write path description currently implies file-level replacement only.

## AC Priority

(Populated at Prepare wave.)

| AC | Priority | Rationale |
| --- | --- | --- |
| AC-1 | required | The improvement depends on comparing existing indexed rows before embedding |
| AC-2 | required | Vector reuse is the core performance win |
| AC-3 | required | Changed content must still become searchable |
| AC-4 | required | Removed content must not remain in search results |
| AC-5 | required | The new row schema must be present consistently before incremental reuse depends on it |
| AC-6 | required | Backward compatibility and correctness must beat optimization |
| AC-7 | required | Reusing vectors must not leave stale line ranges or chunk metadata in search results |
| AC-8 | important | Markdown is the main observed churn case |
| AC-9 | important | Symbol-structured code should benefit from stable chunk IDs |
| AC-10 | required | A single path can contribute rows to both semantic tables |
| AC-11 | required | Line-window fallback is the main corruption risk |
| AC-12 | required | The existing index maintenance contract must stay intact |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-28 | Planned after observing large graph/index rebuild costs and confirming semantic indexing currently replaces all chunks for a changed file. | `indexer.py` changed-file flow and LanceDB incremental write path |
| 2026-05-28 | Implemented chunk-level delta embedding with `chunk_hash`, CHUNKER_VERSION `22`, current-metadata vector reuse, conservative fallback, and architecture updates. | `python -B .wavefoundry/framework/scripts/run_tests.py` passed: 1712 tests across 22 files |

## Decision Log

| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
| 2026-05-28 | Use the existing LanceDB rows as the source of truth for current chunks during incremental updates. | The table already stores chunk IDs and text, so a separate chunk cache would duplicate state. | Maintain a parallel chunk manifest — rejected as extra drift risk |
| 2026-05-28 | Optimize stable-ID chunks first and treat ambiguous fallback chunks conservatively. | Markdown heading chunks and symbol chunks should cover the common case; line-window chunks can churn under line shifts. | Attempt fuzzy reuse for every chunk shape immediately — deferred to avoid wrong-vector reuse |
| 2026-05-28 | Bump the chunker/index schema version to force a one-time rebuild when `chunk_hash` is introduced. | LanceDB row schema should not mix old rows without `chunk_hash` and new rows with it; a rebuild makes the new column consistently available. | Incrementally add `chunk_hash` only for changed files — rejected because it leaves table schema and row compatibility ambiguous |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Reusing a vector for the wrong chunk would corrupt retrieval silently | Require matching ID plus fingerprint for normal reuse; only use text-hash fallback when unambiguous |
| Old LanceDB rows may not have the new fingerprint field | Bump the relevant version so existing tables rebuild once with the new field before reuse is enabled |
| Partial row updates could leave stale chunks if deletes are too narrow | Test removed, changed, and renamed chunks explicitly |
| FTS index may become stale after partial writes | Preserve the existing FTS refresh call after incremental writes |
| Summary chunks may change when a small edit affects headings or symbol lists | Treat summaries as normal chunks and re-embed them when their fingerprint changes |
| Reused vectors could preserve stale row metadata | Rewrite rows with current chunk metadata even when the vector itself is reused |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
