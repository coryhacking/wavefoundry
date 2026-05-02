# Indexer Stat Cache for Incremental Change Detection

Change ID: `12b1a-enh indexer-stat-cache-change-detection`
Change Status: `complete`
Owner: Engineering
Status: complete
Last verified: 2026-05-01
Wave: `12axj chunker-and-pack-improvements`

## Rationale

Every incremental index `update` currently reads and SHA-256s every file in the repo to detect changes (`_build_file_hashes`). On a large codebase this is O(Σ file_sizes) of I/O per update, even when nothing has changed. A two-tier stat cache — `os.stat()` first, SHA-256 only on mtime/size misses — reduces clean-tree update cost to O(n × stat), typically 10–100× faster.

## Requirements

1. The file metadata store must record `mtime`, `size`, and `sha256` per indexed path.
2. On incremental update, `stat()` every file before reading it. If both `mtime` and `size` match the stored values, treat the file as unchanged without computing a hash.
3. Only read and SHA-256 files whose `mtime` or `size` differs from stored values.
4. The stored hash remains the authoritative change signal — a file that passes the stat check is not re-chunked; a file that fails it is hashed, and re-chunked only if the hash also differs.
5. Backward compatibility: entries in the existing `file_hashes` dict (no `mtime`/`size`) must be treated as cache misses that fall through to a full hash on first upgrade pass. After that pass the new format is stored.
6. Full rebuilds (`mode=rebuild`) bypass the stat cache entirely and re-hash everything.
7. The metadata schema change must not break the existing `old_hashes` / `chunker_version` / `model_versions` keys.

## Scope

**Problem statement:** Incremental index updates read every file to compute SHA-256, making them slow on large repos even when nothing changed.

**In scope:**

- `indexer.py`: new `_build_file_stat_cache` / `_changed_files` helpers; update `_build_file_hashes` or replace with stat-cache-aware equivalent; update metadata serialisation to store `{hash, mtime, size}` per path
- Tests in `test_indexer.py` (or equivalent) covering: stat-cache hit skips hash, stat-cache miss triggers hash, mtime-only change triggers re-check, backward-compat with old hash-only entries

**Out of scope:**

- Directory-level mtime short-circuits
- Watcher / inotify integration

## Acceptance Criteria

- AC-1: On a clean incremental update (no files changed), no file is opened for reading — only `stat()` calls occur
- AC-2: A file with changed `mtime` or `size` is hashed; if the hash also differs it is re-chunked
- AC-3: A file with changed `mtime`/`size` but identical hash is not re-chunked (content-identical save/restore)
- AC-4: An index built with the old hash-only metadata format is read without error; affected files fall through to full hash on first update
- AC-5: Full rebuild (`mode=rebuild`) ignores the stat cache and re-processes all files
- AC-6: Metadata written after an update contains `mtime`, `size`, and `hash` for all indexed files
- AC-7: Existing tests continue to pass

## Tasks

- [x] Add `_stat_entry(path)` returning `(mtime, size, inode)` tuple — `inode=0` on Windows/FAT
- [x] Add `_stat_matches(old, mtime, size, inode)` — skips inode check when either value is 0
- [x] Replace incremental path with `_detect_changes(files, root, old_meta)` returning `(current_meta, changed_paths, removed_paths)` — stat pre-filter, hash only on miss
- [x] Full rebuild path populates stat cache entries `{hash, mtime, size, inode}` for future incremental passes
- [x] Metadata read/write uses `file_meta` key; backward-compat `file_hashes` key also written
- [x] Add `StatCacheTests` (5 tests): clean-pass skips `_sha256`, dirty detected, mtime-restore skips re-chunk, old-format compat, full-rebuild bypasses cache
- [x] Update `test_meta_records_file_hashes` → split into two tests asserting both `file_hashes` and `file_meta` with stat fields
- [x] 655 tests pass

## Agent Execution Graph

| Workstream      | Owner       | Depends On | Notes                              |
| --------------- | ----------- | ---------- | ---------------------------------- |
| stat-cache-impl | implementer | —          | indexer.py changes + tests         |

## Serialization Points

- `indexer.py` only — no shared file with other open changes in this wave

## Affected Architecture Docs

N/A — confined to `indexer.py` index pipeline internals; no boundary/flow/interface change visible to callers.

## AC Priority

| AC   | Priority  | Rationale                                              |
| ---- | --------- | ------------------------------------------------------ |
| AC-1 | required  | Core performance goal — no reads on clean pass         |
| AC-2 | required  | Correctness — dirty files must be detected             |
| AC-3 | important | Avoids unnecessary re-chunking on timestamp-only edits |
| AC-4 | required  | Backward compat — existing indexes must not break      |
| AC-5 | required  | Full rebuild must remain authoritative                 |
| AC-6 | required  | New metadata format must be persisted correctly        |
| AC-7 | required  | No regressions                                         |

## Progress Log

| Date | Update | Evidence |
| ---- | ------ | -------- |
| 2026-05-01 | Implemented `_stat_entry`, `_stat_matches`, `_detect_changes`; updated full-rebuild path to populate stat cache; added 5 `StatCacheTests`; 655 tests pass | `indexer.py`, `test_indexer.py` |
| 2026-05-01 | Added inode to stat tuple after user request; `_stat_matches` treats inode=0 as "don't check" for Windows/FAT compat | `indexer.py:170-188` |

## Decision Log

| Date       | Decision | Reason | Alternatives |
| ---------- | -------- | ------ | ------------ |
| 2026-05-01 | Use mtime+size as stat pre-filter, not mtime alone | Size catches same-timestamp overwrites (e.g. truncation); together they match git's index fast-path | mtime-only (faster but misses same-second overwrites) |
| 2026-05-01 | Include inode as optional third check | Catches hard-link swaps and inode-replacing editors; `inode=0` on Windows/FAT → check skipped safely | Omit inode entirely (simpler but misses editor-inode-replace pattern on macOS/Linux) |
| 2026-05-01 | Keep SHA-256 as authoritative signal | mtime can be unreliable after git checkout, rsync, or touch; hash is the correctness backstop | mtime-only with no hash fallback (faster but wrong in edge cases) |

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| mtime precision on FAT/some network filesystems (1-2s resolution) | Hash is still checked on stat miss; worst case is a few extra reads, not incorrect results |
| Metadata format migration breaks CI with cached old-format index | Backward-compat requirement (AC-4): old `file_hashes` entries treated as cache misses, silently upgraded on first pass |

## Session Handoff

See `docs/agents/session-handoff.md` for current session state.
