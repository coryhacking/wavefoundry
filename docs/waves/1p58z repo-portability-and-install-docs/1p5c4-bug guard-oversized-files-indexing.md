# Guard the indexer against pathologically large files

Change ID: `1p5c4-bug guard-oversized-files-indexing`
Change Status: `implemented`
Owner: Engineering
Status: implemented
Last verified: 2026-06-13
Wave: `1p58z repo-portability-and-install-docs`

## Rationale

Field report: a user had a ~1 GB SQL backup in their repo and indexing spun for a long time — the agent traced it to **tree-sitter**, not embedding. The cause: there is no file-size guard anywhere in the indexing path. `walk_repo` only sniffs the first 8 KB for binary magic-bytes, so a large text-ish file passes, is **fully read into memory**, and handed to tree-sitter (`_ts_parse` in *both* the chunker and `graph_indexer`). Building a full AST over ~1 GB is the spin. `MAX_CHUNK_CHARS` doesn't help — it only truncates *after* the read + parse.

## Requirements

1. **Hard size skip** at `walk_repo`: a `stat`-based check (no read) drops files over a threshold from the index entirely, logged once. This single chokepoint feeds both the semantic and graph indexers, so the 1 GB file is never read or parsed.
2. **Tree-sitter parse cap** in both `_ts_parse` sites (chunker + `graph_indexer`): a file over a smaller byte cap skips the AST parse and degrades gracefully — the chunker falls back to regex/line chunking (still indexed as text); graph extraction is skipped for that file. Reuses the existing `_ts_parse → None` fallback path.
3. **Fixed defaults, operator-tunable**: hard cap default ~5 MB (`indexing.max_file_bytes`), tree-sitter cap default ~2 MB (`indexing.max_treesitter_parse_bytes`) in `docs/workflow-config.json`; `0` disables a cap. The indexer resolves the TS cap and publishes it via `WAVEFOUNDRY_MAX_TS_PARSE_BYTES` so the chunker/graph extractor see it in-process or as a subprocess.
4. The `graph_indexer` extraction change (oversized files now contribute no nodes) **bumps `GRAPH_BUILDER_VERSION`** so previously-parsed large files re-extract and their stale nodes prune.

## Scope

**Problem statement:** a single very large file (e.g. a SQL backup) read + tree-sitter-parsed during indexing spins the indexer for a long time; there is no size guard.

**In scope:**

- `walk_repo` hard-skip + a config resolver in `indexer.py`; the TS-parse cap in `chunker._ts_parse` and `graph_indexer._ts_parse`; the env publish from `build_index`; `GRAPH_BUILDER_VERSION` bump.
- Tests (indexer walk-skip + override, chunker cap + fallback, graph cap + version), pipeline-doc note.

**Out of scope:**

- Streaming/partial indexing of large files (they are skipped or text-only, not chunked-by-streaming).
- The other changes in this wave.

## Acceptance Criteria

- [x] AC-1: `walk_repo` skips files over `indexing.max_file_bytes` (default 5 MB) before any read; verified by `test_walk_repo_skips_oversized_files` + the `0`-disables-cap and default-keeps-normal tests.
- [x] AC-2: `chunker._ts_parse` and `graph_indexer._ts_parse` return `None` for sources over `indexing.max_treesitter_parse_bytes` (default 2 MB, via `WAVEFOUNDRY_MAX_TS_PARSE_BYTES`); oversized code still chunks via the fallback (`test_chunk_file_falls_back_on_oversized_code`).
- [x] AC-3: thresholds resolve from `docs/workflow-config.json` with defaults; `0` disables.
- [x] AC-4: `GRAPH_BUILDER_VERSION` bumped 29 → 30; the version test updated.
- [x] AC-5: full framework suite + docs-lint green; pipeline doc documents the guards.

## Tasks

- [x] `indexer.py`: size-limit constants + `_resolve_index_size_limits`; `walk_repo` hard-skip (logged); publish `WAVEFOUNDRY_MAX_TS_PARSE_BYTES` in `build_index`.
- [x] `chunker.py` + `graph_indexer.py`: TS-parse cap in `_ts_parse`; bump `GRAPH_BUILDER_VERSION`.
- [x] Tests across `test_indexer`/`test_chunker`/`test_graph_indexer`; document in `chunking-and-indexing-pipeline.md`.

## Agent Execution Graph


| Workstream     | Owner  | Depends On   | Notes |
| -------------- | ------ | ------------ | ----- |
| [workstream-1] | [role] | —            |       |
| [workstream-2] | [role] | workstream-1 |       |


## Serialization Points

- [Shared file or integration gate that requires coordination before parallel work proceeds]

## Affected Architecture Docs

Updated `docs/architecture/chunking-and-indexing-pipeline.md` (Stage 1: File Discovery) to document the hard size guard + the tree-sitter parse cap and their config keys. No ADR needed (behavior guard, no boundary/contract change).

## AC Priority

| AC   | Priority  | Rationale |
| ---- | --------- | --------- |
| AC-1 | required  | The hard skip is the actual fix for the 1 GB spin. |
| AC-2 | required  | The TS cap protects against large-but-under-hard-cap code files (the "especially code files" ask). |
| AC-3 | important | Operator-tunable defaults; sensible defaults are the main thing, override is the safety valve. |
| AC-4 | required  | A graph extractor output change must bump the builder version so caches converge. |
| AC-5 | required  | Suite + docs-lint green is the regression gate. |


## Progress Log


| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-06-13 | Implemented (operator feedback, folded into 1p58z): hard size skip in `walk_repo` + `_resolve_index_size_limits`; tree-sitter parse cap in `chunker._ts_parse` + `graph_indexer._ts_parse` via `WAVEFOUNDRY_MAX_TS_PARSE_BYTES` published from `build_index`; `GRAPH_BUILDER_VERSION` 29→30; tests in indexer/chunker/graph; pipeline-doc note. | suite 3095 OK; docs-lint ok |
| 2026-06-13 | Tree-sitter cap default 1.5 MB → **2 MB** (memory-bound: tree ≈ 150–200× file size, so 2 MB ≈ ~375 MB transient; per tree-sitter guidance there is no hard limit, editors just gate). | suite 3095 OK |
| 2026-06-14 | Follow-up (operator: "we shouldn't even be walking gitignored index files"): `walk_repo` now **prunes gitignored DIRECTORIES during traversal** (`_matches_ignore` on each dir), so `.wavefoundry/index/` (LanceDB shards), `.wavefoundry/logs/`, and `.wavefoundry/framework/index/` are never descended — previously the full rebuild stat'd hundreds of 33 MB shards and spammed the oversized-skip log. The hard size check also moved to AFTER the ignore filter so ignored blobs never log a skip. Regression test added. | suite 3096 OK; clean rebuild log (no shard skips) |


## Decision Log


| Date | Decision | Reason | Alternatives |
| ---- | -------- | ------ | ------------ |
|      |          |        |              |


## Risks


| Risk | Mitigation |
| ---- | ---------- |
|      |            |


## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
